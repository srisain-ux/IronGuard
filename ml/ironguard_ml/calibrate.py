"""Temperature scaling, ECE and reliability bins (MODEL_SPEC §4.5).

Callers must fit temperatures on VAL logits only; TEST is for reporting ECE.
"""

import numpy as np
import torch
from torch.nn import functional as F

N_BINS = 15
T_MIN, T_MAX = 0.05, 20.0


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """The T > 0 minimizing NLL of softmax(logits / T); 1.0 when there is nothing to fit."""
    if len(labels) == 0:
        return 1.0
    logits = logits.detach()
    log_t = torch.zeros(1, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_t], lr=0.1, max_iter=200)

    def closure():
        optimizer.zero_grad()
        loss = F.cross_entropy(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(np.clip(log_t.exp().item(), T_MIN, T_MAX))


def top_label(probs: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(confidence of the predicted class, whether it was right) per row."""
    probs = np.asarray(probs)
    return probs.max(axis=1), (probs.argmax(axis=1) == np.asarray(labels)).astype(float)


def _bins(confidence: np.ndarray, n_bins: int) -> np.ndarray:
    # Bins are (lo, hi]: 0.95 with 15 bins lands in bin 14, exactly 1/15 in bin 0.
    return np.clip(np.ceil(confidence * n_bins).astype(int) - 1, 0, n_bins - 1)


def reliability(confidence, correct, n_bins: int = N_BINS) -> dict:
    """Non-empty bins only: center, accuracy, mean confidence and count (pitch chart #3)."""
    confidence, correct = np.asarray(confidence, float), np.asarray(correct, float)
    idx = _bins(confidence, n_bins)
    out = {"bins": [], "acc": [], "conf": [], "count": []}
    for b in range(n_bins):
        sel = idx == b
        if sel.any():
            out["bins"].append((b + 0.5) / n_bins)
            out["acc"].append(float(correct[sel].mean()))
            out["conf"].append(float(confidence[sel].mean()))
            out["count"].append(int(sel.sum()))
    return out


def ece(confidence, correct, n_bins: int = N_BINS) -> float | None:
    """Expected calibration error: count-weighted |accuracy - confidence| over the bins."""
    bins = reliability(confidence, correct, n_bins)
    total = sum(bins["count"])
    if not total:
        return None
    return sum(n * abs(a - c) for n, a, c in zip(bins["count"], bins["acc"], bins["conf"])) / total
