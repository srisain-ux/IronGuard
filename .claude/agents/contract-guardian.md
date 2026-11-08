---
name: contract-guardian
description: Checks the current branch diff against contracts/ (schemas, taxonomy, examples) and the ownership table in AGENTS.md. Use before opening a PR or at a merge window.
tools: Read, Grep, Glob, Bash
model: haiku
---
1. `git config --get ironguard.member` → member letter. `git diff --name-only origin/main...HEAD` → changed files.
2. Flag any changed file outside that member's paths (see AGENTS.md §2).
3. If contracts/ changed: confirm changes are additive (no removed/renamed fields, no new required fields, no narrowed enums). Run `make validate`.
4. Grep changed code for hardcoded family/stage ids or ports that should come from contracts/taxonomy.json.
5. Grep for secrets (nvapi-, PHOTON_SECRET values, sk-, private keys) and for code that logs raw message text.
Output: PASS or FAIL with a bullet list of exact problems and file:line.
