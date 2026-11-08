"""Conversation loading, prefixes and conversation-level splits (MODEL_SPEC §2, §3, §4.3)."""

import json
import random
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SCHEMA_PATH = ROOT / "contracts" / "schemas" / "conversation.schema.json"
TAXONOMY = json.loads((ROOT / "contracts" / "taxonomy.json").read_text())

FAMILIES = tuple(f["id"] for f in TAXONOMY["families"])
STAGES = tuple(s["id"] for s in TAXONOMY["stages"])
TTS_BUCKETS = tuple(TAXONOMY["tts_buckets"])  # "0", "1", "2", "3+", "none"

SPLIT_FRACTIONS = (("train", 0.70), ("val", 0.15), ("test", 0.15))
NEAR_DUPLICATE_COSINE = 0.95
HELD_OUT_DEFAULT = "job_task"

_VALIDATOR = jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


class DataError(ValueError):
    """A dataset line or corpus violates the conversation contract."""


@dataclass(frozen=True)
class Turn:
    sender: str
    text: str
    stage: str


@dataclass(frozen=True)
class Conversation:
    id: str
    family: str
    channel: str
    turns: tuple[Turn, ...]
    strike_turn: int | None
    hard_negative: bool
    generator: str


@dataclass(frozen=True)
class Prefix:
    """What the model has seen after `k` turns, with every label derived from §2/§4.3."""

    conv_id: str
    k: int
    turns: tuple[Turn, ...]
    family: str
    next_stage: str
    tts: str  # bucket of strike_turn - k; "none" for benign or once the strike has been seen
    early: bool  # a flag here is early iff k <= strike_turn
    lead_time: int  # strike_turn - (k - 1) while early, else 0


@dataclass(frozen=True)
class Corpus:
    main: tuple[Conversation, ...]  # generated + seed: split 70/15/15
    test_human: tuple[Conversation, ...]  # test only, never split or trained on


