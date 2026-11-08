# 🛡 IronGuard · HackUTD 2026 "Zero Day"

**Intercept the scam before the strike.** A dragonfly-inspired trajectory model forecasts where a text conversation is heading (scam family, next stage, turns until the ask) with honest, calibrated confidence. A leaf-sheep-inspired distillation loop learns brand-new scams from Nemotron-made synthetic data and ships an 82 KB "chloroplast" that runs on the phone. A Nemotron Safeguard Agent and a Photon iMessage/SMS number turn the forecast into protection.

## Start here (H0)
1. **B:** create the GitHub repo from this folder and push it as the **first commit, before running `install-hooks.sh`** (the kit touches every member's folders, so the hook would block it). Set *merge commits only*, protect `main`, create the `a/main`, `b/main` and `c/main` branches, and fill in `.github/CODEOWNERS`. (`docs/PLAYBOOK.md` §7.2)
2. **Everyone:** install the tools (`docs/PLAYBOOK.md` §6.1), then:
   ```bash
   git clone <repo> && cd ironguard
   ./scripts/install-hooks.sh A        # your letter: A, B or C
   git switch a/main                   # your member branch
   ```
3. **Everyone:** read `AGENTS.md` (5 min) and your folder's `AGENTS.md`. Paste the Master Prompt from `docs/PROMPTS.md` into your first agent thread.
4. **15-minute contracts call:** walk through `contracts/` together. When all three agree, `make validate` → **frozen**.

| File | What it's for |
|---|---|
| `AGENTS.md` / `CLAUDE.md` | Rules every agent follows (Codex reads AGENTS.md; Claude reads CLAUDE.md, which imports it) |
| `docs/MODEL_SPEC.md` | **The model**: data, PreyNet, calibration, chloroplasts, evaluation, the biology mapping, the gap |
| `docs/PLAYBOOK.md` | Stack, roles, timeline, device setup, merge protocol, model/effort matrix, demo, risks |
| `docs/PROMPTS.md` | Copy-paste prompts per member per phase, with model and effort |
| `PROGRESS.md` + `progress/*.md` | Phase gates (B) + per-member logs (no shared file means no conflicts) |
| `docs/THEME.md` + `web/src/theme/zero-day.css` | The Zero Day look, sampled from the opening-ceremony deck |
| `contracts/` | The only interface between members: JSON Schemas, examples, taxonomy |
| `scripts/` | Ownership pre-commit hook, contract validator, merge-window helper |
