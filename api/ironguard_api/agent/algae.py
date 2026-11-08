"""Algae: the Nemotron synthetic-conversation factory (docs/MODEL_SPEC.md §3, §9).

python -m ironguard_api.agent.algae --version v1 --per-family 150      (or: make algae)

knobs -> batch of 5 (generator) -> local checks -> critic -> dedupe -> schema -> append to
data/generated/<version>/<family>.jsonl right away. Re-running resumes from what is on disk.
Progress lines carry counts only, never message text.
"""

import argparse
import asyncio
import json
import math
import os
import random
import re
import uuid
from collections import Counter
from itertools import pairwise
from pathlib import Path

from ..contracts import ROOT, validator
from . import nemotron

TAXONOMY = json.loads((ROOT / "contracts" / "taxonomy.json").read_text())
DESC = {f["id"]: f["description"] for f in TAXONOMY["families"]}
SCAMS = [f for f in DESC if f != "benign"]
STAGES = {"bait", "pivot", "hook", "strike"}
ORDER = {"benign": 0, "bait": 1, "pivot": 2, "hook": 3, "strike": 4}
HARD_SHARE = 0.45  # spec asks for >= 40% of benign
DEDUPE_COS = 0.8  # shortcut: word-shingle cosine, not the spec's embedding cosine 0.95; A re-checks with embeddings
CHANNELS = ["sms", "sms", "imessage", "whatsapp"]
VICTIMS = ["cooperative", "skeptical", "silent (very short replies, sometimes ignores messages)"]
STYLES = ["lowercase with a few typos", "lots of emoji", "slangy and abbreviated", "polished and formal",
          "short bursts, no punctuation"]
PERSONAS = [
    "19-year-old UT Dallas student living on campus", "34-year-old nurse in Dallas",
    "67-year-old retiree in rural Texas", "42-year-old long-haul truck driver",
    "28-year-old software contractor in Plano", "55-year-old small-business owner in Fort Worth",
    "23-year-old barista in Deep Ellum", "73-year-old grandmother, new to smartphones",
    "31-year-old parent in Frisco", "45-year-old teacher in Garland",
]
BRANDS = {
    "bank_impersonation": ["PNC", "Capital One", "Chase"], "toll_delivery": ["NTTA TollTag", "USPS", "Amazon"],
    "carrier_support": ["T-Mobile"], "job_task": ["Amazon"], "family_emergency": [], "pig_butchering": [],
    "benign": TAXONOMY["brands_demo_only"],
}
HARD_NEGATIVES = [
    "a wrong-number text that stays harmless: the stranger apologizes, the chat stays friendly or ends, nobody asks for anything",
    "a legitimate bank alert that tells the customer to open the official app or call the number on their card; the bank never asks for codes, links or money",
    "a real delivery or toll notice from a genuine sender: informational, points to the official website or app, no payment link",
    "a real recruiter reaching out about an interview: schedules a call, never asks for money",
    "a friendly golf, brunch or study-group plan that opens like a mistaken text but is between people who really know each other",
    "a real carrier notice about a plan change or bill reminder that points to the official app",
    "a relative who really texted from a new phone and proves it with personal details, never asks for money",
]
LEAK = re.compile(r"\b(scam\w*|fraud\w*|phish\w*|bait\w*|pig[\s-]?butcher\w*)", re.IGNORECASE)
PHONE = re.compile(r"(\d{3})[\s.)-]+(\d{4})\b")
DOMAIN = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|co|us|info|biz|app|xyz|me|ly|gov|edu|top|cc|ru|cn)\b", re.IGNORECASE)

