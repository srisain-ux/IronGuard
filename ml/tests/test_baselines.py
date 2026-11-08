import numpy as np
import pytest

from ironguard_ml.baselines import Baseline
from ironguard_ml.data import Conversation, Turn


def conv(texts, family="benign"):
    return Conversation("test", family, "sms", tuple(Turn("them", t, "benign") for t in texts),
                        None if family == "benign" else len(texts) - 1, False, "human")


def test_rules_latest_only():
    c = conv(["click https://bank.example", "hello", "$5 gift card code", "crypto"])
    assert Baseline("B0").fit([]).score([c]) == [[1, 0, 1, 1]]


def test_tfidf_train_and_latest_only():
    model = Baseline("B1").fit([conv(["hello friend", "lunch tomorrow"]),
                                conv(["send cash", "send cash now"], "job_task")])
    assert "unseen" not in model.vectorizer.vocabulary_
    a, b = model.score([conv(["unseen", "hello friend"]), conv(["hello friend"])])
    assert a[-1] == b[0]
    assert "unseen" not in model.vectorizer.vocabulary_
    assert model.score([]) == []
    with pytest.raises(ValueError, match="both benign and scam"):
        Baseline("B1").fit([conv(["hello"])])


def test_minilm_features_causal_and_mean(monkeypatch):
    def fake_vectors(turns):
        return np.array([[float(t.text)] * 384 + [1] for t in turns])
    monkeypatch.setattr("ironguard_ml.baselines.turn_vectors", fake_vectors)
    c = conv(["2", "4", "9"])
    latest = Baseline("B2")._features([c])
    mean = Baseline("B3")._features([c])
    assert latest.shape == mean.shape == (3, 384)
    np.testing.assert_allclose(latest[:, 0], [2, 4, 9])
    np.testing.assert_allclose(mean[:, 0], [2, 3, 5])
    np.testing.assert_allclose(mean[:2], Baseline("B3")._features([conv(["2", "4"])]))
