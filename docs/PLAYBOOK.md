# PLAYBOOK.md: how three people ship IronGuard in 12 hours without merge hell

> Owner: B. **For what to do right now, follow `docs/PROMPTS.md` (the step-by-step script with the current clock times).** This file is the background: why the stack, roles, merge rules and model choices are what they are. The clock times in §5 were the original plan.
> Companion files: `AGENTS.md` (rules for agents), `docs/MODEL_SPEC.md` (the model), `docs/PROMPTS.md` (copy-paste prompts), `PROGRESS.md` (phase gates), `docs/THEME.md` (look).

---

## 1. Verdict: feasible with 3 people, *if* you keep this scope

| Keep (core) | Simplify | Cut / stretch only |
|---|---|---|
| PreyNet trajectory model + baselines + honest metrics | Chloroplast = **adapter head** (not LoRA) | Real LoRA on PreyNet (stretch, §5.3 of MODEL_SPEC) |
| Algae synthetic data factory (Nemotron) | Official directory = curated JSON of about 25 brands | Auto-replying "decoy honeypot" from the user's number (unsafe, so cut) |
| Zero-day chloroplast loop, live | Lock links in the UI (no bank integration) | "Freeze payments" (no bank API; cut) |
| Safeguard agent with 4 real tools | Browser = the "phone" (no native app) | Photon voice calls (only after everything else works) |
| Photon forward-to-check with reply codes | One API service hosts both ML and agent | Cloud deployment (run locally + tunnel) |

**Why it fits:** the model is small (about 160k params, trains on CPU in minutes); data generation runs in the background while code gets written; every service has a mock from H1, so nobody waits on anybody.

---

## 2. Track alignment (put this table in the Devpost)

| Track | What judges look for (from the deck) | How IronGuard delivers |
|---|---|---|
| **T-Mobile "Safe Signal"** | Any approach; scam detection is a core piece, not the whole product; go beyond classification; clear next steps, honest confidence, privacy by design; *you create the data*; judged on creativity, impact, usability, security & privacy, detection quality. "Customers feel protected **before, during and after** a threat." | **Before:** PreyNet forecasts at turn 1–2 (lead-time metric). **During:** locked links, the Cool-Down Shield, verified official numbers, 1-tap steps. **After:** consented anonymous report → reef → a chloroplast protects everyone. Calibrated confidence + an "uncertain" band. On-device inference. 100% team-made synthetic data plus a human-written test set. |
| **NVIDIA "Nemotron Beyond a Chatbot"** | Beyond a chatbot; multi-step workflows (agents that plan and execute); tool integration; real-world applicability. Prizes: 1st 2× RTX 5080 + $200 Brev; 2nd 1× RTX 5080 + $200 Brev + swag | **There is no chat window.** Two agents: (1) the **Algae red-team factory** (plan mutation axes → generate → self-critique → dedupe → hand to the trainer) and (2) the **Safeguard agent** (tool loop: `lookup_official_contact`, `check_domain` via RDAP, `check_number`, `scrub_and_report` → schema-validated Safety Card). Nemotron's output *trains a model*: it's the teacher in a distillation pipeline. |
| **Photon** | Must integrate Photon 2.0 / API; real human-in-the-loop collaboration; vision (hybrid intelligence), craft, depth (edge cases), traction ("running with real users tomorrow"), extensive use of Photon. $700 / $300 / $400 voice | A real iMessage/SMS number: forward a suspicious thread → forecast + safety card in the same thread → reply 1/2/3 to act. Multi-turn memory per space, edge cases handled (images, duplicates, API down), consented reports. Anyone can text it tomorrow. |
| *(General: Design Track, if allowed)* | Design | The full Zero Day aesthetic matching the deck's own fonts and palette |

⚠ **Track cap:** an older, unofficial HackUTD guide said "up to two sponsor tracks". Confirm in the Hackerpack or on Discord **at H0**. If the cap is two, submit to T-Mobile + NVIDIA and keep Photon as the technology (still in the demo). Log the decision in `PROGRESS.md`.

