#!/usr/bin/env bash
# make doctor: checks that THIS laptop is ready for its member's work. Prints ✅ / ❌ and how to fix each ❌.
cd "$(git rev-parse --show-toplevel)" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:$PATH"
fails=0
ok()   { echo "✅ $1"; }
bad()  { echo "❌ $1"; echo "   ↳ fix: $2"; fails=$((fails + 1)); }
warn() { echo "⚠️  $1"; echo "   ↳ $2"; }
has()  { command -v "$1" >/dev/null 2>&1; }

member="$(git config --get ironguard.member)"
lower="$(echo "$member" | tr 'ABC' 'abc')"
echo "IronGuard doctor: member ${member:-?}"
echo "------------------------------------------"

[ -n "$member" ] && ok "member letter is $member" || bad "member letter not set" "./scripts/install-hooks.sh A   (double=A, ss=B, jcubed=C)"
[ -x "$(git rev-parse --git-common-dir)/hooks/pre-commit" ] && ok "ownership guard installed" || bad "ownership guard missing" "./scripts/install-hooks.sh $member"
branch="$(git branch --show-current)"
if [ "$branch" = "$lower/main" ]; then ok "main folder is on $branch"; else bad "main folder is on '$branch'" "git switch $lower/main"; fi
[ -z "$(git status --porcelain)" ] && ok "main folder has no uncommitted changes" || warn "main folder has uncommitted changes" "commit them or ask your agent; the merge script needs a clean folder"

has git && ok "git" || bad "git missing" "xcode-select --install"
{ has uv || [ -x "$HOME/.local/bin/uv" ]; } && ok "uv" || bad "uv missing" "curl -LsSf https://astral.sh/uv/install.sh | sh"
if has node && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ]; then ok "node $(node -v)"; else bad "node 20+ missing" "install Node 20 LTS from https://nodejs.org"; fi
has pnpm && ok "pnpm" || bad "pnpm missing" "corepack enable   (then open a new terminal)"
has codex && ok "codex" || bad "codex missing" "npm i -g @openai/codex && codex login"
{ has t3 || ls -d /Applications/T3\ Code* >/dev/null 2>&1; } && ok "T3 Code" || warn "T3 Code not found" "install it: brew install --cask t3-code  (or run: npx t3@latest)"

# plugins (best effort: looks for their install folders)
grep -rqs ponytail "$HOME/.codex" 2>/dev/null && ok "Ponytail installed for Codex" || warn "Ponytail not detected for Codex" "codex plugin marketplace add DietrichGebert/ponytail && codex plugin add ponytail@ponytail"
grep -rqsi "ecc" "$HOME/.codex" 2>/dev/null && ok "ECC installed for Codex" || warn "ECC not detected for Codex" "codex plugin marketplace add affaan-m/ECC && codex plugin add ecc@ecc"

if [ "$member" = "A" ] || [ "$member" = "B" ]; then
  has claude && ok "Claude Code" || bad "Claude Code missing" "curl -fsSL https://claude.ai/install.sh | bash"
  grep -rqs ponytail "$HOME/.claude/plugins" 2>/dev/null && ok "Ponytail installed for Claude Code" || warn "Ponytail not detected for Claude Code" "in Claude Code: /plugin marketplace add DietrichGebert/ponytail  then  /plugin install ponytail@ponytail"
  grep -rqsi "ecc" "$HOME/.claude/plugins" 2>/dev/null && ok "ECC installed for Claude Code" || warn "ECC not detected for Claude Code" "in Claude Code: /plugin marketplace add https://github.com/affaan-m/ECC  then  /plugin install ecc@ecc"
fi

if [ "$member" = "B" ]; then
  base="$(grep -E '^NEMOTRON_BASE_URL=' api/.env 2>/dev/null | cut -d= -f2-)"
  key="$(grep -E '^NVIDIA_API_KEY=' api/.env 2>/dev/null | cut -d= -f2-)"
  if [ ! -f api/.env ]; then
    bad "api/.env missing" "cp .env.example api/.env   then follow 'ss only: Nemotron on Brev' in docs/PROMPTS.md"
  elif echo "$base" | grep -q "localhost:8001"; then
    has brev && ok "Brev CLI" || bad "Brev CLI missing" "ask Claude to install it, or: brew install brevdev/homebrew-brev/brev"
    if [ -z "$key" ] || [ "$key" = "the-password-you-gave-brev_serve.sh" ]; then
      bad "NVIDIA_API_KEY in api/.env is still the placeholder" "set it to the password you passed to brev_serve.sh on the Brev machine"
    elif curl -fs -m 5 -H "Authorization: Bearer $key" "$base/models" >/dev/null 2>&1; then
      ok "Nemotron on Brev is reachable at $base"
    else
      bad "Nemotron on Brev not reachable at $base" "open a new Terminal tab in IronGuard and run: make brev-tunnel   (and check the Brev machine said NEMOTRON IS READY)"
    fi
  elif echo "$key" | grep -qE '^nvapi-[A-Za-z0-9_-]{20,}'; then
    ok "build.nvidia.com key is in api/.env"
  else
    bad "Nemotron not configured in api/.env" "follow 'ss only: Nemotron on Brev' in docs/PROMPTS.md (or paste a build.nvidia.com nvapi- key)"
  fi
fi

# B hosts the demo (make bridge) and C builds the bridge: both need Photon keys
if [ "$member" = "B" ] || [ "$member" = "C" ]; then
  if grep -qE '^PHOTON_PROJECT_ID=.+' bridge/.env 2>/dev/null && grep -qE '^PHOTON_SECRET=.+' bridge/.env 2>/dev/null; then ok "Photon keys are in bridge/.env"
  else bad "Photon keys missing from bridge/.env" "app.photon.codes → your project → copy Project ID and Secret; then: cp .env.example bridge/.env and fill PHOTON_PROJECT_ID= and PHOTON_SECRET="; fi
  has cloudflared && ok "cloudflared" || bad "cloudflared missing" "brew install cloudflared   (or download from https://github.com/cloudflare/cloudflared/releases)"
fi

echo "------------------------------------------"
if [ "$fails" -eq 0 ]; then echo "🟢 READY. Any ⚠️ lines are worth fixing but won't block you."; else echo "🔴 $fails thing(s) to fix above, then run: make doctor"; fi
exit "$fails"
