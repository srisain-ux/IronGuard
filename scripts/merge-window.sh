#!/usr/bin/env bash
# Run at every merge window (M0..M4) on YOUR member branch (a/main, b/main or c/main).
# 1) merges your finished worktree branches into your member branch, 2) rebases on origin/main,
# 3) runs checks, 4) pushes. Then open (or update) your PR to main.
# Usage: ./scripts/merge-window.sh [worktree-branch ...]     e.g. ./scripts/merge-window.sh a/preynet a/metrics
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
member="$(git config --get ironguard.member)"
lower="$(echo "$member" | tr 'ABC' 'abc')"
branch="$(git branch --show-current)"

if [ "$branch" != "$lower/main" ]; then
  echo "✋ Switch to your member branch first: git switch $lower/main"; exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "✋ Uncommitted changes. Commit or stash them first."; exit 1
fi

for wt in "$@"; do
  echo "→ merging $wt into $branch"
  git merge --no-ff --no-edit "$wt"
done

git fetch origin
echo "→ rebasing $branch onto origin/main"
git rebase origin/main

echo "→ checks"
make validate
case "$member" in
  A) make check-ml ;;
  B) make check-api ;;
  C) make check-web check-bridge ;;
esac

git push --force-with-lease origin "$branch"
echo "✅ $branch is rebased, checked and pushed. Open/refresh your PR:  gh pr create --base main --head $branch --fill  (or update the existing PR)"
