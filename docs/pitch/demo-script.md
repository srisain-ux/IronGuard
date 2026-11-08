# IronGuard live demo · 3:00

Follow `docs/PLAYBOOK.md` §10 in order. Use a real Photon number and a consenting judge's test phone for the forward flow. Have the browser open to `/phone`, a second browser tab at `/reef`, and the local DevTools Network panel ready. If the API or Photon connection is unavailable, say so and use the labeled browser demonstration; do not present a fixture as a live run.

## 0:00–0:20 · The gap

**Screen:** `/phone`, incident chooser visible.

**Clicks:** Click **Relationship / crypto** in the incident chooser. Leave the thread at its first message.

**Say:** “Most filters ask whether this message is a scam. But the dangerous moment often comes later, after trust is built. IronGuard follows the conversation and forecasts the strike before the request arrives.”

## 0:20–1:10 · Photon live

**Screen:** The consenting judge's Messages app, then the same thread with IronGuard's reply.

**Clicks/actions:** On the judge's phone, open the prepared scam test thread. Select the thread, tap **Forward**, select the registered IronGuard Photon contact, and tap **Send**. Return to Messages and open IronGuard's reply. Read the family, forecast, confidence band, explanation, and reply choices. Type `2` and tap **Send**. Show the official contact response.

**Say:** “This is the same conversation through Photon. The judge forwards the thread, and IronGuard returns the forecast in the same messaging app. Confidence is explicit, and the explanation gives the person something useful to check. Reply two asks for the curated directory contact. Caller ID can be spoofed, so the reply still tells you to verify in the company's official app.”

**Fallback if Photon is unavailable:** Say, “Photon is the opt-in cloud path; this prepared recording shows the reply flow.” Play the verified recording. Do not imply a live delivery.

## 1:10–2:00 · The model

**Screen:** `/reef`, scroll to **Early Warning Rate**, then **Reliability Diagram**.

**Clicks:** Click **REEF LAB** in the header. Scroll until the Early Warning Rate chart fills the screen. Point to PreyNet and the baseline lines. Scroll to the Reliability Diagram.

**Say:** “The model reads turns in order. PreyNet reaches an early-warning rate of 0.591 by turn two, and its measured mean lead time is 2.799 ± 0.324 turns on the full-v1 test set. Its expected calibration error moves from 0.072 to 0.025. Those are test-set measurements, not a promise about every message. The model uses causal sequence state and a population-vector compass to summarize where the conversation is heading.”

## 2:00–2:45 · Zero-day path and privacy

**Screen:** `/reef` terminal, then `/phone`, then DevTools Network.

**Clicks:** Return to the top of Reef Lab. In **new zero-day alert**, enter a short pattern description without private message text, then click **SEND ALERT**. Keep the terminal visible while events arrive. If the API reports a demo endpoint, state that no training job ran. If a real job completes, wait for the validated adapter status, then switch to `/phone` and show the badge. Open DevTools **Network** and point out that ordinary phone scoring makes no request carrying the conversation text.

**Say:** “For a new pattern, the Algae workflow can generate and critique synthetic conversations, then train a small chloroplast adapter. A's measured adapter benchmark took 1.17–1.32 seconds total on its stated in-memory benchmark; this is not the elapsed time of this screen unless the live run confirms it. The browser downloads an adapter, not the training conversations. In ordinary phone mode, message text stays on the device. Photon is the explicit opt-in cloud path.”

## 2:45–3:00 · Close

**Screen:** `/phone`, locked trajectory and safe next steps visible.

**Clicks:** Return to the phone tab. Keep the trajectory HUD and Safety Card actions in frame.

**Say:** “Protected before, during, and after the threat. Built on Nemotron, grounded in a causal model, and reachable from a phone through Photon. IronGuard: intercept the scam before the strike.”

## Rehearsal checks

- Use the same prepared wrong-number thread on the judge's phone and in the browser script.
- Verify the Photon reply codes and the official contact response before the demo.
- Keep the browser footer and mock labels visible whenever a fixture is on screen.
- Only show adapter absorption after the browser has downloaded and validated the manifest.
- Do not claim attention improves results: the handoff says the measured advantage is within one standard deviation.
- Do not present the proxy zero-day experiment as pitch evidence; A marks it unavailable.
