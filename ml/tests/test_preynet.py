import numpy as np
import pytest
import torch

from ironguard_ml.features import MAX_TURNS, TURN_DIM
from ironguard_ml.preynet import FEATURE_DIM, PreyNet, pack


def prefixes(n=5, seed=0):
    turns = np.random.default_rng(seed).normal(size=(n, TURN_DIM)).astype(np.float32)
    return [turns[:k] for k in range(1, n + 1)]


@pytest.mark.parametrize("use_attention", [True, False])
def test_shapes_and_attention(use_attention):
    torch.manual_seed(0)
    net = PreyNet(use_attention).eval()
    out = net(*pack(prefixes()))
    assert out["features"].shape == (5, FEATURE_DIM) == (5, 640)
    assert out["family_logits"].shape == (5, 7)
    assert out["stage_logits"].shape == (5, 5)
    assert out["tts_logits"].shape == (5, 5)
    alpha = out["attention"]
    assert alpha.shape == (5, MAX_TURNS)
    assert torch.allclose(alpha.sum(1), torch.ones(5))
    assert (alpha[torch.arange(5).unsqueeze(1) < torch.arange(MAX_TURNS)] == 0).all()  # causal mask


def test_causal_prefix_outputs_ignore_future_turns():
    torch.manual_seed(0)
    net = PreyNet().eval()
    seqs = prefixes()
    alone = net(*pack(seqs[1:2]))
    batched = net(*pack(seqs))
    assert torch.allclose(alone["features"][0], batched["features"][1], atol=1e-6)


def test_small_brain():
    params = sum(p.numel() for p in PreyNet().parameters())
    assert 150_000 < params < 200_000  # §4.2 "about 160k" (192k as specified); ~0.77 MB fp32


def test_pack_rejects_bad_lengths():
    with pytest.raises(ValueError):
        pack([np.zeros((0, TURN_DIM))])
    with pytest.raises(ValueError):
        pack([np.zeros((MAX_TURNS + 1, TURN_DIM))])
