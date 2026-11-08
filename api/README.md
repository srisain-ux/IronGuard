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
- `POST /v1/zero-day`: `{alert, n_pos=120, n_neg=120}` (10-300 each) -> 202
  `{job_id, status: "queued", events_url}`; 429 while 2 jobs run. The background job
  (`agent/zero_day.py`) plans 8 mutation axes, generates positives + hard negatives,
  critiques, dedupes, trains and saves `api/store/chloroplasts/<id>.json`. SSE:
  `algae.progress {stage, done, total, sample?}`, `train.progress`, `chloroplast.ready`
  (manifest without weights) or `error`. Trainer: `ironguard_ml.chloroplast.train`, or
  the zero-weight `ironguard_ml.stub.train` (ids end in `_stub`) until A lands it.
  Demo adapter: `python -m ironguard_api.agent.zero_day "<alert>" --family zd_parking_boot`.
- `GET /v1/chloroplasts` and `GET /v1/chloroplasts/{id}` read validated manifests
  from `api/store/chloroplasts/*.json`. Stub mode falls back to the contract demo.
  Demo weights are placeholders; do not deploy them for inference.
- `POST /v1/reef/report`: consented `reef_report` → 202 `{accepted: true}`.
  Re-scrubs text, appends to `api/store/reef.jsonl` (gitignored, stops at 5 MB) and keeps a bounded in-memory queue (1,000 reports). The regex
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
or written to disk. Routes do not call NVIDIA or external verification by default.

Safeguard tools are plain typed functions in `ironguard_api/agent/tools.py`:

- `lookup_official_contact(brand)` returns a contact or `None`, plus the label
  **curated demo directory** and its limitation notice. The 25-brand reference
  lives in `data/official_directory.json`; unknown brands are never guessed.
  Display directory matches as "verified against our curated directory".
- `check_domain(domain)` normalizes a DNS hostname (including IDNA), queries
  `https://rdap.org/domain/<domain>` and follows registry referrals with a
  5-second HTTP timeout. Results include registration age in days, registrar,
  official-domain/subdomain matches and full-hostname Levenshtein edit distance
  to the closest official domain. Distances 1–2 flag possible lookalikes.
  `rdap_status` distinguishes `ok`, `not_found` and `unavailable`; missing or
  unusable age/registrar data stays `None`. These checks do not prove safety.
  The optional timezone-aware `now` argument makes date calculations repeatable.
- `check_number(phone)` returns E.164 format or `None`, directory matches,
  North American fictional `555-0100`–`555-0199` and toll-free flags. Bare
  10-digit numbers assume US/Canada; international numbers require `+`.
  Extensions and vanity numbers are rejected. Format does not verify assignment,
  and caller ID can be spoofed even when it matches an official phone number.
- `scrub_and_report(text)` builds a local `ReefReport` dict. Call only after
  explicit reporting consent; it does not obtain consent, submit, queue or log.
  Channel is `other`, family is `unknown` and stages are empty until the caller
  supplies real metadata. Text is scrubbed before truncation to 1,500 characters.
  Brand names/aliases come from the directory; names use a small demo list.
  This is pattern masking, not general PII recognition.

Tools are not yet wired into the Safeguard loop. Their tests use a saved RDAP
fixture and mocked httpx; they make no external network requests.
