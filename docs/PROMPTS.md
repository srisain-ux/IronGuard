# PROMPTS.md: the step-by-step script (lockstep)

> Owner: B (ss). **double = A · ss = B · jcubed = C.**
> Follow this file top to bottom. All three of you move **in lockstep**: everyone finishes their step, everyone merges, everyone syncs, then everyone starts the next step together.

## How every step works

```
STEP n  ──►  each person pastes their prompt(s) in NEW T3 Code thread(s) (new worktree each)
             agents build, then run the FINISH routine on their own (§F)
   │
   ▼
🛑 WAIT  ──►  post "done" in the team chat. Nobody merges until all 3 have said "done".
   │
   ▼
🔀 MERGE ──►  each person pastes the MERGE prompt (§M) in a no-worktree thread → gets a PR link
             humans click: Create PR → teammate approves → ss merges in order double → ss → jcubed
   │
   ▼
🔄 SYNC  ──►  each person pastes the SYNC prompt (§S) → make smoke must be green on all 3 laptops
   │
   ▼
STEP n+1
```

**Thread rules:** one feature = one new thread = one new worktree, branch named exactly as shown (e.g. `a/data`). Pick the model and effort shown in each block's header. Max 3 threads at once.

**Only humans can:** click Create PR / Approve / Merge on GitHub, submit Devpost, text the Photon number from a phone, record the video.

---

## ⓪ MASTER PROMPT (once per person, in your very first thread)

```text
You are a senior engineer on team IronGuard at HackUTD 2026 "Zero Day" (24-hour hackathon; we have 12 build hours).
Read AGENTS.md, docs/MODEL_SPEC.md, docs/PLAYBOOK.md, docs/PROMPTS.md and contracts/ before doing anything. AGENTS.md overrides plugin defaults.

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
- When a feature is done, run the FINISH routine in docs/PROMPTS.md §F without being asked.
Acknowledge with a 5-line plan, then wait for my go.
```

---

## Reusable blocks

### §F · FINISH routine (agents read this themselves; every feature prompt ends with "Then run §F")
1. Run `make validate` and my area's check (A: `make check-ml` · B: `make check-api` · C: `make check-web check-bridge`). Fix every failure and re-run until green.
2. Review your own diff: Claude Code → `/code-review`, then `/ponytail-review branch`; Codex → `$ponytail:ponytail-review`. Fix real bugs, security or privacy issues and contract mismatches; skip style nitpicks.
3. Confirm only files my member letter owns were touched (AGENTS.md §2). Revert anything else and add a line under `## Requests` in my progress file instead.
4. Commit in this worktree: `[<letter>][P<step>] <summary>`. If the pre-commit hook blocks you, fix the cause. Never bypass it.
5. Append to `progress/<letter>.md`: done / skipped / unverified, plus **Handoffs** (anything teammates can now use: exact file names, function signatures, tensor shapes, env vars). Commit it.
6. End with a 5-line report: what works, test results, what's unverified, the branch name, and anything a teammate must do. **Then tell me: "Ready to post DONE in the team chat."** Do not merge into my member branch or main.

### §M · MERGE prompt (paste in a NEW thread with NO worktree, main IronGuard folder · Codex Sol medium or Claude Sonnet medium)
```text
It's merge window <M0|M1|M2|M3|M4>. I am member <A|B|C> (check `git config --get ironguard.member`).
1. List my local branches <letter>/* other than <letter>/main that have commits not yet in <letter>/main. For each, confirm the last commit starts
   with "[<letter>]" and the progress update is committed. Skip (and tell me about) any branch whose worktree has uncommitted changes.
2. Make sure the main folder is clean, then run: git switch <letter>/main && ./scripts/merge-window.sh <all finished branches>
3. Rebase conflict? It can only be in my own files: resolve keeping both intents, git add, git rebase --continue, re-run the script.
   If a conflict is in a file I don't own, STOP and tell me.
4. Checks fail? Fix them on <letter>/main (only in my folders), commit, re-run the script.
5. When it pushes, give me https://github.com/srisain-ux/IronGuard/compare/main...<letter>/main plus a PR title "[<letter>][<window>] ..."
   and a 3-bullet description.
```
**Then humans:** open your link → **Create pull request** → a teammate approves → **ss merges in order: double → ss → jcubed**, always with **Create a merge commit**. Post "merged" in chat.