---

## 3. Tech stack (decided, so don't re-litigate)

| Layer | Choice | Why |
|---|---|---|
| Model | **PyTorch** PreyNet (GRU + attention), **sentence-transformers `all-MiniLM-L6-v2`** embeddings, scikit-learn baselines | Small, CPU-trainable in minutes, same embedder runs in the browser |
| Model runtime (phone) | **transformers.js v3** (`Xenova/all-MiniLM-L6-v2`) + **onnxruntime-web** (PreyNet ONNX) + JS chloroplast heads | Real on-device inference, which is our privacy proof |
| API | **FastAPI** + `sse-starlette`, Python 3.11, **uv** | One process hosts ML + agents; uv is fast with a lockfile per service |
| LLM | **NVIDIA Nemotron** via build.nvidia.com (OpenAI-compatible, `integrate.api.nvidia.com/v1`): **Nemotron 3 Nano** (`nvidia/nemotron-3-nano-30b-a3b`) for bulk generation, **Nemotron 3 Super** for critic + tool calling (verify the ID on build.nvidia.com) | Nano is trained for tool calling and structured output and is fast; Super for harder agent steps |
| Phone UI + Reef Lab | **Vite + React + TS + Tailwind**, recharts | Fast to scaffold; Codex is strong here |
| Messaging | **Photon** via `spectrum-ts` (Node 20 + TS) | Required for the Photon track; the TS SDK means C owns it |
| Realtime | SSE (`GET /v1/events`) | Simpler than websockets |
| Storage | JSON/JSONL files on disk | Nothing to set up; Ponytail-approved |
| Tunnel | `cloudflared` | Public HTTPS for Photon's webhook |
| Repo hygiene | GitHub, per-member branches, pre-commit ownership hook, CODEOWNERS, CI contract check | §7 |
| Agent tooling | **T3 Code** (GUI + worktrees for parallel threads), **Claude Code** (A, B), **Codex** (A, B, C), **ECC** (workflow), **Ponytail** (minimal code) | §6 |

### Architecture
```
                      ┌──────────── Member C ─────────────┐      ┌──────────── Member B ─────────────────┐
 iPhone/Android ──SMS/iMessage──► Photon ──webhook──► bridge (Node, :8787) ──HTTP──► api (FastAPI, :8000)
                      └───────────────────────────────────┘      │  /v1/score ─► ironguard_ml (A)          │
                                                                  │  /v1/agent/safety-card ─► Nemotron    │
 Browser "phone" (web, :5173) ──(no message text!)──────────────► │  /v1/zero-day ─► Algae ─► chloroplast │
   transformers.js + onnxruntime-web + chloroplast heads          │  /v1/chloroplasts, /v1/metrics, SSE   │
   (downloads preynet.onnx + chloroplast manifests only)          └───────────────────────────────────────┘
```

---

## 4. Who does what

### Member A (double): "Dragonfly" (ML lead) · Claude Code + Codex
**Owns the model, the thing the judges score most.** PreyNet, baselines, metrics, calibration, chloroplast trainer, ONNX export, eval charts' data, the seed and human test sets, and `MODEL_SPEC.md`. Writes the "How we trained it" section of the Devpost and presents that part of the pitch.

### Member B (ss): "Algae" (agents, API, integration lead) · Claude Code + Codex
Contracts (already drafted in this kit), the FastAPI service, both Nemotron workflows (Algae factory, Safeguard agent + tools), the zero-day job, reef reports. **Runs every merge window and is the demo host.** Owns root files, scripts and CI.

### Member C (jcubed): "Leaf Sheep" (UI + Photon) · Codex
The Zero Day phone UI and the Reef Lab, the on-device runtime (transformers.js + onnxruntime-web + chloroplast heads), the Photon bridge, the demo video, Devpost copy and screenshots.