STAGE_RULES = {
    True: """Stage labels (label EVERY turn, both senders; a "me" reply gets the same stage as the "them" message it answers):
bait = first contact; pivot = rapport or identity building; hook = pretext, urgency or opportunity;
strike = the first THEM message that sends a link, asks for money, a one-time code, a gift card or a credential.
Stages never go backwards. Turn 1 is bait and the strike turn is a THEM turn. Never use the stage "benign".""",
    False: 'Stage labels: nothing harmful ever happens, so EVERY turn of EVERY conversation has stage "benign".',
}
RESERVED = re.compile(r"(^|\.)example\.(com|org|net)$", re.IGNORECASE)  # RFC 2606 names are safe
SKELETON = """You write realistic text-message conversations for training a scam-defense model.
Return ONLY compact JSON shaped like this (two turns shown; yours have 4-10):
{{"conversations":[{{"family":"{family}","channel":"{channel}","turns":[{{"sender":"them","text":"first message","stage":"{ex_stage}"}},{{"sender":"me","text":"reply","stage":"{ex_stage}"}}]}}]}}
"sender" is exactly "them" (the other person) or "me" (the phone owner). "stage" is exactly one word from the stage list below.
Write {n} different conversations. Family: {family} - {description} Persona of "me": {persona}. Channel: {channel}.
{plot}
Style of "them": {style}. Victim ("me") style: {victim}. Brands you may use if natural: {brands}.
{stage_rules}
Rules: natural texting (typos/emoji ok). Never write the words "scam", "fraud", "phishing" or "bait" in a message
(say "security", "account protection" or "suspicious activity" instead).
Never put a double-quote character inside a message text; use single quotes. Fake numbers and domains only:
555-01xx numbers (like 555-0142) and fake domains (.example, .test, example.com), each conversation has between 4 and 10 turns (never more than 10), all different."""

CRITIC = """You review training conversations for a scam-defense dataset. For EACH conversation give:
realism: integer 1-5 (would it pass as a real text thread: natural, specific, not cartoonish)
label_correct: true only if the stage labels fit the turns, the family fits, and the strike turn is really the
first message that sends a link or asks for money, a code, a gift card or a credential. For family "benign",
true only if nobody ever tries to get money, codes, links or credentials and every stage is "benign".
Return ONLY compact JSON: {{"scores":[{{"i":0,"realism":4,"label_correct":true}}]}} with one entry per conversation.
Conversations: {convs}"""


def prompt_for(family: str, hard: bool, n: int, rng: random.Random) -> str:
    k = rng.randint(2, 5)  # shortcut: spec says 2-6, but THEM turn 6 cannot fit in 10 turns; the model only loosely follows it
    if family == "benign":
        plot = "Strike: none. Nobody ever asks for money, codes, links or gift cards. " + (
            f"Every conversation is {rng.choice(HARD_NEGATIVES)}." if hard
            else "Every conversation is ordinary everyday life (friends, family, work, plans).")
    else:
        plot = f"Scammer patience: strike at turn {k} (1-indexed among THEM turns), the conversation may continue a little after it. The victim may hesitate but THEM still goes for the strike."
    brands = ", ".join(rng.sample(BRANDS[family], min(2, len(BRANDS[family])))) or "none"
    return SKELETON.format(
        family=family, description=LEAK.sub("security", DESC[family]), n=n, ex_stage="benign" if family == "benign" else "bait", channel=rng.choice(CHANNELS), persona=rng.choice(PERSONAS),
        plot=plot, style=rng.choice(STYLES), victim=rng.choice(VICTIMS), brands=brands, stage_rules=STAGE_RULES[family != "benign"])


def fix_stages(conv: dict, family: str) -> None:
    """Contract convention: a "me" reply takes the stage of the turn before it; benign is all benign;
    everything after the first THEM strike is strike."""
    turns = conv.get("turns")
    if not isinstance(turns, list):
        return
    struck = False
    for i, t in enumerate(turns):
        if not isinstance(t, dict):
            return
        if family == "benign":
            t["stage"] = "benign"
            continue
        if t.get("sender") == "me" and i and isinstance(turns[i - 1], dict):
            t["stage"] = turns[i - 1].get("stage")
        if struck:  # nothing comes after the strike in the kill chain
            t["stage"] = "strike"
        struck = struck or (t.get("stage") == "strike" and t.get("sender") == "them")


