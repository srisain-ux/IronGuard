import base64
import hashlib
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest
import torch

from ironguard_ml.chloroplast import (
    STEPS,
    Base,
    build_negative_bank,
    conversation_features,
    load_base,
    save_bank,
    threshold_at_fpr,
    train,
)
from ironguard_ml.data import _parse
from ironguard_ml.features import EMB_DIM
from ironguard_ml.infer import apply_chloroplast
from ironguard_ml.preynet import PreyNet

SCHEMA = json.loads((Path(__file__).resolve().parents[2]
                     / "contracts/schemas/chloroplast.schema.json").read_text())


def fake_encoder(texts):
    """Random per text, plus a shared direction for the new scam's tell ("deposit")."""
    out = []
    for t in texts:
        rng = np.random.default_rng(int(hashlib.sha1(t.encode()).hexdigest()[:8], 16))
        v = rng.normal(size=EMB_DIM)
        v[0] += 8 * ("deposit" in t)
        out.append(v)
    return np.stack(out)


def record(i, family, texts):
    scam = family != "benign"
    stages = ["bait"] * (len(texts) - 1) + ["strike"] if scam else ["benign"] * len(texts)
    return {"id": f"{family}_{i}", "family": family, "channel": "sms",
            "turns": [{"sender": "them" if j % 2 == 0 else "me", "text": t, "stage": s}
                      for j, (t, s) in enumerate(zip(texts, stages, strict=True))],
            "strike_turn": len(texts) - 1 if scam else None, "source": {"generator": "other_llm"}}


POS = [record(i, "zd_task", [f"remote job {i}", "ok", f"deposit to unlock tasks {i}"])
       for i in range(30)]
NEG = [record(i, "benign", [f"recruiter hello {i}", "sure", f"interview at {i} pm"])
       for i in range(30)]


@pytest.fixture(scope="module")
def base():
    torch.manual_seed(0)
    net = PreyNet().eval()
    pool = [_parse(record(i, "benign" if i % 2 else "pig_butchering", [f"hi {i}", "yo", f"x {i}"]),
                   "pool") for i in range(60)]
    return Base(net, *build_negative_bank(net, pool, fake_encoder, cache_dir=None),
                encoder=fake_encoder)


def test_manifest_validates_and_packs_weights(base):
    calls = []
    m = train(POS, NEG, "zd_task", "Pay-to-unlock job", "Jobs that ask a deposit.",
              lambda *a: calls.append(a), base=base)
    jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(m)
    packed = b"".join(base64.b64decode(m["weights"][k]) for k in ("w1", "b1", "w2", "b2"))
    assert m["size_bytes"] == len(packed) == 4 * (32 * 640 + 32 + 32 + 1) == 82_180
    assert m["sha256"] == hashlib.sha256(packed).hexdigest()
    assert m["id"] == f"cp_task_{m['sha256'][:8]}"
    assert calls[-1][:2] == (STEPS, STEPS) and len(calls) == STEPS // 10
    assert m["metrics"]["n_pos"] == m["metrics"]["n_neg"] == 30
    assert m["metrics"]["train_seconds"] > 0  # the 10 s budget is checked by the CLI benchmark


def test_learns_the_tell_and_reference_apply_agrees(base):
    m = train(POS, NEG, "zd_task", "Task", "alert", base=base)
    assert m["metrics"]["val_recall_at_1fpr"] == 1.0
    features, groups = conversation_features(base.net, [_parse(POS[0], "p"), _parse(NEG[0], "n")],
                                             fake_encoder)
    p = apply_chloroplast(m, torch.from_numpy(features))
    assert p[groups == 0][-1] >= m["threshold"] > p[groups == 1].max()  # fires on the deposit turn


def test_same_seed_same_weights(base):
    args = (POS, NEG, "zd_task", "Task", "alert")
    assert train(*args, base=base)["sha256"] == train(*args, base=base)["sha256"]
    assert train(*args, base=base, seed=1)["sha256"] != train(*args, base=base)["sha256"]


def test_threshold_allows_at_most_one_percent_in_float32():
    maxima = np.linspace(0, 1, 200, dtype=np.float32)
    t = threshold_at_fpr(maxima)
    assert (maxima >= np.float32(t)).sum() == 2  # floor(1% of 200)
    assert threshold_at_fpr(np.full(50, 0.5, np.float32)) > 0.5  # ties never sneak past the cap
    with pytest.raises(ValueError, match="saturates"):  # p == 1 negatives: refuse, never cap
        threshold_at_fpr(np.ones(10, np.float32))


@pytest.mark.parametrize("kwargs, error", [
    ({"family_id": "job_task"}, ValueError),
    ({"label": ""}, ValueError),
    ({"alert": "x" * 401}, ValueError),
    ({"pos": POS[:4]}, ValueError),
    ({"neg": ["not a dict"] * 5}, TypeError),
    ({"neg": [{**NEG[0], "strike_turn": 1}] * 5}, ValueError),  # schema/semantic DataError
    ({"progress_cb": "nope"}, ValueError),
])
def test_rejects_bad_input(base, kwargs, error):
    args = {"pos": POS, "neg": NEG, "family_id": "zd_task", "label": "Task", "alert": "alert",
            **kwargs}
    with pytest.raises(error):
        train(**args, base=base)


def test_load_base_refuses_missing_or_stale_bank(tmp_path, base):
    torch.save({"state_dict": base.net.state_dict(), "config": base.net.config, "meta": {}},
               tmp_path / "preynet.pt")
    with pytest.raises(FileNotFoundError):
        load_base(tmp_path)
    save_bank(tmp_path, base.bank, base.bank_groups)
    assert load_base(tmp_path).bank.shape == base.bank.shape
    load_base.cache_clear()
    (tmp_path / "preynet.pt").write_bytes(b"other weights")
    with pytest.raises(ValueError, match="other PreyNet weights"):
        load_base(tmp_path)


def test_bank_keeps_whole_conversations_and_excludes_callers_negatives(base):
    other = [_parse(record(i, "pig_butchering", [f"a {i}", "b", "c", "d"]), "o") for i in range(200)]
    benign = [_parse(record(i, "benign", [f"x {i}", "y"]), "b") for i in range(3)]
    _, groups = build_negative_bank(base.net, benign + other, fake_encoder, cache_dir=None,
                                           exclude_ids=frozenset({"benign_0", "benign_1"}))
    sizes = np.bincount(groups)
    assert sizes[0] == 2  # only benign_2 is left, with both of its prefixes
    assert (sizes[1:] == 4).all() and sizes[1:].sum() == 500  # whole conversations, ~500 target
