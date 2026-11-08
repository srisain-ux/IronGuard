"""Conversation-level warning metrics, with 1-based prefix lengths (§2, §6.2).

Strike recall follows §6.2 literally: flag prefix <= strike_turn. With the
§2 index convention, this excludes the strike message, just like EWR.
Undefined denominators return None (JSON null), never fabricated zeros.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ironguard_ml.data import Conversation


@dataclass(frozen=True)
class ScoredConversation:
    conversation: Conversation
    risks: tuple[float, ...]

    def __post_init__(self):
        if len(self.risks) != len(self.conversation.turns):
            raise ValueError("need exactly one risk per turn")
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in self.risks):
            raise ValueError("risks must be finite probabilities in [0, 1]")

    def first_flag(self, threshold: float) -> int | None:
        return next((k for k, risk in enumerate(self.risks, 1) if risk >= threshold), None)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def ewr_at_k(rows: Sequence[ScoredConversation], threshold: float, k: int) -> float | None:
    if k < 1:
        raise ValueError("k must be positive")
    return _mean([float((flag := r.first_flag(threshold)) is not None
                        and flag <= min(k, r.conversation.strike_turn))
                  for r in rows if r.conversation.strike_turn is not None])


def lead_time(rows: Sequence[ScoredConversation], threshold: float) -> float | None:
    return _mean([float(max(0, r.conversation.strike_turn - (flag - 1)))
                  if (flag := r.first_flag(threshold)) is not None else 0.0
                  for r in rows if r.conversation.strike_turn is not None])


def strike_recall(rows: Sequence[ScoredConversation], threshold: float) -> float | None:
    return _mean([float((flag := r.first_flag(threshold)) is not None
                        and flag <= r.conversation.strike_turn)
                  for r in rows if r.conversation.strike_turn is not None])


def benign_fpr(rows: Sequence[ScoredConversation], threshold: float) -> float | None:
    return _mean([float(r.first_flag(threshold) is not None)
                  for r in rows if r.conversation.family == "benign"])


def hard_neg_fpr(rows: Sequence[ScoredConversation], threshold: float) -> float | None:
    return benign_fpr([r for r in rows if r.conversation.hard_negative], threshold)


def threshold_at_fpr(val: Sequence[ScoredConversation], target: float = 0.01) -> float:
    """Lowest threshold with empirical benign VAL conversation FPR <= target.

    Uses max risk per conversation, respects >= ties, and never interpolates.
    A threshold just above 1 disables a binary rule if its alarms exceed the cap.
    The caller must supply VAL only; test outcomes never influence selection.
    """
    if not 0 <= target < 1:
        raise ValueError("target must be in [0, 1)")
    maxima = sorted(max(r.risks) for r in val if r.conversation.family == "benign")
    if not maxima:
        raise ValueError("threshold selection requires benign VAL conversations")
    allowed = math.floor(target * len(maxima))
    return math.nextafter(maxima[len(maxima) - allowed - 1], math.inf)


def summarize(rows: Sequence[ScoredConversation], threshold: float) -> dict:
    return {
        "ewr_at_k": [ewr_at_k(rows, threshold, k) for k in range(1, 7)],
        "lead_time": lead_time(rows, threshold),
        "strike_recall": strike_recall(rows, threshold),
        "hard_neg_fpr": hard_neg_fpr(rows, threshold),
    }
