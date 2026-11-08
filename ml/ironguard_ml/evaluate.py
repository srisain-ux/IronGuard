"""Run B0–B3: TRAIN fitting, VAL-only thresholds, TEST reporting (§6.4).

`make eval` works before v1 lands by falling back to the seed smoke fixture.
Missing metrics are null; PreyNet/zero-day/calibration results are unavailable.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import jsonschema

from ironguard_ml.baselines import Baseline
from ironguard_ml.data import DATA_DIR, ROOT, prepare_splits
from ironguard_ml.features import mean_turn_embedding
from ironguard_ml.metrics import (
    ScoredConversation,
    benign_fpr,
    summarize,
    threshold_at_fpr,
)


def score(model, conversations):
    return [ScoredConversation(c, tuple(risks))
            for c, risks in zip(conversations, model.score(conversations), strict=True)]


def evaluate(splits: dict, dataset: dict) -> dict:
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
    availability = ({"available": False, "display": "--"}
                    if dataset.get("version") == "seed-smoke" else {"available": True})
    return {
        **availability,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": dataset,
        "models": models,
        "zero_day": None,
        "reliability": {"bins": [], "acc": [], "conf": []},
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
    if data == DATA_DIR / "seed":
        version = None
    elif data.parent == DATA_DIR / "generated":
        version = data.name
        if not data.exists() and version == "v1":
            print("v1 unavailable; evaluating seed smoke fixture (not pitch evidence)")
            version = None
    else:
        parser.error("--data must be data/seed or data/generated/<version>")
    splits, dropped = prepare_splits(version, mean_turn_embedding, seed=0)
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
                  "PreyNet, zero-day and calibration have not been evaluated.",
                  "abstains=true means the VAL FPR cap required a threshold above 1."],
    }
    result = evaluate(splits, dataset)
    schema = json.loads((ROOT / "contracts/schemas/metrics.schema.json").read_text())
    jsonschema.validate(result, schema)
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload)
    print(f"Wrote {args.out} ({dataset['version']}; splits {dataset['split_counts']})")


if __name__ == "__main__":
    main()
