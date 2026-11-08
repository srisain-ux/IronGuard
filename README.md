# Reef Guard

Multi-turn text scam forecasting built for HackUTD 2026 “Zero Day.”

Reef Guard analyzes how a conversation develops and predicts the scam family, next stage, and remaining turns before a **strike**: the first request for money, credentials, a verification code, a gift card, or a suspicious link interaction.

The core model, **PreyNet**, runs locally in the browser. An optional Photon bridge provides iMessage/SMS access through server-side inference. Nemotron powers entity verification and synthetic data generation for new scam patterns.

## Components

- **PreyNet / Dragonfly** — causal sequence model with family, next-stage, and turns-to-strike prediction heads.
- **Chloroplasts / Leaf Sheep** — small adapter heads trained on synthetic conversations to recognize new scam families without retraining the base model.
- **Algae** — Nemotron pipeline for generating, critiquing, and deduplicating synthetic training conversations.
- **Safeguard** — tool-calling agent that checks claimed brands, domains, and phone numbers, then builds a safety card.
- **Photon bridge** — opt-in iMessage/SMS interface for forwarding suspicious conversations.
- **Web app** — local inference interface at `/phone` and evaluation/event dashboard at `/reef`.

## Stack

- **ML:** Python 3.11, PyTorch, sentence-transformers, scikit-learn, ONNX.
- **API:** FastAPI, Pydantic, JSON Schema, server-sent events.
- **Web:** React, TypeScript, Vite, Tailwind CSS, Recharts, Transformers.js, ONNX Runtime Web.
- **Bridge:** Node.js, TypeScript, Spectrum SDK, Photon Beta API.
- **Teacher model:** Nemotron through an OpenAI-compatible endpoint, either self-hosted on NVIDIA Brev or NVIDIA’s hosted API.

## Quick start

### Requirements