**Everyone, in idle minutes:** write 10 realistic conversations for `data/test_human/` (send them to A in a Request or a DM; A commits them). Human-written test data is our best defense against "your model only learned Nemotron's style".

---

## 5. Timeline (anchored at H0 = 6:00 PM Saturday; shift if you start later)

| Hour | Clock | A: Dragonfly | B: Algae | C: Leaf Sheep | Gate |
|---|---|---|---|---|---|
| H0:00 | 6:00 PM | Install tools; `ml/` skeleton; **stub.py** | Create the GitHub repo from this kit; branches; settings; contracts review call (15 min, everyone) | Install; Photon beta signup **first**; Vite scaffold + theme | |
| H1:00 | 7:00 PM | | **M0 merge window** | | **M0**: smoke green ×3 |
| H1–H4 | 7–10 PM | Loader, splitter, embeddings, baselines B0–B3 on seed data → on v1 data | **Algae v1**: first 300 conversations by H2:30 (express data drop), full set by H3:30; tools + tests | Phone shell, thread view, HUD + compass on mocks; Photon echo bot | |
| — | **≤ 10:45 PM** | | **Submit the Devpost placeholder** (title, team, tracks, 2-line description) | | Initial deadline 11 PM |
| H4:00 | 10:00 PM | | **M1 merge window** (Olympics 9:30–10:30: send one person max, or skip) | | **M1** |
| H4–H7 | 10 PM–1 AM | **PreyNet** train ×3 seeds, calibration, lock-on, eval v2 | Safeguard agent loop; real model behind `/v1/score` | Bridge → api → reply + reply codes; Reef dashboard charts | |
| H7:00 | 1:00 AM | | **M2 merge window** | | **M2**: Photon end-to-end |
| H7–H9:30 | 1–3:30 AM | Chloroplast trainer, LOFO + sample efficiency, ONNX export + parity | Zero-day job + SSE progress; reef reports | Browser runtime + chloroplast badges + live training view | |
| H9:30 | 3:30 AM | | **M3 merge window** | | **M3**: live zero-day on device |
| H10:00 | 4:00 AM | **FEATURE FREEZE** | | | |
| H10–H11 | 4–5 AM | Final eval; charts data; leakage-hunter pass | Clean-clone run on a 2nd laptop; fix list | Record the demo video; Devpost copy; screenshots | |
| H11:00 | 5:00 AM | | **M4 final merge**, tag `v1.0-hackutd` | | **M4** |
| H11–H12 | 5–6 AM | | **Submit the final Devpost** (it can still be edited until 12:00 PM) | | Done by 6 AM |
| — | 6–10 AM | **Sleep in shifts** (the Hackerpack lists sleeping rooms) | | | |
| — | 10–11:30 AM | Two timed rehearsals; re-test the Photon number; charge laptops | | | Deadline 12 PM · Judging 1–4 PM |

---

## 6. Running the agents: T3 Code + Claude Code + Codex + ECC + Ponytail

### 6.1 Install, per laptop (H0, about 20 min, in parallel)
```bash
# everyone
curl -LsSf https://astral.sh/uv/install.sh | sh          # Python env manager
brew install node@20 cloudflared gh                       # macOS; use winget/apt equivalents elsewhere
corepack enable                                           # gives you pnpm
npm i -g @openai/codex && codex login                     # Codex
brew install --cask t3-code                               # T3 Code desktop (or: npx t3@latest)
# A and B only
curl -fsSL https://claude.ai/install.sh | bash && claude  # Claude Code (log in on first run)
```

**Ponytail** (minimal-code skill):
- Claude Code, as **two separate prompts**: `/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`
- Codex: `codex plugin marketplace add DietrichGebert/ponytail` then `codex plugin add ponytail@ponytail`, then open `/hooks` in Codex, trust its two hooks, and start a new thread.

