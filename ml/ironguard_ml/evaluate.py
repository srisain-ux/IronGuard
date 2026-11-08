"""Run B0–B3, PreyNet and its ablations: TRAIN fitting, VAL-only early stopping, temperatures
and thresholds, TEST reporting (§6.4).

`make eval` works before v1 lands by falling back to the seed smoke fixture.
Missing metrics are null; zero-day (LOFO) results are not produced here yet.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
import numpy as np
import torch

from ironguard_ml.baselines import Baseline
from ironguard_ml.calibrate import ece, reliability, top_label
from ironguard_ml.data import DATA_DIR, ROOT
from ironguard_ml.features import turn_vectors
from ironguard_ml.infer import THETA_LOCK, lock_states
from ironguard_ml.metrics import (
    ScoredConversation,
    benign_fpr,
    flicker_rate,
    summarize,
    threshold_at_fpr,
)
from ironguard_ml.train import (
    SEEDS,
    VARIANTS,
    FitResult,
    PrefixData,
    best_of,
    encode,
    fit,
    load_splits,
    per_conversation,
    predict,
    risks,
    scored,
    temperatures,
)

AVERAGED = ("lead_time", "strike_recall", "hard_neg_fpr", "ece_before", "ece_after",
            "flicker_rate", "flicker_rate_no_lock")


def score(model, conversations):
    return [ScoredConversation(c, tuple(risks))
            for c, risks in zip(conversations, model.score(conversations), strict=True)]


def _mean(values) -> float | None:
    return None if any(v is None for v in values) else float(np.mean(values))


def _run(result: FitResult, data: dict[str, PrefixData]) -> dict:
    """Calibrate and threshold on VAL, then report one seed on TEST and test_human."""
    temp = temperatures(result.net, data["val"])["family"]
    val_rows = scored(data["val"].conversations,
                      risks(predict(result.net, data["val"])["family_logits"], temp))
    threshold = threshold_at_fpr(val_rows)
    test = data["test"]
    logits = predict(result.net, test)["family_logits"]
    test_risk = risks(logits, temp)
    before = top_label(torch.softmax(logits, 1).numpy(), test.family.numpy())
    after = top_label(torch.softmax(logits / temp, 1).numpy(), test.family.numpy())
    convs = per_conversation(test.conversations, test_risk)
    human = data.get("test_human")
    human_rows = (scored(human.conversations,
                         risks(predict(result.net, human)["family_logits"], temp)) if human else [])
    return {
        **summarize(scored(test.conversations, test_risk), threshold),
        "threshold": threshold,
        "val_fpr": benign_fpr(val_rows, threshold),
        "ece_before": ece(*before),
        "ece_after": ece(*after),
        "flicker_rate": flicker_rate([lock_states(r.tolist(), [t.sender for t in c.turns])
                                      for c, r in zip(test.conversations, convs, strict=True)]),
        "flicker_rate_no_lock": flicker_rate([(r >= THETA_LOCK).tolist() for r in convs]),
        "test_human": summarize(human_rows, threshold),
        "reliability": reliability(*after),
    }


def _aggregate(fits: list[FitResult], runs: list[dict]) -> dict:
    """Mean over seeds (sample std for lead time); per-seed provenance kept for honesty."""
    lead = [r["lead_time"] for r in runs]
    return {
        "ewr_at_k": [_mean([r["ewr_at_k"][i] for r in runs]) for i in range(6)],
        **{key: _mean([r[key] for r in runs]) for key in AVERAGED},
        "lead_time_std": None if None in lead else float(np.std(lead, ddof=1)),
        "test_human": {
            "ewr_at_k": [_mean([r["test_human"]["ewr_at_k"][i] for r in runs]) for i in range(6)],
            **{key: _mean([r["test_human"][key] for r in runs])
               for key in ("lead_time", "strike_recall", "hard_neg_fpr")},
        },
        "seeds": [{"seed": f.seed, "epoch": f.epoch, "val_ewr_at_2": f.val_ewr_at_2,
                   "threshold": r["threshold"], "val_fpr": r["val_fpr"], "lead_time": r["lead_time"]}
                  for f, r in zip(fits, runs, strict=True)],
    }


def evaluate_preynet(splits: dict, vectors=turn_vectors) -> tuple[dict, dict]:
    """(model entries for PreyNet + ablations, reliability bins of the shipped seed)."""
    data = {name: encode(splits[name], vectors) for name in ("train", "val", "test")}
    if splits["test_human"]:
        data["test_human"] = encode(splits["test_human"], vectors)
    models, shipped_reliability = {}, None
    for name, variant in VARIANTS.items():
        fits = [fit(data["train"], data["val"], seed, variant) for seed in SEEDS]
        runs = [_run(f, data) for f in fits]
        models[name] = _aggregate(fits, runs)
        if name == "PreyNet":  # same selection rule as `make train`
            shipped_reliability = runs[fits.index(best_of(fits))]["reliability"]
    return models, shipped_reliability


def evaluate(splits: dict, dataset: dict, with_preynet: bool = False,
             vectors=turn_vectors) -> dict:
    models = {}
    for model_id in ("B0", "B1", "B2", "B3"):
        model = Baseline(model_id).fit(splits["train"])
        val = score(model, splits["val"])
        threshold = threshold_at_fpr(val)
        models[model_id] = {
            **summarize(score(model, splits["test"]), threshold),
            "threshold": threshold,
            "val_fpr": benign_fpr(val, threshold),
            "abstains": threshold > 1,
            "test_human": summarize(score(model, splits["test_human"]), threshold),
        }
    reliability_bins = {"bins": [], "acc": [], "conf": []}
    if with_preynet:
        preynet_models, reliability_bins = evaluate_preynet(splits, vectors)
        models.update(preynet_models)
    availability = ({"available": False, "display": "--"}
                    if dataset.get("version") == "seed-smoke" else {"available": True})
    return {
        **availability,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": dataset,
        "models": models,
        "zero_day": None,
        "reliability": reliability_bins,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_DIR / "generated" / "v1")
    parser.add_argument("--human", type=Path, default=DATA_DIR / "test_human")
    parser.add_argument("--out", type=Path, default=ROOT / "ml/artifacts/eval_summary.json")
    args = parser.parse_args()
    data = args.data.resolve()
    # --human preserves the Makefile interface; load_corpus isolates the fixed test-only set.
    if args.human.resolve() != DATA_DIR / "test_human":
        parser.error("--human must be the repository's test-only data/test_human directory")
    try:
        splits, dropped, version = load_splits(data)
    except ValueError as exc:
        parser.error(str(exc))
    dataset = {
        "version": version or "seed-smoke",
        "n_conversations": sum(len(splits[s]) for s in ("train", "val", "test")),
        "n_test": len(splits["test"]), "n_test_human": len(splits["test_human"]),
        "split_seed": 0, "split_counts": {s: len(c) for s, c in splits.items()},
        "split_denominators": {s: {
            "scam": sum(c.family != "benign" for c in rows),
            "benign": sum(c.family == "benign" for c in rows),
            "hard_negative": sum(c.hard_negative for c in rows),
        } for s, rows in splits.items()},
        "n_dropped_near_duplicates": len(dropped),
        "notes": ["Null metrics have no eligible conversations.",
                  "Strike recall uses prefix <= strike_turn literally (MODEL_SPEC §6.2).",
                  "Thresholds cap empirical benign VAL conversation FPR at 1%.",
                  "abstains=true means the VAL FPR cap required a threshold above 1.",
                  "PreyNet entries are means over seeds 0/1/2; lead_time_std is the sample std.",
                  "PreyNet temperatures, thresholds and early stopping use VAL only.",
                  ("ECE and reliability use the family head's top-label confidence on TEST "
                  "prefixes; reliability is the shipped seed (best VAL EWR@2)."),
                  ("flicker_rate: share of warned TEST conversations whose warning goes off and "
                  "back on (LockOn 0.70/0.40/2 turns vs risk >= 0.70 without lock-on)."),
                  "Lock-on is inference-only, so PreyNet without lock-on is flicker_rate_no_lock.",
                  "zero_day (LOFO) is not evaluated yet."],
    }
    result = evaluate(splits, dataset, with_preynet=True)
    schema = json.loads((ROOT / "contracts/schemas/metrics.schema.json").read_text())
    jsonschema.validate(result, schema)
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload)
    print(f"Wrote {args.out} ({dataset['version']}; splits {dataset['split_counts']})")


if __name__ == "__main__":
    main()
