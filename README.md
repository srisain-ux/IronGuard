# 🛡 IronGuard · HackUTD 2026 "Zero Day"

**Intercept the scam before the strike.** A dragonfly-inspired trajectory model forecasts where a text conversation is heading (scam family, next stage, turns until the ask) with honest, calibrated confidence. A leaf-sheep-inspired distillation loop learns brand-new scams from Nemotron-made synthetic data and ships an 82 KB "chloroplast" that runs on the phone. A Nemotron Safeguard Agent and a Photon iMessage/SMS number turn the forecast into protection.

## Start here
**Follow [`docs/PROMPTS.md`](docs/PROMPTS.md) top to bottom.** It's the step-by-step script: what to click, what to paste, and when to merge.

First, on every laptop, inside the `IronGuard` folder:
```bash
git pull --rebase origin main && make doctor
```
Fix every ❌ that `make doctor` prints (each one shows the exact fix) until it says 🟢 READY.

New teammate? Clone first: `git clone https://github.com/srisain-ux/IronGuard.git && cd IronGuard && ./scripts/install-hooks.sh A` (double=A, ss=B, jcubed=C), then `git switch a/main` (or `b/main` / `c/main`).

| File | What it's for |
|---|---|
| `AGENTS.md` / `CLAUDE.md` | Rules every agent follows (Codex reads AGENTS.md; Claude reads CLAUDE.md, which imports it) |
| `docs/MODEL_SPEC.md` | **The model**: data, PreyNet, calibration, chloroplasts, evaluation, the biology mapping, the gap |
| `docs/PLAYBOOK.md` | Stack, roles, timeline, device setup, merge protocol, model/effort matrix, demo, risks |
| `docs/PROMPTS.md` | **The step-by-step script**: human steps + copy-paste prompts per step, with model and effort |
| `PROGRESS.md` + `progress/*.md` | Phase gates (B) + per-member logs (no shared file means no conflicts) |
| `docs/THEME.md` + `web/src/theme/zero-day.css` | The Zero Day look, sampled from the opening-ceremony deck |
| `contracts/` | The only interface between members: JSON Schemas, examples, taxonomy |
| `scripts/` | Ownership pre-commit hook, contract validator, merge-window helper |
