"""Independent §2/§6.2 oracle; never inspect or reuse metrics.py's implementation.

Flags are indexed by the last message seen (zero-based); prefix lengths are
one-based. The production functions are used only as black-box comparison targets.
"""

import importlib
import importlib.util
import itertools
import math
import random

import pytest

from ironguard_ml.data import Conversation, Turn

SEED = 20261108
TOLERANCE = 1e-9


@pytest.fixture(scope="module")
def metrics():
    if importlib.util.find_spec("ironguard_ml.metrics") is None:
        pytest.skip(
            "metrics.py is not in this branch yet; re-run this cross-check "
            "after A2's express drop."
        )
    # Do not hide broken imports or missing dependencies in an existing module.
    return importlib.import_module("ironguard_ml.metrics")


def reference_ewr(cases, k):
    """Fraction of scams with a flagged prefix <= k strictly before the strike."""
    scams = [(flags, strike) for flags, strike in cases if strike is not None]
    if not scams:
        return None  # Existing public API's undefined-denominator convention.
    caught = 0
    for flags, strike in scams:
        for last_seen, flag in enumerate(flags):
            if flag and last_seen < strike and last_seen + 1 <= k:
                caught += 1
                break
    return caught / len(scams)


def reference_lead_time(cases):
    """Mean unseen messages until strike at the first flag; misses contribute 0."""
    leads = []
    for flags, strike in cases:
        if strike is None:
            continue
        lead = 0
        for last_seen, flag in enumerate(flags):
            if flag:
                # Count message positions rather than reuse a production helper.
                lead = len(range(last_seen, strike))
                break
        leads.append(lead)
    return sum(leads) / len(leads) if leads else None


def scored_rows(metrics, cases):
    rows = []
    for index, (flags, strike) in enumerate(cases):
        turns = tuple(
            Turn("them", "synthetic fixture", "benign" if strike is None else
                 "strike" if turn == strike else "bait" if turn < strike else "hook")
            for turn in range(len(flags))
        )
        conversation = Conversation(
            f"crosscheck_{index}", "benign" if strike is None else "job_task",
            "sms", turns, strike, False, "human",
        )
        # Fixed threshold isolates metric semantics from VAL threshold selection.
        rows.append(metrics.ScoredConversation(conversation, tuple(map(float, flags))))
    return rows


def results(metrics, cases, metric, k):
    rows = scored_rows(metrics, cases)
    if metric == "EWR":
        return reference_ewr(cases, k), metrics.ewr_at_k(rows, 0.5, k)
    return reference_lead_time(cases), metrics.lead_time(rows, 0.5)


def differs(expected, actual):
    if expected is None or actual is None:
        return expected is not actual
    return not math.isclose(expected, actual, rel_tol=0, abs_tol=TOLERANCE)


def smallest_failure(metrics, cases, metric, k):
    """Minimize conversation count, then exhaust single-case flag sequences.

    A multi-conversation witness is deletion-minimal. For a single scam, search
    all sequences up to its length, ordered by length, strike index and flags,
    so the reported single-conversation witness is the smallest in that order.
    This diagnostic runs only on a mismatch, never on the passing path.
    """
    cases = list(cases)
    changed = True
    while changed and len(cases) > 1:
        changed = False
        for index in range(len(cases)):
            candidate = cases[:index] + cases[index + 1:]
            if differs(*results(metrics, candidate, metric, k)):
                cases = candidate
                changed = True
                break
    if len(cases) == 1:
        for length in range(1, len(cases[0][0]) + 1):
            for strike in (*range(length), None):
                for flags in itertools.product((False, True), repeat=length):
                    candidate = [(flags, strike)]
                    if differs(*results(metrics, candidate, metric, k)):
                        return candidate
    return cases


def assert_crosscheck(metrics, cases):
    for metric, k in [("EWR", k) for k in range(1, 7)] + [("lead_time", None)]:
        if differs(*results(metrics, cases, metric, k)):
            witness = smallest_failure(metrics, cases, metric, k)
            expected, actual = results(metrics, witness, metric, k)
            message = (
                f"Smallest failing case (seed={SEED}, {metric}, k={k}, "
                f"threshold=0.5): {witness!r}; expected={expected!r}, actual={actual!r}. "
                "Each case is (zero-based flags, zero-based strike_turn); "
                "multi-conversation witnesses are deletion-minimal."
            )
            print(message)
            pytest.fail(message, pytrace=False)


def random_cases():
    rng = random.Random(SEED)
    cases = []
    for _ in range(200):
        length = rng.randint(1, 12)
        strike = None if rng.random() < 0.2 else rng.randrange(length)
        probability = rng.random()
        flags = tuple(rng.random() < probability for _ in range(length))
        cases.append((flags, strike))
    return cases


@pytest.mark.parametrize("case", [
    ((True,), 0),                       # Strike on first turn: no early warning.
    ((True, False, False), 2),          # Prefix 1: two turns of lead time.
    ((False, True, False), 2),          # Prefix strike_turn: one turn of lead time.
    ((False, False, True), 2),          # At strike: zero lead time, not early.
    ((False, False, True), 1),          # After strike: zero lead time.
    ((False, False, False), 2),         # Never flagged: included as a zero.
    ((True, False, True, True), 3),     # First flag wins despite flickering.
    ((False,) * 5 + (True, False), 6),  # k=6 inclusive.
    ((False,) * 6 + (True, False), 7),  # First early flag beyond reported k.
    ((False,) * 18 + (True, False), 19),  # Contract's maximum turn count.
    ((True, True, True), None),         # Benign excluded from both denominators.
])
def test_index_boundaries(metrics, case):
    assert_crosscheck(metrics, [case])


def test_200_random_flag_sequences(metrics):
    cases = random_cases()
    assert len(cases) == 200
    # Shortest generated cases are checked first; aggregation cannot mask errors.
    for case in sorted(cases, key=lambda case: len(case[0])):
        assert_crosscheck(metrics, [case])
    assert_crosscheck(metrics, cases)
    for start in range(0, len(cases), 17):
        assert_crosscheck(metrics, cases[start:start + 17])


def test_mixed_denominator(metrics):
    cases = [((False, True, False, False), 3),  # lead=2
             ((False, False, True), 2),        # at strike=0
             ((False, False, False), 2),       # never=0
             ((True, True, True), None)]       # benign ignored
    assert reference_ewr(cases, 1) == 0
    assert reference_ewr(cases, 2) == 1 / 3
    assert reference_lead_time(cases) == 2 / 3
    assert_crosscheck(metrics, cases)