def check(conv: object, family: str) -> str | None:
    """Reason to drop, or None. Everything the model says is untrusted."""
    turns = conv.get("turns") if isinstance(conv, dict) else None
    if not isinstance(turns, list) or not 4 <= len(turns) <= 10:
        return "length"
    if not all(isinstance(t, dict) and t.get("sender") in ("them", "me") and isinstance(t.get("text"), str)
               and t["text"].strip() and len(t["text"]) <= 1000 for t in turns):
        return "shape"
    stages = [t.get("stage") for t in turns]
    if any(s not in ORDER for s in stages):
        return "stage"
    text = " ".join(t["text"] for t in turns)
    if LEAK.search(text):
        return "leak-word"
    if any(m.group(1) != "555" or m.group(2)[:2] != "01" for m in PHONE.finditer(text)) or any(
            not RESERVED.search(m.group(0)) for m in DOMAIN.finditer(text)):
        return "real-looking-contact"
    if family == "benign":
        return None if set(stages) == {"benign"} else "stage"
    if stages[0] != "bait" or set(stages) - STAGES or "strike" not in stages:
        return "stage"
    if any(ORDER[a] > ORDER[b] for a, b in pairwise(stages)):
        return "stage"
    s = stages.index("strike")
    if turns[s]["sender"] != "them":
        return "stage"
    return None


def shingles(conv: dict) -> Counter:
    words = " ".join(t["text"] for t in conv["turns"]).lower().split()
    return Counter(zip(words, words[1:], words[2:]))


def cosine(a: Counter, b: Counter) -> float:
    small, big = (a, b) if len(a) < len(b) else (b, a)
    dot = sum(v * big[g] for g, v in small.items() if g in big)
    return dot / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())) or 1)


