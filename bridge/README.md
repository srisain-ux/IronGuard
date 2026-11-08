# Photon forecast bridge

Forward text to the Photon number to get an IronGuard trajectory and safety card in the same conversation. The bridge keeps at most 20 forwarded turns per space in memory, clears a space after 30 minutes idle, and never logs message text. Newlines in a forward become separate turns. Reply `1` to submit a consented anonymous pattern report and get phone blocking instructions, `2` for an available official contact or safe verification instructions, or `3` for the reasons behind the card. Photon cannot block a sender on your phone.

`MOCK_API=1` uses the shared score and safety-card examples and requires no API; reports are simulated in that mode. With `MOCK_API=0`, set `IRONGUARD_API_URL` (default `http://localhost:8000`); the bridge calls `/v1/score`, then `/v1/agent/safety-card` when risk is at least 0.35. It also sends a fully masked preview to `/v1/events/publish`. That event is optional and never contains forwarded text. The stub API returns demo forecasts and an unverified demo card; its replies are not real model or contact verification.

Node 20.12+ loads an optional `bridge/.env` at startup; exported environment variables take precedence. Without a file or credentials, the bridge still starts on port 8787 and `/health` reports `needs_credentials`. It does not accept Photon traffic until configured. Other environment-file errors fail startup.

1. Open Terminal tab 1 in this checkout and run `make api-stub`.
2. Open Terminal tab 2 in this checkout and run `make bridge`. Wait for **Photon ready**.
3. Open Terminal tab 3 in this checkout and run `make tunnel`. Copy the `https://…trycloudflare.com` URL. Leave all three tabs running.
4. Open the Photon dashboard for the project with the iMessage/SMS number. Register the URL **plus `/webhook`**, selecting inbound message events. Copy the one-time secret directly into `PHOTON_WEBHOOK_SECRET=` in **this checkout's** `bridge/.env`. Never paste it into chat or commit it. Restart tab 2 with Control-C, then `make bridge`.
5. Send the two messages below as separate texts to the Photon number from your phone. The second text has a newline and should produce a trajectory reply; reply `2` to test the safe official-contact step.

   Message 1: `Hey, are we still on for golf tomorrow at 9?`

   Message 2:
   ```text
   I think you have the wrong number
   Oh so sorry! My assistant must have typed it wrong. You seem nice though, I'm Anna, I just moved to Dallas
   ```

   In stub mode, the `wrong number` text selects the demo relationship-scam trajectory. The safety card is a generic stub. If you need the contract fixture reply instead, set `MOCK_API=1` in `bridge/.env` and restart tab 2; tab 1 is then optional.

If `bridge/.env` does not exist, copy the root `.env.example` into it and fill `PHOTON_PROJECT_ID`, `PHOTON_SECRET`, and later `PHOTON_WEBHOOK_SECRET`. Keep `.env` ignored. Each worktree has its own `.env`.

## If the reply is missing

- Run `curl http://localhost:8787/health`. `needs_credentials`: fill project ID and secret; `needs_webhook_secret`: save the registration secret; `connection_failed`: check credentials, enabled channel, and network; then restart `make bridge`.
- Open the tunnel URL plus `/health`. If it cannot load, keep `make bridge` and `make tunnel` running. A restarted quick tunnel gets a new URL; update the dashboard webhook.
- In the dashboard, inspect the latest webhook delivery's HTTP status. `404`: use `/webhook`; `401`: confirm the saved secret is for that webhook and restart the bridge; `503`: check `/health`; `413`: payload exceeds 64 KB.
- If the webhook returned `200` but no reply arrived, check the bridge for the safe **Photon reply failed** message and check the project's channel/number status. Send a fresh text after fixing it. Outbound events and duplicate delivery IDs are ignored to prevent loops.
- Share only the status code and safe bridge status when asking for help. Keep secrets, phone numbers, message bodies and raw payloads private.

The SDK is pinned to `spectrum-ts@12.15.0`. Native Spectrum JSON signatures and timestamp freshness are checked by its webhook implementation. The bridge acknowledges before scoring, limits inbound bodies, disables SDK telemetry/logging, and retains only bounded message hashes and thread history in memory. Work in a space is serialized so close-together forwards remain in order. No streaming subscription is opened, so one inbound event has one delivery path.

## Photon Beta (2.0) projects

Projects beginning `pho_prj_` use the newer Photon API, not the Spectrum SDK. Keep the project API key in the existing `PHOTON_SECRET` setting. The bridge selects the compatible transport automatically; it adds no dependencies. It uses [Photon Beta webhook documentation](https://photon.codes/docs/beta/message-delivery/webhook), payload version `2026-07-01`, Standard Webhooks signatures, and the HTTPS messaging API at `https://api.photon.codes/v1`.

The project must already have an assigned iMessage line. Test from the sender identity assigned to that line, using a blue iMessage bubble. The API key needs project read/write access and permission to manage webhook destinations for automated registration. Do not buy or assign a new line merely to start this bridge.

In the [Beta dashboard](https://app.beta.photon.codes), create a webhook destination for `<tunnel-url>/webhook`, version `2026-07-01`, subscribed to `message.received`. Save its `whsec_…` signing secret as `PHOTON_WEBHOOK_SECRET` and restart the bridge. For API automation, create it with `POST /v1/projects/{projectId}/webhooks/destinations`, Bearer auth, and a stable `Idempotency-Key`; save the returned secret directly to ignored `bridge/.env`. Retrying the same logical creation with the same key can recover the one-time response without duplicating the destination.

The Beta transport verifies the original body and all three `webhook-*` headers, checks the event/project/channel and human-to-agent direct conversation, then queues a forecast through the message API. It replies using the incoming Space ID and receiving agent's User ID. The reply's idempotency key derives from the incoming Message ID, so retries across restarts reuse the same send. API acceptance means queued delivery; the message arriving on the phone confirms the round trip.

`/health` includes only safe diagnostics: API type, received-event count, accepted-reply count and failed-reply count. No phone number or message text appears there. A restarted quick tunnel has a new URL and needs a new destination/secret; leave the active tunnel running during the demo. Beta uses different signature headers from Spectrum, so the two versions cannot share signing secrets.

Checks: `make check-bridge` and `pnpm --dir bridge test`.
