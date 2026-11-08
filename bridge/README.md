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

The SDK is pinned to `spectrum-ts@12.15.0`. Native Photon/Spectrum JSON signatures and timestamp freshness are checked by its webhook implementation. The bridge acknowledges before sending, limits inbound bodies, disables SDK telemetry/logging, and retains only bounded delivery hashes in memory. No streaming subscription is opened, so one inbound event has one delivery path.

Checks: `make check-bridge` and `pnpm --dir bridge test`.
