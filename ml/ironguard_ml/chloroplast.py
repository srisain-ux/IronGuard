"""Leaf Sheep chloroplast trainer (MODEL_SPEC §5.1): frozen PreyNet features → a tiny adapter head.

`train(pos, neg, family_id, label, alert, progress_cb)` returns a manifest that validates against
contracts/schemas/chloroplast.schema.json. Negatives = the caller's hard negatives + a bank of base
benign and other-family prefixes sampled from TRAIN (artifacts/negative_bank.npz, written by
`make export`). The threshold allows <= 1% conversation-level false alarms on a held-out 20% of
the negative conversations. `python -m ironguard_ml.chloroplast` prints a timing benchmark.
"""

import argparse
import base64
import hashlib
import logging
import math
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch import nn
from torch.nn import functional as F

from ironguard_ml.data import DATA_DIR, ROOT, Conversation, _parse, read_records
from ironguard_ml.features import (
    CACHE_DIR,
    Encoder,
    minilm_encoder,
    prefix_sequence,
    turn_vectors,
)
from ironguard_ml.preynet import FEATURE_DIM, PreyNet, load_net, pack

HIDDEN_DIM = 32
STEPS = 300
LR = 3e-3
WEIGHT_DECAY = 1e-4
HOLDOUT = 0.2  # share of negative (and positive) conversations held out for threshold + metrics
TARGET_FPR = 0.01
HALF_LIFE_HOURS = 72
MIN_CONVERSATIONS = 5  # per side, so the 20% hold-out is never empty
BANK_BENIGN, BANK_OTHER = 1000, 500  # §5.1 base negatives
PROGRESS_EVERY = 10
CHUNK = 1024
ARTIFACTS = ROOT / "ml/artifacts"
BANK_FILE = "negative_bank.npz"
WEIGHT_ORDER = ("w1", "b1", "w2", "b2")

log = logging.getLogger(__name__)
ProgressCb = Callable[[int, int, float], None]


@dataclass(frozen=True)
class Base:
    """Frozen feature extractor + its bank of base negative prefix features."""

    net: PreyNet
    bank: np.ndarray  # (n, 640) float32
    bank_groups: np.ndarray  # (n,) source conversation per row (for the conversation hold-out)
    encoder: Encoder | None = None  # None = MiniLM
    cache_dir: Path | None = None  # None = embed in memory only (API jobs)


def conversation_features(net: PreyNet, convs: Sequence[Conversation], encoder=None,
                          cache_dir: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(640-d features of every prefix k = 1..n of every conversation, conversation index per row)."""
    lengths = [len(c.turns) for c in convs]
    vectors = turn_vectors([t for c in convs for t in c.turns], encoder, cache_dir)
    seqs, groups, start = [], [], 0
    for i, n in enumerate(lengths):
        seqs += [prefix_sequence(vectors[start:start + n], k) for k in range(1, n + 1)]
        groups += [i] * n
        start += n
    net.eval()
    with torch.no_grad():
        parts = [net(*pack(seqs[i:i + CHUNK]))["features"] for i in range(0, len(seqs), CHUNK)]
    return torch.cat(parts).numpy(), np.array(groups, dtype=np.int64)


def build_negative_bank(net: PreyNet, train: Sequence[Conversation], encoder=None,
                        cache_dir: Path | None = CACHE_DIR, seed: int = 0,
                        exclude_ids: frozenset[str] = frozenset()):
    """(features, groups) of random WHOLE TRAIN conversations: ~1,000 benign + ~500 other-family
    prefixes. Whole conversations keep the hold-out's per-conversation max p a true maximum.
    `exclude_ids` keeps the caller's own negatives out, so no conversation gets two group ids."""
    rng = np.random.default_rng(seed)
    picked = []
    for is_benign, target in ((True, BANK_BENIGN), (False, BANK_OTHER)):
        pool = [c for c in train if (c.family == "benign") == is_benign and c.id not in exclude_ids]
        total = 0
        for i in rng.permutation(len(pool)):
            if total >= target:
                break
            picked.append(pool[i])
            total += len(pool[i].turns)
    return conversation_features(net, picked, encoder, cache_dir)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_bank(artifacts: Path, features: np.ndarray, groups: np.ndarray) -> Path:
    path = artifacts / BANK_FILE
    np.savez(path, features=features.astype(np.float32), groups=groups,
             preynet_sha256=_sha256_file(artifacts / "preynet.pt"))
    return path


@lru_cache(maxsize=2)
def load_base(artifacts: Path = ARTIFACTS) -> Base:
    """The shipped PreyNet + its negative bank; refuses a bank built for different weights."""
    bank_path = artifacts / BANK_FILE
    if not bank_path.exists():
        raise FileNotFoundError(f"missing {bank_path} (run `make export`)")
    with np.load(bank_path) as bank:
        if str(bank["preynet_sha256"]) != _sha256_file(artifacts / "preynet.pt"):
            raise ValueError(f"{bank_path} was built for other PreyNet weights (run `make export`)")
        return Base(load_net(artifacts), bank["features"], bank["groups"])


def _parse_all(name: str, records) -> list[Conversation]:
    if not isinstance(records, list | tuple) or len(records) < MIN_CONVERSATIONS:
        raise ValueError(f"{name} needs at least {MIN_CONVERSATIONS} conversations")
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"{name}[{i}] must be a conversation dict")
    return [_parse(r, f"{name}[{i}]") for i, r in enumerate(records)]


