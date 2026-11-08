import hashlib
import os

import numpy as np
import pytest

from ironguard_ml.data import Conversation, Turn
from ironguard_ml.features import (
    EMB_DIM,
    MAX_TURNS,
    TURN_DIM,
    cache_key,
    embed_texts,
    mean_turn_embedding,
    prefix_sequence,
    role_text,
    turn_vectors,
)


class FakeEncoder:
    """Deterministic, deliberately un-normalized, and counts what it was asked to encode."""

    def __init__(self):
        self.seen = []

    def __call__(self, texts):
        self.seen.extend(texts)
        rows = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha1(text.encode()).digest()[:4], "little")
            rows.append(np.random.default_rng(seed).normal(size=EMB_DIM) * 3.0)
        return np.array(rows)


TURNS = (Turn("them", "hello there", "bait"), Turn("me", "who is this?", "bait"))


def test_cache_hit_returns_identical_vectors_without_re_encoding(tmp_path):
    enc = FakeEncoder()

    first = embed_texts(["[THEM] hi", "[ME] yo"], enc, tmp_path)
    calls_after_first = len(enc.seen)
    second = embed_texts(["[THEM] hi", "[ME] yo"], enc, tmp_path)

    assert calls_after_first == 2
    assert len(enc.seen) == 2
    assert np.array_equal(first, second)


def test_cache_persists_across_encoder_instances(tmp_path):
    first = embed_texts(["[THEM] hi"], FakeEncoder(), tmp_path)
    cold = FakeEncoder()

    second = embed_texts(["[THEM] hi"], cold, tmp_path)

    assert cold.seen == []
    assert np.array_equal(first, second)


def test_only_misses_reach_the_encoder_and_order_is_preserved(tmp_path):
    enc = FakeEncoder()
    embed_texts(["[THEM] a"], enc, tmp_path)
    enc.seen.clear()

    out = embed_texts(["[ME] b", "[THEM] a", "[ME] b"], enc, tmp_path)

    assert enc.seen == ["[ME] b"]
    assert np.array_equal(out[0], out[2])
    assert not np.array_equal(out[0], out[1])


def test_cache_files_are_named_by_sha1(tmp_path):
    embed_texts(["[THEM] hi"], FakeEncoder(), tmp_path)

    names = [p.name for p in tmp_path.iterdir()]

    assert names == [f"{cache_key('[THEM] hi')}.npy"]
    assert len(cache_key("x")) == 40


def test_embeddings_are_l2_normalized_float32(tmp_path):
    out = embed_texts(["[THEM] a", "[ME] b", "[THEM] c"], FakeEncoder(), tmp_path)

    assert out.dtype == np.float32
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-5)


def test_empty_input_returns_empty_matrix(tmp_path):
    assert embed_texts([], FakeEncoder(), tmp_path).shape == (0, EMB_DIM)


def test_turn_vectors_are_role_prefixed_385d_with_is_them_flag(tmp_path):
    enc = FakeEncoder()

    vecs = turn_vectors(TURNS, enc, tmp_path)

    assert enc.seen == ["[THEM] hello there", "[ME] who is this?"]
    assert vecs.shape == (2, TURN_DIM)
    assert vecs[:, -1].tolist() == [1.0, 0.0]


def test_same_text_from_different_senders_embeds_differently(tmp_path):
    vecs = turn_vectors((Turn("them", "ok", "bait"), Turn("me", "ok", "bait")), FakeEncoder(), tmp_path)

    assert role_text(Turn("me", "ok", "bait")) == "[ME] ok"
    assert not np.array_equal(vecs[0, :EMB_DIM], vecs[1, :EMB_DIM])


def test_prefix_sequence_left_truncates_to_max_turns():
    vectors = np.arange(15 * TURN_DIM, dtype=np.float32).reshape(15, TURN_DIM)

    assert prefix_sequence(vectors, 5).shape == (5, TURN_DIM)
    long = prefix_sequence(vectors, 15)
    assert long.shape == (MAX_TURNS, TURN_DIM)
    assert np.array_equal(long[0], vectors[15 - MAX_TURNS])
    assert np.array_equal(long[-1], vectors[14])


def test_mean_turn_embedding_is_384d(tmp_path):
    c = Conversation("c", "pig_butchering", "sms", TURNS, None, False, "human")

    assert mean_turn_embedding(c, FakeEncoder(), tmp_path).shape == (EMB_DIM,)


@pytest.mark.skipif(not os.environ.get("IRONGUARD_REAL_ENCODER"), reason="downloads MiniLM; opt in")
def test_real_minilm_gives_unit_vectors_and_similar_texts_are_closer(tmp_path):
    out = embed_texts(["[THEM] pay the toll now", "[THEM] settle your toll today", "[ME] lunch?"],
                      None, tmp_path)

    assert out.shape == (3, EMB_DIM)
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-4)
    assert out[0] @ out[1] > out[0] @ out[2]
