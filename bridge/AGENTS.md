# bridge/AGENTS.md: Member C (Photon bridge). Root AGENTS.md rules still apply.

## What it is
A small Node 20 + TypeScript service that connects the Photon number (iMessage/SMS) to the IronGuard API. One process: it receives inbound messages and replies with `spectrum-ts`.

## Stack
Node 20, TypeScript, `spectrum-ts` (**pin the exact version you install**; the SDK is in early preview), `tsx` for dev, the built-in `fetch`. Port **8787**. Exposed with `make tunnel` (cloudflared) for the Photon webhook.

## Flow (per Photon "space" = one conversation)
1. Inbound message → **acknowledge immediately** (return 2xx right away; Photon retries slow handlers) → queue the work.
2. Keep `history[space.id]` **in memory only** (max 20 turns, cleared after 30 min idle). Forwarded text counts as `sender: "them"`. If the user pastes several messages at once, split on newlines into separate turns.
3. Reply-code handling first: if a `pending[space.id]` exists and the text is `1`/`2`/`3` → run that next step (report / official number / explain) and reply.
4. Otherwise `POST {IRONGUARD_API_URL}/v1/score` with the thread → if `risk ≥ 0.35`, call `POST /v1/agent/safety-card` → format the reply (template below) → `space.send(text(...))`.
5. Publish a masked preview to the API event stream (the API owns SSE; the bridge calls `POST /v1/events/publish` if B exposes it, otherwise skip).

## Reply template (plain text; works over SMS)
```
🛡 IronGuard · {BAND} confidence
{headline}
Trajectory: {family_label} · {next_stage} next · ~{tts} turns to strike
Why: {why[0]}
Reply 1 = block & report anonymously · 2 = {official_label} · 3 = why?
(Forward mode: this thread was analyzed in the cloud because you sent it to us.)
```
For `uncertain`, say so plainly: `Not sure yet. Forward the next message and we'll update the forecast.`

## Edge cases (Photon judges score "depth")
Non-text content (images, reactions) → reply "I can only read text right now." · Empty or emoji-only → ignore · Same message forwarded twice → dedupe by hash · API down → "Can't check right now. Don't click links or send money until you verify with the company's official app." · Webhook signature check uses `PHOTON_WEBHOOK_SECRET` (shown once at registration).

## Mock mode
`MOCK_API=1` → use `contracts/examples/score_response.turn3.json` and `safety_card.bank.json` so the bridge works before the API is ready.
