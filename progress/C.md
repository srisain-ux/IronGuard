# progress/C.md: Member C (jcubed), Leaf Sheep (UI + Photon)

> Only member C (and their agents) edits this file. Append; don't rewrite history.
> Format for each entry: `[HH:MM][P<phase>] what changed | skipped | unverified`

## Now
- Phase: P1
- Working on: `/phone` mock demo and Photon echo shipped on `c/phone-hud`; awaiting live phone test.
- Blocked by: Photon webhook registration/secret and a user-sent test text are still required for end-to-end confirmation.

## Log
- 
- [02:05][P1] Built `/phone`: three scripted conversations, independent next-message/replay controls, incoming-message risk/word bands/TTS/lock HUDs, weighted six-direction taxonomy compass, current/predicted kill chain, highest-attention highlight, locked address spans, ten-second breathing modal, local Safety Card actions and leaf-sheep placeholder. Added Vite/React/TS/Tailwind scaffolding and contract-derived fixtures. | skipped: live inference, parity, `/reef`, real verification/reporting and adapter metrics (outside this mock step); missing metrics/vitality show `--` | unverified: real model integration and physical phone echo. Web commit `cc7761d`.
- [02:05][P1] Added pinned `spectrum-ts@12.15.0` Photon echo on 8787. `bridge/package.json` dev script uses `node --env-file=.env --import tsx src/index.ts`. Native signed webhook at `/webhook` (also `/`), health at `/health`, prompt acknowledgment, bounded delivery-hash dedupe, inbound-only replies, no raw text persistence, SDK telemetry/logging off. Copied ignored credentials into this worktree without displaying them. | skipped: score/history/reply-code integration (later phase) | unverified: live Photon credentials/channels and delivery; last check found no running bridge/tunnel and an empty webhook secret. Provided four numbered setup steps and explained that the echo follows a text sent by the user. Bridge commit `cf46eaf`.
- [02:05][P1] §F checks: `make validate check-web check-bridge`, `pnpm --dir bridge test` (4 tests), `pnpm --dir web build`, all local mock schemas plus attention/probability consistency passed. Browser QA passed all three scripts, counters/replay, turn-three locked forecast, six compass labels, kill-chain states, locked links, actual 10-second gating, modal Tab cycling/Escape/focus restoration, Safety Card actions, benign no-lock behavior, reduced motion, 390px no overflow, 44px targets, no uploads and no browser errors. Fixed modal focus behavior, below-viewport background, premature bank-check copy and unavailable vitality semantics during review. | skipped: unavailable Ponytail/ECC skill invocations (searched installed skill/plugin paths; doctor's recursive text detection is not proof of availability); performed direct correctness/privacy/contract and bloat reviews instead. Used stdlib/existing stack, no animation/UI library or real runtime dependency added. | unverified: Node 20 execution (local Node is 26.13.0), full screen-reader session, and real upstreams. T3 preview initially worked, then timed out twice; completed QA with temporary Playwright tooling and installed Chrome, without adding test dependencies to the service manifest. Ownership guard and staged whitespace checks passed; only C-owned paths changed. No PR, push or merge.

## Requests (changes I need from another owner; they pick these up)
<!-- e.g. - [ ] @B contracts/score_response: add optional field `latency_ms` (number). Why: HUD shows it. -->
- [ ] @B `scripts/doctor.sh`: detect actual Ponytail/ECC skill/plugin entry points instead of matching any `ponytail`/`ecc` text under `.codex`; doctor reported installed but neither callable review skill was present.
- [ ] @B add `contracts/examples/conversation.bank_impersonation.json` and per-prefix bank/benign score examples. Current web bank/prefix fixtures live only in `web/src/mocks/`, are schema-valid and explicitly scripted; replace these with shared examples when available.

## Handoffs (things I've shipped that others can now use)
<!-- e.g. - [x] ml/artifacts/preynet.onnx v2 (features output = 640-d) merged in M2 -->
- [x] P1 web: `VITE_USE_MOCKS=1 make web` → `http://localhost:5173/phone`; `web/src/demo.ts` exports `demos`, `Score`, `safetyCard(id, score)`; `web/src/compass.tsx` exports `Compass({score})` using `contracts/taxonomy.json` angles. `web/README.md` documents the local demo and runtime limits. All displayed forecasts are fixtures, not evaluation results.
- [x] P1 Photon: `make bridge`, `make tunnel`, register `<tunnel-https-url>/webhook`, save `PHOTON_WEBHOOK_SECRET` in this worktree's ignored `bridge/.env`, restart bridge, then text the project number. `bridge/src/server.ts` exports `ONLINE`, `echoHandler`, `bridgeServer`; `bridge/README.md` gives exact setup and safe debugging by health/webhook status. Echo is `IronGuard online 🛡`; no API required, including with `MOCK_API=1`.
