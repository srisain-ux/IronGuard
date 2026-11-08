import asyncio
import json

from ironguard_api.agent import algae
from ironguard_api.contracts import validator


def conv(texts, senders="tmtmtm", stages=("bait", "bait", "pivot", "pivot", "strike", "strike"), family="bank_impersonation"):
    return {"family": family, "channel": "sms", "turns": [
        {"sender": {"t": "them", "m": "me"}[s], "text": x, "stage": st} for s, x, st in zip(senders, texts, stages)]}


TEXTS = ["hi it is your bank", "who", "we saw a login", "ok", "send the code to 555-0142", "no"]


def test_check_accepts_good_and_rejects_bad():
    assert algae.check(conv(TEXTS), "bank_impersonation") is None
    assert algae.check(conv(["Fraud alert"] + TEXTS[1:]), "bank_impersonation") == "leak-word"
    assert algae.check(conv(TEXTS[:4] + ["call 214-555-0987", "no"]), "bank_impersonation") == "real-looking-contact"
    assert algae.check(conv(TEXTS[:4] + ["go to evil.com", "no"]), "bank_impersonation") == "real-looking-contact"
    assert algae.check(conv(TEXTS[:4] + ["go to pay.example.com", "no"]), "bank_impersonation") is None
    assert algae.check(conv(TEXTS[:3]), "bank_impersonation") == "length"
    assert algae.check(conv(TEXTS, stages=("bait",) * 6), "bank_impersonation") == "stage"  # no strike
    assert algae.check(conv(TEXTS, stages=("bait", "bait", "hook", "hook", "pivot", "pivot")), "bank_impersonation") == "stage"


def test_fix_stages_follows_contract_convention():
    c = conv(TEXTS, stages=("bait", "strike", "pivot", None, "strike", "hook"))
    algae.fix_stages(c, "bank_impersonation")
    assert [t["stage"] for t in c["turns"]] == ["bait", "bait", "pivot", "pivot", "strike", "strike"]
    after = conv(TEXTS, "tmtmtt", ("bait", "bait", "pivot", "pivot", "strike", "hook"))
    algae.fix_stages(after, "bank_impersonation")
    assert after["turns"][5]["stage"] == "strike" and algae.check(after, "bank_impersonation") is None
    b = conv(["a", "b", "c", "d"], "tmtm", ("bait",) * 4, "benign")
    algae.fix_stages(b, "benign")
    assert {t["stage"] for t in b["turns"]} == {"benign"} and algae.check(b, "benign") is None


def test_cosine_flags_near_duplicates():
    a, b, c = (algae.shingles(conv(t)) for t in (TEXTS, TEXTS[:5] + ["no thanks"], ["totally", "different", "words", "here", "for", "you"]))
    assert algae.cosine(a, a) > 0.99 and algae.cosine(a, b) > algae.DEDUPE_COS and algae.cosine(a, c) == 0


def test_batch_writes_valid_line_then_resumes(monkeypatch, tmp_path):
    for k in ("NEMOTRON_GEN_MODEL", "NEMOTRON_AGENT_MODEL"):
        monkeypatch.setenv(k, "nemotron")
    replies = iter([{"conversations": [conv(TEXTS), conv(TEXTS[:3] + ["x", "y", "z"], stages=("bait",) * 6)]},
                    {"scores": [{"i": 0, "realism": 4, "label_correct": True}]}])

    async def fake_call(self, *a, **kw):
        return next(replies)

    monkeypatch.setattr(algae.Factory, "call", fake_call)
    f = algae.Factory("t", 1, 2, 5, tmp_path)
    asyncio.run(f.batch(("bank_impersonation", False)))
    lines = (tmp_path / "t" / "bank_impersonation.jsonl").read_text().splitlines()
    rec = json.loads(lines[0])
    assert len(lines) == 1 and validator("conversation").is_valid(rec) and rec["strike_turn"] == 4
    assert f.drops["stage"] == 1
    again = algae.Factory("t", 1, 2, 5, tmp_path)  # resume: quota already met, fingerprint loaded
    assert again.remaining(("bank_impersonation", False)) == 0 and len(again.seen["bank_impersonation"]) == 1
