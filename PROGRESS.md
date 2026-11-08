# PROGRESS.md: phase gates (only B edits this file, during merge windows)

> Per-member logs live in `progress/A.md`, `progress/B.md`, `progress/C.md`.
> This file only records the **phase gates**: what must be true on `main` before the next phase starts.
> H0 = the minute you start building. Write the real clock times in the table below.

| Gate | Hour | Clock | Status |
|---|---|---|---|
| M0: skeleton + frozen contracts | H1:00 | `00:45` | ✅ (A0/C0 code merges at M1) |
| Devpost placeholder (skipped by team decision; final entry only) | — | — | ➖ |
| M1: data v1 + baselines + UI shell + Photon echo | target | `03:45` | ⬜ |
| M2: end-to-end forward → forecast → safety card | target | `2026-11-08 05:24 CST` | ✅ (merged; make sync green; live-phone verification outstanding) |
| M3: live zero-day chloroplast + on-device inference | target | `2026-11-08 06:28 CST` | ✅ (all window PRs merged; make sync green; live demo/privacy verification outstanding) |
| FREEZE: features frozen; fixes only | target | `09:00` | ⬜ |
| M4: final merge, tag v1.0-hackutd | target | `10:30` | ⬜ |
| SUBMIT: final Devpost (hard deadline **12:00 PM**) | target | `11:30` | ⬜ |

**Current phase:** `P4` (next: Step 4 in docs/PROMPTS.md; final numbers, clean-machine test and pitch; fixes only)

---

## P0: Setup and contracts (H0:00–H1:00)

**Goal:** Everyone can run the whole stack locally on mocks, and contracts are frozen.

- [ ] (all) Tools installed: git, uv, Node 20 + pnpm, Codex, T3 Code, Ponytail, ECC; Claude Code for A and B
- [ ] (all) Repo cloned; `git config ironguard.member <X>`; `./scripts/install-hooks.sh` run
- [ ] (B) Contracts reviewed by all three and frozen (`make validate` green)
- [ ] (B) `NVIDIA_API_KEY` works: one Nemotron call returns JSON
- [ ] (C) Photon beta account + project + number; `PHOTON_*` values shared privately (never in git)
- [ ] (A) `ml/ironguard_ml/stub.py` returns a valid `score_response` for any input
- [ ] (B) `api` serves every route from examples or the stub (`make api-stub`)
- [ ] (C) `web` renders `/phone` and `/reef` from mocks; `bridge` type-checks
- [ ] (all) `make smoke` green on **each** laptop

**Exit gate M0:** `make smoke` passes on main on all three machines. Contracts become additive-only.

## P1: Data and foundations (H1:00–H4:00)

- [ ] (B) Algae data factory v1: base families + benign + hard negatives → `data/generated/v1/*.jsonl`, schema-valid. **First 300 conversations by H2:30**; the full set by H3:30
- [ ] (A) `data/seed/` (about 30 conversations) + `data/test_human/` (40+ human-written, never used for training)
- [ ] (A) Embedding cache + conversation-level splitter + leakage test
- [ ] (A) Baselines B0–B3 trained; first `eval_summary.json` (EWR@k, lead time)
- [ ] (B) Safeguard tools implemented and unit-tested with fixtures (directory, RDAP, number, card, scrub)
- [ ] (C) Zero Day theme, phone shell, thread view, Trajectory HUD (mock data)
- [ ] (C) Photon echo bot: text the number, get a reply

**Exit gate M1:** dataset v1 and baseline numbers merged; UI shell merged; Photon echo works from a real phone.

## P2: Dragonfly model and Safeguard agent (H4:00–H7:00)

- [ ] (A) PreyNet trained (multi-task, causal GRU + CSTMD1 attention); 3 seeds
- [ ] (A) Temperature-scaled calibration + reliability numbers; lock-on hysteresis in `infer.py`
- [ ] (A) `eval_summary.json` v2: PreyNet vs B0–B3, ablations, cross-generator gap
- [ ] (B) `/v1/score` runs the real model; `/v1/agent/safety-card` runs the Nemotron tool loop
- [ ] (C) Bridge → api → reply in thread with HITL reply codes (1/2/3)
- [ ] (C) Reef dashboard: metrics charts read `/v1/metrics`

**Exit gate M2:** forward a scam's first two turns to the Photon number → the forecast and safety card come back in the thread. The same thread renders in `/phone`.

## P3: Leaf Sheep loop (H7:00–H9:30)

- [ ] (A) `chloroplast.train()` < 10 s on CPU; LOFO zero-day experiment + sample-efficiency curve
- [ ] (A) ONNX export with a `features` output + parity test vs PyTorch (max abs diff < 1e-4)
- [ ] (B) `/v1/zero-day` job: alert → Algae mutations → critique filter → train → publish manifest; SSE progress
- [ ] (B) Reef report endpoint (consent-only, scrubbed)
- [ ] (C) Browser inference: transformers.js MiniLM + onnxruntime-web PreyNet + chloroplast heads in JS
- [ ] (C) Leaf-sheep chloroplast badges with a vitality decay bar; live training view in `/reef`

**Exit gate M3:** a judge types a brand-new scam → chloroplast ready in about 2 min → a phone running in the browser flags that scam **with no message text on the network** (shown in the DevTools Network tab).

## P4: Freeze and polish (H9:30–H11:00)

- [ ] (all) **H10:00 FEATURE FREEZE.** Bug fixes only after this
- [ ] (A) Final `eval_summary.json`; charts exported to `docs/pitch/` (send them to C via a Request)
- [ ] (C) Demo video (≤ 3 min), Devpost text, screenshots
- [ ] (B) Clean-machine run: fresh clone → `make smoke` → full demo
- [ ] (all) Two full demo rehearsals with a timer

## P5: Submit (H11:00–H12:00)

- [ ] (B) Final merge; tag `v1.0-hackutd`
- [ ] (C) Devpost: tracks selected (T-Mobile Safe Signal, NVIDIA Nemotron, Photon), video, repo link
- [ ] (all) Laptops charged; the Photon number tested one last time; backup demo video on two machines

## Decisions log (append only)

| Time | Decision | Why |
|---|---|---|
| | | |
