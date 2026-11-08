# PROMPTS.md: copy-paste prompts for every thread

> Owner: B. **How to use:** paste the **Master Prompt** as the first message of each member's first thread (or rely on AGENTS.md, which every agent reads automatically). Then, for each feature, open a **new T3 Code thread in a new worktree** and paste that phase's block. The header of each block says which tool, model and effort to pick.

---

## ⓪ MASTER PROMPT (shared context: paste once per member)

```text
You are a senior engineer on team IronGuard at HackUTD 2026 "Zero Day" (24-hour hackathon; we have 12 build hours).
Read AGENTS.md, docs/MODEL_SPEC.md, docs/PLAYBOOK.md and contracts/ before doing anything. AGENTS.md overrides plugin defaults.

WHAT WE'RE BUILDING
IronGuard intercepts multi-turn text scams BEFORE the strike (the turn where the scammer sends the link or asks for money, codes or gift cards).
The MODEL is the product. Everything else exists to show it and act on it.
1) Dragonfly / PreyNet: a causal, multi-task sequence model over MiniLM turn embeddings (Linear → GRU → CSTMD1-style attention → heads for
   family, next kill-chain stage, turns-to-strike). Calibrated with temperature scaling, with an honest "uncertain" band and lock-on hysteresis.
   Biology: dragonflies intercept prey with internal predictive models (Mischiati et al. 2015), encode prey direction as a population vector
   across 8 pairs of descending neurons (Gonzalez-Bellido et al. 2013), and their CSTMD1 neuron locks on to one target and is primed by earlier
   targets on the same trajectory (Wiederman & O'Carroll 2013; Lancer et al. 2019). We mirror these as forecast heads, a Trajectory Compass,
   and attention + lock-on.
2) Leaf Sheep / Chloroplasts (klepto-distillation): Costasiella kuroshimae eats Avrainvillea algae and keeps only the chloroplasts, which are
   short-lived, so it must keep feeding. Our version: a one-sentence zero-day alert → Nemotron ("algae") generates and self-critiques synthetic
   conversations → we train a ~82 KB adapter head on PreyNet's 640-d features in under 10 s → phones download only that head and run inference
   on device. No customer text is used for training or sent to the cloud by default. Adapters show a vitality half-life and get refreshed from the reef.
3) Safeguard Agent (NVIDIA "beyond a chatbot"): Nemotron with real tool calls (official-contact lookup, RDAP domain check, number check,
   PII-scrub-and-report) turns a forecast into a schema-validated Safety Card with 1-tap next steps. It never invents confidence;
   confidence = model risk.
4) Photon: a real iMessage/SMS number. Users forward a thread and get the forecast + Safety Card back in the same thread, then reply 1/2/3 to act
   (human-in-the-loop). This is an opt-in cloud mode, and we say so in the reply.

THE GAP WE FILL
Existing filters ask "is this message a scam?" and react at the strike. The strongest shipping system we know of (Google Messages Scam Detection
with on-device Gemini Nano) is reported to run on recent flagship Android only. We (a) forecast with measurable LEAD TIME and calibrated
confidence, (b) adapt to zero-day scams in minutes without customer data, and (c) reach any phone through Photon and act through verified next steps.
Our headline metrics: EWR@k (early-warning rate at 1% false alarms), lead time (turns of warning before the ask), ECE, the zero-day before/after,
and the cross-generator gap on a human-written test set. Never fabricate a number; every number comes from ml/artifacts/eval_summary.json.

TRACKS: T-Mobile "Safe Signal" (protect before, during and after; honest confidence; privacy by design; our own synthetic data),
NVIDIA Nemotron "beyond a chatbot" (multi-step agents + tools), Photon (real channel, human-in-the-loop, edge cases, traction).

STYLE: The UI must look like it came out of the HackUTD Zero Day deck: neon night city, indigo/violet (#1b1445, #2c214a, #4f3288), neon pink
"ZERO DAY" sign (#e83f8f), T-Mobile magenta grid floor (#e20074), teal panels, cream titles (#f8f3ec), Orbitron headings, Roboto Mono HUD,
Inter body. Breach vocabulary: "INCIDENT 0x01 // TRAJECTORY LOCKED", "T-2 TURNS TO STRIKE", "CHLOROPLAST ABSORBED · 82 KB · 4.8 s".
Emoji kill-chain strip: 🎣 BAIT ➡ 🎭 PIVOT ➡ 🪝 HOOK ➡ 💸 STRIKE. Tokens are in web/src/theme/zero-day.css.

HOW WE WORK (non-negotiable)
- I am member <A|B|C> (check: git config --get ironguard.member). Only touch my paths from AGENTS.md §2; the pre-commit hook enforces it.
- Contracts in contracts/ are the only interface between members. Frozen at M0; additive-only after that.
- Build against mocks/stubs until the real dependency lands. Use Ponytail (least code that works); use ECC for plan → review.
- Small commits on my worktree branch "<letter>/<feature>", message "[X][P#] summary". Never touch main.
- Finish every task by updating progress/<X>.md with done / skipped / unverified.
Acknowledge with a 5-line plan for my first task, then wait for my go.
```

