"""Role-prefixed MiniLM turn embeddings with an on-disk cache (MODEL_SPEC §4.1)."""

import hashlib
import os
import tempfile
from collections.abc import Callable, Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np

from ironguard_ml.data import Conversation, Turn

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
EMB_DIM = 384
TURN_DIM = EMB_DIM + 1  # + is_them flag
MAX_TURNS = 12
CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "emb"

Encoder = Callable[[list[str]], np.ndarray]


def role_text(turn: Turn) -> str:
    return f"[{'THEM' if turn.sender == 'them' else 'ME'}] {turn.text}"


def cache_key(text: str, model_id: str = MODEL_ID) -> str:
    # model_id is hashed in so swapping the encoder can never serve stale vectors
    return hashlib.sha1(f"{model_id}\0{text}".encode()).hexdigest()


@lru_cache(maxsize=1)
def minilm_encoder() -> Encoder:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_ID, device="cpu")
    return lambda texts: model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.maximum(norms, 1e-12)).astype(np.float32)


def _encode(texts: list[str], encoder: Encoder | None) -> np.ndarray:
    vectors = _l2_normalize(np.asarray((encoder or minilm_encoder())(texts), dtype=np.float32))
    if vectors.shape != (len(texts), EMB_DIM):
        raise ValueError(f"encoder returned {vectors.shape}, expected {(len(texts), EMB_DIM)}")
    return vectors


def _save_atomic(path: Path, vector: np.ndarray) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            np.save(f, vector)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _load_cached(path: Path) -> np.ndarray | None:
    """A cached vector, or None if absent or unusable (the cache is derived data, so re-encode)."""
    try:
        vec = np.load(path)
    except (OSError, ValueError, EOFError):  # missing, empty or truncated file
        path.unlink(missing_ok=True)
        return None
    if vec.shape != (EMB_DIM,) or vec.dtype != np.float32:
        path.unlink(missing_ok=True)
        return None
    return vec


def embed_texts(
    texts: Sequence[str],
    encoder: Encoder | None = None,
    cache_dir: Path | None = CACHE_DIR,
    model_id: str = MODEL_ID,
) -> np.ndarray:
    """(len(texts), 384) float32, L2-normalized. Only cache misses reach the encoder.

    Pass a distinct `model_id` with any non-default `encoder` (e.g. the ONNX one from the §4.1
    parity rule) so its vectors never share cache entries with the sentence-transformers ones.
    `cache_dir=None` touches no disk: inference on customer text must use it (AGENTS.md rule 8).
    """
    if not texts:
        return np.zeros((0, EMB_DIM), dtype=np.float32)
    if cache_dir is None:
        return _encode(list(texts), encoder)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = [cache_dir / f"{cache_key(t, model_id)}.npy" for t in texts]
    vectors = {p: _load_cached(p) for p in set(paths)}
    misses = {p: t for p, t in zip(paths, texts) if vectors[p] is None}
    if misses:
        fresh = _encode(list(misses.values()), encoder)
        for path, vector in zip(misses, fresh):
            _save_atomic(path, vector)
            vectors[path] = vector
    return np.stack([vectors[p] for p in paths])


def turn_vectors(
    turns: Sequence[Turn],
    encoder: Encoder | None = None,
    cache_dir: Path | None = CACHE_DIR,
    model_id: str = MODEL_ID,
) -> np.ndarray:
    """(len(turns), 385): [embedding of the role-prefixed text, is_them]."""
    emb = embed_texts([role_text(t) for t in turns], encoder, cache_dir, model_id)
    is_them = np.array([[t.sender == "them"] for t in turns], dtype=np.float32).reshape(-1, 1)
    return np.concatenate([emb, is_them], axis=1)


def prefix_sequence(vectors: np.ndarray, k: int) -> np.ndarray:
    """Model input for prefix length k: the first k turn vectors, left-truncated to MAX_TURNS."""
    return vectors[max(0, k - MAX_TURNS) : k].copy()


def mean_turn_embedding(
    conv: Conversation,
    encoder: Encoder | None = None,
    cache_dir: Path | None = CACHE_DIR,
    model_id: str = MODEL_ID,
) -> np.ndarray:
    """Mean of the 384-d turn embeddings (is_them flag excluded); used for near-duplicate removal."""
    return turn_vectors(conv.turns, encoder, cache_dir, model_id)[:, :EMB_DIM].mean(axis=0)
