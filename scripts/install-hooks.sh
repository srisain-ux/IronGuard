#!/usr/bin/env bash
# One-time setup per clone (worktrees share it). Usage: ./scripts/install-hooks.sh A|B|C
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ $# -ge 1 ]; then git config ironguard.member "$1"; fi
member="$(git config --get ironguard.member || true)"
[ -z "$member" ] && { echo "Usage: ./scripts/install-hooks.sh A|B|C"; exit 1; }

hooks="$(git rev-parse --git-common-dir)/hooks"
mkdir -p "$hooks"
cat > "$hooks/pre-commit" <<'HOOK'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/check_ownership.sh"
HOOK
chmod +x "$hooks/pre-commit" scripts/*.sh

# Merge-friendly git defaults for this repo
git config pull.rebase true          # never create accidental merge commits on pull
git config rebase.autoStash true     # rebase even with uncommitted work in progress
git config rerere.enabled true       # remember conflict resolutions across rebases
git config fetch.prune true
git config core.autocrlf false       # .gitattributes handles line endings

echo "✅ Hooks installed for member $member. Ownership guard active in every worktree of this clone."