---

## Member A: Dragonfly (ML)

### A0 · P0 · stub + skeleton · Codex · GPT-6 Sol · low
```text
Create the ml/ Python package per ml/AGENTS.md using uv (Python 3.11): pyproject with torch (cpu), sentence-transformers, scikit-learn,
numpy, onnx, onnxruntime, jsonschema, pytest, ruff. Create ironguard_ml/ with empty modules from the layout table.
Implement ironguard_ml/stub.py FULLY: load(path) -> StubModel with .score(turns, chloroplasts=[]) returning a dict that validates against
contracts/schemas/score_response.schema.json. Use deterministic keyword heuristics (wrong number → pig_butchering, bank/fraud → bank_impersonation,
mom/new phone → family_emergency, toll/package → toll_delivery, account suspended/code → carrier_support, job/task → job_task),
attention = recency-weighted, locked = risk>=0.7. Also stub chloroplast_train(...) returning a schema-valid manifest with zero weights.
Add tests/test_stub.py validating outputs with jsonschema against the contracts. `make check-ml` must pass. Update progress/A.md.
```

### A1 · P1 · data pipeline + baselines · Claude Code · Sonnet 5.5 · high (then Codex Sol medium for baselines)
```text
/ecc:plan "IronGuard data pipeline and baselines per docs/MODEL_SPEC.md §3, §4.1, §6.1"
Implement ironguard_ml/data.py (load JSONL from data/generated/<v>/, data/seed/, data/test_human/; make_prefixes(conv) per the §2 index
conventions; conversation-level stratified 70/15/15 split with seed; job_task excluded from base training when held_out="job_task"),
ironguard_ml/features.py (role-prefixed MiniLM embeddings, L2-normalized, cached by sha1 in ml/.cache/emb/), and ironguard_ml/baselines.py (B0–B3).
Tests: no conversation id appears in two splits; prefixes respect strike_turn; cache hit returns identical vectors.
Until data/generated/v1 lands, use data/seed/. Then run the data-auditor subagent on the dataset and paste its verdict into progress/A.md.
```

### A2 · P2 · PreyNet + metrics + calibration · Claude Code · Opus 5.5 · high
```text
/ecc:plan "PreyNet per docs/MODEL_SPEC.md §4 and metrics per §6.2"
Implement preynet.py (Linear 385→128 GELU → causal GRU 128 → CstmdAttention → features 640-d → heads family/next_stage/tts),
train.py (all prefixes, multi-task loss L = CE_f + 0.5·CE_s + 0.5·CE_tts, class weights, AdamW 2e-3, early stop on val EWR@2, seeds 0,1,2),
metrics.py (ewr_at_k, lead_time, strike_recall, hard_neg_fpr, flicker_rate, threshold_at_fpr) EXACTLY per the §2 conventions, with hand-computed
unit tests, calibrate.py (temperature scaling per head on VAL only, ECE 15 bins, reliability bins), infer.py (load + score + LockOn
hysteresis θ_lock 0.70 / θ_release 0.40 / 2 turns + rule-based evidence on top-attention turns), evaluate.py writing
ml/artifacts/eval_summary.json in the exact §6.4 shape (baselines B0–B3, PreyNet, ablations, test_human).
Then run the leakage-hunter subagent on data.py, train.py, metrics.py, evaluate.py and fix every CONFIRMED issue.
Commit artifacts at the merge window only. Report the headline numbers in progress/A.md, exactly as produced.
```