**ECC** (Everything Claude Code; official repo `affaan-m/ECC`, plugin `ecc@ecc`, npm `ecc-universal`. Beware of malware-laced mirrors):
- Claude Code (A, B): `/plugin marketplace add https://github.com/affaan-m/ECC` then `/plugin install ecc@ecc`. Rules don't ship with the plugin; copy only the packs you need into your **user** folder (not the repo):
  ```bash
  git clone --depth 1 https://github.com/affaan-m/ECC ~/ecc-src
  mkdir -p ~/.claude/rules/ecc && cp -R ~/ecc-src/rules/common ~/ecc-src/rules/python ~/.claude/rules/ecc/
  ```
- Codex (everyone): `npx ecc-universal@2.2.3 install --guided --harness codex --dry-run`, check what it would do, then `npx ecc-universal@2.2.3 install --guided`. **Pick one install path per tool; don't stack installs.** Trust its hooks in `/hooks`.
- **Context hygiene:** ECC warns that MCP tool descriptions eat your context window. Keep fewer than 10 MCP servers on; run `/context-budget` if the agent gets forgetful.

**How they split the work:** Ponytail decides *how much code* gets written; ECC gives *workflow* commands. Our `AGENTS.md` overrides both on testing policy.

| Moment | Claude Code | Codex |
|---|---|---|
| Start a feature | `/ecc:plan "<feature from PROMPTS.md>"` → approve → implement | Paste the PROMPTS.md block; ask it to plan first |
| Build is broken | `/build-fix` | ask: "fix the build; minimal change" |
| Before a risky change | `/checkpoint` | commit first |
| Before a PR | `/code-review` then `/ponytail-review branch` | `$ponytail:ponytail-review` + an ECC review skill |
| Context is filling up | `/save-session` + update `progress/<you>.md` | update progress file; new thread |
| P4 write-up | `/ponytail-debt` → list of shortcuts for "What's next" | same skill via `$ponytail:` |

### 6.2 T3 Code workflow (each person runs T3 Code on their own laptop)
1. Open the repo in T3 Code. In **Settings → Providers**, confirm `codex` (and `claude` for A and B) are detected and logged in.
2. **One thread = one feature = one worktree.** Create threads with the "new worktree" option, branch `<letter>/<feature>` (e.g. `a/preynet`). Run at most **3 threads at once** per person; more makes your merges painful.
3. Pick the model and effort per thread from §8.
4. When a thread's feature is done and checked, merge its branch into your member branch (`a/main`) with `./scripts/merge-window.sh a/preynet`, or merge locally and keep working.
5. Clean up finished worktrees in **Settings → Worktrees → Cleanup**.
6. **Usage-limit tip (A and B):** T3 Code's author reports that running Claude through it drains the 5-hour window faster. Do long Opus sessions in Claude Code directly; use T3 Code for Codex threads and quick Claude tasks.

### 6.3 Subagents
- **Claude Code** subagents are in `.claude/agents/`: `data-auditor` (Haiku), `leakage-hunter` (Opus), `eval-runner` (Sonnet), `contract-guardian` (Haiku). Say "use the leakage-hunter subagent on ml/" or let Claude pick them. They run in parallel and keep your main context clean.
- **Codex:** if your Codex version supports subagents or agent roles (ECC configures `explorer`, `reviewer` and `docs_researcher` roles in `.codex/agents/`), use them for read-only review and research. **Otherwise the reliable parallelism is several T3 Code threads in separate worktrees.** That's how C should work.

---

## 7. The merge-proof protocol (why last time failed, and how this prevents it)

Merge pain comes from four things: **two people editing the same file**, **interfaces changing silently**, **big-bang merges at the end**, and **lockfile/format churn**. Each rule below kills one of them.

