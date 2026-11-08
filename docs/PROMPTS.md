# PROMPTS.md: the IronGuard step-by-step (follow top to bottom)

> **double = A (the model) · ss = B (Nemotron, API, merging) · jcubed = C (website + Photon texting)**
> **Final deadline: 12:00 PM.** Everyone moves together: finish a step → wait for everyone → merge → sync → next step.
> You copy the gray boxes into T3 Code. Everything else is written for you to do with your hands.

---

## 📖 Words you need (30 seconds)

| Word | What it means |
|---|---|
| **Terminal** | The black window where you type commands. Open it from inside your `IronGuard` folder. |
| **Thread** | One chat with an AI agent in T3 Code. One thread = one job. |
| **Worktree** | A private copy of the code that a thread works in, so two threads never overwrite each other. |
| **Branch** | A named version of the code. Yours is `a/main`, `b/main` or `c/main`. |
| **PR (pull request)** | A request on GitHub to add your branch's work into `main`. |
| **Merge** | Actually adding it into `main`. Only ss clicks the final Merge button. |
| **Sync** | Downloading the newest `main` onto your laptop and checking that everything still works. |

## 🧭 How to open a thread in T3 Code (you'll do this a lot)
1. Open **T3 Code** and make sure the `IronGuard` folder is the open project.
2. Click **New thread**.
3. If a prompt says **"new worktree"**: choose the **new worktree** option and type the branch name the prompt gives you (for example `a/data`). If it says **"no worktree"**: choose the option that works in the project folder itself.
4. Pick the **AI** (Claude or Codex) and the **model + effort** shown next to the prompt.
5. Paste the gray box. Press Enter. Let it work.
6. If it asks you a question, answer it. If it's waiting for permission to run a command, allow it.

> **Never** use more than 3 threads at once. **Never** paste the same prompt into two threads.

## 🔁 Every step works like this

```
1. BUILD   Paste your step's prompt(s). The agent builds, tests, reviews and commits by itself (the "Finish" routine, §F).
2. WAIT    When your agent says "Ready to post DONE", write  DONE  in the team chat. Wait until all 3 have said DONE.
3. MERGE   Paste the MERGE prompt (§M). It gives you a GitHub link. Open it → Create pull request.
           Approvals: double approves ss's PR · ss approves double's and jcubed's PRs.
           ss clicks Merge in this order: double → ss → jcubed. ss writes  MERGED  in the chat.
4. SYNC    Everyone pastes the SYNC prompt (§S). When it says "SYNCED, green", write  GREEN  in the chat.
5. NEXT    When all 3 say GREEN, start the next step.
```

---

# 🚦 BEFORE STEP 1: do this now (about 15 min)

**Everyone, in Terminal, inside the `IronGuard` folder:**
```bash
git pull --rebase origin main && make doctor
```
`make doctor` checks your laptop and prints ✅ (good), ⚠️ (should fix) or ❌ (must fix). **Every ❌ line tells you the exact fix.** Do the fix, then run `make doctor` again until it says **🟢 READY**.

Common fixes:
- **pnpm missing:** run `corepack enable`, then close Terminal and open a new one.
- **codex missing:** run `npm i -g @openai/codex`, then `codex login`.
- **cloudflared missing (ss, jcubed):** run `brew install cloudflared`. If `brew` isn't found, download it from https://github.com/cloudflare/cloudflared/releases.

### ss only: run Nemotron on NVIDIA Brev (our $60 credits) · about 20 min, mostly waiting
Nemotron is the AI that writes our training data and runs the Safeguard agent. We run it on our own rented NVIDIA GPU on Brev, so there are no per-call limits.

**Part 1: rent the GPU (on brev.nvidia.com)**
1. Go to **https://brev.nvidia.com** and sign in. Check that your **$60 credit** shows in your account/billing page.
2. Click **Create** (or **New Instance**). Choose **GPU** and pick one of these, whichever is available and cheapest:
   **L40S (48 GB)**, **A100 (80 GB)** or **H100 (80 GB)**. Look at the **price per hour** and pick one **under about $3.50/hour**, so $60 lasts until judging ends at 4 PM.
3. Keep the default machine image (a VM with Docker), set disk to **200 GB** if there's a disk option, and name the instance exactly **`ironguard-nemotron`**.
4. Click **Deploy** / **Create** and wait until it says **Running** (a few minutes).

