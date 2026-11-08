# IronGuard API scaffold

Use `make api-stub` from the repository root (Python 3.11 and uv). The API listens
on port 8000. `make check-api` runs lint and tests; `make smoke` also validates
contracts and checks web/bridge when their package manifests exist.

`pyproject.toml` declares `ironguard-ml` as an editable dependency on `../ml`.
Until member A supplies `ml/pyproject.toml`, `scripts/run_api.py` installs only the
API dependencies in uv's cache. Stub mode uses contract fixtures, labels its
score model `stub/contract-fixture`, and reports `fixture: true` in `/health`.
Once ML lands, normal uv project resolution and `ironguard_ml.stub.load()` are
used automatically. `preynet` mode never falls back to fixtures.

- `POST /v1/score`: `score_request` → `score_response`.
- `POST /v1/agent/safety-card`: `{score, entities, source?: "web" | "photon", text?}`.
  Web mode rejects text. This scaffold returns a demo card, preserves model risk,
  and makes no verification claims. Nemotron and agent tools are not connected.
- `POST /v1/zero-day`: `{alert}` → 202 `{job_id, status: "demo", events_url}`.
  Background work emits an honest `error` event; no training or adapter is claimed.
- `GET /v1/chloroplasts` and `GET /v1/chloroplasts/{id}` read validated manifests
  from `api/store/chloroplasts/*.json`. Stub mode falls back to the contract demo.
  Demo weights are placeholders; do not deploy them for inference.
- `POST /v1/reef/report`: consented `reef_report` → 202 `{accepted: true}`.
  Re-scrubs text and retains a bounded in-memory queue (1,000 reports). The regex
  scrubber includes a small demo name/brand list, not general PII recognition.
- `GET /health`, `GET /v1/metrics`, `GET /models/preynet.onnx`: actual artifacts
  from `IRONGUARD_ARTIFACTS` (relative paths resolve from `api/`). Missing metrics
  return `{available: false, models: {}, display: "--"}`; missing ONNX returns 404.
- `GET /v1/events`: live SSE with named events and JSON `data`, 15-second pings,
  no replay. Each subscriber keeps the latest 100 events and disconnects cleanly.
- `POST /v1/events/publish`: `event` → 202 `{accepted: true}`. Bridge events are
  re-scrubbed; `photon.message` retains only a masked preview up to 60 characters.

`CORS_ORIGINS` is a comma-separated allowlist, defaulting to
`http://localhost:5173`. SSE is process-local: run one worker for this demo.
Forwarded text stays in memory; neither inference requests nor bodies are logged
or written to disk. This scaffold does not call NVIDIA or any external service.
