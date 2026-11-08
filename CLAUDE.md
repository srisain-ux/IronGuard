# CLAUDE.md

@AGENTS.md

## Claude Code specifics (members A and B)

- `AGENTS.md` above is the single source of truth. Codex reads it directly. This file only adds Claude-specific notes, so **never duplicate rules here**.
- Your member letter comes from `git config ironguard.member`. Check it at the start of a session (`git config --get ironguard.member`) and stay inside that member's paths.
- **Subagents** (defined in `.claude/agents/`). Use them for anything parallel or read-only, and keep the main thread for design decisions:
  - `data-auditor` (Haiku): checks a JSONL dataset for schema validity, class balance, near-duplicates, and labels that leak into text.
  - `leakage-hunter` (Opus): reviews training and eval code for train/test leakage. Run it before any metric reaches the pitch.
  - `eval-runner` (Sonnet): runs `make eval`, compares against the last `eval_summary.json`, and reports regressions.
  - `contract-guardian` (Haiku): checks a diff against `contracts/` and the ownership table.
- Before opening a PR: `/code-review`, then `/ponytail-review branch`, then `make validate && make check-<area>`.
- Under context pressure, save state to `progress/<you>.md` before the conversation gets summarized (or use ECC `/save-session`).
- T3 Code runs Claude through the Agent SDK, which its author reports drains the 5-hour usage window faster. For long ML sessions (member A), run Claude Code directly in a terminal and use T3 Code for orchestration and Codex threads.