class Factory:
    def __init__(self, version: str, per_family: int, concurrency: int, batch_size: int, out: Path):
        self.version, self.bs, self.out = version, batch_size, out / version
        self.workers, self.lock = concurrency, asyncio.Lock()
        self.gen_model, self.critic_model = os.environ["NEMOTRON_GEN_MODEL"], os.environ["NEMOTRON_AGENT_MODEL"]
        hard = round(HARD_SHARE * len(SCAMS) * per_family)
        self.quota = {(f, False): per_family for f in SCAMS}
        self.quota |= {("benign", True): hard, ("benign", False): len(SCAMS) * per_family - hard}
        self.kept, self.seen, self.drops = Counter(), {f: [] for f in DESC if f in self.quota_families()}, Counter()
        self.out.mkdir(parents=True, exist_ok=True)
        for f in self.seen:  # resume: count and fingerprint what is already on disk
            path = self.out / f"{f}.jsonl"
            for line in path.read_text().splitlines() if path.exists() else []:
                rec = json.loads(line)
                self.kept[(f, rec.get("hard_negative", False))] += 1
                self.seen[f].append(shingles(rec))

    def quota_families(self):
        return {f for f, _ in self.quota}

    def remaining(self, key):
        return max(0, self.quota[key] - self.kept[key])

    async def call(self, *args, **kwargs):
        return await nemotron.chat_json(*args, **kwargs)

    async def batch(self, key) -> None:
        family, hard = key
        seed = random.SystemRandom().randrange(2**31)
        prompt = prompt_for(family, hard, self.bs, random.Random(seed))
        try:
            out = await self.call([{"role": "user", "content": prompt}], model=self.gen_model,
                                  temperature=0.9, top_p=0.95, max_tokens=3500, thinking=False)
            convs = [c for c in out.get("conversations", []) if isinstance(c, dict)][: self.bs]
            good = []
            for c in convs:
                fix_stages(c, family)
                reason = check(c, family)
                if reason:
                    self.drops[reason] += 1
                else:
                    good.append(c)
            scores = {}
            if good:
                listing = json.dumps([{"i": i, "family": family, "turns": [
                    {"sender": t["sender"], "text": t["text"], "stage": t["stage"]} for t in c["turns"]]}
                    for i, c in enumerate(good)])
                graded = await self.call([{"role": "user", "content": CRITIC.format(convs=listing)}],
                                         model=self.critic_model, temperature=0.2, max_tokens=1500, thinking=False)
                scores = {s["i"]: s for s in graded.get("scores", []) if isinstance(s, dict) and "i" in s}
        except Exception as exc:  # noqa: BLE001  one bad batch must not stop the run; count it
            self.drops[f"error:{type(exc).__name__}"] += 1
            return
        async with self.lock:
            for i, c in enumerate(good):
                self.add(key, c, scores.get(i), seed)
            print(f"[algae] {family}{'/hard' if hard else ''} {self.kept[key]}/{self.quota[key]} | "
                  f"total {sum(self.kept.values())}/{sum(self.quota.values())} | drops {dict(self.drops)}", flush=True)

    def add(self, key, conv: dict, score: dict | None, seed: int) -> None:
        family, hard = key
        realism = score.get("realism") if score else None
        if not isinstance(realism, (int, float)) or isinstance(realism, bool) or realism < 4 \
                or score.get("label_correct") is not True:
            self.drops["critic"] += 1
            return
        if self.remaining(key) == 0:
            return  # quota already full (batches overshoot slightly); not a quality drop
        rec = {
            "id": f"{family}_{self.version}_{uuid.uuid4().hex[:10]}", "family": family,
            "channel": conv.get("channel") if conv.get("channel") in TAXONOMY["channels"] else "sms",
            "hard_negative": hard,
            "turns": [{"sender": t["sender"], "text": t["text"].strip(), "stage": t["stage"]} for t in conv["turns"]],
            "strike_turn": None if family == "benign" else next(
                i for i, t in enumerate(conv["turns"]) if t["stage"] == "strike"),
            "source": {"generator": "nemotron", "model": self.gen_model, "prompt_id": f"gen_{self.version}",
                       "seed": seed, "critic_realism": float(realism)},
        }
        fp = shingles(rec)
        if any(cosine(fp, other) > DEDUPE_COS for other in self.seen[family]):
            self.drops["duplicate"] += 1
            return
        if not validator("conversation").is_valid(rec):
            self.drops["schema"] += 1
            return
        with open(self.out / f"{family}.jsonl", "a") as f:  # one write per record: crash-safe
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.seen[family].append(fp)
        self.kept[key] += 1

    async def run(self, max_rounds: int) -> None:
        for rnd in range(1, max_rounds + 1):
            need = {k: math.ceil(self.remaining(k) / self.bs) for k in self.quota}
            jobs = [k for i in range(max(need.values())) for k in self.quota if i < need[k]]  # interleave families
            if not jobs:
                break
            print(f"[algae] round {rnd}: {len(jobs)} batches", flush=True)
            todo = iter(jobs)  # a fixed pool: each worker runs a whole batch (generate + critic), so
            # critic calls never queue behind the round's remaining generation calls

            async def worker(todo):
                for key in todo:
                    await self.batch(key)

            await asyncio.gather(*(worker(todo) for _ in range(self.workers)))
        short = {f"{f}{'/hard' if h else ''}": self.remaining((f, h)) for f, h in self.quota if self.remaining((f, h))}
        print(f"[algae] done: {sum(self.kept.values())}/{sum(self.quota.values())} kept; short {short or 'none'}; "
              f"drops {dict(self.drops)}", flush=True)


def main() -> None:
    os.environ.setdefault("NEMOTRON_TIMEOUT", "150")  # 5-conversation batches take 30-60 s with 12 in flight
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default="v1")
    ap.add_argument("--per-family", type=int, default=150)
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=5)
    ap.add_argument("--max-rounds", type=int, default=8)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "generated")
    a = ap.parse_args()
    factory = Factory(a.version, a.per_family, a.concurrency, a.batch_size, a.out)
    asyncio.run(factory.run(a.max_rounds))


if __name__ == "__main__":
    main()
