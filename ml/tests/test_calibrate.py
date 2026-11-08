import numpy as np
import pytest
import torch
from torch.nn import functional as F

from ironguard_ml.calibrate import ece, fit_temperature, reliability, top_label


def test_ece_toy_case_by_hand():
    # Bin 14 (0.933, 1]: conf .95, acc .5 -> gap .45 on 2 rows.
    # Bin 2 (0.133, 0.2]: conf .15, acc 0 -> gap .15 on 2 rows.  ECE = (2*.45 + 2*.15) / 4 = .3
    assert ece([.95, .95, .15, .15], [1, 0, 0, 0]) == pytest.approx(.3)
    assert ece([.8] * 10, [1] * 8 + [0] * 2) == pytest.approx(0)
    assert ece([], []) is None


def test_reliability_bins_are_non_empty_and_half_open():
    bins = reliability([1 / 15, .95, 1.0], [1, 1, 0])
    assert bins["count"] == [1, 2]
    assert bins["bins"] == pytest.approx([.5 / 15, 14.5 / 15])
    assert bins["acc"] == [1.0, .5]


def test_top_label():
    conf, correct = top_label(np.array([[.2, .8], [.6, .4]]), np.array([1, 1]))
    assert conf.tolist() == [.8, .6] and correct.tolist() == [1, 0]


def test_temperature_softens_overconfident_logits():
    torch.manual_seed(0)
    labels = torch.randint(0, 3, (400,))
    noisy = torch.where(torch.rand(400) < .6, labels, torch.randint(0, 3, (400,)))
    logits = F.one_hot(noisy, 3).float() * 8  # ~70% right but ~100% confident
    t = fit_temperature(logits, labels)
    assert t > 1
    assert F.cross_entropy(logits / t, labels) < F.cross_entropy(logits, labels)
    assert fit_temperature(logits[:0], labels[:0]) == 1.0
