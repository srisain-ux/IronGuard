"""make nemotron-check: one tiny Nemotron call using api/.env (works for Brev or build.nvidia.com)."""
import os
import sys

from openai import OpenAI

base = os.getenv("NEMOTRON_BASE_URL", "")
key = os.getenv("NVIDIA_API_KEY", "")
model = os.getenv("NEMOTRON_GEN_MODEL", "")
if not (base and key and model):
    sys.exit("❌ api/.env is missing NEMOTRON_BASE_URL, NVIDIA_API_KEY or NEMOTRON_GEN_MODEL. See 'BEFORE STEP 1' in docs/PROMPTS.md.")
print(f"Talking to {base} (model: {model}) ...")
try:
    client = OpenAI(base_url=base, api_key=key, timeout=120)
    reply = client.chat.completions.create(
        model=model, max_tokens=300, temperature=0.2,
        messages=[{"role": "user", "content": "Reply with exactly: NEMOTRON ONLINE"}],
    )
    text = (reply.choices[0].message.content or "").strip()
except Exception as exc:  # show the real reason in plain words
    hint = " Is `make brev-tunnel` running in another Terminal tab?" if "localhost" in base else ""
    sys.exit(f"❌ Nemotron call failed: {exc}.{hint}")
print(f"✅ Nemotron answered: {text[:120]!r}")
