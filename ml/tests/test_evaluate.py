"""Evaluation wiring: fit TRAIN only and freeze thresholds before TEST scoring."""

import json

import jsonschema
import numpy as np
from test_baselines import conv

from ironguard_ml.data import ROOT
from ironguard_ml.evaluate import evaluate, evaluate_preynet
from ironguard_ml.features import TURN_DIM


def test_val_only_threshold_and_summary_contract(monkeypatch):
    train = (conv([".1"]), conv([".9"], "job_task"))
    val = (conv([".2", ".4"]),)
    test = (conv([".7", ".9"], "job_task"), conv([".8"]))
    human = (conv([".6", ".9"], "job_task"),)
    fitted = []

    class FakeBaseline:
        def __init__(self, model_id):
            pass

        def fit(self, conversations):
            assert conversations is train
            fitted.append(conversations)
            return self

        def score(self, conversations):
            return [[float(t.text) for t in c.turns] for c in conversations]

    monkeypatch.setattr("ironguard_ml.evaluate.Baseline", FakeBaseline)
    splits = {"train": train, "val": val, "test": test, "test_human": human}
    result = evaluate(splits, {"version": "fixture"})
    assert result["available"] is True
    assert len(fitted) == 4
    assert set(result["models"]) == {"B0", "B1", "B2", "B3"}
    for metrics in result["models"].values():
        assert .4 < metrics["threshold"] < .6
        assert metrics["val_fpr"] == 0
        assert metrics["ewr_at_k"] == [1] * 6
        assert metrics["lead_time"] == 1
        assert metrics["hard_neg_fpr"] is None
        assert metrics["test_human"]["lead_time"] == 1
    changed = evaluate({**splits, "test": (conv(["0"]),), "test_human": ()}, {})
    for model_id in result["models"]:
        assert changed["models"][model_id]["threshold"] == result["models"][model_id]["threshold"]
    schema = json.loads((ROOT / "contracts/schemas/metrics.schema.json").read_text())
    jsonschema.validate(result, schema)
    json.dumps(result, allow_nan=False)
    smoke = evaluate(splits, {"version": "seed-smoke"})
    assert smoke["available"] is False
    assert smoke["display"] == "--"
    assert smoke["models"]["B0"]["ewr_at_k"] == [1] * 6
    jsonschema.validate(smoke, schema)


def fake_vectors(turns):
    # Scam turns mention "pay", so the fixture is learnable without the real encoder.
    rows = [np.random.default_rng(len(t.text)).normal(size=TURN_DIM) * .1 for t in turns]
    for row, t in zip(rows, turns):
        row[0] += 3.0 if "pay" in t.text else -3.0
    return np.stack(rows).astype(np.float32)


def test_preynet_val_only_selection_and_summary_shape(monkeypatch):
    monkeypatch.setattr("ironguard_ml.evaluate.SEEDS", (0, 1))
    split = lambda n: tuple(conv(["hi"] * (i % 3 + 1)) for i in range(n)) + tuple(
        conv(["hi", "pay now"], "job_task") for _ in range(n))
    splits = {"train": split(8), "val": split(4), "test": split(4), "test_human": ()}
    models, rel = evaluate_preynet(splits, fake_vectors)
    assert set(models) == {"PreyNet", "PreyNet_no_attention", "PreyNet_no_multitask"}
    keys = {"ewr_at_k", "lead_time", "lead_time_std", "strike_recall", "hard_neg_fpr",
            "ece_before", "ece_after", "flicker_rate", "flicker_rate_no_lock", "test_human", "seeds"}
    for entry in models.values():
        assert keys <= set(entry)
        assert len(entry["ewr_at_k"]) == 6 and len(entry["seeds"]) == 2
        assert entry["test_human"]["lead_time"] is None  # empty human set stays null
    assert rel["bins"] and len(rel["bins"]) == len(rel["acc"]) == len(rel["conf"])
    json.dumps(models, allow_nan=False)
    changed, _ = evaluate_preynet({**splits, "test": split(2)[:1]}, fake_vectors)
    assert [s["threshold"] for s in changed["PreyNet"]["seeds"]] == \
        [s["threshold"] for s in models["PreyNet"]["seeds"]]
