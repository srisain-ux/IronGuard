"""Thin Nemotron client (OpenAI-compatible: vLLM on Brev, or build.nvidia.com as backup).

Env: NEMOTRON_BASE_URL, NVIDIA_API_KEY (scripts/run_api.py loads api/.env). Reads only
message.content; reasoning, if any, comes back separately and is ignored.
"""

import asyncio
import json
import os
import re

import openai

NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}
_client: openai.AsyncOpenAI | None = None


def client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        base, key = os.getenv("NEMOTRON_BASE_URL"), os.getenv("NVIDIA_API_KEY")
        if not (base and key):
            raise RuntimeError("NEMOTRON_BASE_URL and NVIDIA_API_KEY must be set (api/.env)")
        # max_retries=0: we do our own backoff below so it is visible and testable
        _client = openai.AsyncOpenAI(base_url=base, api_key=key, timeout=float(os.getenv("NEMOTRON_TIMEOUT", "60")), max_retries=0)
    return _client


def extract_json(text: str) -> dict:
    """First top-level JSON object in text, tolerating code fences and chatter."""
    text = re.sub(r"```(?:json)?", "", text or "")
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in reply")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("JSON reply is not an object")  # noqa: TRY004  (chat_json catches ValueError)
    return obj


async def chat_message(messages: list[dict], *, model: str, temperature: float, retries: int = 3,
                       top_p: float | None = None, max_tokens: int = 4096,
                       thinking: bool = True, tools: list[dict] | None = None):
    """One completion message (content + tool_calls); exponential backoff on 429 / 5xx /
    connection errors / timeouts."""
    extra = {} if thinking else {"extra_body": NO_THINKING}
    if top_p is not None:
        extra["top_p"] = top_p
    if tools:
        extra["tools"] = tools
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            reply = await client().chat.completions.create(
                model=model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, **extra)
            return reply.choices[0].message
        except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError) as exc:
            last = exc
        except openai.APIStatusError as exc:
            if exc.status_code < 500 and exc.status_code not in (408, 409):
                raise
            last = exc
        if attempt < retries:
            await asyncio.sleep(min(2 ** attempt, 30))
    raise last


async def chat(messages: list[dict], **kwargs) -> str:
    return (await chat_message(messages, **kwargs)).content or ""


async def chat_json(messages: list[dict], **kwargs) -> dict:
    """Strict JSON reply; one repair retry that shows the model its own broken output."""
    text = await chat(messages, **kwargs)
    try:
        return extract_json(text)
    except ValueError:  # JSONDecodeError is a ValueError
        repair = messages + ([{"role": "assistant", "content": text}] if text else []) + [
            {"role": "user", "content": "That was not valid JSON. Reply again with ONLY the "
             "corrected JSON object, no commentary, no code fences."},
        ]
        return extract_json(await chat(repair, **{**kwargs, "temperature": 0.0}))
