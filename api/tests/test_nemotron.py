import asyncio
from types import SimpleNamespace

import httpx
import openai
import pytest

from ironguard_api.agent import nemotron


def test_extract_json_tolerates_fences_and_chatter():
    assert nemotron.extract_json('Sure!\n```json\n{"a": [1, {"b": 2}]}\n```\nbye') == {"a": [1, {"b": 2}]}
    with pytest.raises(ValueError):
        nemotron.extract_json("no json here")


def test_chat_json_repairs_once(monkeypatch):
    replies = iter(['{"a": ', '{"a": 1}'])
    seen = []

    async def fake_chat(messages, **kw):
        seen.append(messages)
        return next(replies)

    monkeypatch.setattr(nemotron, "chat", fake_chat)
    assert asyncio.run(nemotron.chat_json([{"role": "user", "content": "x"}])) == {"a": 1}
    assert len(seen) == 2 and seen[1][-2]["content"] == '{"a": '  # repair shows the broken reply


def test_chat_retries_429_then_gives_up(monkeypatch):
    calls = []

    async def create(**kw):
        calls.append(kw)
        if len(calls) < 3:
            raise openai.RateLimitError(
                "slow down", response=httpx.Response(429, request=httpx.Request("POST", "http://x")), body=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])

    async def no_sleep(_):
        pass

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(nemotron, "client", lambda: fake)
    monkeypatch.setattr(nemotron.asyncio, "sleep", no_sleep)
    assert asyncio.run(nemotron.chat([], model="m", temperature=0, thinking=False)) == "ok"
    assert len(calls) == 3 and calls[0]["extra_body"] == nemotron.NO_THINKING

    calls.clear()
    with pytest.raises(openai.RateLimitError):
        asyncio.run(nemotron.chat([], model="m", temperature=0, retries=1))
    assert len(calls) == 2