### §S · SYNC prompt (same no-worktree thread, after ss says all 3 PRs are merged)
```text
All PRs for this merge window are merged into main.
1. Run: git switch <letter>/main && git pull --rebase origin main && git push --force-with-lease
2. Rebase every still-open worktree branch <letter>/* onto <letter>/main (conflicts only in my files; otherwise stop and tell me).
3. Run: cd api && uv sync && cd ../web && pnpm install && cd ../bridge && pnpm install && cd .. && make smoke
4. If smoke fails: say exactly which part and whose folder. If mine, fix it in a new commit on <letter>/main, push, and give me the PR link.
   If someone else's, write the exact error for me to send them.
5. If I'm member B and smoke is green: tick this window's gate in PROGRESS.md with the current time, commit, push b/main, give me the PR link.
6. Tell me "SYNCED, green" so I can post it in the team chat.
```
**Gate passes when all 3 post "SYNCED, green".** If someone is red, only that person fixes it (10-minute limit, otherwise ss reverts their PR on GitHub). Then everyone moves to the next step.

### §X · EXPRESS DROP (the ONLY allowed mid-step merge: ss's data in Step 1, double's model files in Steps 2–3)
```text
Express drop. Commit only what's ready now (B: data/generated/** · A: ml/artifacts/** plus the code needed to load it), run `make validate`
(B also: make validate-data), then from the main folder run: git switch <letter>/main && ./scripts/merge-window.sh <this branch>
Give me the PR link and a one-line message for my teammates about what landed. Then go back to this worktree and keep working.
```
A teammate approves and ss merges it right away. The receiver then pastes into one of their threads: `git switch <letter>/main && git pull --rebase origin main`, then rebase this worktree onto it.

### §R · CONTEXT RESET (when an agent gets slow or confused)
```text
Save state: append to progress/<letter>.md exactly where you are, what's done, what's next, decisions and gotchas. Commit it.
Then give me a 10-line "resume prompt" to paste into a fresh thread to continue this feature.
```

---

# STEP 0 · Setup ✅ (A0, B0, C0 already done)

### A0 · `a/stub` · Codex · GPT-6 Sol · low
```text
Create the ml/ Python package per ml/AGENTS.md using uv (Python 3.11): pyproject with torch (cpu), sentence-transformers, scikit-learn,
numpy, onnx, onnxruntime, jsonschema, pytest, ruff. Create ironguard_ml/ with empty modules from the layout table.
Implement ironguard_ml/stub.py FULLY: load(path) -> StubModel with .score(turns, chloroplasts=[]) returning a dict that validates against
contracts/schemas/score_response.schema.json. Use deterministic keyword heuristics (wrong number → pig_butchering, bank/fraud → bank_impersonation,
mom/new phone → family_emergency, toll/package → toll_delivery, account suspended/code → carrier_support, job/task → job_task),
attention = recency-weighted, locked = risk>=0.7. Also stub chloroplast_train(...) returning a schema-valid manifest with zero weights.
Add tests/test_stub.py validating outputs with jsonschema against the contracts. Then run §F.
```

### B0 · `b/api-skeleton` · Codex · GPT-6 Sol · medium
```text
Create api/ per api/AGENTS.md (uv, Python 3.11, FastAPI, uvicorn, sse-starlette, openai, httpx, jsonschema, pytest, ruff; ironguard-ml as an editable
path dependency on ../ml). Implement every route from api/AGENTS.md. Where the real logic isn't built yet, return the matching file from
contracts/examples/ or call ironguard_ml.stub (IRONGUARD_MODEL=stub). Add GET /v1/events (SSE) with an in-process pub/sub and a POST /v1/events/publish
for the bridge. CORS from CORS_ORIGINS. Add tests/test_smoke.py that hits every route and validates each response against its schema. Then run §F.
```

### C0 · `c/scaffold` · Codex · GPT-6 Sol · medium
```text
Scaffold web/ with Vite + React 18 + TypeScript + Tailwind + react-router-dom + recharts (pnpm). Import src/theme/zero-day.css in main.tsx.
Add routes /phone and /reef. Copy contracts/examples/*.json into src/mocks/ and build a tiny api client that returns mocks when VITE_USE_MOCKS=1.
Generate TS types from contracts/schemas (json-schema-to-typescript) into src/contracts/. The page background must look like the HackUTD Zero Day
deck (night-city gradient, magenta grid floor, scanlines) with an "IRONGUARD" neon-sign wordmark in Orbitron 900.
Scaffold bridge/ (Node 20 + TS + tsx + spectrum-ts, PINNED version) as an ECHO bot on port 8787 that acks webhooks immediately and replies
"IronGuard online 🛡". Read https://photon.codes/docs/webhooks/quickstart and https://docs.photon.codes/spectrum-ts. Then run §F.
```

