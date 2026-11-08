"""Causal binary risk baselines from MODEL_SPEC §6.1 (no stage labels as inputs)."""

import itertools
import re
from collections.abc import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from ironguard_ml.data import Conversation
from ironguard_ml.features import EMB_DIM, turn_vectors

RULE = re.compile(
    r"https?://|www\.|\b[\w-]+\.(?:com|net|org|example|test)\b|\$|"
    r"\b(?:gift\s*cards?|codes?|otp|crypto|bitcoin|click)\b", re.IGNORECASE
)


class Baseline:
    """Fit on every TRAIN prefix; score one risk per prefix in original turn order.

    B1/B2 see only the latest turn, B3 sees the arithmetic mean of all seen
    MiniLM vectors. B1 uses raw text; B2/B3 use role-prefixed embeddings
    from features.py (§4.1). B0 emits binary rule hits, not calibrated risks.
    """

    def __init__(self, model_id: str):
        if model_id not in ("B0", "B1", "B2", "B3"):
            raise ValueError(f"unknown baseline: {model_id}")
        self.model_id = model_id
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.classifier = LogisticRegression(max_iter=1000, random_state=0)

    def _features(self, conversations: Sequence[Conversation], fit: bool = False):
        if self.model_id == "B1":
            texts = [t.text for c in conversations for t in c.turns]
            return (self.vectorizer.fit_transform(texts) if fit
                    else self.vectorizer.transform(texts))
        blocks = []
        for conv in conversations:
            vectors = turn_vectors(conv.turns)[:, :EMB_DIM]
            if self.model_id == "B3":
                vectors = vectors.cumsum(axis=0) / np.arange(1, len(vectors) + 1)[:, None]
            blocks.append(vectors)
        return np.concatenate(blocks)

    def fit(self, conversations: Sequence[Conversation]):
        if self.model_id != "B0":
            labels = [int(c.family != "benign") for c in conversations for _ in c.turns]
            if len(set(labels)) != 2:
                raise ValueError("TRAIN must contain both benign and scam conversations")
            self.classifier.fit(self._features(conversations, fit=True), labels)
        return self

    def score(self, conversations: Sequence[Conversation]) -> list[list[float]]:
        if not conversations:
            return []
        if self.model_id == "B0":
            return [[float(bool(RULE.search(t.text))) for t in c.turns] for c in conversations]
        risks = self.classifier.predict_proba(self._features(conversations))[:, 1]
        offsets = np.cumsum([0] + [len(c.turns) for c in conversations])
        return [risks[a:b].tolist() for a, b in itertools.pairwise(offsets)]
