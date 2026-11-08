import numpy as np
import torch
from test_baselines import conv

from ironguard_ml.features import TURN_DIM
from ironguard_ml.train import encode, encode_train

BENIGN = (conv(["lunch?", "sure", "noon works"]), conv(["hey", "hi there"]))
SCAM = conv(["hi mom new phone", "send $300 now"], "family_emergency")


def vectors(turns):
    """One constant row per text, so every spliced row can be traced to its source turns."""
    return np.stack([np.full(TURN_DIM, sum(map(ord, t.text)), np.float32) for t in turns])


def ids(x, valid):
    return [int(v) for v in x[valid][:, 0]]


def test_splice_repeats_every_conversation_after_another_benign_opener():
    convs = (*BENIGN, SCAM)
    plain, spliced = encode(convs, vectors), encode_train(convs, vectors)
    n = len(plain.x)
    assert spliced.conversations == plain.conversations  # extra rows are TRAIN-only, never scored
    assert torch.equal(spliced.x[:n], plain.x) and len(spliced.x) == 2 * n
    for key in ("family", "stage", "tts", "tts_mask"):  # labels of the conversation's own prefix k
        assert torch.equal(getattr(spliced, key)[n:], getattr(plain, key))
    openers = {int(vectors(c.turns)[0, 0]) for c in BENIGN}
    for i in range(n):
        own, both = ids(plain.x[i], plain.mask[i]), ids(spliced.x[n + i], spliced.mask[n + i])
        j = len(both) - len(own)
        assert 1 <= j <= 3 and both[j:] == own  # the conversation's own turns follow the opener
        assert both[0] in openers and both[0] != own[0]  # opener from another benign conversation


def test_splice_is_deterministic_and_skips_benign_without_another_opener():
    convs = (*BENIGN, SCAM)
    assert torch.equal(encode_train(convs, vectors).x, encode_train(convs, vectors).x)
    one = (BENIGN[0], SCAM)  # the lone benign conversation has no other opener; the scam does
    assert len(encode_train(one, vectors).x) == len(encode(one, vectors).x) + len(SCAM.turns)