## 🛑 WAIT → 🔀 MERGE M0 (§M) → 🔄 SYNC (§S)
Gate: `make smoke` green on all 3 laptops. **Contracts are now frozen (add-only).**

---

# STEP 1 · Data and foundations

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A1a, then A1b (same thread is fine) | B1 ‖ B1-t (two threads at once) | C1 |

### A1a · `a/data` · Claude Code · Sonnet 5.5 · high
```text
/ecc:plan "IronGuard data pipeline per docs/MODEL_SPEC.md §2, §3, §4.1"
Implement ironguard_ml/data.py (load JSONL from data/generated/<v>/, data/seed/, data/test_human/; make_prefixes(conv) per the §2 index
conventions; conversation-level stratified 70/15/15 split with seed; job_task excluded from base training when held_out="job_task") and
ironguard_ml/features.py (role-prefixed MiniLM embeddings, L2-normalized, cached by sha1 in ml/.cache/emb/).
Tests: no conversation id in two splits; prefixes respect strike_turn; cache hits return identical vectors.
Also write ~30 seed conversations into data/seed/seed.jsonl (schema-valid; mix of all families + hard negatives) so the pipeline runs before
Nemotron data lands. Then run §F.
```

### A1b · `a/baselines` · Codex · GPT-6 Sol · medium (start after A1a's §F)
```text
Implement ironguard_ml/baselines.py per docs/MODEL_SPEC.md §6.1 (B0 rules, B1 TF-IDF+LR, B2 MiniLM+LR on the latest message, B3 mean-MiniLM+LR),
and a first ironguard_ml/metrics.py + evaluate.py that write ml/artifacts/eval_summary.json in the §6.4 shape for the baselines only
(EWR@k, lead time, strike recall, hard-negative FPR; thresholds at 1% FPR on VAL). Use data/generated/v1 if present on my branch, else data/seed.
Then ask the data-auditor subagent (or do its checks yourself) on the dataset and paste its verdict into progress/A.md. Then run §F.
```

### B1 · `b/algae` · Claude Code · Sonnet 5.5 · high
```text
/ecc:plan "Algae synthetic data factory per docs/MODEL_SPEC.md §3 and §9"
Implement api/ironguard_api/agent/nemotron.py (OpenAI-compatible client for NEMOTRON_BASE_URL; retries + exponential backoff on 429/5xx; 60 s timeout;
strict JSON extraction with one repair retry) and agent/algae.py with a CLI: `uv run python -m ironguard_api.agent.algae --version v1 --per-family 150`.
Steps: sample diversity knobs → generate in batches of 5 conversations (NEMOTRON_GEN_MODEL, temp 0.9) with asyncio.Semaphore(8) → critic pass
(NEMOTRON_AGENT_MODEL, temp 0.2; drop realism < 4 or wrong labels) → dedupe → validate each line against conversation.schema.json →
append to data/generated/v1/<family>.jsonl IMMEDIATELY after each batch (crash-safe). Benign: 900 total, ≥40% hard negatives, same prompt skeleton.
Start the full generation run in the background as soon as it works. As soon as ≥300 valid conversations exist, do an EXPRESS DROP (§X)
so double can train on them, then let generation continue. When the full set is done, run §F.
```

### B1-t · `b/tools` · Codex · GPT-6 Sol · high (in parallel with B1)
```text
Implement api/ironguard_api/agent/tools.py and scrub.py per api/AGENTS.md: lookup_official_contact(brand) from api/data/official_directory.json
(create it with ~25 brands; mark it "curated demo directory"), check_domain(domain) (RDAP via https://rdap.org/domain/<d>: age in days, registrar,
plus Levenshtein/lookalike distance vs official domains), check_number(phone) (normalize E.164; in directory?; fictional 555-01xx range; toll-free
heuristics), scrub_and_report(text) → ReefReport dict with placeholders. Pure, typed functions, each with fixture-based tests (no network; mock httpx).
Then run §F.
```