**Part 2: start Nemotron (in the Brev machine's terminal)**
5. On the instance's page, open its terminal: click **Open Terminal** / **Shell** / **Jupyter → Terminal** (whichever you see).
6. Make up a password (letters and numbers only, e.g. `ironguard7342`). Paste this into the Brev terminal, replacing `YOURPASSWORD`, and press Enter:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/srisain-ux/IronGuard/main/scripts/brev_serve.sh | bash -s YOURPASSWORD
   ```
7. Wait. The first time, it downloads the model (5–15 minutes). It's done when it prints **✅ NEMOTRON IS READY**.

**Part 3: connect your laptop (in Terminal on your laptop, inside `IronGuard`)**
8. Log in to Brev once (a browser window opens; approve it):
   ```bash
   brev login
   ```
9. Open a **new Terminal tab** in the `IronGuard` folder and run this. **Leave this tab open the whole night**, because it's the cable between your laptop and the GPU:
   ```bash
   make brev-tunnel
   ```
10. In your first Terminal tab:
    ```bash
    cp .env.example api/.env && open -e api/.env
    ```
    In the window that opens, change `NVIDIA_API_KEY=the-password-you-gave-brev_serve.sh` to `NVIDIA_API_KEY=YOURPASSWORD` (the same password as step 6). Leave the other lines alone. Save and close.
11. Test it:
    ```bash
    make nemotron-check && make doctor
    ```
    You should see **✅ Nemotron answered** and the doctor's Nemotron line in ✅.

> **Keep it running until judging ends (4 PM)**, then **stop the instance on brev.nvidia.com** so it stops using credits.
> **If your laptop sleeps or the tunnel tab closes:** run `make brev-tunnel` again in a new tab.
> **Backup if Brev has no GPUs available:** use NVIDIA's hosted API instead. Get a free `nvapi-` key at https://build.nvidia.com (open *nemotron-3-nano-30b-a3b* → **Get API Key**), then in `api/.env` use the 4 "OPTION B" lines from `.env.example`.
> Never paste the password or keys into a chat or a commit. `api/.env` is ignored by git on purpose.

### jcubed only: connect Photon (our real iMessage/SMS number)
1. Go to **https://photon.codes/beta**, sign up, open the **dashboard**, create a project called `IronGuard`, and add the **iMessage** and **SMS** channels.
2. Copy the **Project ID** and **Secret** from the project settings.
3. In Terminal:
   ```bash
   cp .env.example bridge/.env && open -e bridge/.env
   ```
4. Fill in `PHOTON_PROJECT_ID=` and `PHOTON_SECRET=`. Save and close. (You'll fill `PHOTON_WEBHOOK_SECRET=` later in Step 1, when the agent registers the webhook. **It's shown only once, so copy it immediately.**)
5. Run `make doctor`. The Photon line should now be ✅.

### Everyone: turn on the coding skills
- **Claude Code users (double, ss):** in a Claude Code window, type `/ponytail full` and press Enter, then `/ponytail band on`. This shows a status bar with test results above your prompt.
- **Codex users (everyone):** open Codex, type `/hooks`, and make sure Ponytail and ECC are **trusted**.

When all 3 laptops say **🟢 READY**, write **READY** in the team chat and start Step 1.

---

# 🧩 REUSABLE PROMPTS (you'll paste these at the end of every step)

### ⓪ MASTER prompt: paste ONCE at the very start of your first Step 1 thread, before your Step 1 prompt
```text
You are a senior engineer on team IronGuard at HackUTD 2026 "Zero Day". The final deadline is 12:00 PM.
Read AGENTS.md, docs/MODEL_SPEC.md, docs/PLAYBOOK.md, docs/PROMPTS.md and contracts/ before doing anything. AGENTS.md overrides plugin defaults.
IronGuard intercepts multi-turn text scams BEFORE the strike (the turn where the scammer sends the link or asks for money, codes or gift cards).
The MODEL is the product: PreyNet (dragonfly-inspired causal sequence model: forecast heads, CSTMD1-style lock-on attention, Trajectory Compass)
plus Leaf Sheep chloroplasts (Nemotron generates synthetic conversations for a new scam; we train a tiny adapter that runs on the phone; no
customer text is used for training or uploaded). A Nemotron Safeguard agent with real tools turns forecasts into protection; Photon brings it
to real iMessage/SMS. Every number must come from ml/artifacts/eval_summary.json; never invent one.
Style: HackUTD Zero Day deck (neon night city, Orbitron/Roboto Mono/Inter, tokens in web/src/theme/zero-day.css).
Rules: I am member <A|B|C> (check `git config --get ironguard.member`); only touch my paths (AGENTS.md §2); contracts are add-only;
build against mocks until the real thing lands; Ponytail = least code that works; when a feature is done run the FINISH routine in
docs/PROMPTS.md §F without being asked. Explain anything you need from me in simple numbered steps.
Reply with a 5-line plan for my Step 1 work, then wait for my go.
```

### §F · FINISH routine (agents do this by themselves; every feature prompt ends with "Then run §F")
1. Run `make validate` and my area's check (A: `make check-ml` · B: `make check-api` · C: `make check-web check-bridge`). If something fails: Claude Code → run `/build-fix`; Codex → fix it directly. Re-run until green.
2. Review your own work. **Claude Code:** `/code-review`, then `/ponytail-review branch`. **B only, when the code handles keys, messages or reports:** also `/security-scan`. **Codex:** `$ponytail:ponytail-review`, then type `$` and run ECC's review skill if it's in the list. Fix real bugs, security or privacy issues and contract mismatches; skip style nitpicks.
3. Confirm only files my member letter owns were touched (AGENTS.md §2). Claude Code: use the `contract-guardian` subagent. Revert anything outside my lane and add a line under `## Requests` in my progress file instead.
4. Commit in this worktree: `[<letter>][P<step>] <summary>`. If the pre-commit hook blocks you, fix the cause. Never bypass it.
5. Append to `progress/<letter>.md`: done / skipped / unverified, plus **Handoffs** (anything teammates can now use: exact file names, function names, tensor shapes, env vars). Commit it. Claude Code: then run `/learn` to save useful patterns.
6. End with a 5-line report in plain words, then say exactly: **"Ready to post DONE in the team chat."** Do not merge into my member branch or main.

### §M · MERGE prompt: NEW thread, **no worktree**, Codex GPT-6 Sol medium (or Claude Sonnet medium)
```text
It's merge window <M1|M2|M3|M4>. I am member <A|B|C> (check `git config --get ironguard.member`).
1. Run `git worktree list` and `git branch`. List EVERY branch that has commits not yet in my member branch <a|b|c>/main, including
   branches from earlier steps that were never merged and worktree branches whose names don't start with my letter. Show me the list.
2. For each worktree with uncommitted changes, commit them there as "[<letter>][P<step>] finish work" (only files I own).
3. Make sure the main folder is clean and run: git switch <a|b|c>/main && ./scripts/merge-window.sh <every branch from step 1>
4. If the rebase has a conflict, it can only be in my own files: fix it keeping both intents, git add, git rebase --continue, re-run the script.
   If a conflict is in a file I don't own, STOP and explain it to me in simple words.
5. If checks fail, fix them on my member branch (only in my folders), commit, and re-run the script.
6. When it pushes, remove the worktrees and branches you merged (git worktree remove <path>; git branch -d <branch>).
7. Give me, as numbered steps a middle schooler could follow:
   a) the link https://github.com/srisain-ux/IronGuard/compare/main...<a|b|c>/main
   b) the exact PR title "[<letter>][<window>] <summary>" and a 3-bullet description to paste
   c) the reminder: "click Create pull request, then post the link in the team chat for approval."
```
**Your hands, after the agent finishes:**
1. Open the link → click **Create pull request** → paste the title and description → click **Create pull request** again.
2. Post the PR link in the team chat.
3. **Approve:** double approves ss's PR; ss approves double's and jcubed's. To approve: open the PR → **Files changed** tab → **Review changes** (top right) → **Approve** → **Submit review**.
4. **ss merges, in order double → ss → jcubed:** open each PR → **Merge pull request** (make sure it says **Create a merge commit**) → **Confirm merge**. Then write **MERGED** in the chat.

### §S · SYNC prompt: same no-worktree thread, after ss writes MERGED
```text
All PRs for this merge window are merged into main.
1. Run: git switch <a|b|c>/main && git pull --rebase origin main && git push --force-with-lease
2. Rebase every still-open worktree branch of mine onto my member branch (conflicts only in my files; otherwise stop and explain).
3. Run: make sync
4. If it fails: tell me in simple words which part failed and whose it is (ml = double, api = ss, web/bridge = jcubed).
   If it's mine, fix it in a new commit on my member branch, push, and give me the PR link with simple steps.
   If it's someone else's, write a short message I can paste to them with the exact error.
5. If I'm member B and everything is green: in PROGRESS.md mark this window's gate ✅ with the current time and set "Current phase" to the next step,
   commit, push b/main, and give me the PR link (it will be merged at the next window).
6. Finish with exactly: "SYNCED, green" (or "NOT GREEN" plus the reason).
```
When all 3 have written **GREEN** in the chat, start the next step. If someone isn't green, only they fix it, with a 10-minute limit. After that, ss reverts their PR on GitHub (open the merged PR → **Revert** → merge the revert PR) and everyone syncs again.

### §X · EXPRESS DROP: the only allowed merge in the middle of a step (ss's data, double's model files)
The prompts that need it tell the agent to do it. The agent gives you a PR link. **Your hands:** Create pull request → post the link → teammate approves → ss merges right away. The person receiving it pastes into one of their threads:
```text
A teammate's express drop just merged into main. Run: git switch <a|b|c>/main && git pull --rebase origin main, then rebase this
worktree onto <a|b|c>/main and continue using the new files.
```

### §R · RESET: when an agent gets slow, forgetful or confused
```text
Save state: append to progress/<letter>.md exactly where you are, what's done, what's next, decisions and gotchas. Commit it.
Claude Code: also run /save-session. Then give me a 10-line "resume prompt" to paste into a fresh thread.
```
Then open a new thread **in the same worktree branch**, paste the resume prompt, and keep going. (Claude Code users can type `/resume-session` instead.)

### §H · HELP: when something is broken and you don't know why
```text
Something is broken. Here is exactly what I see: <paste the error or describe it>.
Explain in simple words what it means, then fix it if it's inside my folders (AGENTS.md §2). If the fix belongs to a teammate,
write a 2-line message I can send them. Claude Code: use /build-fix for build errors and /context-budget if you feel overloaded.
```

---

# ✅ STEP 0 · Setup: DONE
All three of you finished A0, B0 and C0, and `make sync` is green. **Not merged yet:** double's A0 and jcubed's C0. They're still in your worktrees; the §M prompt at M1 finds them and merges them automatically. Don't do anything about them now.

---

# 🟦 STEP 1 · Data and foundations · ⏰ until about 3:45 AM

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A1a, **then** A1b | B1 **and** B1-t at the same time | C1 |

### A1a · new worktree `a/data` · Claude Code · Sonnet 5.5 · high
```text
/ecc:plan "IronGuard data pipeline per docs/MODEL_SPEC.md §2, §3, §4.1"
After I approve the plan: implement ironguard_ml/data.py (load JSONL from data/generated/<v>/, data/seed/, data/test_human/; make_prefixes(conv)
per the §2 index conventions; conversation-level stratified 70/15/15 split with a seed; job_task excluded from base training when
held_out="job_task") and ironguard_ml/features.py (role-prefixed MiniLM embeddings, L2-normalized, cached by sha1 in ml/.cache/emb/).
Tests: no conversation id in two splits; prefixes respect strike_turn; cache hits return identical vectors.
Write ~30 seed conversations into data/seed/seed.jsonl (schema-valid; all families + hard negatives) so the pipeline runs before Nemotron data lands.
Then run the data-auditor subagent on data/seed and fix what it finds. Then run §F.
```
**double's hands while it works:** write 10–20 realistic text conversations (scams *and* normal chats) in a notes file. Ask ss and jcubed for 5 each. Paste them into a new prompt later: *"Turn these into schema-valid lines in data/test_human/human.jsonl with generator "human"."*

### A1b · new worktree `a/baselines` · Codex · GPT-6 Sol · medium · start AFTER A1a says "Ready to post DONE"
```text
Rebase this worktree onto a/data first (git rebase a/data) so you have the data pipeline.
Implement ironguard_ml/baselines.py per docs/MODEL_SPEC.md §6.1 (B0 rules, B1 TF-IDF+LR, B2 MiniLM+LR on the latest message, B3 mean-MiniLM+LR),
and a first ironguard_ml/metrics.py + evaluate.py that write ml/artifacts/eval_summary.json in the §6.4 shape for the baselines
(EWR@k, lead time, strike recall, hard-negative FPR; thresholds at 1% FPR on VAL only). Use data/generated/v1 if it has arrived on main
(pull it in), otherwise data/seed. Then run §F.
```

### B1 · new worktree `b/algae` · Claude Code · Sonnet 5.5 · high
```text
FIRST: run `make doctor` and `make nemotron-check`. If either fails, STOP and walk me through the fix in simple words (usually: start
`make brev-tunnel` in its own Terminal tab, or fix api/.env per 'ss only: run Nemotron on NVIDIA Brev'). Don't write code until both pass.
/ecc:plan "Algae synthetic data factory per docs/MODEL_SPEC.md §3 and §9"
After I approve: implement api/ironguard_api/agent/nemotron.py (OpenAI-compatible client; base URL NEMOTRON_BASE_URL, key NVIDIA_API_KEY, both
read from the environment, which scripts/run_api.py loads from api/.env; retries with exponential backoff on 429/5xx; 60 s timeout; strict JSON
extraction with one repair retry). The server is vLLM on Brev serving model name "nemotron" (or build.nvidia.com as a backup); the model
may return its reasoning separately, so read only message.content. For bulk generation, try extra_body={"chat_template_kwargs":
{"enable_thinking": False}} and keep it only if the replies still come back as valid JSON. Make ONE test call and show me the reply.
Then implement agent/algae.py as a module runnable with `make algae` (python -m ironguard_api.agent.algae --version v1 --per-family 150).
Steps: sample diversity knobs → batches of 5 conversations (NEMOTRON_GEN_MODEL, temp 0.9) with asyncio.Semaphore(12) → critic pass
(NEMOTRON_AGENT_MODEL, temp 0.2; drop realism < 4 or wrong labels) → dedupe → validate each line against conversation.schema.json →
append to data/generated/v1/<family>.jsonl IMMEDIATELY after each batch (crash-safe). Benign: 900 total, ≥40% hard negatives, same prompt skeleton.
Start `make algae` in the background as soon as it works and show me the progress. When ≥300 valid conversations exist, do an EXPRESS DROP:
commit data/generated/**, run make validate-data, then from the main folder run git switch b/main && ./scripts/merge-window.sh b/algae,
and give me the PR link with simple steps. Then keep generating. When the full set is done, run the data-auditor subagent on it, then §F.
```

### B1-t · new worktree `b/tools` · Codex · GPT-6 Sol · high · at the same time as B1
```text
Implement api/ironguard_api/agent/tools.py and extend scrub.py per api/AGENTS.md: lookup_official_contact(brand) from api/data/official_directory.json
(create it with ~25 brands; label it "curated demo directory"), check_domain(domain) (RDAP via https://rdap.org/domain/<d>: age in days, registrar,
plus lookalike distance vs official domains), check_number(phone) (normalize E.164; in directory?; fictional 555-01xx range; toll-free heuristics),
scrub_and_report(text) → ReefReport dict with placeholders. Pure, typed functions, each with a fixture-based test (no network; mock httpx).
Then run §F.
```

### C1 · new worktree `c/phone` · Codex · GPT-6 Sol · high
```text
FIRST: run `make doctor`. If the Photon line is ❌, give me the fix steps in simple words, but continue with the web part.
Build /phone per web/AGENTS.md and docs/THEME.md on mocks: phone frame; thread list; thread view with bubbles; per-message Trajectory HUD
(risk meter with the band WORD + color; "T-2 TURNS TO STRIKE"; LOCKED badge with pulse); Trajectory Compass SVG (6 family directions from
contracts/taxonomy.json compass_deg; needle angle = probability-weighted direction, length = risk); kill-chain strip
(🎣 BAIT ➡ 🎭 PIVOT ➡ 🪝 HOOK ➡ 💸 STRIKE; current stage lit, predicted next dashed); locked links (.zd-locked-link); Cool-Down Shield modal
(10-second breathing countdown before a link can be revealed); Safety Card with next-step buttons; highlight the highest-attention turn as
"this message primed the lock". Accessibility per THEME.md. Demo data: 3 scripted threads (pig butchering, bank impersonation, benign hard
negative) revealed turn by turn with a "next message" button.
Photon: make the bridge load bridge/.env (Node's --env-file in the dev script). Then walk me through, as numbered steps: 1) run `make bridge`
in one Terminal tab, 2) run `make tunnel` in a second tab and copy the https URL it prints, 3) register that URL as the webhook in the Photon
dashboard and paste the one-time PHOTON_WEBHOOK_SECRET into bridge/.env, 4) text the Photon number from my phone and confirm the
"IronGuard online 🛡" reply. If the echo doesn't work, debug it with me. Then run §F.
```

**Step 1 is done when:** double's A1b, ss's B1 and B1-t, and jcubed's C1 all say "Ready to post DONE", and jcubed got a reply from the Photon number on a real phone.

## 🛑 WAIT → 🔀 §M (window **M1**) → 🔄 §S
If Photon still doesn't reply at M1: keep building the web phone, and ss writes the decision in PROGRESS.md (Decisions log). Don't let it block everyone.

---

# 🟪 STEP 2 · The Dragonfly model and the Safeguard agent · ⏰ about 4:00 → 6:30 AM

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A2 **and** A2-x at the same time | B2 | C2a **and** C2b at the same time |

### A2 · new worktree `a/preynet` · Claude Code · **Opus 5.5** · high
```text
/ecc:plan "PreyNet per docs/MODEL_SPEC.md §4 and metrics per §6.2"
After I approve (use /checkpoint before big changes): implement preynet.py (Linear 385→128 GELU → causal GRU 128 → CstmdAttention → features 640-d
→ heads family/next_stage/tts), train.py (all prefixes, multi-task loss L = CE_f + 0.5·CE_s + 0.5·CE_tts, class weights, AdamW 2e-3, early stop
on val EWR@2, seeds 0,1,2), finish metrics.py (ewr_at_k, lead_time, strike_recall, hard_neg_fpr, flicker_rate, threshold_at_fpr) EXACTLY per the
§2 conventions with hand-computed unit tests, calibrate.py (temperature scaling per head on VAL only, ECE 15 bins, reliability bins), infer.py
(load + score + LockOn hysteresis θ_lock 0.70 / θ_release 0.40 / 2 turns + rule-based evidence on top-attention turns), and evaluate.py writing
ml/artifacts/eval_summary.json in the exact §6.4 shape (baselines B0–B3, PreyNet, ablations, test_human).
As soon as the first trained model loads through infer.load(), do an EXPRESS DROP of ml/artifacts/ (commit, then from the main folder:
git switch a/main && ./scripts/merge-window.sh a/preynet; give me the PR link with simple steps) so ss can switch the API to the real model.
Then run the leakage-hunter subagent on data.py, train.py, metrics.py, evaluate.py and fix every CONFIRMED issue. Then run the eval-runner
subagent and report the headline numbers exactly as produced. Then run §F.
```

### A2-x · new worktree `a/metrics-check` · Codex · GPT-6 Sol · high · at the same time as A2
```text
WITHOUT reading ml/ironguard_ml/metrics.py, write ml/tests/test_metrics_crosscheck.py with your own independent implementation of EWR@k and
lead time from docs/MODEL_SPEC.md §2 and §6.2 (index conventions are exact). Generate 200 random flag sequences and assert your results equal
ironguard_ml.metrics within 1e-9 (skip with a clear message if metrics.py isn't in my branch yet; tell me to re-run you after A2's express drop).
If they differ, print the smallest failing case. Do not modify metrics.py. Then run §F.
```

### B2 · new worktree `b/safeguard` · Claude Code · **Opus 5.5** · high
```text
/ecc:plan "Nemotron Safeguard agent per api/AGENTS.md and contracts/schemas/safety_card.schema.json"
After I approve: implement agent/safeguard.py: input = ScoreResponse + entities (+ turns only in Photon mode). OpenAI-style tool calling with
NEMOTRON_AGENT_MODEL, max 6 steps: decide tools (from agent/tools.py), call them, observe, then emit SafetyCard JSON. Enforce:
confidence = ScoreResponse.risk (overwrite if changed); verdict from risk + checks; next_steps with reply_codes 1/2/3; locked_links = URLs/numbers
that failed checks; cool_down on urgency words; privacy_note says exactly what left the device. Validate against the schema; on failure retry
once, then fall back to a deterministic rule-built card. Publish "card" events on SSE. Wire POST /v1/agent/safety-card. Tests with a mocked
Nemotron client. Run /security-scan on the agent code.
When double's express drop of ml/artifacts/ lands on main, pull it, make /v1/score use the real model with IRONGUARD_MODEL=preynet (stub stays
the default when artifacts are missing), and show me one real score. Then run §F.
```

### C2a · new worktree `c/bridge` · Codex · GPT-6 Sol · high
```text
Implement the full Photon bridge flow in bridge/AGENTS.md: in-memory history per space.id, newline splitting, reply codes 1/2/3 via pending[space.id],
POST /v1/score then /v1/agent/safety-card when risk ≥ 0.35, the exact reply template, every listed edge case, MOCK_API=1 mode, masked previews to
POST /v1/events/publish. Never log message text. Then give me numbered steps to test it: which Terminal tabs to run (make api-stub, make bridge,
make tunnel) and the exact 2 messages to forward to the Photon number from my phone. Then run §F.
```

### C2b · new worktree `c/reef` · Codex · GPT-6 Sol · medium · at the same time as C2a
```text
Build /reef "Algae Reef Lab" per web/AGENTS.md: live SSE log panel (Roboto Mono, [algae]/[critic]/[train]/[reef] prefixes), live Photon feed
(masked), and 3 charts from GET /v1/metrics: EWR@k lines per model (PreyNet neon pink, baselines lavender/teal), zero-day before/after bar +
sample-efficiency line, reliability diagram. Show "--" when a value is missing. Never hardcode numbers. Zero Day styling per docs/THEME.md.
Then run §F.
```

**Step 2 is done when:** forwarding the first 2 messages of a scam to the Photon number gets a forecast + Safety Card back on the phone, and the same thread shows in `/phone`.

## 🛑 WAIT → 🔀 §M (window **M2**) → 🔄 §S

---

# 🟩 STEP 3 · Leaf Sheep: learning a brand-new scam, on the phone · ⏰ about 6:45 → 9:00 AM

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A3 | B3 | C3 |

### A3 · new worktree `a/chloroplast` · Claude Code · **Opus 5.5** · high
```text
/ecc:plan "Chloroplast trainer + LOFO zero-day experiment + ONNX export per docs/MODEL_SPEC.md §5, §6.3, §7"
After I approve: implement chloroplast.train(pos, neg, family_id, label, alert, progress_cb) -> manifest dict (contracts/schemas/chloroplast.schema.json):
frozen PreyNet features → MLP 640→32→1, weighted BCE, 300 AdamW steps, threshold at 1% FPR on held-out synthetic negatives, base64 float32 LE
weights, sha256, size_bytes, train_seconds. Must run < 10 s on a laptop CPU (print timing). Add a reference apply_chloroplast() in infer.py.
Run the LOFO experiment (job_task held out) and the sample-efficiency curve (N = 25/50/100/200); add them to eval_summary.json → zero_day.
Export ONNX (opset 17, dynamic turn axis, outputs family_logits, stage_logits, tts_logits, attention, features) + tests/test_onnx_parity.py
(max abs diff < 1e-4). As soon as parity passes, do an EXPRESS DROP of ml/artifacts/ (give me the PR link with simple steps) and write a
Handoff for jcubed in progress/A.md: input tensor name/shape, output names, temperature.json format, lock-on params.
Run the leakage-hunter subagent on the zero-day experiment code. Then run §F.
```

### B3 · new worktree `b/zero-day` · Claude Code · Sonnet 5.5 · high
```text
Implement POST /v1/zero-day {alert, n_pos=120, n_neg=120} → job_id (return immediately). Background job: Algae mutation planner (8 axes) →
generate positives + hard negatives → critic → dedupe → ironguard_ml.chloroplast.train(..., progress_cb → SSE "train.progress") → save manifest to
api/store/chloroplasts/<id>.json → SSE "chloroplast.ready" (manifest without weights). Stream "algae.progress" with stage/done/total and a short
sample line. Implement POST /v1/reef/report (validate, re-scrub server-side, append to api/store/reef.jsonl, SSE "reef.report").
Use the stub train() until double's real one is on main, then switch and test once end to end. Pre-train one demo chloroplast
(zd_parking_boot) and keep it in api/store as the demo fallback. Run /security-scan. Then run §F.
```

### C3 · new worktree `c/runtime` · Codex · GPT-6 Sol · **xhigh**
```text
Implement web/src/runtime/ per web/AGENTS.md using double's Handoff in progress/A.md (tensor names, shapes, temperature.json, lock-on params):
embed.ts (transformers.js Xenova/all-MiniLM-L6-v2, mean pool + L2 normalize, "[THEM] "/"[ME] " prefixes), preynet.ts (onnxruntime-web session from
/models/preynet.onnx; input [1, turns, 385]; softmax with temperature; build a score_response-shaped object with runtime "browser"),
lockon.ts (identical hysteresis), chloroplast.ts (decode base64 float32 LE; sigmoid(W2·gelu(W1·f+b1)+b2); fire if ≥ threshold).
Fetch manifests from GET /v1/chloroplasts and render the leaf-sheep avatar: each chloroplast is a glowing green cerata badge with a vitality bar
= 0.5^(age_h/half_life_h) (display only). Add /phone?debug=1 comparing browser vs API scores on the example thread (must match within ±0.02).
In /reef add the zero-day terminal: "> new zero-day alert: _" → POST /v1/zero-day → stream progress → "CHLOROPLAST ABSORBED · {size} · {s} s".
If double's ONNX isn't on main yet, build against the Handoff and test with the stub, then pull and retest when it lands.
Finally give me numbered steps to prove privacy: open the browser's DevTools → Network tab, score a message, and confirm no request contains
the message text. Then run §F.
```

**Step 3 is done when:** typing a new scam into `/reef` produces a chloroplast in about 2 minutes, the browser phone flags that scam, and the Network tab shows no message text leaving the browser.

## 🛑 WAIT → 🔀 §M (window **M3**) → 🔄 §S

# 🧊 FEATURE FREEZE. From now on: only fixes. No new features, no matter how small.

---

# 🟨 STEP 4 · Final numbers, clean test, pitch · ⏰ about 9:15 → 10:30 AM

| double (A) | ss (B) | jcubed (C) |
|---|---|---|
| A4 | B4 | C4 |

### A4 · new worktree `a/final` · Claude Code · Sonnet 5.5 · medium
```text
Run the eval-runner subagent, then the leakage-hunter subagent one last time. Produce: 1) the headline sentence from MODEL_SPEC §0 filled ONLY
with eval_summary.json values (mean ± std); 2) a 6-bullet "How we trained it" Devpost section (data, leakage defenses, architecture, calibration,
zero-day, honest limits incl. the cross-generator gap). Put both under Handoffs in progress/A.md for ss and jcubed. Run /ponytail-audit on ml/ and
fix only real bugs (freeze: no new features). Then run §F.
```

### B4 · new worktree `b/final` · Claude Code · **Opus 5.5** · high
```text
Simulate a clean machine: clone https://github.com/srisain-ux/IronGuard into a temp folder, run make doctor and make sync there, then start the
stack (make api, make web, make bridge, make tunnel) and walk through the demo in docs/PLAYBOOK.md §10. List every failure with its owner
(A/B/C) and the exact error, and fix the ones in my folders. Run /ponytail-audit and /security-scan on api/ (fix real bugs only).
Then draft the Devpost write-up into progress/B.md: inspiration (the gap), what it does, how we built it (use double's Handoff numbers only),
Nemotron workflows, Photon usage, challenges, what's next (run /ponytail-debt), and the track table from PLAYBOOK §2. Then run §F.
```

### C4 · new worktree `c/pitch` · Codex · GPT-6 Luna · medium
```text
Run $ponytail:ponytail-audit on web/ and bridge/ and fix only real bugs (freeze: no new features).
Write docs/pitch/demo-script.md (3:00, following PLAYBOOK §10 with exact clicks and spoken lines), docs/pitch/devpost-copy.md (tagline:
"Intercept the scam before the strike."; sections ready to paste) and docs/pitch/shot-list.md for a 2:30 screen recording with captions in the
Zero Day voice. Use ONLY numbers from double's Handoff in progress/A.md. Tell me exactly which screens to capture, in order. Then run §F.
```

## 🛑 WAIT → 🔀 §M (window **M4**) → 🔄 §S

Then **ss** pastes into the no-worktree thread:
```text
Tag the release: git switch main && git pull && git tag v1.0-hackutd && git push origin v1.0-hackutd && git switch b/main. Confirm the tag is on GitHub.
```

---

# 🏁 FINISH LINE · ⏰ 10:30 → 11:45 AM (deadline 12:00 PM)
1. **jcubed (10:30–11:00):** record the demo video (under 3 minutes) following `docs/pitch/shot-list.md`. Upload it to YouTube as **Unlisted** and copy the link.
2. **ss (by 11:30):** on Devpost, open the IronGuard project → fill in each section from `docs/pitch/devpost-copy.md` and `progress/B.md` → add the video link and `https://github.com/srisain-ux/IronGuard` → select the tracks (T-Mobile Safe Signal, NVIDIA Nemotron, Photon) → **Submit**. Check that all 3 teammates are listed.
3. **Everyone (11:00–11:45):** one full timed rehearsal of the 3-minute demo, then test the Photon number one last time from a phone.
4. **Judging is 1–4 PM.** Demo from ss's laptop, with `make brev-tunnel` running in its own tab. Keep the video on 2 laptops as a backup.
5. **After judging (ss):** go to brev.nvidia.com → your `ironguard-nemotron` instance → **Stop** (or **Delete**) so it stops using credits.

---

# 🆘 If something goes wrong

| Problem | What to do |
|---|---|
| A command says "not found" | Run `make doctor` and follow the ❌ fix line. |
| The pre-commit hook says "ownership check failed" | Your agent touched a teammate's file. Tell it: "Revert files outside my lane and add a Request instead." |
| `merge-window.sh` says "Uncommitted changes" | Tell the agent: "Commit or stash my uncommitted changes, then re-run." |
| GitHub says "This branch has conflicts" | Paste §H with the message. The fix is always in the PR author's own branch. |
| GitHub won't let you merge ("review required") | The right teammate hasn't approved yet (§M approval rules). |
| `make sync` isn't green | Paste §S again; it tells you whose part failed. That person fixes it within 10 minutes, otherwise ss reverts that PR. |
| The agent is slow or confused | Paste §R and continue in a fresh thread. |
| Claude usage limit hit | Switch that thread to Codex GPT-6 Sol high and paste §R's resume prompt. |
| `make nemotron-check` says connection error | Your `make brev-tunnel` tab closed or the laptop slept. Run `make brev-tunnel` again in a new tab. |
| Brev machine says the server stopped | In the Brev terminal run `docker logs --tail 40 nemotron` and paste it into §H. Re-run the step 6 command to restart. |
| No Brev GPUs available | Use the build.nvidia.com backup (see the Brev section's backup note). |
| Nemotron is slow or errors (429) | Tell B1: "Lower the concurrency to 4 and keep the batches you already saved." |

# ⏳ If you're running late (cut in this order, never cut the model)
1. Photon voice calls (never started, skip)
2. Reef Lab live Photon feed (keep the charts)
3. Leaf-sheep vitality animation (keep the badges)
4. Browser-side model (fall back to the phone page calling the local API, and say so honestly)
5. The sample-efficiency curve (keep the zero-day before/after)

---

## Appendix: Step 0 prompts (only if someone has to redo Step 0)

**A0 · `a/stub` · Codex · GPT-6 Sol · low:** create the ml/ uv package per ml/AGENTS.md; implement ironguard_ml/stub.py fully (load(path).score(turns, chloroplasts) returning a schema-valid score_response from keyword heuristics; stub chloroplast_train returning a schema-valid manifest); tests validating against contracts; then §F.

**B0 · `b/api-skeleton` · Codex · GPT-6 Sol · medium:** done and merged (API routes, SSE, contract fixtures, smoke tests).

**C0 · `c/scaffold` · Codex · GPT-6 Sol · medium:** Vite + React + TS + Tailwind web app with /phone and /reef on mocks and the Zero Day background; bridge/ echo bot with spectrum-ts (pinned) on port 8787; then §F.
