# api/AGENTS.md: Member B (Algae, agent, API, integration). Root AGENTS.md rules still apply.

## Stack
Python 3.11, `uv`, FastAPI + uvicorn, `sse-starlette`, `openai` SDK pointed at NVIDIA (`NEMOTRON_BASE_URL`), httpx (RDAP), pydantic v2, pytest, ruff. `ironguard-ml` is a **path dependency** (`uv add --editable ../ml`). Never copy ML code into api.

## Layout (`ironguard_api/`)
| File | Responsibility |
|---|---|
| `main.py` | app factory, CORS (`CORS_ORIGINS`), routes, loads the model once: `IRONGUARD_MODEL=stub\|preynet` |
| `routes/score.py` | `POST /v1/score` → `model.score()` |
| `routes/agent.py` | `POST /v1/agent/safety-card` → Safeguard agent |
| `routes/zero_day.py` | `POST /v1/zero-day` → background job: Algae → `chloroplast.train` → store manifest → SSE |
| `routes/chloroplasts.py` | `GET /v1/chloroplasts`, `GET /v1/chloroplasts/{id}` (JSON files in `api/store/chloroplasts/`, gitignored except demo seeds) |
| `routes/reef.py` | `POST /v1/reef/report` (validates `reef_report`, re-scrubs, appends to the reef queue) |
| `routes/meta.py` | `GET /health`, `GET /v1/metrics` (serves `ml/artifacts/eval_summary.json`), `GET /models/preynet.onnx` (static) |
| `events.py` | in-process pub/sub → `GET /v1/events` (SSE; shapes in `event.schema.json`) |
| `agent/nemotron.py` | thin client: retries with backoff, JSON-mode / strict-JSON parsing, request timeout of 60 s |
| `agent/algae.py` | **Algae workflow** (multi-step): plan mutation axes → generate in parallel batches → critique (drop realism < 4 or wrong label) → dedupe → validate against `conversation.schema.json` → write `data/generated/<version>/*.jsonl` |
| `agent/safeguard.py` | **Safeguard workflow** (tool-calling loop, max 6 steps): input = ScoreResponse + entities (never raw text in web mode) → tools → `SafetyCard` (schema-validated; on invalid output retry once, then fall back to a rule-built card) |
| `agent/tools.py` | `lookup_official_contact(brand)` (from `api/data/official_directory.json`), `check_domain(domain)` (RDAP age + lookalike distance vs official domains), `check_number(phone)`, `scrub_and_report(text)` |
| `scrub.py` | PII scrubber: regex for phone, email, URL, amounts, @handles, plus a name list; placeholders `[PHONE] [EMAIL] [URL] [AMOUNT] [NAME] [BRAND]` |

## Rules specific to the API and agent
- **The agent never invents confidence.** `SafetyCard.confidence` = `ScoreResponse.risk`. The model decides *how sure*; the agent decides *what to do*.
- **Privacy:** `/v1/agent/safety-card` from the web receives entities + the ScoreResponse only. Photon mode may include text (the user forwarded it); keep it in memory and never write it to disk or logs.
- Every tool is a plain function with a unit test that uses fixtures (no network in tests; mock RDAP).
- The official directory is a **curated demo file**; say so in the UI ("verified against our curated directory").
- **Return a 2xx fast; do slow work in the background** (zero-day jobs, Photon replies). Long requests hit timeouts and retries.
- Rate limits: batch generation with `asyncio.Semaphore(8)` and exponential backoff on 429. Cache each generated batch to disk immediately so a crash never loses data.
