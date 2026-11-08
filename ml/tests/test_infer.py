import base64
import hashlib
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
import torch

from ironguard_ml.data import Turn
from ironguard_ml.features import EMB_DIM
from ironguard_ml.infer import (
    chloroplast_probs,
    confidence_band,
    evidence,
    load,
    lock_states,
)
from ironguard_ml.preynet import FEATURE_DIM, PreyNet
from ironguard_ml.stub import chloroplast_train

SCHEMAS = Path(__file__).resolve().parents[2] / "contracts" / "schemas"


def fake_encoder(texts):
    return np.stack([np.random.default_rng(int(hashlib.sha1(t.encode()).hexdigest()[:8], 16))
                     .normal(size=EMB_DIM) for t in texts])


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    out = tmp_path_factory.mktemp("artifacts")
    torch.manual_seed(0)
    net = PreyNet()
    torch.save({"state_dict": net.state_dict(), "config": net.config,
                "meta": {"version": "test"}}, out / "preynet.pt")
    (out / "temperature.json").write_text(json.dumps({"family": 2.0, "next_stage": 1.0, "tts": 1.0}))
    return load(out, encoder=fake_encoder)


def validate(value, name):
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(value)


def test_score_validates_and_covers_every_turn(model):
    turns = [{"sender": "them" if i % 2 == 0 else "me", "text": f"message {i}"} for i in range(14)]
    for k in (1, 3, 14):  # 14 > MAX_TURNS: early turns fall outside the attention window
        result = model.score(turns[:k], chloroplasts=[])
        validate(result, "score_response")
        assert len(result["attention"]) == k
        assert sum(result["attention"]) == pytest.approx(1, abs=1e-5)
        assert result["risk"] == pytest.approx(1 - result["family_probs"]["benign"], abs=1e-6)
    assert result["attention"][:2] == [0.0, 0.0]


def test_zero_chloroplast_reported_but_never_fires(model):
    manifest = chloroplast_train([], [], "zd_test", "Test", "alert")  # zero weights -> p = .5
    validate(manifest, "chloroplast")
    result = model.score([{"sender": "them", "text": "hi"}], chloroplasts=[manifest])
    validate(result, "score_response")
    assert result["chloroplast_hits"] == [{"id": manifest["id"], "p": 0.5, "fired": False}]
    assert result["family"]["source"] == "base"


def test_chloroplast_math_matches_formula():
    rng = np.random.default_rng(0)
    w1, b1 = rng.normal(size=(4, FEATURE_DIM)).astype("<f4"), rng.normal(size=4).astype("<f4")
    w2, b2 = rng.normal(size=(1, 4)).astype("<f4"), rng.normal(size=1).astype("<f4")
    enc = lambda a: base64.b64encode(a.tobytes()).decode()
    manifest = {"feature_dim": FEATURE_DIM, "hidden_dim": 4,
                "weights": {"w1": enc(w1), "b1": enc(b1), "w2": enc(w2), "b2": enc(b2)}}
    f = torch.from_numpy(rng.normal(size=(3, FEATURE_DIM)).astype(np.float32))
    expected = torch.sigmoid(torch.nn.functional.gelu(f @ torch.from_numpy(w1).T
                             + torch.from_numpy(b1)) @ torch.from_numpy(w2).T + torch.from_numpy(b2))
    assert torch.allclose(chloroplast_probs(manifest, f), expected.squeeze(1))
    manifest["hidden_dim"] = 5
    with pytest.raises(ValueError, match="bytes"):
        chloroplast_probs(manifest, f)


def test_lock_on_hysteresis():
    them = ["them"] * 6
    assert lock_states([.2, .7, .5, .3, .3, .8], them) == [False, True, True, True, False, True]
    assert lock_states([.69, .1], ["them"] * 2) == [False, False]
    # "me" turns never count toward release, and a THEM turn above θ_release resets the count
    assert lock_states([.9, .1, .1, .5, .1, .1], ["them", "them", "me", "them", "them", "them"]) \
        == [True, True, True, True, True, False]


@pytest.mark.parametrize("risk,top_p,band", [
    (.85, .3, "high"), (.05, .9, "high"), (.5, .9, "uncertain"),
    (.2, .4, "uncertain"), (.2, .7, "low"), (.8, .2, "high"),
])
def test_confidence_band(risk, top_p, band):
    assert confidence_band(risk, top_p) == band


def test_evidence_uses_top_attention_scammer_turns_without_quoting():
    turns = [Turn("them", "wrong number, sorry!", "bait"), Turn("me", "pay me $5", "bait"),
             Turn("them", "nice day", "pivot"), Turn("them", "send $200 in USDT now", "strike")]
    items = evidence(turns, [.3, .5, .1, .1])
    assert items == [{"turn_idx": 0, "reason": "Identity switch or unexpected sender"},
                     {"turn_idx": 3, "reason": "Asks for money, crypto or a gift card"}]


@pytest.mark.parametrize("turns", [[], [{"sender": "bot", "text": "x"}], [{"sender": "me"}], "hi"])
def test_rejects_bad_turns(model, turns):
    with pytest.raises(ValueError):
        model.score(turns)


def test_missing_artifacts_fail_loudly(tmp_path):
    with pytest.raises(FileNotFoundError, match="make train"):
        load(tmp_path, encoder=fake_encoder)


def test_val_tuned_theta_lock_drives_locked(tmp_path):
    torch.manual_seed(0)
    net = PreyNet()
    torch.save({"state_dict": net.state_dict(), "config": net.config,
                "meta": {"version": "test"}}, tmp_path / "preynet.pt")
    temps = {"family": 1.0, "next_stage": 1.0, "tts": 1.0}
    turns = [{"sender": "them", "text": "hi"}]
    for theta, expected in ((0.0, True), (1.01, False)):
        (tmp_path / "temperature.json").write_text(json.dumps({**temps, "theta_lock": theta}))
        assert load(tmp_path, encoder=fake_encoder).score(turns)["locked"] is expected
    assert lock_states([.3, .1], ["them"] * 2, theta_lock=.2) == [True, True]  # release <= lock
