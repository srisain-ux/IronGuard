"""Load PreyNet artifacts and score a conversation prefix (MODEL_SPEC §4.5–§4.7, §5.2, §7).

Same interface as stub.py: `load(artifacts_dir).score(turns, chloroplasts) -> score_response`.
Customer text is embedded in memory only: nothing derived from it is written to disk.
"""

import base64
import json
import logging
import re
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from ironguard_ml.data import FAMILIES, STAGES, TAXONOMY, TTS_BUCKETS, Turn
from ironguard_ml.features import Encoder, minilm_encoder, prefix_sequence, turn_vectors
from ironguard_ml.preynet import FEATURE_DIM, PreyNet, pack

THETA_LOCK, THETA_RELEASE, RELEASE_TURNS = 0.70, 0.40, 2  # §4.6
BAND_HIGH, BAND_LOW, UNCERTAIN_RISK, UNCERTAIN_FAMILY_P = 0.80, 0.10, 0.35, 0.5  # §4.5
MAX_EVIDENCE = 3
BENIGN = FAMILIES.index("benign")
LABELS = {f["id"]: f["label"] for f in TAXONOMY["families"]}
log = logging.getLogger(__name__)

_I = re.IGNORECASE
EVIDENCE_RULES = (  # checked in order; the first match names the reason for a turn
    ("Contains a link", re.compile(
        r"https?://|www\.|\b[\w-]+\.(?:com|net|org|io|co|ly|me|example|test)\b", _I)),
    ("Asks for money, crypto or a gift card", re.compile(
        r"\$\s?\d|\b(?:crypto|bitcoin|btc|usdt|wallet|wire|zelle|venmo|cash\s?app|"
        r"gift\s*cards?|deposit|invest\w*|fees?|pay(?:ment)?)\b", _I)),
    ("Asks for a code or login details", re.compile(
        r"\b(?:codes?|otp|pin|password|passcode|verif\w*|ssn|log\s?in)\b", _I)),
    ("Moves the chat to another app or number", re.compile(
        r"\b(?:whatsapp|telegram|signal|wechat|text me at|call (?:me|this number)|"
        r"new number)\b", _I)),
    ("Identity switch or unexpected sender", re.compile(
        r"\b(?:wrong number|new phone|it'?s me|lost my phone|who is this)\b", _I)),
    ("Urgency or pressure", re.compile(
        r"\b(?:urgent\w*|immediately|right now|asap|today|within \d+|final notice|"
        r"expir\w*|suspend\w*|locked|last chance|hurry)\b", _I)),
)


def lock_states(risks: Sequence[float], senders: Sequence[str], theta_lock: float = THETA_LOCK,
                theta_release: float = THETA_RELEASE, release_turns: int = RELEASE_TURNS) -> list[bool]:
    """CSTMD1 lock-on per prefix: lock at risk >= θ_lock; release only after `release_turns`
    consecutive scammer ("them") turns below θ_release. "me" turns never move the counter."""
    theta_release = min(theta_release, theta_lock)
    locked, below, states = False, 0, []
    for risk, sender in zip(risks, senders, strict=True):
        if not locked:
            locked, below = risk >= theta_lock, 0
        elif sender == "them":
            below = below + 1 if risk < theta_release else 0
            if below >= release_turns:
                locked, below = False, 0
        states.append(locked)
    return states


def confidence_band(risk: float, top_family_p: float) -> str:
    """§4.5, rules applied in the order written."""
    if risk >= BAND_HIGH or risk <= BAND_LOW:
        return "high"
    if top_family_p < UNCERTAIN_FAMILY_P or UNCERTAIN_RISK <= risk < BAND_HIGH:
        return "uncertain"
    return "low"


def evidence(turns: Sequence[Turn], attention: Sequence[float]) -> list[dict]:
    """Rule reasons for the most-attended scammer turns. Reasons never quote the message."""
    ranked = sorted((i for i, t in enumerate(turns) if t.sender == "them"),
                    key=lambda i: -attention[i])
    items = []
    for i in ranked[:MAX_EVIDENCE]:
        reason = next((r for r, rx in EVIDENCE_RULES if rx.search(turns[i].text)), None)
        if reason:
            items.append({"turn_idx": i, "reason": reason})
    return items


def _decode(b64: str, count: int, name: str) -> np.ndarray:
    raw = base64.b64decode(b64, validate=True)
    if len(raw) != 4 * count:
        raise ValueError(f"chloroplast weight {name} has {len(raw)} bytes, expected {4 * count}")
    return np.frombuffer(raw, dtype="<f4").astype(np.float32)


def apply_chloroplast(manifest: dict, features: torch.Tensor) -> torch.Tensor:
    """§5.2 reference: p_new = sigmoid(W2·gelu(W1·f + b1) + b2) for each row of `features`.

    `features` is PreyNet's (n, 640) output; the browser (onnx `features`) must match this.
    The caller applies the rule: fired = p >= threshold; risk = max(base risk, p) when fired.
    """
    if manifest.get("feature_dim") != FEATURE_DIM:
        raise ValueError(f"chloroplast feature_dim must be {FEATURE_DIM}")
    h, w = int(manifest["hidden_dim"]), manifest["weights"]
    w1 = torch.from_numpy(_decode(w["w1"], h * FEATURE_DIM, "w1").reshape(h, FEATURE_DIM))
    b1 = torch.from_numpy(_decode(w["b1"], h, "b1"))
    w2 = torch.from_numpy(_decode(w["w2"], h, "w2").reshape(1, h))
    b2 = torch.from_numpy(_decode(w["b2"], 1, "b2"))
    return torch.sigmoid(F.gelu(features @ w1.T + b1) @ w2.T + b2).squeeze(1)