def _validate(family_id, label, alert, progress_cb) -> None:
    if not isinstance(family_id, str) or not re.fullmatch(r"zd_[a-z0-9_]+", family_id):
        raise ValueError("family_id must match zd_[a-z0-9_]+")
    if not isinstance(label, str) or not 0 < len(label) <= 80:
        raise ValueError("label must be a non-empty string of at most 80 characters")
    if not isinstance(alert, str) or not 0 < len(alert) <= 400:
        raise ValueError("alert must be a non-empty string of at most 400 characters")
    if progress_cb is not None and not callable(progress_cb):
        raise ValueError("progress_cb must be callable")


def _holdout(groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    unique = np.unique(groups)
    held = rng.choice(unique, max(1, round(HOLDOUT * len(unique))), replace=False)
    return np.isin(groups, held)


def _group_max(p: np.ndarray, groups: np.ndarray) -> np.ndarray:
    return np.array([p[groups == g].max() for g in np.unique(groups)], dtype=np.float32)


def threshold_at_fpr(negative_maxima: np.ndarray, target: float = TARGET_FPR) -> float:
    """Lowest float32 threshold with <= target of the negative conversations at p >= threshold.

    Same rule as metrics.threshold_at_fpr, but stepped in float32: consumers compare float32 p.
    Raises if the cap needs a threshold above 1 (negatives saturate at p = 1): such an adapter
    would fire on them, so it must not be published.
    """
    maxima = np.sort(np.asarray(negative_maxima, dtype=np.float32))
    allowed = math.floor(target * len(maxima))
    above = float(np.nextafter(maxima[len(maxima) - allowed - 1], np.float32(np.inf)))
    if above > 1:
        raise ValueError("chloroplast cannot reach 1% FPR on held-out negatives (p saturates at "
                         "1); generate more varied positives or hard negatives")
    return above


def _fit(pos: np.ndarray, neg: np.ndarray, seed: int, progress_cb: ProgressCb | None) -> nn.Module:
    x = torch.from_numpy(np.concatenate([pos, neg]))
    y = torch.cat([torch.ones(len(pos)), torch.zeros(len(neg))])
    with torch.random.fork_rng(devices=[]):  # deterministic init without touching global RNG
        torch.manual_seed(seed)
        head = nn.Sequential(nn.Linear(FEATURE_DIM, HIDDEN_DIM), nn.GELU(), nn.Linear(HIDDEN_DIM, 1))
    opt = torch.optim.AdamW(head.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    pos_weight = torch.tensor(len(neg) / len(pos))  # weighted BCE balances the classes
    for step in range(1, STEPS + 1):
        opt.zero_grad()
        loss = F.binary_cross_entropy_with_logits(head(x).squeeze(1), y, pos_weight=pos_weight)
        loss.backward()
        opt.step()
        if progress_cb is not None and (step % PROGRESS_EVERY == 0 or step == STEPS):
            progress_cb(step, STEPS, loss.item())
    return head.eval()


def _probs(head: nn.Module, features: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        return torch.sigmoid(head(torch.from_numpy(features)).squeeze(1)).numpy()


def train(pos, neg, family_id, label, alert, progress_cb: ProgressCb | None = None, *,
          base: Base | None = None, seed: int = 0) -> dict:
    """Train one chloroplast. `base` (keyword-only) swaps in another frozen PreyNet + bank (LOFO)."""
    start = time.perf_counter()
    _validate(family_id, label, alert, progress_cb)
    pos_convs, neg_convs = _parse_all("pos", pos), _parse_all("neg", neg)
    base = base or load_base()
    pos_f, pos_g = conversation_features(base.net, pos_convs, base.encoder, base.cache_dir)
    hard_f, hard_g = conversation_features(base.net, neg_convs, base.encoder, base.cache_dir)
    neg_f = np.concatenate([hard_f, base.bank])
    embedded = time.perf_counter()

    # Hold out 20% of conversations per source, so both get their own 1% cap: the threshold must
    # hold on the caller's hard negatives too, not just on the larger base bank.
    rng = np.random.default_rng(seed)
    pos_held = _holdout(pos_g, rng)
    hard_held, bank_held = _holdout(hard_g, rng), _holdout(base.bank_groups, rng)
    head = _fit(pos_f[~pos_held], neg_f[~np.r_[hard_held, bank_held]], seed, progress_cb)
    pos_max = _group_max(_probs(head, pos_f[pos_held]), pos_g[pos_held])
    hard_max = _group_max(_probs(head, hard_f[hard_held]), hard_g[hard_held])
    bank_max = _group_max(_probs(head, base.bank[bank_held]), base.bank_groups[bank_held])
    threshold = max(threshold_at_fpr(hard_max), threshold_at_fpr(bank_max))
    neg_max = np.r_[hard_max, bank_max]

    raw = {k: p.detach().numpy().astype("<f4").tobytes()
           for k, p in zip(WEIGHT_ORDER, head.parameters(), strict=True)}
    packed = b"".join(raw[k] for k in WEIGHT_ORDER)
    sha = hashlib.sha256(packed).hexdigest()
    seconds = time.perf_counter() - start
    log.info("chloroplast %s: features %.2fs, fit+threshold %.2fs, total %.2fs",
             family_id, embedded - start, seconds - (embedded - start), seconds)
    return {
        "id": f"cp_{family_id[3:]}_{sha[:8]}", "family_id": family_id,
        "label": label, "alert": alert,
        "created_at": datetime.now(UTC).isoformat(),
        "half_life_hours": HALF_LIFE_HOURS, "feature_dim": FEATURE_DIM, "hidden_dim": HIDDEN_DIM,
        "weights": {k: base64.b64encode(v).decode("ascii") for k, v in raw.items()},
        "threshold": threshold,
        "metrics": {
            "n_pos": len(pos_convs), "n_neg": len(neg_convs), "train_seconds": round(seconds, 3),
            "val_auc": float(roc_auc_score(np.r_[np.ones(len(pos_max)), np.zeros(len(neg_max))],
                                           np.r_[pos_max, neg_max])),
            "val_recall_at_1fpr": float((pos_max >= threshold).mean()),
        },
        "size_bytes": len(packed), "sha256": sha,
    }


def main():
    """Timing benchmark on v1 data with the shipped artifacts and real MiniLM (no disk cache)."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--n", type=int, default=120, help="positives and hard negatives each")
    args = parser.parse_args()
    records = read_records(DATA_DIR / "generated" / "v1")
    pos = [r for r in records if r["family"] == "job_task"][:args.n]
    neg = [r for r in records if r.get("hard_negative")][:args.n]
    load_base()
    minilm_encoder()  # model load is a one-time server start-up cost, not per-chloroplast
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    manifest = train(pos, neg, "zd_bench", "Benchmark", "Timing benchmark only.")
    print(f"{len(pos)} pos / {len(neg)} neg conversations: train_seconds "
          f"{manifest['metrics']['train_seconds']} (budget 10 s), {manifest['size_bytes']} bytes, "
          f"threshold {manifest['threshold']:.4f}")


if __name__ == "__main__":
    main()
