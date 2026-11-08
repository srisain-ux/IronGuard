"""Hand calculations and an independent event-index cross-check for §6.2."""

import math

import numpy as np
import pytest

from ironguard_ml.data import Conversation, Turn
from ironguard_ml.metrics import (
    ScoredConversation,
    benign_fpr,
    ewr_at_k,
    flicker_rate,
    hard_neg_fpr,
    lead_time,
    strike_recall,
    summarize,
    threshold_at_fpr,
)


def row(risks, strike=None, hard=False):
    conv = Conversation("fixture", "benign" if strike is None else "job_task", "sms",
                        tuple(Turn("them", "text", "benign") for _ in risks),
                        strike, hard, "human")
    return ScoredConversation(conv, tuple(risks))


def test_hand_computed():
    rows = [row([0, 1, 0, 0], 3), row([0, 0, 1], 2), row([0, 0, 0], 2),
            row([1, 0], hard=True), row([0, 0], hard=True), row([0, 1])]
    assert ewr_at_k(rows, .5, 1) == 0
    assert ewr_at_k(rows, .5, 2) == 1 / 3
    assert ewr_at_k(rows, .5, 6) == 1 / 3
    assert lead_time(rows, .5) == 2 / 3  # early 2, at-strike 0, never 0
    assert strike_recall(rows, .5) == 1 / 3
    assert hard_neg_fpr(rows, .5) == .5
    assert benign_fpr(rows, .5) == 2 / 3


def test_first_turn_strike_and_last_chance_warning():
    assert lead_time([row([1], 0)], .5) == 0
    assert strike_recall([row([1], 0)], .5) == 0
    assert ewr_at_k([row([1], 0)], .5, 6) == 0
    assert lead_time([row([0, 1, 0], 2)], .5) == 1
    assert strike_recall([row([0, 0, 1], 1)], .5) == 0


def test_undefined_is_null():
    assert summarize([], .5) == {
        "ewr_at_k": [None] * 6, "lead_time": None,
        "strike_recall": None, "hard_neg_fpr": None, "fpr": None,
    }
    with pytest.raises(ValueError, match="benign VAL"):
        threshold_at_fpr([row([1], 0)])


def test_threshold_uses_conversation_max_and_handles_ties():
    val = [row([0, .7]), row([.7]), row([1, 1, 1], 2)]
    threshold = threshold_at_fpr(val)
    assert threshold == math.nextafter(.7, math.inf)
    assert benign_fpr(val, threshold) == 0
    assert threshold_at_fpr([row([1])]) > 1  # B0 must be allowed to abstain
    val = [row([i / 100]) for i in range(100)]
    threshold = threshold_at_fpr(val)
    assert benign_fpr(val, threshold) == .01
    assert threshold < .99
    tied = [row([.8])] * 100
    assert benign_fpr(tied, threshold_at_fpr(tied)) == 0


def test_independent_cross_check():
    # Independent implementation uses zero-based alarm indices and explicit scans,
    # without calling first_flag or sharing the production metric formulas.
    rng = np.random.default_rng(83)
    rows = [row(rng.random(n), int(rng.integers(n))) for n in range(1, 21)]
    for threshold in (0, .3, .8, 1, 1.01):
        early_counts = [0] * 6
        total_lead = 0
        for r in rows:
            alarm_indices = np.flatnonzero(np.asarray(r.risks) >= threshold)
            if not len(alarm_indices):
                continue
            first = int(alarm_indices[0])
            s = r.conversation.strike_turn
            if first < s:
                total_lead += len(range(first, s))
            for limit in range(1, 7):
                if any(i < s and i < limit for i in alarm_indices):
                    early_counts[limit - 1] += 1
        assert lead_time(rows, threshold) == total_lead / len(rows)
        assert [ewr_at_k(rows, threshold, k) for k in range(1, 7)] == [
            count / len(rows) for count in early_counts
        ]


def test_flicker_rate_hand_computed():
    T, F = True, False
    states = [
        [F, T, F, T],     # on, off, on again: flickers
        [T, F, F, T, T],  # starts on, gap, back on: flickers
        [F, T, T, F],     # on then off for good: no flicker
        [T, T, T],        # steady lock: no flicker
        [F, F, F],        # never warned: excluded from the denominator
    ]
    assert flicker_rate(states) == 2 / 4
    assert flicker_rate([[F, F]]) is None
    assert flicker_rate([]) is None


@pytest.mark.parametrize("risks", [[math.nan], [math.inf], [-.1], [1.1], []])
def test_invalid_scores(risks):
    with pytest.raises(ValueError):
        ScoredConversation(row([0]).conversation, tuple(risks))
