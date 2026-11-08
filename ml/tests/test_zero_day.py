import json

import pytest

from ironguard_ml.data import _parse
from ironguard_ml.zero_day import ZD_FAMILY, run_lofo, synthetic_data
from tests.test_chloroplast import fake_encoder, record


def corpus():
    """Small splits: benign (half hard negatives), pig_butchering and 16 job_task conversations."""
    recs = {}

    def make(i, family, texts, **extra):
        r = {**record(i, family, texts), **extra}
        recs[r["id"]] = r
        return _parse(r, r["id"])

    def split(offset, n):
        return tuple(
            [make(offset + i, "benign", [f"hello {offset + i}", "hi", f"lunch {i}"],
                  hard_negative=i % 2 == 0) for i in range(n)]
            + [make(offset + i, "pig_butchering", [f"wrong number {offset + i}", "?", "crypto"])
               for i in range(n)]
            + [make(offset + i, "job_task", [f"remote job {offset + i}", "ok", "deposit now"])
               for i in range(n // 2)])

    return {"train": split(0, 16), "val": split(100, 8), "test": split(200, 8),
            "test_human": ()}, recs


def test_proxy_never_trains_on_its_test_half(tmp_path):
    splits, recs = corpus()
    data = synthetic_data(splits, recs, zd_dir=tmp_path / "absent")
    pos_ids = {r["id"] for r in data["pos"]}
    test_ids = {c.id for c in data["test"]}
    assert data["source"] == "v1_proxy" and not pos_ids & test_ids
    assert pos_ids | test_ids == {c.id for s in ("train", "val", "test") for c in splits[s]
                                  if c.family == "job_task"}
    assert {r["family"] for r in data["pos"]} == {ZD_FAMILY}
    train_ids = {c.id for c in splits["train"]}
    assert data["neg"] and all(r["id"] in train_ids and r["hard_negative"] for r in data["neg"])


def test_algae_data_tests_on_every_held_out_conversation(tmp_path):
    splits, recs = corpus()
    pos = [record(i, ZD_FAMILY, ["job?", "ok", "deposit"]) for i in range(6)]
    neg = [{**record(i, "benign", ["real recruiter", "ok", "see you"]), "hard_negative": True}
           for i in range(6)]
    (tmp_path / "zd.jsonl").write_text("\n".join(json.dumps(r) for r in pos + neg))
    (tmp_path / "meta.json").write_text(json.dumps({"alert": "Job deposit.", "generate_seconds": 9}))
    data = synthetic_data(splits, recs, tmp_path)
    assert (data["source"], len(data["pos"]), len(data["neg"]), len(data["test"])) == \
        ("algae", 6, 6, 16)
    assert (data["alert"], data["generate_seconds"]) == ("Job deposit.", 9)


@pytest.fixture(scope="module")
def lofo_runs(tmp_path_factory):
    nowhere = tmp_path_factory.mktemp("no_zd") / "absent"
    splits, recs = corpus()
    first = run_lofo(splits, recs, encoder=fake_encoder, zd_dir=nowhere)
    test_ids = {c.id for c in synthetic_data(splits, recs, nowhere)["test"]}

    def scramble(conv):  # rewrite the text of a held-out test conversation
        if conv.id not in test_ids:
            return conv
        r = recs[conv.id]
        return _parse({**r, "turns": [{**t, "text": t["text"] + " changed"} for t in r["turns"]]},
                      conv.id)

    changed = {name: tuple(map(scramble, convs)) for name, convs in splits.items()}
    return first, run_lofo(changed, recs, encoder=fake_encoder, zd_dir=nowhere)


def test_changing_test_conversations_cannot_change_training(lofo_runs):
    keys = ("theta", "chloroplast_threshold", "val_recall_at_1fpr")
    first, changed = lofo_runs
    assert [[s[k] for k in keys] for s in first["seeds"]] == \
        [[s[k] for k in keys] for s in changed["seeds"]]


def test_summary_shape(lofo_runs):
    z = lofo_runs[0]
    assert (z["available"], z["display"], z["source"], z["family"]) == \
        (False, "--", "v1_proxy", "job_task")
    assert [p["n"] for p in z["sample_efficiency"]] == [25, 50, 100, 200]
    assert all(p["ewr_at_3"] is None for p in z["sample_efficiency"])  # only 8 positives
    assert len(z["base"]["ewr_at_k"]) == len(z["chloroplast"]["ewr_at_k"]) == 6
    assert z["time_to_protection_s"] is None and len(z["seeds"]) == 3
