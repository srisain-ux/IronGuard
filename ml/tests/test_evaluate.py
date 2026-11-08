"""Evaluation wiring: fit TRAIN only and freeze thresholds before TEST scoring."""

import json

import jsonschema
from test_baselines import conv

from ironguard_ml.data import ROOT
from ironguard_ml.evaluate import evaluate


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