def _parse(record: dict, where: str) -> Conversation:
    errors = sorted(_VALIDATOR.iter_errors(record), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        path = "/".join(map(str, err.path)) or "<root>"
        raise DataError(f"{where}: {path}: {err.message}")
    turns = tuple(Turn(t["sender"], t["text"], t["stage"]) for t in record["turns"])
    strike = record["strike_turn"]
    first_strike = next((i for i, t in enumerate(turns) if t.stage == "strike"), None)
    if strike != first_strike:
        raise DataError(f"{where}: strike_turn={strike} but first strike stage is {first_strike}")
    if (record["family"] == "benign") != (strike is None):
        raise DataError(f"{where}: strike_turn must be null exactly when family is benign")
    return Conversation(
        id=record["id"],
        family=record["family"],
        channel=record["channel"],
        turns=turns,
        strike_turn=strike,
        hard_negative=record.get("hard_negative", False),
        generator=record["source"]["generator"],
    )


def load_jsonl(path: Path) -> list[Conversation]:
    convs = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        where = f"{path}:{i}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DataError(f"{where}: invalid JSON: {exc.msg}") from exc
        convs.append(_parse(record, where))
    return convs


def _load_dir(directory: Path) -> list[Conversation]:
    return [c for p in sorted(directory.glob("*.jsonl")) for c in load_jsonl(p)]


def load_corpus(version: str = "v1", data_dir: Path = DATA_DIR) -> Corpus:
    """Load data/generated/<version>/ + data/seed/ (main) and data/test_human/ (test only)."""
    main = _load_dir(data_dir / "generated" / version) + _load_dir(data_dir / "seed")
    test_human = _load_dir(data_dir / "test_human")
    seen: set[str] = set()
    for conv in main + test_human:
        if conv.id in seen:
            raise DataError(f"duplicate conversation id '{conv.id}' (possible test contamination)")
        seen.add(conv.id)
    return Corpus(main=tuple(main), test_human=tuple(test_human))


def tts_bucket(strike_turn: int | None, k: int) -> str:
    """Bucket strike_turn - k; only prefixes with k <= strike_turn get a bucket (§4.3)."""
    if strike_turn is None or k > strike_turn:
        return "none"
    remaining = strike_turn - k
    return "3+" if remaining >= 3 else str(remaining)


def make_prefixes(conv: Conversation) -> list[Prefix]:
    """One prefix per k = 1..n. Prefix k has seen turns[0:k], so its last turn is index k-1."""
    n = len(conv.turns)
    prefixes = []
    for k in range(1, n + 1):
        early = conv.strike_turn is not None and k <= conv.strike_turn
        prefixes.append(
            Prefix(
                conv_id=conv.id,
                k=k,
                turns=conv.turns[:k],
                family=conv.family,
                next_stage=conv.turns[k].stage if k < n else "benign",
                tts=tts_bucket(conv.strike_turn, k),
                early=early,
                lead_time=conv.strike_turn - (k - 1) if early else 0,
            )
        )
    return prefixes


def _stratum(conv: Conversation) -> str:
    if conv.family != "benign":
        return conv.family
    return "benign_hard_negative" if conv.hard_negative else "benign"


def _quotas(n: int, rng: random.Random) -> list[int]:
    """Largest-remainder counts for (train, val, test); train always gets at least one."""
    raw = [n * frac for _, frac in SPLIT_FRACTIONS]
    counts = [int(x) for x in raw]
    by_remainder = sorted(range(len(raw)), key=lambda i: (-(raw[i] - counts[i]), rng.random()))
    for i in by_remainder[: n - sum(counts)]:
        counts[i] += 1
    return counts


def stratified_split(
    convs: Iterable[Conversation], seed: int = 0
) -> dict[str, tuple[Conversation, ...]]:
    """Conversation-level 70/15/15 split stratified by family (hard negatives are their own stratum).

    Any `split` field on incoming records is ignored: A owns the splits. Output depends only on
    the set of conversations and the seed, not on input order.
    """
    strata: dict[str, list[Conversation]] = defaultdict(list)
    for conv in convs:
        strata[_stratum(conv)].append(conv)
    out: dict[str, list[Conversation]] = {name: [] for name, _ in SPLIT_FRACTIONS}
    for key in sorted(strata):
        members = sorted(strata[key], key=lambda c: c.id)
        rng = random.Random(f"{seed}:{key}")
        rng.shuffle(members)
        start = 0
        for (name, _), count in zip(SPLIT_FRACTIONS, _quotas(len(members), rng)):
            out[name].extend(members[start : start + count])
            start += count
    return {name: tuple(items) for name, items in out.items()}


def exclude_held_out(
    splits: Mapping[str, Sequence[Conversation]], held_out: str | None = HELD_OUT_DEFAULT
) -> dict[str, tuple[Conversation, ...]]:
    """Base-training view: drop the held-out family from train and val, keep it in test (LOFO, §6.3)."""
    return {
        name: tuple(c for c in convs if name not in ("train", "val") or c.family != held_out)
        for name, convs in splits.items()
    }


def drop_near_duplicates(
    convs: Iterable[Conversation],
    mean_embedding: Callable[[Conversation], np.ndarray],
    threshold: float = NEAR_DUPLICATE_COSINE,
) -> tuple[list[Conversation], list[str]]:
    """Keep the first of each near-duplicate cluster (by id order); return (kept, dropped ids)."""
    ordered = sorted(convs, key=lambda c: c.id)
    kept: list[Conversation] = []
    kept_vecs: list[np.ndarray] = []
    dropped: list[str] = []
    for conv in ordered:
        vec = np.asarray(mean_embedding(conv), dtype=np.float32)
        vec = vec / max(float(np.linalg.norm(vec)), 1e-12)
        if kept_vecs and float(np.max(np.stack(kept_vecs) @ vec)) > threshold:
            dropped.append(conv.id)
            continue
        kept.append(conv)
        kept_vecs.append(vec)
    return kept, dropped