### 7.1 Structural rules (set up at H0 by B)
1. **Ownership by directory** (`AGENTS.md` §2), **enforced** by `scripts/check_ownership.sh` as a pre-commit hook in every worktree, plus CODEOWNERS, plus CI on every PR. Tested: a commit touching another member's file is rejected with instructions.
2. **No shared mutable files.** Each member has their own `progress/<X>.md`; only B touches `PROGRESS.md`, and only in merge windows.
3. **Contracts first, frozen at M0.** All cross-boundary data is defined in `contracts/` (7 JSON Schemas + examples + `taxonomy.json`). After M0: additive changes only, approved by all three in the PR.
4. **Mocks from H1:** web on mocks, api on the stub model, bridge on mock API. Nobody waits; integration is just switching a flag.
5. **No root manifests.** Separate `ml/pyproject.toml`, `api/pyproject.toml`, `web/package.json`, `bridge/package.json`, each with its own lockfile and owner. No lockfile conflicts are possible.
6. **Generated data and model artifacts have one writer each** (B for `data/generated/`, A for `ml/artifacts/`), and `.gitattributes` marks them `merge=binary`.
7. **Formatting is per area** (ruff in Python areas, prettier in web/bridge), `eol=lf` everywhere (`.gitattributes`), so you never get whole-file diffs from line endings or formatters.
8. **No notebooks in git.**

### 7.2 GitHub settings (B, at H0)
- Repo → Settings → General → Pull Requests: **allow merge commits only** (turn off squash and rebase merging). *Squash merges break the "rebase my branch on main" step at the next window.*
- Branch protection on `main`: require a PR, require the `ci` check, require 1 approval (code owner), no force-push, no deletion.
- Create the long-lived branches `a/main`, `b/main`, `c/main` from `main`. Add teammates as collaborators.

### 7.3 Daily driver (each member)
```bash
git clone git@github.com:<org>/ironguard.git && cd ironguard
./scripts/install-hooks.sh A            # your letter; also sets pull.rebase, rerere, autostash
git switch a/main                        # your member branch (b/main, c/main)
# T3 Code threads create worktrees off a/main, named a/<feature>
```

### 7.4 Merge window (M0, M1, M2, M3, M4): 15 minutes, run by B
| T− | Who | Step |
|---|---|---|
| −10 min | everyone | Stop starting new work; let agents finish; commit in your worktrees |
| −5 min | everyone | `./scripts/merge-window.sh <your finished worktree branches>`: merges them into your member branch, rebases on `origin/main`, runs checks, pushes. Open or refresh your PR (`[A][M2] …`) |
| 0 | B | Merge in this order, running `make smoke` after each: **contracts** (if any) → **A (ml)** → **B (api)** → **C (web, bridge)** |
| +5 | B | If smoke fails: the owner of that area has **10 min** to push a fix, otherwise B reverts that PR (`git revert -m 1 <merge-sha>`). **Never debug on main.** |
| +10 | everyone | `git switch <x>/main && git pull --rebase origin main && git push --force-with-lease && make sync`. In any still-open worktree: `git rebase <x>/main`. Update `progress/<X>.md`. B updates `PROGRESS.md` gates |

**Express lanes (any time, no window needed):** B's data-only PRs (`data/generated/**`) and A's artifact-only PRs (`ml/artifacts/**`). One writer and no code means they can't conflict.

### 7.5 If a conflict happens anyway
It can only be in a file you own (thanks to the hook), so: `git status`, open the file, keep both intents, `make check-<area>`, `git add`, `git rebase --continue`. `rerere` remembers the resolution if the same conflict shows up again. If it's in a file you *don't* own, someone bypassed the rules: stop and call B.

---

## 8. Model + effort for every feature

Claude effort: set it in `/model` (or in the T3 Code thread settings). Codex effort: `/model` in a session, or `codex -m <model> -c model_reasoning_effort=high`. Codex models at time of writing: **GPT-6 Sol** (coding/agentic) and **GPT-6 Luna** (cheap, simple tasks). Check `/model` for the exact names on your account. `xhigh` costs about 3–5× the tokens of `medium`; use it only where noted.