def _parse_turns(turns) -> list[Turn]:
    if not isinstance(turns, list) or not turns:
        raise ValueError("turns must be a non-empty list")
    parsed = []
    for i, t in enumerate(turns):
        if not isinstance(t, dict) or t.get("sender") not in ("them", "me") \
                or not isinstance(t.get("text"), str):
            raise ValueError(f"turns[{i}] needs sender 'them'|'me' and string text")
        parsed.append(Turn(t["sender"], t["text"], "benign"))
    return parsed


class Model:
    def __init__(self, net: PreyNet, temperatures: dict, encoder: Encoder, version: str):
        self.net = net.eval()
        self.temperatures = temperatures
        # θ_lock tuned on VAL (§4.6) = the 1%-FPR operating point the reported metrics use.
        self.theta_lock = float(temperatures.get("theta_lock", THETA_LOCK))
        self.encoder = encoder
        self.version = version

    def score(self, turns, chloroplasts=None) -> dict:
        start = time.perf_counter()
        parsed = _parse_turns(turns)
        n = len(parsed)
        vectors = turn_vectors(parsed, self.encoder, cache_dir=None)  # memory only
        with torch.no_grad():
            out = self.net(*pack([prefix_sequence(vectors, k) for k in range(1, n + 1)]))
            family = torch.softmax(out["family_logits"] / self.temperatures["family"], dim=1)
            stage = torch.softmax(out["stage_logits"][-1] / self.temperatures["next_stage"], dim=0)
            tts = torch.softmax(out["tts_logits"][-1] / self.temperatures["tts"], dim=0)
            effective = 1 - family[:, BENIGN]
            lock_risk = effective.clone()  # a fired adapter is a detection, so it locks too
            hits, best_cp = [], None
            for cp in chloroplasts or []:
                try:
                    cp_id, threshold = str(cp["id"]), float(cp["threshold"])
                    p = apply_chloroplast(cp, out["features"])
                    if not torch.isfinite(p).all():
                        raise ValueError("non-finite output")
                except (AttributeError, KeyError, TypeError, ValueError) as exc:
                    # One broken adapter must never switch off base protection (§5.2).
                    log.warning("skipping a malformed chloroplast: %s", exc)
                    continue
                fired = p >= threshold
                effective = torch.where(fired, torch.maximum(effective, p), effective)
                lock_risk = torch.where(fired, torch.clamp(lock_risk, min=self.theta_lock), lock_risk)
                hits.append({"id": cp_id, "p": float(p[-1]), "fired": bool(fired[-1])})
                if fired[-1] and (best_cp is None or p[-1] > best_cp[1]):
                    best_cp = (cp, float(p[-1]))
        risks = effective.clamp(0, 1).tolist()
        base_probs = {fid: float(family[-1, i]) for i, fid in enumerate(FAMILIES)}
        if best_cp and best_cp[1] > 1 - base_probs["benign"]:
            cp, p = best_cp
            fam = {"id": cp["family_id"], "label": cp["label"], "p": p, "source": "chloroplast"}
        else:
            top = max(base_probs, key=base_probs.get)
            fam = {"id": top, "label": LABELS[top], "p": base_probs[top], "source": "base"}
        seen = out["attention"][-1, : min(n, out["attention"].shape[1])].tolist()
        attention = [0.0] * (n - len(seen)) + seen  # turns before the 12-turn window get 0
        result = {
            "risk": risks[-1],
            "confidence_band": confidence_band(risks[-1], fam["p"]),
            "family": fam,
            "family_probs": base_probs,
            "next_stage": {"stage": STAGES[int(stage.argmax())], "p": float(stage.max())},
            "turns_to_strike": {"bucket": TTS_BUCKETS[int(tts.argmax())], "p": float(tts.max())},
            "locked": lock_states(lock_risk.tolist(), [t.sender for t in parsed],
                                  self.theta_lock)[-1],
            "attention": attention,
            "evidence": evidence(parsed, attention),
            "chloroplast_hits": hits,
            "model": {"name": "preynet", "version": self.version, "runtime": "python"},
        }
        result["model"]["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return result


def load(artifacts_dir, encoder: Encoder | None = None) -> Model:
    """Load preynet.pt + temperature.json. `encoder` is injectable for tests (default MiniLM)."""
    path = Path(artifacts_dir)
    weights, temps = path / "preynet.pt", path / "temperature.json"
    for required in (weights, temps):
        if not required.exists():
            raise FileNotFoundError(f"missing PreyNet artifact: {required} (run `make train`)")
    checkpoint = torch.load(weights, map_location="cpu", weights_only=True)
    net = PreyNet(**checkpoint["config"])
    net.load_state_dict(checkpoint["state_dict"])
    temperatures = json.loads(temps.read_text())
    if not {"family", "next_stage", "tts"} <= set(temperatures):
        raise ValueError(f"{temps} must have family, next_stage and tts temperatures")
    return Model(net, temperatures, encoder or minilm_encoder(), checkpoint["meta"]["version"])
