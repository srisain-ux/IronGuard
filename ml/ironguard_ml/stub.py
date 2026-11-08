"""Deterministic integration fixtures, not calibrated model predictions."""

import base64
import hashlib
import re
from datetime import UTC, datetime

_RULES = (
    ("pig_butchering", "Relationship / crypto (pig butchering)", r"\bwrong number\b"),
    ("bank_impersonation", "Bank impersonation", r"\b(?:bank|fraud)\b"),
    ("family_emergency", "Family emergency ('Hi Mom')", r"\b(?:mom|new phone)\b"),
    ("toll_delivery", "Toll / delivery fee", r"\b(?:toll|package)\b"),
    ("carrier_support", "Carrier / tech support", r"\b(?:account suspended|code)\b"),
    ("job_task", "Fake job / task scam", r"\b(?:job|task)\b"),
)


class StubModel:
    """Stateless rules with stable family-priority tie breaking."""

    def score(self, turns, chloroplasts=None):
        """Score a prefix; zero-weight adapters are reported but never fire."""
        hits = []
        for family, label, pattern in _RULES:
            indices = [i for i, turn in enumerate(turns)
                       if turn["sender"] == "them"
                       and re.search(pattern, turn["text"], re.IGNORECASE)]
            if indices:
                hits.append((family, label, indices))
        family, label, indices = hits[0] if hits else ("benign", "Not a scam", [])
        risk = 0.8 if hits else 0.05
        probabilities = {"benign": 1 - risk}
        probabilities.update({key: risk / len(_RULES) if not hits else risk if key == family else 0.0 for key, _, _ in _RULES})
        total = len(turns) * (len(turns) + 1) / 2
        return {
            "risk": risk,
            "confidence_band": "high",
            "family": {"id": family, "label": label,
                       "p": probabilities[family], "source": "base"},
            "family_probs": probabilities,
            "next_stage": {"stage": "hook" if hits else "benign", "p": 0.6},
            "turns_to_strike": {"bucket": "2" if hits else "none", "p": 0.6},
            "locked": risk >= 0.7,
            "attention": [(i + 1) / total for i in range(len(turns))],
            "evidence": [{"turn_idx": i, "reason": f"Stub keyword match: {family}"}
                         for i in reversed(indices[-3:])],
            "chloroplast_hits": [{"id": cp["id"], "p": 0.5, "fired": False}
                                 for cp in (chloroplasts or [])],
            "model": {"name": "stub", "version": "0.1.0", "runtime": "python"},
        }


def load(path):
    """Return a stub without reading artifacts or accessing the network."""
    return StubModel()


def chloroplast_train(pos, neg, family_id, label, alert, progress_cb=None):
    """Return a correctly packed zero adapter; no training is performed."""
    if not re.fullmatch(r"zd_[a-z0-9_]+", family_id):
        raise ValueError("family_id must match zd_[a-z0-9_]+")
    if not isinstance(label, str) or len(label) > 80:
        raise ValueError("label must be a string of at most 80 characters")
    if not isinstance(alert, str) or len(alert) > 400:
        raise ValueError("alert must be a string of at most 400 characters")
    sizes = {"w1": 32 * 640, "b1": 32, "w2": 32, "b2": 1}
    raw = {key: bytes(count * 4) for key, count in sizes.items()}
    packed = b"".join(raw.values())
    if progress_cb is not None:
        progress_cb(1, 1, 0.0)
    return {
        "id": f"cp_{family_id[3:]}_stub", "family_id": family_id,
        "label": label, "alert": alert,
        "created_at": datetime.now(UTC).isoformat(),
        "half_life_hours": 72, "feature_dim": 640, "hidden_dim": 32,
        "weights": {key: base64.b64encode(value).decode("ascii")
                    for key, value in raw.items()},
        "threshold": 0.7,
        "metrics": {"n_pos": len(pos), "n_neg": len(neg), "train_seconds": 0},
        "size_bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest(),
    }


train = chloroplast_train
