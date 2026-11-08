import json

import numpy as np
import pytest

from ironguard_ml.data import (
    FAMILIES,
    Conversation,
    DataError,
    Turn,
    drop_near_duplicates,
    exclude_held_out,
    load_corpus,
    load_jsonl,
    make_prefixes,
    stratified_split,
)

SCAM_FAMILIES = [f for f in FAMILIES if f != "benign"]


def conv(cid, family="pig_butchering", n_turns=6, strike=3, hard_negative=False):
    turns = tuple(
        Turn(
            "them" if i % 2 == 0 else "me",
            f"msg {i}",
            "benign" if strike is None else ("strike" if i >= strike else "bait"),
        )
        for i in range(n_turns)
    )
    return Conversation(cid, family, "sms", turns, strike, hard_negative, "human")


def population():
    scams = [conv(f"{f}_{i:02d}", f) for f in SCAM_FAMILIES for i in range(20)]
    benign = [conv(f"b_{i:02d}", "benign", strike=None, hard_negative=i < 16) for i in range(40)]
    return scams + benign


def record(cid="x_1", **overrides):
    base = {
        "id": cid,
        "family": "pig_butchering",
        "channel": "sms",
        "turns": [
            {"sender": "them", "text": "hi", "stage": "bait"},
            {"sender": "them", "text": "send $5", "stage": "strike"},
        ],
        "strike_turn": 1,
        "source": {"generator": "human"},
    }
    return {**base, **overrides}


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


# ---- splits ----


def test_no_conversation_id_in_two_splits():
    splits = stratified_split(population(), seed=0)

    all_ids = [c.id for convs in splits.values() for c in convs]

    assert len(all_ids) == len(set(all_ids)) == len(population())


def test_prefixes_of_one_conversation_never_cross_splits():
    splits = stratified_split(population(), seed=1)

    prefix_splits = {}
    for name, convs in splits.items():
        for c in convs:
            for p in make_prefixes(c):
                prefix_splits.setdefault(p.conv_id, set()).add(name)

    assert all(len(s) == 1 for s in prefix_splits.values())


def test_split_is_stratified_70_15_15_per_family():
    splits = stratified_split(population(), seed=0)

    for family in SCAM_FAMILIES:
        counts = {n: sum(c.family == family for c in cs) for n, cs in splits.items()}
        assert counts == {"train": 14, "val": 3, "test": 3}
    hard = {n: sum(c.hard_negative for c in cs) for n, cs in splits.items()}
    assert hard["train"] > hard["val"] >= 2 and hard["test"] >= 2


def test_split_is_deterministic_and_independent_of_input_order():
    pop = population()

    a = stratified_split(pop, seed=3)
    b = stratified_split(list(reversed(pop)), seed=3)
    c = stratified_split(pop, seed=4)

    assert a == b
    assert a != c


def test_tiny_stratum_still_has_a_train_conversation():
    for n in (1, 2, 3, 4):
        splits = stratified_split([conv(f"t_{i}") for i in range(n)], seed=0)
        assert len(splits["train"]) >= 1


def test_exclude_held_out_drops_family_from_train_and_val_only():
    splits = stratified_split(population(), seed=0)

    base = exclude_held_out(splits, held_out="job_task")

    for name in ("train", "val"):
        assert all(c.family != "job_task" for c in base[name])
    assert base["test"] == splits["test"]
    assert any(c.family == "job_task" for c in base["test"])
    assert exclude_held_out(splits, held_out=None) == splits


# ---- prefixes (§2 index conventions) ----


def test_prefix_labels_respect_strike_turn():
    prefixes = make_prefixes(conv("c", n_turns=6, strike=3))

    assert [p.k for p in prefixes] == [1, 2, 3, 4, 5, 6]
    assert [p.tts for p in prefixes] == ["2", "1", "0", "none", "none", "none"]
    assert [p.early for p in prefixes] == [True, True, True, False, False, False]
    assert [p.lead_time for p in prefixes] == [3, 2, 1, 0, 0, 0]
    assert all(len(p.turns) == p.k for p in prefixes)


