import base64
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from ironguard_ml.stub import chloroplast_train, load

SCHEMAS = Path(__file__).resolve().parents[2] / "contracts" / "schemas"


def validate(value, name):
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(value)


@pytest.mark.parametrize("text,family", [
    ("Wrong number!", "pig_butchering"), ("BANK fraud alert", "bank_impersonation"),
    ("Mom, new phone", "family_emergency"), ("Your package toll", "toll_delivery"),
    ("Account suspended, code", "carrier_support"), ("A job task", "job_task"),
    ("See you soon", "benign"), ("decode the taskbar", "benign"),
])
def test_families(text, family):
    model = load("missing/artifacts")
    turns = [{"sender": "them", "text": text}]
    result = model.score(turns)
    validate(result, "score_response")
    assert result == model.score(turns)
    assert result["family"]["id"] == family
    assert result["locked"] == (result["risk"] >= 0.7)
    assert sum(result["family_probs"].values()) == pytest.approx(1)


def test_attention_evidence_and_empty_prefix():
    turns = [{"sender": "them", "text": "wrong number"}] * 5
    result = load(None).score(turns)
    assert result["attention"] == pytest.approx([1/15, 2/15, 3/15, 4/15, 5/15])
    assert len(result["evidence"]) == 3
    validate(result, "score_response")
    empty = load(None).score([])
    validate(empty, "score_response")
    assert empty["attention"] == []
    assert load(None).score([{"sender": "me", "text": "bank"}])["family"]["id"] == "benign"


def test_manifest_and_adapter_hits():
    progress = []
    manifest = chloroplast_train([{}], [{}, {}], "zd_parking", "Parking", "Boot alert",
                                 lambda *args: progress.append(args))
    validate(manifest, "chloroplast")
    weights = [base64.b64decode(manifest["weights"][key], validate=True)
               for key in ("w1", "b1", "w2", "b2")]
    assert [len(weight) for weight in weights] == [81920, 128, 128, 4]
    packed = b"".join(weights)
    assert not any(packed)
    assert len(packed) == manifest["size_bytes"]
    assert hashlib.sha256(packed).hexdigest() == manifest["sha256"]
    assert manifest["metrics"] == {"n_pos": 1, "n_neg": 2, "train_seconds": 0}
    assert progress == [(1, 1, 0.0)]
    result = load(None).score([], [manifest])
    validate(result, "score_response")
    assert result["chloroplast_hits"] == [{"id": manifest["id"], "p": 0.5, "fired": False}]


@pytest.mark.parametrize("family,label,alert", [("bad", "ok", "ok"),
                                              ("zd_ok", "x" * 81, "ok"),
                                              ("zd_ok", "ok", "x" * 401)])
def test_invalid_manifest_metadata(family, label, alert):
    with pytest.raises(ValueError):
        chloroplast_train([], [], family, label, alert)


def test_compatibility_import():
    from ironguard_ml.stub import load as compatibility_load
    assert compatibility_load(None).score([]) == load(None).score([])