| Member | Feature | Tool | Model | Effort | Why |
|---|---|---|---|---|---|
| A | `stub.py` + package skeleton | Codex | GPT-6 Sol | low | Boilerplate, fully specified |
| A | Loader + conversation-level splitter + leakage test | Claude Code | Sonnet 5.5 | high | Subtle correctness |
| A | Embedding cache + baselines B0–B3 | Codex | GPT-6 Sol | medium | Standard sklearn |
| A | **PreyNet + multi-task training** | Claude Code | **Opus 5.5** | high (xhigh when debugging) | Core IP; design judgment |
| A | **metrics.py** (EWR@k, lead time…) | Claude Code | Opus 5.5 | high | Numbers we pitch |
| A | Independent re-implementation of EWR@k + lead time as a cross-check test | Codex | GPT-6 Sol | high | Two vendors agreeing beats one model trusting itself |
| A | Calibration + lock-on hysteresis | Claude Code | Opus 5.5 | high | Honest confidence |
| A | Chloroplast trainer | Claude Code | Opus 5.5 | high | Leaf Sheep core |
| A | LOFO zero-day + sample-efficiency runs | Codex | GPT-6 Sol | medium | Scripted experiments |
| A | ONNX export + parity test | Claude Code | Sonnet 5.5 | high | Fiddly but well defined |
| A | Subagents | Claude | Haiku (auditor) · Opus (leakage) · Sonnet (eval) | — | Cheap where possible |
| B | Repo bootstrap, contract review | Claude Code | Opus 5.5 | medium | Kit already drafted |
| B | FastAPI skeleton + mock routes + SSE | Codex | GPT-6 Sol | medium | Boilerplate |
| B | **Algae factory** (async batches, retries, JSON repair, critic) | Claude Code | Sonnet 5.5 | high | Throughput + robustness |
| B | Tools (directory, RDAP, number, scrub) + tests | Codex | GPT-6 Sol | high | Many small exact functions |
| B | **Safeguard tool-calling loop** + schema-valid card + fallback | Claude Code | Opus 5.5 | high | Agent reliability = NVIDIA score |
| B | Zero-day job orchestration | Claude Code | Sonnet 5.5 | high | Async + progress events |
| B | Merge windows / integration debugging | Claude Code | Opus 5.5 | high, fresh session each window | Cross-cutting reasoning |
| B | Devpost technical sections | Claude Code | Sonnet 5.5 | medium | Writing |
| C | Vite scaffold + theme + mocks | Codex | GPT-6 Sol | medium | Fast UI |
| C | Photon echo bot → full bridge + edge cases | Codex | GPT-6 Sol | high | New SDK, early preview |
| C | Phone shell, threads, HUD, Trajectory Compass | Codex | GPT-6 Sol | high | Custom SVG + state |
| C | Reef Lab + charts + SSE log | Codex | GPT-6 Sol | medium | Standard |
| C | **On-device runtime** (transformers.js + onnxruntime-web + chloroplast JS) | Codex | GPT-6 Sol | **xhigh** | Hardest frontend piece; parity matters |
| C | Leaf-sheep avatar + vitality bars | Codex | GPT-6 Sol | medium | Visual |
| C | Devpost copy, video script, captions | Codex | GPT-6 Luna | medium | Cheap writing |

**If Claude usage runs low:** move A's medium-effort tasks to Codex Sol, and drop Opus → Sonnet for everything except PreyNet, metrics and the Safeguard loop.

---

## 9. How it runs on each laptop, and how it comes together

