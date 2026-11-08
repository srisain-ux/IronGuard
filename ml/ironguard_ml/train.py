"""Multi-task PreyNet training (MODEL_SPEC §4.3–§4.5): TRAIN fits, VAL early-stops and calibrates.

`make train` trains seeds 0/1/2, ships the best VAL EWR@2 seed to artifacts/preynet.pt and
writes VAL-fitted temperatures to artifacts/temperature.json. TEST is never read here.
"""

import argparse
import copy
import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from ironguard_ml.calibrate import fit_temperature
from ironguard_ml.data import (
    DATA_DIR,
    FAMILIES,
    ROOT,
    STAGES,
    TTS_BUCKETS,
    Conversation,
    make_prefixes,
    prepare_splits,
)
from ironguard_ml.features import mean_turn_embedding, prefix_sequence, turn_vectors
from ironguard_ml.metrics import ScoredConversation, ewr_at_k, threshold_at_fpr
from ironguard_ml.preynet import PreyNet, pack

SEEDS = (0, 1, 2)
LR, WEIGHT_DECAY, BATCH_SIZE, MAX_EPOCHS, PATIENCE = 2e-3, 1e-4, 64, 20, 5
AUX_WEIGHT = 0.5  # next_stage and tts loss weights (§4.4)
EARLY_STOP_K = 2
BENIGN = FAMILIES.index("benign")
VERSION = "0.1.0"


@dataclass(frozen=True)
class Variant:
    use_attention: bool = True
    multitask: bool = True


VARIANTS = {
    "PreyNet": Variant(),
    "PreyNet_no_attention": Variant(use_attention=False),
    "PreyNet_no_multitask": Variant(multitask=False),
}


@dataclass(frozen=True)
class PrefixData:
    """Every prefix of every conversation, in conversation order then k = 1..n."""

    conversations: tuple[Conversation, ...]
    x: torch.Tensor
    mask: torch.Tensor
    family: torch.Tensor
    stage: torch.Tensor
    tts: torch.Tensor
    tts_mask: torch.Tensor  # early scam prefixes + benign ("none"); post-strike prefixes excluded


def encode(conversations: Sequence[Conversation], vectors=turn_vectors) -> PrefixData:
    seqs, family, stage, tts, tts_mask = [], [], [], [], []
    for conv in conversations:
        turn_vecs = vectors(conv.turns)
        for p in make_prefixes(conv):
            seqs.append(prefix_sequence(turn_vecs, p.k))
            family.append(FAMILIES.index(p.family))
            stage.append(STAGES.index(p.next_stage))
            tts.append(TTS_BUCKETS.index(p.tts))
            tts_mask.append(p.early or p.family == "benign")
    x, mask = pack(seqs)
    return PrefixData(tuple(conversations), x, mask, torch.tensor(family), torch.tensor(stage),
                      torch.tensor(tts), torch.tensor(tts_mask, dtype=torch.bool))


def class_weights(labels: torch.Tensor, n_classes: int) -> torch.Tensor:
    """Inverse frequency, mean 1 over the classes present; absent classes get 0."""
    counts = torch.bincount(labels, minlength=n_classes).float()
    present = counts > 0
    weights = torch.zeros(n_classes)
    weights[present] = counts.sum() / (present.sum() * counts[present])
    return weights


@torch.no_grad()
def predict(net: PreyNet, data: PrefixData, chunk: int = 1024) -> dict[str, torch.Tensor]:
    net.eval()
    parts = [net(data.x[i:i + chunk], data.mask[i:i + chunk]) for i in range(0, len(data.x), chunk)]
    return {key: torch.cat([p[key] for p in parts]) for key in parts[0]}


def risks(family_logits: torch.Tensor, temperature: float = 1.0) -> np.ndarray:
    """risk = 1 - P(benign) (§4.5)."""
    probs = torch.softmax(family_logits / temperature, dim=1)
    return np.clip(1 - probs[:, BENIGN].numpy(), 0.0, 1.0)


def per_conversation(conversations: Sequence[Conversation], values: np.ndarray) -> list[np.ndarray]:
    bounds = np.cumsum([0] + [len(c.turns) for c in conversations])
    return [values[a:b] for a, b in itertools.pairwise(bounds)]


def scored(conversations: Sequence[Conversation], risk: np.ndarray) -> list[ScoredConversation]:
    return [ScoredConversation(c, tuple(map(float, r)))
            for c, r in zip(conversations, per_conversation(conversations, risk), strict=True)]


def _loss(out, data: PrefixData, idx, weights, multitask: bool) -> torch.Tensor:
    loss = F.cross_entropy(out["family_logits"], data.family[idx], weight=weights["family"])
    if not multitask:
        return loss
    loss = loss + AUX_WEIGHT * F.cross_entropy(out["stage_logits"], data.stage[idx],
                                               weight=weights["stage"])
    m = data.tts_mask[idx]
    if m.any():
        loss = loss + AUX_WEIGHT * F.cross_entropy(out["tts_logits"][m], data.tts[idx][m],
                                                   weight=weights["tts"])
    return loss


