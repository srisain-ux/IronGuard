# Devpost submission copy

## Project name

IronGuard

## Tagline

Intercept the scam before the strike.

## Inspiration

Scam defenses often judge one message at a time. Yet many scams take shape across a conversation: a harmless opening, a shift in the story, then a request for a link, money, a code, or a gift card. We wanted to help people see that trajectory while there is still time to act.

## What it does

IronGuard reads a conversation turn by turn and forecasts its likely scam family, next stage, and time to strike. A calibrated confidence band makes uncertainty visible. In the browser phone, inference runs on-device; suspicious links are locked and the Safety Card offers practical next steps. People can also opt in to forward a thread to IronGuard through Photon and receive a forecast in the same messaging conversation.

When a new scam pattern appears, the Algae workflow can generate and critique synthetic conversations. A small chloroplast adapter can then teach the on-device model about that pattern without distributing the generated conversations to phones.

## How we built it

Dragonfly / PreyNet is a causal sequence model over role-prefixed MiniLM turn embeddings. It forecasts family, next stage, and turns to strike. A lock-on threshold reduces warning flicker. The browser runs the encoder and ONNX model locally, and validates downloaded chloroplast adapters before using them.

On the full-v1 test set of 266 conversations, PreyNet's EWR@1 through EWR@6 was 0.471, 0.591, 0.667, 0.719, 0.739, and 0.739. Mean lead time was 2.799 ± 0.324 turns. Test false-positive rate was 0.018, hard-negative false-positive rate was 0.034, and expected calibration error changed from 0.072 to 0.025. These are measured results for this test set; the human-written cross-generator test set was empty, so cross-generator performance remains unverified.

A's in-memory chloroplast benchmark used real MiniLM embeddings and measured 1.17–1.32 seconds total. This is a benchmark result, not a claim about every live training job. The project keeps ordinary browser scoring local. Photon is explicitly opt-in cloud forwarding; thread history stays in bridge memory.

## Nemotron workflows

Nemotron supports the Algae red-team workflow: plan scam variations, generate synthetic conversations, critique them, and hand suitable examples to the adapter trainer. The Safeguard workflow uses tools to look up curated official contacts, check domains and numbers, and prepare safer next steps. The product is a forecast and an action path, not a chat window.

## Photon usage

Photon connects a real iMessage/SMS number to IronGuard. A person forwards a suspicious thread and receives a forecast and safe actions in that same thread. Reply codes can request an official contact, ask why the forecast fired, or prepare an anonymous pattern report. This is an opt-in cloud mode; ordinary browser scoring does not send conversation text over the network.

## Challenges we ran into

Honest evaluation mattered as much as model quality. The full-v1 measurements support an early-warning story, but the human cross-generator set was empty. The zero-day proxy experiment is marked unavailable for pitch evidence, and its sample-efficiency values are not presented as real-world results. We also had to make the product clear about the boundary between local browser analysis and the user's explicit Photon forward.

## What's next

Evaluate on a human-written cross-generator test set, measure real Algae-generated zero-day protection end to end, and verify the live Photon flow with more users. Keep confidence calibrated, preserve the local-first default, and report false alarms alongside early warnings.

## Track alignment

| Track | How IronGuard fits |
|---|---|
| T-Mobile “Safe Signal” | **Before:** forecast a conversation's trajectory. **During:** lock suspicious links and offer safe next steps. **After:** support a consented anonymous pattern report. Local inference and visible uncertainty keep privacy and confidence in view. |
| NVIDIA “Nemotron Beyond a Chatbot” | Nemotron supports multi-step Algae generation and critique, plus Safeguard's tool workflow. Generated data can train an adapter head for local inference. |
| Photon | A person forwards a suspicious thread and receives the forecast and reply-code actions in the same messaging app. |