### A2-x · P2 · independent metric cross-check · Codex · GPT-6 Sol · high (separate thread)
```text
WITHOUT reading ml/ironguard_ml/metrics.py, implement ml/tests/test_metrics_crosscheck.py containing your own independent implementation of
EWR@k and lead time from docs/MODEL_SPEC.md §2 and §6.2 (index conventions are exact). Generate 200 random synthetic flag sequences and
assert your results equal ironguard_ml.metrics within 1e-9. If they differ, print the smallest failing case. Do not modify metrics.py.
```

### A3 · P3 · chloroplast + zero-day experiment + export · Claude Code · Opus 5.5 · high
```text
/ecc:plan "Chloroplast trainer + LOFO zero-day experiment + ONNX export per docs/MODEL_SPEC.md §5, §6.3, §7"
Implement chloroplast.train(pos, neg, family_id, label, alert, progress_cb) -> manifest dict (schema: contracts/schemas/chloroplast.schema.json):
frozen PreyNet features → MLP 640→32→1, weighted BCE, 300 AdamW steps, threshold at 1% FPR on held-out synthetic negatives, base64 float32 LE
weights, sha256, size_bytes, train_seconds. It must run in under 10 s on a laptop CPU (print timing). Add a reference apply_chloroplast() in infer.py.
Run the LOFO experiment (job_task held out) and the sample-efficiency curve (N = 25/50/100/200); add them to eval_summary.json → zero_day.
Export ONNX (opset 17, dynamic turn axis, outputs family_logits, stage_logits, tts_logits, attention, features) + tests/test_onnx_parity.py
(max abs diff < 1e-4). Write a Handoff in progress/A.md for C: input tensor name/shape, output names, temperature.json format, lock-on params.
```

### A4 · P4 · final numbers · Claude Code · Sonnet 5.5 · medium
```text
Run the eval-runner subagent, then the leakage-hunter subagent one final time. Produce docs-ready numbers: 1) the headline sentence from
MODEL_SPEC §0 filled ONLY with eval_summary.json values (mean ± std), 2) a 6-bullet "How we trained it" section for Devpost (data, leakage
defenses, architecture, calibration, zero-day, honest limits incl. the cross-generator gap). Put both in progress/A.md under Handoffs for C and B.
```

---

## Member B: Algae (agents, API, integration)

### B0 · P0 · repo + API skeleton · Codex · GPT-6 Sol · medium
```text
Create api/ per api/AGENTS.md (uv, Python 3.11, FastAPI, uvicorn, sse-starlette, openai, httpx, jsonschema, pytest, ruff; ironguard-ml as an editable
path dependency on ../ml). Implement every route from api/AGENTS.md. Where the real logic isn't built yet, return the matching file from
contracts/examples/ or call ironguard_ml.stub (IRONGUARD_MODEL=stub). Add GET /v1/events (SSE) with an in-process pub/sub and a POST /v1/events/publish
for the bridge. CORS from CORS_ORIGINS. Add tests/test_smoke.py that hits every route and validates each response against its schema.
`make api-stub` and `make smoke` must pass. Update progress/B.md.
```

### B1 · P1 · Algae data factory · Claude Code · Sonnet 5.5 · high
```text
/ecc:plan "Algae synthetic data factory per docs/MODEL_SPEC.md §3 and §9"
Implement api/ironguard_api/agent/nemotron.py (OpenAI-compatible client for NEMOTRON_BASE_URL; retries + exponential backoff on 429/5xx; 60 s timeout;
strict JSON extraction with one repair retry) and agent/algae.py with a CLI: `uv run python -m ironguard_api.agent.algae --version v1 --per-family 150`.
Steps: sample diversity knobs → generate in batches of 5 conversations (NEMOTRON_GEN_MODEL, temp 0.9) with asyncio.Semaphore(8) → critic pass
(NEMOTRON_AGENT_MODEL, temp 0.2; drop realism < 4 or wrong labels) → dedupe → validate each line against conversation.schema.json →
append to data/generated/v1/<family>.jsonl IMMEDIATELY after each batch (crash-safe). Benign: 900 total, ≥40% hard negatives using the same
prompt skeleton. Print progress. Ship the first 300 conversations by H2:30 as an express data PR. Then ask the data-auditor subagent for a verdict.
```

