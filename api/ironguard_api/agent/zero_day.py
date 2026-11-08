"""Zero-day job: one-sentence alert -> Algae -> chloroplast adapter (docs/MODEL_SPEC.md §5.1).

plan 8 mutation axes -> batches of positives + hard negatives (generate -> local checks -> critic
-> dedupe) -> ironguard_ml chloroplast train() -> manifest on disk. Progress goes out through the
`emit(kind, data)` callback; only counts and one scrubbed synthetic line, never customer text.

demo adapter:  python -m ironguard_api.agent.zero_day "<alert>" --family zd_parking_boot
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import re
import time
from math import ceil
from pathlib import Path
from uuid import uuid4

from ..contracts import ROOT, validator
from ..scrub import scrub
from . import nemotron
from .algae import (
    CHANNELS,
    CRITIC,
    DEDUPE_COS,
    LEAK,
    PERSONAS,
    SKELETON,
    STAGE_RULES,
    TAXONOMY,
    check,
    cosine,
    fix_stages,
    shingles,
)

AXES = ("pretext", "sender_persona", "opening_hook", "urgency_tactic", "payment_or_link_method",
        "victim_reaction", "writing_style", "brand_or_authority")
PLAN = """You design variations of ONE new text-message scam for a defensive training set.
Scam alert: {alert}
Return ONLY compact JSON: {{"family_id":"zd_short_snake_case","label":"under 60 characters","axes":{{{axes}}}}}
Each axis holds exactly 4 different short values (under 12 words each) describing how this scam can vary.
Never write real phone numbers, domains or names of real people."""
CALL_TIMEOUT = 150  # seconds: a 5-conversation batch takes 30-60 s with 8 in flight
BATCH, ROUNDS, WORKERS, MIN_KEPT = 5, 4, 8, 10  # MIN_KEPT: fewer than this per side is not worth training


class JobError(Exception):
    """Message is safe to show on the public SSE stream."""


def trainer():
    try:
        from ironguard_ml.chloroplast import train
    except ModuleNotFoundError as exc:
        if exc.name != "ironguard_ml.chloroplast":
            raise
        # shortcut: zero-weight placeholder until A lands chloroplast.py; its ids end in "_stub"
        from ironguard_ml.stub import train

        logging.getLogger(__name__).warning("ironguard_ml.chloroplast missing: using the stub trainer")
    return train


def parse_plan(reply: dict, alert: str) -> tuple[str, str, dict]:
    """Everything the planner says is untrusted: keep only well-formed axes, a safe id and label."""
    axes = reply.get("axes")
    if not isinstance(axes, dict):
        raise JobError("Planner returned no mutation axes")
    clean = {}
    for axis in AXES:
        values = axes.get(axis)
        values = [v.strip()[:100] for v in values if isinstance(v, str) and v.strip()] if isinstance(values, list) else []
        if not values:
            raise JobError(f"Planner returned no values for axis {axis}")
        clean[axis] = values[:6]
    family = reply.get("family_id")
    if not (isinstance(family, str) and re.fullmatch(r"zd_[a-z0-9_]{1,40}", family)):
        family = "zd_" + hashlib.sha1(alert.encode()).hexdigest()[:8]
    label = reply.get("label")
    label = label.strip()[:80] if isinstance(label, str) and label.strip() else alert[:77]
    return family, label, clean


def accepted(score: object) -> bool:
    realism = score.get("realism") if isinstance(score, dict) else None
    return (isinstance(realism, (int, float)) and not isinstance(realism, bool) and realism >= 4
            and score.get("label_correct") is True)


class Job:
    def __init__(self, emit, alert: str, n_pos: int, n_neg: int):
        self.emit, self.alert = emit, alert
        self.quota = {False: n_pos, True: n_neg}  # key: hard negative?
        self.kept = {False: [], True: []}
        self.seen = {False: [], True: []}
        self.count = {"plan": 0, "generate": 0, "critique": 0, "dedupe": 0}
        self.gen_model, self.critic_model = os.getenv("NEMOTRON_GEN_MODEL"), os.getenv("NEMOTRON_AGENT_MODEL")
        if not (self.gen_model and self.critic_model):
            raise JobError("NEMOTRON_GEN_MODEL and NEMOTRON_AGENT_MODEL must be set")
        self.failures: list[str] = []
        self.sem = asyncio.Semaphore(WORKERS)  # Brev serves at most 16 sequences
        self.family = self.label = self.axes = None

    def progress(self, stage: str, sample: str | None = None, step: int = 0) -> None:
        self.count[stage] += step
        total = 1 if stage == "plan" else sum(self.quota.values())
        data = {"stage": stage, "done": min(self.count[stage], total), "total": total}
        if sample:
            data["sample"] = scrub(sample)[:80]
        self.emit("algae.progress", data)

    async def plan(self, family_id: str | None, label: str | None) -> None:
        shown = LEAK.sub("security", self.alert)
        prompt = PLAN.format(alert=shown, axes=",".join(f'"{a}":["v1","v2","v3","v4"]' for a in AXES))
        reply = await nemotron.chat_json([{"role": "user", "content": prompt}], model=self.critic_model,
                                         temperature=0.7, max_tokens=1500, thinking=False, timeout=CALL_TIMEOUT)
        self.family, self.label, self.axes = parse_plan(reply, self.alert)
        self.family, self.label = family_id or self.family, label or self.label
        self.progress("plan", f"{len(AXES)} axes: {self.label}", 1)

    def prompt(self, hard: bool, rng: random.Random) -> str:
        pick = {a: rng.choice(self.axes[a]) for a in AXES}
        scenario = LEAK.sub("security", self.alert)
        if hard:
            plot = ("Strike: none. Nobody ever asks for money, codes, links or gift cards. Every conversation is the "
                    f"GENUINE, legitimate counterpart of this situation: {scenario} A real sender writes about the "
                    "same topic but only informs and points to the official app, website or number; no payment link.")
        else:
            varied = "; ".join(f"{a.replace('_', ' ')}: {pick[a]}" for a in AXES[:5])
            plot = (f"Scenario: {scenario} Vary it like this: {varied}. "
                    f"Strike at turn {rng.randint(2, 5)} (1-indexed among THEM turns), the conversation may continue "
                    "a little after it. The victim may hesitate but THEM still goes for the strike.")
        return SKELETON.format(
            family="benign" if hard else self.family, description="a realistic message thread about this situation",
            n=BATCH, ex_stage="benign" if hard else "bait", channel=rng.choice(CHANNELS), persona=rng.choice(PERSONAS),
            plot=plot, style=pick["writing_style"], victim=pick["victim_reaction"], brands=pick["brand_or_authority"],
            stage_rules=STAGE_RULES[not hard])

    async def batch(self, hard: bool) -> None:
        family = "benign" if hard else self.family
        seed = random.SystemRandom().randrange(2**31)
        async with self.sem:
            try:
                out = await nemotron.chat_json(
                    [{"role": "user", "content": self.prompt(hard, random.Random(seed))}], model=self.gen_model,
                    temperature=0.9, top_p=0.95, max_tokens=3500, thinking=False, timeout=CALL_TIMEOUT)
                good = []
                for conv in [c for c in out.get("conversations", []) if isinstance(c, dict)][:BATCH]:
                    fix_stages(conv, family)
                    if check(conv, family) is None:
                        good.append(conv)
                self.progress("generate", step=len(good))
                scores = {}
                if good:
                    listing = json.dumps([{"i": i, "family": family, "turns": [
                        {"sender": t["sender"], "text": t["text"], "stage": t["stage"]} for t in c["turns"]]}
                        for i, c in enumerate(good)])
                    graded = await nemotron.chat_json(
                        [{"role": "user", "content": CRITIC.format(convs=listing)}], model=self.critic_model,
                        temperature=0.2, max_tokens=1500, thinking=False, timeout=CALL_TIMEOUT)
                    scores = {int(s["i"]): s for s in graded.get("scores", [])
                              if isinstance(s, dict) and str(s.get("i")).isdigit()}
            except Exception as exc:  # noqa: BLE001  one bad batch must not kill the job; the next round refills
                self.failures.append(type(exc).__name__)
                logging.getLogger(__name__).warning("zero-day batch failed: %s", type(exc).__name__)
                return
        self.progress("critique", step=len(good))
        for i, conv in enumerate(good):
            self.add(hard, conv, scores.get(i))

    def add(self, hard: bool, conv: dict, score: dict | None) -> None:
        if not accepted(score) or len(self.kept[hard]) >= self.quota[hard]:
            return
        rec = {"id": f"{self.family}_{uuid4().hex}",
               "family": "benign" if hard else self.family, "hard_negative": hard,
               "channel": conv.get("channel") if conv.get("channel") in TAXONOMY["channels"] else "sms",
               "turns": [{"sender": t["sender"], "text": t["text"].strip(), "stage": t["stage"]}
                         for t in conv["turns"]],
               "strike_turn": None if hard else next(i for i, t in enumerate(conv["turns"]) if t["stage"] == "strike"),
               "source": {"generator": "nemotron", "model": self.gen_model,
                          "prompt_id": "zero_day"}}
        fp = shingles(rec)
        if any(cosine(fp, other) > DEDUPE_COS for other in self.seen[hard]):
            return
        self.seen[hard].append(fp)
        self.kept[hard].append(rec)
        self.progress("dedupe", f"{'neg' if hard else 'pos'}: {rec['turns'][0]['text']}", 1)

    async def generate(self) -> None:
        for _ in range(ROUNDS):
            jobs = [hard for hard in (False, True)
                    for _ in range(ceil(max(0, self.quota[hard] - len(self.kept[hard])) * 1.4 / BATCH))]
            if not jobs:
                return
            self.failures.clear()
            await asyncio.gather(*(self.batch(hard) for hard in jobs))
            if len(self.failures) == len(jobs):  # fail fast instead of hammering a dead endpoint
                raise JobError(f"Every Nemotron call failed ({self.failures[0]})")


async def run_job(emit, alert: str, n_pos: int, n_neg: int, store: Path, *,
                  family_id: str | None = None, label: str | None = None) -> dict:
    """Run the whole pipeline; returns the manifest after saving it to store/<id>.json."""
    started = time.monotonic()
    job = Job(emit, alert, n_pos, n_neg)
    await job.plan(family_id, label)
    await job.generate()
    pos, neg = job.kept[False], job.kept[True]
    if min(len(pos), len(neg)) < MIN_KEPT:
        raise JobError(f"Algae kept only {len(pos)} positive and {len(neg)} negative conversations; not training")
    generated = time.monotonic() - started
    loop = asyncio.get_running_loop()

    def progress_cb(step, total, loss):  # runs in the training thread; the bus is not thread-safe
        loop.call_soon_threadsafe(emit, "train.progress", {"step": int(step), "total": int(total), "loss": float(loss)})

    manifest = await asyncio.to_thread(trainer(), pos=pos, neg=neg, family_id=job.family, label=job.label,
                                       alert=alert, progress_cb=progress_cb)
    if not validator("chloroplast").is_valid(manifest):
        raise JobError("Trainer returned an invalid chloroplast manifest")
    manifest["metrics"]["generate_seconds"] = round(generated, 1)
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{manifest['id']}.json"  # id matches ^cp_[a-z0-9_]+$, so no path tricks
    tmp = path.with_suffix(f".{uuid4().hex}.tmp")  # unique, so concurrent jobs never share a temp file
    tmp.write_text(json.dumps(manifest))
    tmp.replace(path)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("alert")
    ap.add_argument("--family")
    ap.add_argument("--label")
    ap.add_argument("--n-pos", type=int, default=120)
    ap.add_argument("--n-neg", type=int, default=120)
    ap.add_argument("--store", type=Path, default=ROOT / "api" / "store" / "chloroplasts")
    a = ap.parse_args()
    os.environ.setdefault("NEMOTRON_TIMEOUT", "150")
    manifest = asyncio.run(run_job(lambda kind, data: print(kind, json.dumps(data)[:160], flush=True),
                                   a.alert, a.n_pos, a.n_neg, a.store, family_id=a.family, label=a.label))
    print("saved", a.store / f"{manifest['id']}.json", manifest["metrics"])


if __name__ == "__main__":
    main()