### C1 · `c/phone` · Codex · GPT-6 Sol · high
```text
Build /phone per web/AGENTS.md and docs/THEME.md on mocks: phone frame; thread list; thread view with bubbles; per-message Trajectory HUD
(risk meter with band WORD + color; "T-2 TURNS TO STRIKE"; LOCKED badge with pulse); Trajectory Compass SVG (6 family directions from
contracts/taxonomy.json compass_deg; needle angle = probability-weighted direction, length = risk); kill-chain strip
(🎣 BAIT ➡ 🎭 PIVOT ➡ 🪝 HOOK ➡ 💸 STRIKE; current stage lit, predicted next dashed); locked links (.zd-locked-link); Cool-Down Shield modal
(10-second breathing countdown before a link can be revealed); Safety Card with next-step buttons; highlight the highest-attention turn as
"this message primed the lock". Accessibility per THEME.md. Demo data: 3 scripted threads (pig butchering, bank impersonation, benign hard
negative) revealed turn by turn with a "next message" button.
Also make sure the Photon echo bot works end to end: give me the exact steps to run `make bridge` + `make tunnel` and register the webhook,
and tell me when to text the number from my phone. Then run §F.
```
**Human tasks in Step 1:** ss submits the **Devpost placeholder before 10:45 PM**. jcubed texts the Photon number. double (and anyone free) hand-writes 10–20 conversations for `data/test_human/` (send them to double; only double commits there).

## 🛑 WAIT → 🔀 MERGE M1 (§M) → 🔄 SYNC (§S)
Gate: data v1 + baseline numbers + phone UI + Photon echo working. If Photon still fails, log the fallback decision in PROGRESS.md.

---

# STEP 2 · The Dragonfly model and the Safeguard agent

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A2 ‖ A2-x | B2 | C2a ‖ C2b |

### A2 · `a/preynet` · Claude Code · **Opus 5.5** · high
```text
/ecc:plan "PreyNet per docs/MODEL_SPEC.md §4 and metrics per §6.2"
Implement preynet.py (Linear 385→128 GELU → causal GRU 128 → CstmdAttention → features 640-d → heads family/next_stage/tts),
train.py (all prefixes, multi-task loss L = CE_f + 0.5·CE_s + 0.5·CE_tts, class weights, AdamW 2e-3, early stop on val EWR@2, seeds 0,1,2),
finish metrics.py (ewr_at_k, lead_time, strike_recall, hard_neg_fpr, flicker_rate, threshold_at_fpr) EXACTLY per the §2 conventions with hand-computed
unit tests, calibrate.py (temperature scaling per head on VAL only, ECE 15 bins, reliability bins), infer.py (load + score + LockOn hysteresis
θ_lock 0.70 / θ_release 0.40 / 2 turns + rule-based evidence on top-attention turns), and evaluate.py writing ml/artifacts/eval_summary.json in
the exact §6.4 shape (baselines B0–B3, PreyNet, ablations, test_human).
As soon as the first trained model loads through infer.load(), do an EXPRESS DROP (§X) of ml/artifacts/ so ss can switch the API to the real model.
Then use the leakage-hunter subagent on data.py, train.py, metrics.py, evaluate.py and fix every CONFIRMED issue. Report the headline numbers
exactly as produced. Then run §F.
```

### A2-x · `a/metrics-check` · Codex · GPT-6 Sol · high (in parallel with A2)
```text
WITHOUT reading ml/ironguard_ml/metrics.py, write ml/tests/test_metrics_crosscheck.py with your own independent implementation of EWR@k and
lead time from docs/MODEL_SPEC.md §2 and §6.2 (index conventions are exact). Generate 200 random flag sequences and assert your results equal
ironguard_ml.metrics within 1e-9 (skip with a clear message if metrics.py isn't merged into my branch yet). If they differ, print the smallest
failing case. Do not modify metrics.py. Then run §F.
```