### B1-t · P1 · Safeguard tools · Codex · GPT-6 Sol · high
```text
Implement api/ironguard_api/agent/tools.py and scrub.py per api/AGENTS.md: lookup_official_contact(brand) from api/data/official_directory.json
(create it with ~25 brands; mark it "curated demo directory"), check_domain(domain) (RDAP via https://rdap.org/domain/<d>: age in days,
registrar, plus Levenshtein/lookalike distance vs official domains), check_number(phone) (normalize E.164; in-directory?; fictional 555-01xx range;
toll-free heuristics), scrub_and_report(text) → ReefReport dict with placeholders. Pure functions, typed, each with fixture-based tests (no network:
mock httpx). `make check-api` green.
```

### B2 · P2 · Safeguard agent loop · Claude Code · Opus 5.5 · high
```text
/ecc:plan "Nemotron Safeguard agent per api/AGENTS.md and contracts/schemas/safety_card.schema.json"
Implement agent/safeguard.py: input = ScoreResponse + entities (+ turns only in Photon mode). Use OpenAI-style tool calling with
NEMOTRON_AGENT_MODEL, max 6 steps: decide which tools to call, call them, observe, then emit a SafetyCard JSON. Enforce:
confidence = ScoreResponse.risk (overwrite if the model changes it); verdict from the risk + checks; next_steps with reply_codes 1/2/3; locked_links
= all URLs/numbers that failed checks; cool_down when urgency words appear; privacy_note says exactly what left the device. Validate against the
schema; on failure retry once, then fall back to a deterministic rule-built card. Publish "card" events on SSE. Wire POST /v1/agent/safety-card.
Switch /v1/score to the real model when ml/artifacts exists (IRONGUARD_MODEL=preynet). Tests with a mocked Nemotron client.
```

### B3 · P3 · zero-day job · Claude Code · Sonnet 5.5 · high
```text
Implement POST /v1/zero-day {alert, n_pos=120, n_neg=120} → job_id (return immediately). Background job: Algae mutation planner (8 axes) →
generate positives + hard negatives → critic → dedupe → ironguard_ml.chloroplast.train(..., progress_cb → SSE "train.progress") → save the manifest to
api/store/chloroplasts/<id>.json → SSE "chloroplast.ready" (manifest without weights). Stream "algae.progress" with stage/done/total and a short
sample line. Also implement POST /v1/reef/report (validate, re-scrub server-side, append to api/store/reef.jsonl, SSE "reef.report").
Pre-train one demo chloroplast (zd_parking_boot) and keep it in api/store as the demo fallback.
```

### B4 · P4 · integration + submission · Claude Code · Opus 5.5 · high (fresh session)
```text
Fresh clone on a second laptop → follow docs/PLAYBOOK.md §7.3 → make smoke → run the full demo script (§10) and list every failure with its owner.
Then draft the Devpost: inspiration (the gap), what it does, how we built it (link MODEL_SPEC numbers from A's handoff), Nemotron workflows,
Photon usage, challenges, what's next (from /ponytail-debt), and the track alignment table from PLAYBOOK §2.
```

---

## Member C: Leaf Sheep (UI + Photon), Codex only

### C0 · P0 · scaffold + theme + Photon echo · Codex · GPT-6 Sol · medium (echo: high)
```text
Scaffold web/ with Vite + React 18 + TypeScript + Tailwind + react-router-dom + recharts (pnpm). Import src/theme/zero-day.css in main.tsx
(already provided). Add routes /phone and /reef. Copy contracts/examples/*.json into src/mocks/ and build a tiny api client that returns mocks
when VITE_USE_MOCKS=1. Generate TS types from contracts/schemas (json-schema-to-typescript) into src/contracts/ (commit them; regenerate only
when contracts change). The page background must look like the HackUTD Zero Day deck (night-city gradient, magenta grid floor, scanlines) with an
"IRONGUARD" neon-sign wordmark in Orbitron 900.
Separately, scaffold bridge/ (Node 20 + TS + tsx + spectrum-ts, PINNED version) as an ECHO bot on port 8787 that acks webhooks immediately and
replies "IronGuard online 🛡". Read the Photon docs: https://photon.codes/docs/webhooks/quickstart and https://docs.photon.codes/spectrum-ts.
Run `make tunnel` and register the webhook. Text the number from a real phone. Update progress/C.md.
```

