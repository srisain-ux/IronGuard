"""PreyNet: the causal Dragonfly trajectory forecaster (MODEL_SPEC §4.2)."""

import math
from collections.abc import Sequence

import numpy as np
import torch
from torch import nn

from ironguard_ml.data import FAMILIES, STAGES, TTS_BUCKETS
from ironguard_ml.features import EMB_DIM, MAX_TURNS, TURN_DIM

HIDDEN = 128
FEATURE_DIM = 2 * HIDDEN + EMB_DIM  # [pooled ; h_t ; mean_emb] = 640


def pack(sequences: Sequence[np.ndarray]) -> tuple[torch.Tensor, torch.Tensor]:
    """Right-pad (k_i, 385) prefix inputs to (N, MAX_TURNS, 385) plus a validity mask.

    The GRU is causal, so padding after the last real turn never changes its states.
    """
    x = torch.zeros(len(sequences), MAX_TURNS, TURN_DIM)
    mask = torch.zeros(len(sequences), MAX_TURNS, dtype=torch.bool)
    for i, seq in enumerate(sequences):
        if not 1 <= len(seq) <= MAX_TURNS:
            raise ValueError(f"prefix length must be 1..{MAX_TURNS}, got {len(seq)}")
        x[i, : len(seq)] = torch.from_numpy(np.asarray(seq, dtype=np.float32))
        mask[i, : len(seq)] = True
    return x, mask


class CstmdAttention(nn.Module):
    """CSTMD1-style selective attention: the latest state queries every state seen so far.

    q = W_q h_t ; α_i = softmax_i(q · W_k h_i / √d) over i ≤ t. With `selective=False`
    (the no-attention ablation) α is uniform over the turns seen.
    """

    def __init__(self, dim: int = HIDDEN, selective: bool = True):
        super().__init__()
        self.w_q = nn.Linear(dim, dim, bias=False)
        self.w_k = nn.Linear(dim, dim, bias=False)
        self.selective = selective
        self.scale = 1 / math.sqrt(dim)

    def forward(self, states, mask, h_t):
        if self.selective:
            scores = torch.einsum("bd,btd->bt", self.w_q(h_t), self.w_k(states)) * self.scale
        else:
            scores = torch.zeros(mask.shape, dtype=states.dtype)
        alpha = torch.softmax(scores.masked_fill(~mask, float("-inf")), dim=1)
        return torch.einsum("bt,btd->bd", alpha, states), alpha


class PreyNet(nn.Module):
    """Linear+GELU → causal GRU → CstmdAttention → 640-d features → family/stage/tts heads."""

    def __init__(self, use_attention: bool = True, dropout: float = 0.1):
        super().__init__()
        self.config = {"use_attention": use_attention, "dropout": dropout}
        self.proj = nn.Sequential(nn.Linear(TURN_DIM, HIDDEN), nn.GELU(), nn.Dropout(dropout))
        self.gru = nn.GRU(HIDDEN, HIDDEN, num_layers=1, batch_first=True)
        self.attention = CstmdAttention(HIDDEN, selective=use_attention)
        self.family = nn.Linear(FEATURE_DIM, len(FAMILIES))
        self.next_stage = nn.Linear(FEATURE_DIM, len(STAGES))
        self.tts = nn.Linear(FEATURE_DIM, len(TTS_BUCKETS))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> dict[str, torch.Tensor]:
        states, _ = self.gru(self.proj(x))
        last = mask.sum(dim=1) - 1
        h_t = states[torch.arange(len(x)), last]
        pooled, alpha = self.attention(states, mask, h_t)
        valid = mask.unsqueeze(-1).to(x.dtype)
        mean_emb = (x[..., :EMB_DIM] * valid).sum(dim=1) / valid.sum(dim=1)
        features = torch.cat([pooled, h_t, mean_emb], dim=1)
        return {
            "family_logits": self.family(features),
            "stage_logits": self.next_stage(features),
            "tts_logits": self.tts(features),
            "attention": alpha,
            "features": features,
        }