### B2 · `b/safeguard` · Claude Code · **Opus 5.5** · high
```text
/ecc:plan "Nemotron Safeguard agent per api/AGENTS.md and contracts/schemas/safety_card.schema.json"
Implement agent/safeguard.py: input = ScoreResponse + entities (+ turns only in Photon mode). OpenAI-style tool calling with NEMOTRON_AGENT_MODEL,
max 6 steps: decide tools, call them, observe, then emit SafetyCard JSON. Enforce: confidence = ScoreResponse.risk (overwrite if changed); verdict
from risk + checks; next_steps with reply_codes 1/2/3; locked_links = URLs/numbers that failed checks; cool_down on urgency words; privacy_note
says exactly what left the device. Validate against the schema; on failure retry once, then fall back to a deterministic rule-built card.
Publish "card" events on SSE. Wire POST /v1/agent/safety-card. Tests with a mocked Nemotron client.
When double's express drop of ml/artifacts/ lands on main, pull it and make /v1/score use the real model with IRONGUARD_MODEL=preynet
(stub stays the default when artifacts are missing). Then run §F.
```

### C2a · `c/bridge` · Codex · GPT-6 Sol · high
```text
Implement the full Photon bridge flow in bridge/AGENTS.md: in-memory history per space.id, newline splitting, reply codes 1/2/3 via pending[space.id],
POST /v1/score then /v1/agent/safety-card when risk ≥ 0.35, the exact reply template, every listed edge case, MOCK_API=1 mode, masked previews
to POST /v1/events/publish. Never log message text. Then run §F and tell me exactly what to text the Photon number to test it.
```

### C2b · `c/reef` · Codex · GPT-6 Sol · medium (in parallel with C2a)
```text
Build /reef "Algae Reef Lab" per web/AGENTS.md: live SSE log panel (Roboto Mono, [algae]/[critic]/[train]/[reef] prefixes), live Photon feed
(masked), and 3 charts from GET /v1/metrics: EWR@k lines per model (PreyNet neon pink, baselines lavender/teal), zero-day before/after bar +
sample-efficiency line, reliability diagram. Show "--" when a value is missing. Never hardcode numbers. Zero Day styling per docs/THEME.md.
Then run §F.
```

## 🛑 WAIT → 🔀 MERGE M2 (§M) → 🔄 SYNC (§S)
Gate: forward the first 2 messages of a scam to the Photon number → forecast + Safety Card come back in the thread; the same thread renders in `/phone`.

---

# STEP 3 · Leaf Sheep: zero-day chloroplasts, on device

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A3 | B3 | C3 |

### A3 · `a/chloroplast` · Claude Code · **Opus 5.5** · high
```text
/ecc:plan "Chloroplast trainer + LOFO zero-day experiment + ONNX export per docs/MODEL_SPEC.md §5, §6.3, §7"
Implement chloroplast.train(pos, neg, family_id, label, alert, progress_cb) -> manifest dict (contracts/schemas/chloroplast.schema.json):
frozen PreyNet features → MLP 640→32→1, weighted BCE, 300 AdamW steps, threshold at 1% FPR on held-out synthetic negatives, base64 float32 LE
weights, sha256, size_bytes, train_seconds. Must run < 10 s on a laptop CPU (print timing). Add a reference apply_chloroplast() in infer.py.
Run the LOFO experiment (job_task held out) and the sample-efficiency curve (N = 25/50/100/200); add them to eval_summary.json → zero_day.
Export ONNX (opset 17, dynamic turn axis, outputs family_logits, stage_logits, tts_logits, attention, features) + tests/test_onnx_parity.py
(max abs diff < 1e-4). As soon as parity passes, do an EXPRESS DROP (§X) of ml/artifacts/ and write a Handoff for jcubed in progress/A.md:
input tensor name/shape, output names, temperature.json format, lock-on params. Then run §F.
```

### B3 · `b/zero-day` · Claude Code · Sonnet 5.5 · high
```text
Implement POST /v1/zero-day {alert, n_pos=120, n_neg=120} → job_id (return immediately). Background job: Algae mutation planner (8 axes) →
generate positives + hard negatives → critic → dedupe → ironguard_ml.chloroplast.train(..., progress_cb → SSE "train.progress") → save manifest to
api/store/chloroplasts/<id>.json → SSE "chloroplast.ready" (manifest without weights). Stream "algae.progress" with stage/done/total and a short
sample line. Implement POST /v1/reef/report (validate, re-scrub server-side, append to api/store/reef.jsonl, SSE "reef.report").
Use the stub train() until double's real one is on main, then switch. Pre-train one demo chloroplast (zd_parking_boot) and keep it in api/store
as the demo fallback. Then run §F.
```