- Python 3.11
- [uv](https://docs.astral.sh/uv/)
- Node.js 20.12+
- pnpm; package manifests specify `12.16.1`
- `make`

Photon credentials and a Nemotron endpoint are optional for the browser mock demo.

### Install

```bash
git clone https://github.com/srisain-ux/Reef Guard.git
cd Reef Guard

pnpm --dir web install
pnpm --dir bridge install
uv sync --project ml --python 3.11
```

### Run the mock demo

```bash
VITE_USE_MOCKS=1 make web
```

Open:

- `http://localhost:5173/phone` — scripted conversations and forecast UI.
- `http://localhost:5173/reef` — dashboard with mock events.

Mock mode uses bundled contract fixtures. It does not perform model inference, contact verification, or adapter training.

To run the API with a stub model, use a separate terminal:

```bash
make api-stub
```

The API listens on `http://localhost:8000`. API dependencies are resolved by the launch script.

### Run real inference

Start the API and web app in separate terminals:

```bash
make api
```

```bash
VITE_USE_MOCKS=0 make web
```

The web startup script stages `preynet.onnx`, `temperature.json`, and matching runtime WASM files. Typed messages are scored in the browser; the API supplies metrics, events, and adapter manifests.

The first inference requires downloading the MiniLM encoder from Hugging Face. Once loaded, inference can continue in the open page without network access. A fresh offline launch is not supported.

Check API mode before treating a response as a real forecast:

```bash
curl http://localhost:8000/health
```

The API can fall back to the stub when model weights are missing. Confirm that `model` is `preynet`.

## Model

### Input and architecture

Each turn receives a sender prefix, `[THEM]` or `[ME]`, before embedding.

1. MiniLM produces a normalized 384-dimensional embedding.
2. A sender indicator produces a 385-dimensional turn vector.
3. PreyNet processes up to 12 turns, keeping the most recent turns when the thread is longer.
4. A linear projection and causal GRU produce sequential hidden states.
5. Attention pooling combines those states into a 640-dimensional feature vector.
6. Three prediction heads produce family, next-stage, and turns-to-strike distributions.

The browser uses `Xenova/all-MiniLM-L6-v2` through Transformers.js and runs the exported PreyNet model through ONNX Runtime Web.

### Outputs

A forecast includes:

- Calibrated scam risk: `1 − P(benign)`.
- Family probabilities and the selected family.
- Predicted next stage.
- Turns-to-strike bucket: `0`, `1`, `2`, `3+`, or `none`.
- Confidence band: `low`, `uncertain`, or `high`.
- Warning lock state.
- Attention weights, evidence, and adapter hits.

Temperature scaling is fitted on validation data. Warning hysteresis prevents a single harmless-looking turn from immediately clearing a warning. The lock threshold comes from the calibration artifact; release requires risk below `0.40` for two consecutive sender turns.

Attention identifies influential turns. It is not proof that those turns caused the prediction.

### Taxonomy

Base classes are:

```
benign
pig_butchering
bank_impersonation
family_emergency
job_task
toll_delivery
carrier_support
```

Conversation stages are:

```
benign → bait → pivot → hook → strike
```

The authoritative definitions are in [`contracts/taxonomy.json`](contracts/taxonomy.json). Full architecture, labeling, and evaluation rules are in [`docs/MODEL_SPEC.md`](docs/MODEL_SPEC.md).

## Zero-day adaptation

A submitted scam description starts a background job:

1. Nemotron plans variations across eight mutation axes.
2. Algae generates scam conversations and legitimate hard negatives.
3. Validation, critique, and deduplication filter the generated records.
4. A small `640 → 32 → 1` adapter trains on frozen PreyNet features.
5. The API stores and publishes a validated adapter manifest.
6. The browser downloads the adapter and applies it locally.

Progress is emitted through `algae.progress`, `train.progress`, `chloroplast.ready`, and `error` events.

Adapters include a threshold, encoded weights, training metadata, and a half-life. The displayed vitality decays with age; it does not disable inference.

The current API accepts at most two concurrent jobs. A working Nemotron endpoint and compatible model artifacts are required.

## API

Default address: `http://localhost:8000`

Request and response schemas live in [`contracts/schemas`](contracts/schemas). Shared examples live in [`contracts/examples`](contracts/examples).

- `GET /health` — active model mode and fixture status.
- `POST /v1/score` — score a conversation, optionally selecting adapters.
- `POST /v1/agent/safety-card` — build a safety card from a forecast and extracted entities.
- `POST /v1/zero-day` — queue synthetic generation and adapter training.
- `GET /v1/chloroplasts` — list adapter manifests.
- `GET /v1/chloroplasts/{id}` — retrieve an adapter.
- `GET /v1/metrics` — return the evaluation artifact.
- `GET /v1/events` — subscribe to live SSE events.
- `POST /v1/events/publish` — publish a bridge event.
- `POST /v1/reef/report` — accept a consented, scrubbed pattern report.
- `GET /models/preynet.onnx` — download the exported model.

Example scoring request using the public fixture:

```bash
curl http://localhost:8000/v1/score \
  -H 'Content-Type: application/json' \
  --data-binary @contracts/examples/score_request.photon.json
```

This endpoint is intended for Photon and developer tools. Normal browser scoring does not submit message text to it.

Safeguard checks use a curated contact directory, phone-format checks, and RDAP domain information. Nemotron selects tools and writes wording; application code controls verdicts, action payloads, and verification claims. Agent failures return a rule-built card.

## Configuration

Use service-local environment files. Never commit credentials.

**`api/.env`**

- `Reef Guard_MODEL` — `stub` or `preynet`.
- `Reef Guard_ARTIFACTS` — artifact directory; defaults to `../ml/artifacts`.
- `CORS_ORIGINS` — allowed browser origins.
- `NEMOTRON_BASE_URL` — OpenAI-compatible endpoint.
- `NVIDIA_API_KEY` — endpoint credential.
- `NEMOTRON_GEN_MODEL` — synthetic generation model.
- `NEMOTRON_AGENT_MODEL` — agent and critique model.

**`web/.env`**

- `VITE_API_URL` — defaults to `http://localhost:8000`.
- `VITE_USE_MOCKS` — `1` for fixtures, `0` for local inference and live services.

**`bridge/.env`**

- `PHOTON_PROJECT_ID`
- `PHOTON_SECRET`
- `PHOTON_WEBHOOK_SECRET`
- `Reef Guard_API_URL` — defaults to `http://localhost:8000`.
- `MOCK_API` — `1` for API fixtures, `0` for the live API.

See [`.env.example`](.env.example) for endpoint examples.

## Photon bridge

Configure `bridge/.env`, then run these commands in separate terminals:

```bash
make api
```

```bash
make bridge
```

```bash
make tunnel
```

Register `<public-tunnel-url>/webhook` with Photon, save the signing secret in `bridge/.env`, and restart the bridge.

The bridge supports Spectrum projects and Photon Beta projects. It verifies webhook signatures, deduplicates deliveries, and serializes work within each conversation.

Thread history stays in memory, is limited to 20 turns per conversation, and expires after 30 minutes of inactivity.

Replies support:

- `1` — consent to submit a scrubbed pattern report and receive blocking instructions.
- `2` — retrieve an available official contact or verification instructions.
- `3` — explain the forecast and safety card.

Reef Guard cannot block a sender through the phone’s messaging app. See [`bridge/README.md`](bridge/README.md) for transport-specific setup and troubleshooting.

## Evaluation

Results are stored in [`ml/artifacts/eval_summary.json`](ml/artifacts/eval_summary.json).

The artifact generated on November 8, 2026 reports:

- **1,773 conversations**, with 259 in the synthetic test split.
- **47.80% EWR@2** for PreyNet: the share of scam conversations warned by the second turn, before the strike.
- **2.35 ± 0.12 turns** mean lead time across three training seeds.
- **0.77%** benign test conversation false-positive rate.

Thresholds are selected on validation data under a 1% empirical false-positive cap. Reported test rates are measured separately.

The artifact contains **zero human test conversations**. Cross-generator results are unavailable. Its zero-day experiment is marked unavailable because it uses a same-generator proxy split; those values should not be presented as validated zero-day performance.

The shipped base model includes all six scam families. A leave-one-family-out experiment requires a separately trained base model.

## Development

Run from the repository root:

```bash
make validate
make check-ml
make check-api
make check-web
make check-bridge
make smoke
```

Additional web and bridge checks:

```bash
pnpm --dir web test
pnpm --dir web build
pnpm --dir bridge test
```

ML pipeline commands regenerate artifacts:

```bash
make train
make eval
make export
```

`make export` also runs ONNX/PyTorch parity tests. Browser/API comparison is available at `/phone?debug=1` using a fixed public conversation.

For repository contributors, read [`AGENTS.md`](AGENTS.md) before editing. It defines path ownership, branch naming, contract compatibility, and required checks.

## Repository layout

```
api/                  FastAPI service, Safeguard, Algae, scrubber
bridge/               Photon webhook and messaging bridge
contracts/            JSON Schemas, examples, taxonomy
data/
  generated/          Synthetic datasets
  seed/               Seed conversations
  test_human/         Test-only human/cross-generator conversations
docs/                 Model specification, setup, theme, pitch
ml/
  Reef Guard_ml/       Training, inference, calibration, adapters, metrics
  artifacts/         Checkpoints, ONNX export, calibration, evaluation
  tests/             Model and pipeline tests
scripts/              Validation, environment checks, development tools
web/                  Browser runtime and React interface
progress/             Per-member implementation logs
```

## Privacy and current limits

Browser message scoring stays on-device and has no API inference fallback. Browser safety cards and block/report actions currently remain local demonstrations.

Photon is an explicit cloud mode. Forwarded text reaches the bridge and API; masked text may also reach Nemotron during safety-card generation. Raw thread history is not persisted by the application.

Consented reef reports are re-scrubbed and stored separately. The scrubber uses patterns and a limited name list, so masking is not a guarantee of anonymization. Customer messages and reports are not used for model training by default.

Contact-directory matches, phone formatting, domain age, and lookalike checks provide verification signals; they cannot establish that a sender or domain is safe.

The API uses process-local events and job state. Run one worker for the current demo deployment.