def val_ewr(net: PreyNet, val: PrefixData) -> tuple[float, float]:
    """(VAL EWR@2 at the VAL 1%-FPR threshold, VAL family NLL) for early stopping."""
    logits = predict(net, val)["family_logits"]
    rows = scored(val.conversations, risks(logits))
    ewr = ewr_at_k(rows, threshold_at_fpr(rows), EARLY_STOP_K)
    return (ewr or 0.0), float(F.cross_entropy(logits, val.family))


@dataclass(frozen=True)
class FitResult:
    net: PreyNet
    seed: int
    variant: Variant
    epoch: int
    val_ewr_at_2: float
    val_nll: float


def fit(train: PrefixData, val: PrefixData, seed: int, variant: Variant = VARIANTS["PreyNet"]) -> FitResult:
    """Train on TRAIN prefixes; keep the epoch with the best VAL EWR@2 (ties: lower VAL NLL)."""
    torch.manual_seed(seed)
    generator = torch.Generator().manual_seed(seed)
    net = PreyNet(use_attention=variant.use_attention)
    optimizer = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    weights = {
        "family": class_weights(train.family, len(FAMILIES)),
        "stage": class_weights(train.stage, len(STAGES)),
        "tts": class_weights(train.tts[train.tts_mask], len(TTS_BUCKETS)),
    }
    best, best_key, best_epoch, stale = None, None, 0, 0
    for epoch in range(1, MAX_EPOCHS + 1):
        net.train()
        for idx in torch.randperm(len(train.x), generator=generator).split(BATCH_SIZE):
            loss = _loss(net(train.x[idx], train.mask[idx]), train, idx, weights, variant.multitask)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        ewr, nll = val_ewr(net, val)
        if best_key is None or (ewr, -nll) > best_key:
            best, best_key, best_epoch, stale = copy.deepcopy(net.state_dict()), (ewr, -nll), epoch, 0
        else:
            stale += 1
            if stale >= PATIENCE:
                break
    net.load_state_dict(best)
    net.eval()
    return FitResult(net, seed, variant, best_epoch, best_key[0], -best_key[1])


def best_of(fits: Sequence[FitResult]) -> FitResult:
    return max(fits, key=lambda f: (f.val_ewr_at_2, -f.val_nll))


def temperatures(net: PreyNet, val: PrefixData) -> dict[str, float]:
    """One temperature per head, fit on VAL only (§4.5)."""
    out = predict(net, val)
    return {
        "family": fit_temperature(out["family_logits"], val.family),
        "next_stage": fit_temperature(out["stage_logits"], val.stage),
        "tts": fit_temperature(out["tts_logits"][val.tts_mask], val.tts[val.tts_mask]),
    }


def load_splits(data: Path):
    """(splits, near-duplicate ids, version) for data/seed or data/generated/<version>."""
    data = data.resolve()
    if data == DATA_DIR / "seed":
        version = None
    elif data.parent == DATA_DIR / "generated":
        version = data.name
        if not data.exists() and version == "v1":
            print("v1 unavailable; using the seed smoke fixture (not pitch evidence)")
            version = None
    else:
        raise ValueError("--data must be data/seed or data/generated/<version>")
    splits, dropped = prepare_splits(version, mean_turn_embedding, seed=0)
    return splits, dropped, version


def save(fit_result: FitResult, temps: dict, out_dir: Path, dataset: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"version": f"{VERSION}-{dataset}-s{fit_result.seed}", "seed": fit_result.seed,
            "epoch": fit_result.epoch, "val_ewr_at_2": fit_result.val_ewr_at_2,
            "dataset": dataset, "trained_at": datetime.now(UTC).isoformat()}
    torch.save({"state_dict": fit_result.net.state_dict(), "config": fit_result.net.config,
                "meta": meta}, out_dir / "preynet.pt")
    (out_dir / "temperature.json").write_text(json.dumps(temps, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_DIR / "generated" / "v1")
    parser.add_argument("--out", type=Path, default=ROOT / "ml/artifacts")
    args = parser.parse_args()
    try:
        splits, _, version = load_splits(args.data)
    except ValueError as exc:
        parser.error(str(exc))
    train, val = encode(splits["train"]), encode(splits["val"])
    fits = []
    for seed in SEEDS:
        fits.append(fit(train, val, seed))
        f = fits[-1]
        print(f"seed {seed}: best epoch {f.epoch}, VAL EWR@2 {f.val_ewr_at_2:.3f}, "
              f"VAL NLL {f.val_nll:.3f}")
    best = best_of(fits)
    temps = temperatures(best.net, val)
    save(best, temps, args.out, version or "seed-smoke")
    print(f"Wrote {args.out / 'preynet.pt'} (seed {best.seed}) and temperature.json {temps}")


if __name__ == "__main__":
    main()