| Phase | A's laptop | B's laptop (integration + demo host) | C's laptop |
|---|---|---|---|
| P0–P1 | `cd ml && uv run …` (training on CPU; data via git) | `make api-stub` · Algae generation in the background (`NVIDIA_API_KEY`) | `make web` with `VITE_USE_MOCKS=1` · `make bridge` + `make tunnel` (Photon webhook → C's tunnel) |
| P2 | Real model → commits `ml/artifacts/` (express lane) | `make api` with the real model | web → `VITE_API_URL=http://localhost:8000` running **its own local api** (`make api-stub` or `make api` after a pull), bridge → local api |
| P3 | Chloroplast experiments | Zero-day job live | Browser runtime loads `/models/preynet.onnx` from the local api |
| Demo | (backup laptop with the same stack) | **Runs everything**: api + web + bridge + **named** cloudflared tunnel | Presents from B's screen or mirrors it |

- **Every laptop can run the whole stack** (`make api-stub && make web && make bridge`), so nobody depends on campus Wi-Fi peer-to-peer (it's often blocked).
- **Photon has one webhook target at a time.** During dev it's C's tunnel. At M3, re-register it to B's tunnel and don't restart it. A quick `cloudflared` tunnel gets a **new URL every restart**; a named tunnel (free Cloudflare account) keeps it stable.
- **Phone hotspot as backup** for the demo (Nemotron + Photon need internet; on-device inference doesn't).

---

## 10. The 3-minute demo (in this order)
1. **(0:00) The gap, 20 s.** "Filters ask *is this message a scam*. By the time the link arrives, the victim is hooked. We forecast where the conversation is going."
2. **(0:20) Photon live, 50 s.** A judge forwards turn 2 of a "wrong number" thread from their own phone → the reply shows family, `~2 turns to strike`, an honest band, why, and reply codes. They reply `2` → the official number comes back.
3. **(1:10) The model, 50 s.** The Reef Lab's **lead-time chart** (PreyNet vs per-message filters) and the **reliability diagram**. One sentence on the dragonfly mapping (internal model, lock-on attention, population-vector compass).
4. **(2:00) Zero-day live, 45 s.** A judge types a new scam → Algae streams → chloroplast `82 KB · 4.8 s` → the browser phone flags it; flip to DevTools → Network: **no message text left the device.**
5. **(2:45) Close, 15 s.** "Protected before, during and after. Built on Nemotron. Reachable from any phone through Photon."

**Backups:** a pre-recorded video of the full demo on 2 laptops; a pre-trained demo chloroplast in `api/store/chloroplasts/` in case Nemotron is slow.

---

## 11. Risk register
| Risk | Early signal | Fallback |
|---|---|---|
| Nemotron rate limits or slowness | v1 generation < 100 conversations by H2 | Smaller N per family; OpenRouter's free Nemotron route; reuse the cached batches |
| Photon beta won't connect | Echo bot not working by **H2** | Web phone only; keep Photon for the pitch; decide at M1 and log it |
| Browser ONNX/transformers.js trouble | Parity page fails at H8 | Browser calls the **local** api on the same laptop (still "on your machine"); say so honestly |
| PreyNet ≈ baselines | eval v2 at M2 | Tune lock-on, add hard negatives, check leakage; still pitch lead time + calibration honestly |
| Synthetic data too easy (≈99%) | in-distribution ≫ test_human | Lead with the test_human numbers; that honesty scores on "detection quality" |
| Claude usage window exhausted | `/usage` or limit warnings | Move tasks to Codex Sol (§8) |
| Merge failure | smoke red at a window | 10-minute fix or revert (§7.4) |

## 12. Sources
- HackUTD 2026 opening ceremony deck (T-Mobile p15–16, NVIDIA p64, Photon p67–68, schedule p105–108)
- ECC: https://github.com/affaan-m/ECC
- Ponytail: https://ponytail.dev/ · https://github.com/DietrichGebert/ponytail
- T3 Code: https://github.com/pingdotgg/t3code
- Codex models and effort: https://openai.com/index/introducing-gpt-6-sol-and-luna/ · https://dev.to/aicoding-guide/how-to-change-reasoning-effort-in-codex-cli-modelreasoningeffort-values-and-one-off-overrides-2bf4
- Nemotron 3 Nano model card: https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b/modelcard
- Photon webhooks + spectrum-ts: https://photon.codes/docs/webhooks/quickstart · https://docs.photon.codes/spectrum-ts
- Biology and competitive landscape: see `docs/MODEL_SPEC.md` §10
