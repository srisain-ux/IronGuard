#!/usr/bin/env bash
# Pre-commit guard: blocks commits that touch files outside your member's ownership.
# Your letter: git config ironguard.member A|B|C  (shared by all worktrees of this clone)
# Allowed bypasses: merge commits (MERGE_HEAD present) and IRONGUARD_ALLOW=1 (integration lead in a merge window only).
set -euo pipefail

member="$(git config --get ironguard.member || true)"
if [ -z "$member" ]; then
  echo "✋ IronGuard: set your member letter first:  git config ironguard.member A   (or B / C)"
  exit 1
fi

git_dir="$(git rev-parse --git-dir)"
if [ -f "$git_dir/MERGE_HEAD" ] || [ -f "$git_dir/REBASE_HEAD" ] || [ "${IRONGUARD_ALLOW:-}" = "1" ]; then
  exit 0
fi

case "$member" in
  A) allowed="ml/ data/seed/ data/test_human/ docs/MODEL_SPEC.md progress/A.md" ;;
  B) allowed="api/ contracts/ data/generated/ scripts/ .claude/ .github/ docs/PLAYBOOK.md docs/PROMPTS.md progress/B.md AGENTS.md CLAUDE.md PROGRESS.md Makefile README.md .gitignore .gitattributes .env.example" ;;
  C) allowed="web/ bridge/ docs/THEME.md docs/pitch/ progress/C.md" ;;
  *) echo "✋ ironguard.member must be A, B or C (got '$member')"; exit 1 ;;
esac

bad=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  ok=0
  for p in $allowed; do
    case "$f" in
      "$p"*) ok=1; break ;;
    esac
  done
  # nested agent docs inside your own dirs are covered by the prefixes above
  if [ "$ok" -eq 0 ]; then bad="$bad
   - $f"; fi
done <<EOF
$(git diff --cached --name-only --diff-filter=ACMRD)
EOF

if [ -n "$bad" ]; then
  echo "✋ IronGuard ownership check failed for member $member. You staged files you don't own:$bad"
  echo
  echo "Fix: git restore --staged <file> && git checkout -- <file>"
  echo "Then add a line under '## Requests' in progress/$member.md asking the owner for the change."
  exit 1
fi

# If contracts changed (B only), they must still validate.
if git diff --cached --name-only | grep -q '^contracts/'; then
  if command -v uv >/dev/null 2>&1; then
    uv run --quiet --with jsonschema python scripts/validate_contracts.py
  else
    echo "⚠ uv not found; skipping contract validation (run 'make validate' before pushing)"
  fi
fi
exit 0