def test_tts_bucket_3_plus_for_far_strikes():
    prefixes = make_prefixes(conv("c", n_turns=9, strike=7))

    assert [p.tts for p in prefixes[:4]] == ["3+", "3+", "3+", "3+"]
    assert prefixes[4].tts == "2"


def test_next_stage_is_following_turn_or_benign_at_the_end():
    c = conv("c", n_turns=4, strike=2)

    prefixes = make_prefixes(c)

    assert [p.next_stage for p in prefixes] == ["bait", "strike", "strike", "benign"]


def test_benign_prefixes_are_never_early_and_have_no_tts():
    prefixes = make_prefixes(conv("b", "benign", n_turns=5, strike=None))

    assert {p.tts for p in prefixes} == {"none"}
    assert not any(p.early for p in prefixes)
    assert {p.lead_time for p in prefixes} == {0}
    assert {p.family for p in prefixes} == {"benign"}


# ---- loading ----


def test_load_jsonl_parses_valid_records(tmp_path):
    path = tmp_path / "a.jsonl"
    write_jsonl(path, [record("a_1"), record("a_2", hard_negative=False)])

    convs = load_jsonl(path)

    assert [c.id for c in convs] == ["a_1", "a_2"]
    assert convs[0].turns[1] == Turn("them", "send $5", "strike")
    assert convs[0].strike_turn == 1


@pytest.mark.parametrize(
    "bad",
    [
        record(strike_turn=0),  # first strike stage is at 1
        record(family="benign"),  # benign must have null strike_turn
        record(strike_turn=None),  # scam family without a strike_turn
        record(family="made_up_family"),  # outside the taxonomy pattern
        record(turns=[]),  # schema: minItems 1
    ],
)
def test_load_jsonl_rejects_contract_violations_with_location(tmp_path, bad):
    path = tmp_path / "bad.jsonl"
    write_jsonl(path, [record("ok_1"), bad])

    with pytest.raises(DataError, match=r"bad\.jsonl:2"):
        load_jsonl(path)


def test_load_jsonl_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json\n")

    with pytest.raises(DataError, match=r"bad\.jsonl:1"):
        load_jsonl(path)


def test_load_corpus_reads_generated_and_seed_and_keeps_test_human_apart(tmp_path):
    write_jsonl(tmp_path / "generated" / "v1" / "train.jsonl", [record("g_1")])
    write_jsonl(tmp_path / "seed" / "seed.jsonl", [record("s_1")])
    write_jsonl(tmp_path / "test_human" / "human.jsonl", [record("h_1")])

    corpus = load_corpus("v1", tmp_path)

    assert [c.id for c in corpus.main] == ["g_1", "s_1"]
    assert [c.id for c in corpus.test_human] == ["h_1"]


def test_load_corpus_tolerates_missing_generated_dir(tmp_path):
    write_jsonl(tmp_path / "seed" / "seed.jsonl", [record("s_1")])

    assert [c.id for c in load_corpus("v1", tmp_path).main] == ["s_1"]


def test_load_corpus_rejects_id_shared_between_train_data_and_test_human(tmp_path):
    write_jsonl(tmp_path / "generated" / "v1" / "train.jsonl", [record("same_id")])
    write_jsonl(tmp_path / "test_human" / "human.jsonl", [record("same_id")])

    with pytest.raises(DataError, match="duplicate conversation id 'same_id'"):
        load_corpus("v1", tmp_path)


# ---- near-duplicates ----


def test_drop_near_duplicates_keeps_first_of_each_cluster():
    convs = [conv("a"), conv("b"), conv("c")]
    vectors = {"a": [1.0, 0.0], "b": [0.99, 0.01], "c": [0.0, 1.0]}

    kept, dropped = drop_near_duplicates(convs, lambda c: np.array(vectors[c.id]))

    assert [c.id for c in kept] == ["a", "c"]
    assert dropped == ["b"]