### C3 · `c/runtime` · Codex · GPT-6 Sol · **xhigh**
```text
Implement web/src/runtime/ per web/AGENTS.md using double's Handoff in progress/A.md (tensor names, shapes, temperature.json, lock-on params):
embed.ts (transformers.js Xenova/all-MiniLM-L6-v2, mean pool + L2 normalize, "[THEM] "/"[ME] " prefixes), preynet.ts (onnxruntime-web session from
/models/preynet.onnx; input [1, turns, 385]; softmax with temperature; build a score_response-shaped object with runtime "browser"),
lockon.ts (identical hysteresis), chloroplast.ts (decode base64 float32 LE; sigmoid(W2·gelu(W1·f+b1)+b2); fire if ≥ threshold).
Fetch manifests from GET /v1/chloroplasts and render the leaf-sheep avatar: each chloroplast is a glowing green cerata badge with a vitality bar
= 0.5^(age_h/half_life_h) (display only). Add /phone?debug=1 comparing browser vs API scores on the example thread (must match within ±0.02).
Verify no network request contains message text during scoring. In /reef add the zero-day terminal: "> new zero-day alert: _" → POST /v1/zero-day →
stream progress → "CHLOROPLAST ABSORBED · {size} · {s} s". If double's ONNX isn't on main yet, build against the Handoff and test with the stub,
then pull and retest when it lands. Then run §F.
```

## 🛑 WAIT → 🔀 MERGE M3 (§M) → 🔄 SYNC (§S)
Gate: type a new scam in `/reef` → chloroplast in ~2 min → the browser phone flags it, with no message text in DevTools → Network.

# 🧊 FEATURE FREEZE. From here on: bug fixes only.

---

# STEP 4 · Final numbers, clean run, pitch assets

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A4 | B4 | C4 |

### A4 · `a/final` · Claude Code · Sonnet 5.5 · medium
```text
Use the eval-runner subagent, then the leakage-hunter subagent one last time. Produce: 1) the headline sentence from MODEL_SPEC §0 filled ONLY
with eval_summary.json values (mean ± std); 2) a 6-bullet "How we trained it" Devpost section (data, leakage defenses, architecture, calibration,
zero-day, honest limits incl. the cross-generator gap). Put both under Handoffs in progress/A.md for ss and jcubed. Then run §F.
```

### B4 · `b/final` · Claude Code · **Opus 5.5** · high (fresh session)
```text
Simulate a clean machine: clone the repo into a temp folder, follow docs/PLAYBOOK.md §7.3, run make smoke, then walk through the demo script in
PLAYBOOK §10 against the running stack and list every failure with its owner (A/B/C) and the exact error. Fix the ones in my folders.
Then draft the Devpost write-up into progress/B.md: inspiration (the gap), what it does, how we built it (use double's Handoff numbers only),
Nemotron workflows, Photon usage, challenges, what's next (run /ponytail-debt), and the track table from PLAYBOOK §2. Then run §F.
```

### C4 · `c/pitch` · Codex · GPT-6 Luna · medium
```text
Write docs/pitch/demo-script.md (3:00, following PLAYBOOK §10 with exact clicks and spoken lines), docs/pitch/devpost-copy.md (tagline:
"Intercept the scam before the strike."; sections ready to paste) and docs/pitch/shot-list.md for a 2:30 screen recording with captions in the
Zero Day voice. Use ONLY numbers from double's Handoff in progress/A.md. Tell me exactly which screens to capture. Then run §F.
```

## 🛑 WAIT → 🔀 MERGE M4 (§M) → 🔄 SYNC (§S)
Then **ss** pastes into the no-worktree thread:
```text
Tag the release: git switch main && git pull && git tag v1.0-hackutd && git push origin v1.0-hackutd. Confirm the tag is on GitHub.
```

---

# FINISH LINE (humans)
1. **jcubed:** record the demo video (under 3 min) from the shot list; save copies on 2 laptops.
2. **ss:** submit the final Devpost (editable until **12:00 PM**): video, repo link, tracks, copy from `docs/pitch/devpost-copy.md`.
3. **Everyone:** sleep in shifts. Then 10:00–11:30 AM: two timed rehearsals, re-test the Photon number, charge laptops, have a hotspot ready.
4. **Judging 1–4 PM.** Demo from ss's laptop.
