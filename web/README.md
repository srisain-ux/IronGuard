# IronGuard phone demo

From the repo root, run `VITE_USE_MOCKS=1 make web`, then open http://localhost:5173/phone.

Choose Anna, PNC security, or the benign wrong-number thread. Use **Next message** to reveal one turn. At Anna's third turn the exact contract example shows `0.74 · UNCERTAIN`, `T-2 TURNS TO STRIKE`, and lock-on. Finish the thread to review the locked example domain through the ten-second Cool-Down Shield. Replay and thread switching preserve independent turn counters.

All scores are explicitly scripted, schema-shaped UI fixtures. The base turn-three score and two conversations are copied from `contracts/examples/`; the other prefixes and the bank conversation are local demo scripts, not model evaluation. No real verification, blocking, reporting, model inference or API parity is claimed. Missing evaluation and adapter metrics display `--`.

The compass imports angles from `contracts/taxonomy.json`. Its vector uses the six scam-family probabilities, with SVG zero degrees pointing north; benign contributes no direction. Opposing equal probabilities show no dominant direction. Needle length is the supplied risk. Stage labels use the script's current stage; the dashed label uses the forecast's next stage.

No fetch or text input exists in this mock experience. Safety Card buttons show local instructions. Suspicious addresses are non-interactive spans with screen-reader labels. Reveal displays plain text only; it never navigates. The native modal traps focus, closes with Escape, and restores focus. Pulse and breathing animations honor reduced motion.

`VITE_USE_MOCKS=0` still uses scripts and visibly states that the live phone model is unavailable. The real browser runtime and parity view are outside this mock task.

`/reef` reads `/v1/metrics` and subscribes to `/v1/events` in live mode. It shows Algae and training progress, masked Photon previews, adapter status, EWR@k, zero-day adaptation and sample efficiency, and reliability. Missing evaluation values display `--`; the current seed smoke artifact has no PreyNet, zero-day, or calibration result. Mock mode uses contract fixtures and labels its event as a fixture. A zero-day alert goes to `/v1/zero-day` only when submitted in live mode; the current API returns a demo-only job until the Algae pipeline is connected.

Checks: `make check-web` and `pnpm --dir web build`.
