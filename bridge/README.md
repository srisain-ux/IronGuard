# Photon echo bridge

This step verifies real Photon delivery. It replies **IronGuard online 🛡** to inbound text; it does not score or store conversations yet. `MOCK_API=1` needs no API in this echo stage. Forecast replies and reply-code actions are a later integration.

Node 20.6+ loads `bridge/.env` through the dev script's `--env-file=.env`. Node 20 also needs a release that supports `--import` (20.6+). Use the repo's fixed port 8787.

1. Open Terminal tab 1 in this checkout and run `make bridge`.
2. Open tab 2 in the same checkout and run `make tunnel`. Copy the `https://…trycloudflare.com` URL. Leave both tabs running.
3. Open the Photon dashboard for the project with the iMessage/SMS number. Register the URL **plus `/webhook`**, selecting inbound message events. Copy the one-time secret directly into `PHOTON_WEBHOOK_SECRET=` in **this checkout's** `bridge/.env`. Never paste it into chat or commit it. Restart tab 1 with Control-C, then `make bridge`. Wait for **Photon ready**.
4. Text the Photon number from your phone. Check for **IronGuard online 🛡**.

If `bridge/.env` does not exist, copy the root `.env.example` into it and fill `PHOTON_PROJECT_ID`, `PHOTON_SECRET`, and later `PHOTON_WEBHOOK_SECRET`. Keep `.env` ignored. Each worktree has its own `.env`.

## If the reply is missing

- Run `curl http://localhost:8787/health`. `needs_credentials`: fill project ID and secret; `needs_webhook_secret`: save the registration secret; `connection_failed`: check credentials, enabled channel, and network; then restart `make bridge`.
- Open the tunnel URL plus `/health`. If it cannot load, keep `make bridge` and `make tunnel` running. A restarted quick tunnel gets a new URL; update the dashboard webhook.
- In the dashboard, inspect the latest webhook delivery's HTTP status. `404`: use `/webhook`; `401`: confirm the saved secret is for that webhook and restart the bridge; `503`: check `/health`; `413`: payload exceeds 64 KB.
- If the webhook returned `200` but no reply arrived, check the bridge for the safe **Photon reply failed** message and check the project's channel/number status. Send a fresh text after fixing it. Outbound events and duplicate delivery IDs are ignored to prevent loops.
- Share only the status code and safe bridge status when asking for help. Keep secrets, phone numbers, message bodies and raw payloads private.

The SDK is pinned to `spectrum-ts@12.15.0`. Native Spectrum JSON signatures and timestamp freshness are checked by its webhook implementation. The bridge acknowledges before sending, limits inbound bodies, disables SDK telemetry/logging, and retains only bounded delivery hashes in memory. No streaming subscription is opened, so one inbound event has one delivery path.

## Photon Beta (2.0) projects

Projects beginning `pho_prj_` use the newer Photon API, not the Spectrum SDK. Keep the project API key in the existing `PHOTON_SECRET` setting. The bridge selects the compatible transport automatically; it adds no dependencies. It uses [Photon Beta webhook documentation](https://photon.codes/docs/beta/message-delivery/webhook), payload version `2026-07-01`, Standard Webhooks signatures, and the HTTPS messaging API at `https://api.photon.codes/v1`.

The project must already have an assigned iMessage line. Test from the sender identity assigned to that line, using a blue iMessage bubble. The API key needs project read/write access and permission to manage webhook destinations for automated registration. Do not buy or assign a new line merely to start this bridge.

In the [Beta dashboard](https://app.beta.photon.codes), create a webhook destination for `<tunnel-url>/webhook`, version `2026-07-01`, subscribed to `message.received`. Save its `whsec_…` signing secret as `PHOTON_WEBHOOK_SECRET` and restart the bridge. For API automation, create it with `POST /v1/projects/{projectId}/webhooks/destinations`, Bearer auth, and a stable `Idempotency-Key`; save the returned secret directly to ignored `bridge/.env`. Retrying the same logical creation with the same key can recover the one-time response without duplicating the destination.

The Beta transport verifies the original body and all three `webhook-*` headers, checks the event/project/channel and human-to-agent direct conversation, then queues an echo through the message API. It replies using the incoming Space ID and receiving agent's User ID. The reply's idempotency key derives from the incoming Message ID, so retries across restarts reuse the same send. API acceptance means queued delivery; the message arriving on the phone confirms the round trip.

`/health` includes only safe diagnostics: API type, received-event count, accepted-reply count and failed-reply count. No phone number or message text appears there. A restarted quick tunnel has a new URL and needs a new destination/secret; leave the active tunnel running during the demo. Beta uses different signature headers from Spectrum, so the two versions cannot share signing secrets.

Checks: `make check-bridge` and `pnpm --dir bridge test`.