### C1 · P1 · phone UI + HUD · Codex · GPT-6 Sol · high
```text
Build /phone per web/AGENTS.md and docs/THEME.md on mocks: a phone frame; thread list; thread view with bubbles; per-message Trajectory HUD
(risk meter with band WORD + color; "T-2 TURNS TO STRIKE"; LOCKED badge with a pulse); a Trajectory Compass SVG (6 family directions from
contracts/taxonomy.json compass_deg; needle angle = probability-weighted direction, length = risk); the kill-chain emoji strip
(🎣 BAIT ➡ 🎭 PIVOT ➡ 🪝 HOOK ➡ 💸 STRIKE; current stage lit, predicted next stage dashed); locked links (.zd-locked-link); a Cool-Down Shield modal
(a 10-second breathing countdown before any link can be revealed); a Safety Card with next-step buttons; highlight the turn with the highest
attention as "this message primed the lock". Accessibility per THEME.md. Demo data: script 3 threads (pig butchering, bank impersonation,
benign hard negative) that reveal turn by turn with a "next message" button.
```

### C2 · P2 · bridge → API + Reef Lab · Codex · GPT-6 Sol · high (Reef: medium)
```text
Bridge: implement the full flow in bridge/AGENTS.md: in-memory history per space.id, newline splitting, reply codes 1/2/3 via pending[space.id],
POST /v1/score then /v1/agent/safety-card when risk ≥ 0.35, the exact reply template, all listed edge cases, MOCK_API=1 mode, and publishing masked
previews to POST /v1/events/publish. Never log message text.
Web: build /reef "Algae Reef Lab": a live SSE log panel (Roboto Mono, [algae]/[critic]/[train]/[reef] prefixes), a Photon live feed (masked),
and 3 charts from GET /v1/metrics: EWR@k lines per model (PreyNet in neon pink, baselines in lavender/teal), a zero-day before/after bar +
sample-efficiency line, and a reliability diagram. Show "--" when a value is missing. Never hardcode numbers.
```

### C3 · P3 · on-device runtime + leaf sheep · Codex · GPT-6 Sol · xhigh
```text
Implement web/src/runtime/ per web/AGENTS.md using A's Handoff in progress/A.md (tensor names, shapes, temperature.json, lock-on params):
embed.ts (transformers.js Xenova/all-MiniLM-L6-v2, mean pool + L2 normalize, "[THEM] "/"[ME] " prefixes), preynet.ts (onnxruntime-web session from
/models/preynet.onnx; input [1, turns, 385]; softmax with temperature; build a score_response-shaped object with runtime "browser"),
lockon.ts (identical hysteresis), chloroplast.ts (decode base64 float32 LE; sigmoid(W2·gelu(W1·f+b1)+b2); fire if ≥ threshold).
Fetch chloroplast manifests from GET /v1/chloroplasts and render the leaf-sheep avatar: each chloroplast is a glowing green cerata badge
with a vitality bar = 0.5^(age_h/half_life_h) (display only). Add /phone?debug=1 to compare browser vs API scores on the example thread
(must match within ±0.02). Confirm in the DevTools Network tab that NO request contains message text during scoring.
In /reef add the zero-day terminal: "> new zero-day alert: _" → POST /v1/zero-day → stream progress → "CHLOROPLAST ABSORBED · {size} · {s} s".
```

### C4 · P4 · demo + Devpost assets · Codex · GPT-6 Luna · medium
```text
Write docs/pitch/demo-script.md (3:00, following PLAYBOOK §10 with exact clicks and lines), docs/pitch/devpost-copy.md (tagline:
"Intercept the scam before the strike."; sections ready to paste), and a shot list for a 2:30 screen recording with captions in the Zero Day
voice. Use ONLY numbers from A's handoff. Capture screenshots of /phone (locked trajectory), /reef (charts) and the Photon thread.
```
