# Reef Guard botanical theme (owner: C)

The user-supplied botanical redesign replaces the original Zero Day neon visual direction for the web app. Reef Guard is the displayed product name; internal model names, contracts, environment variables, routes, and service identifiers retain their existing names.

## Design contract

Reef Guard is a calm, usable conversation-protection tool. The primary phone action is choosing a conversation and revealing its next message. The primary Reef Lab action is submitting a new scam-pattern description. The model's uncertainty, privacy boundaries, and measured results must remain visible.

The supplied `ironguard-botanical-redesign.zip` provides the paper notebook, sage pond, seafoam reef, watercolor dragonfly and leaf sheep, tape, and organic panel references. Its embedded artwork is extracted and compressed under `web/public/botanical/`. The replacement `Reef Guard.png` supplies the complete botanical emblem and wordmark, used unchanged in the navigation and favicon. The display name is **Reef Guard**.

Phone hierarchy: shared navigation → short illustrated introduction → conversation selector, phone simulation, forecast outlook → deeper conversation graphs. Reef hierarchy: pattern notebook and learning journey → validated adapter shelf → event journal and Photon feed → evaluation graphs and data tables. At narrow widths the phone follows the conversation selector, with the analysis and local-message tools below it. Target review viewports are 1280×800 desktop and 390×844 mobile, with an additional 320px overflow check.

## Palette and type

Tokens remain in `web/src/theme/zero-day.css` so existing imports and semantic classes stay compatible.

| Role | Value |
| --- | --- |
| Pond paper | `#f6f5e9` |
| Reef paper | `#eef3e8` |
| Notebook | `#fffef6` |
| Primary ink | `#2c4234` |
| Secondary ink | `#55664f` |
| Forest action | `#3e6248` |
| Sage wash | `#dfe7ce` |
| Mint wash | `#dcebe1` |
| Caution | `#886421` |
| High-risk coral | `#a9503c` |
| Borders | `#cbd3ba` |

Headings use the local Iowan Old Style / Palatino / Georgia serif stack. Body copy uses Avenir Next / Segoe UI / sans-serif. Numeric and technical labels use SF Mono / Consolas / monospace. There are no remote font requests or new UI dependencies.

## Surfaces and behaviors

- Paper panels have restrained borders, asymmetric rounded corners, and offset shadows. The conversation outlook resembles a lily pad; the phone keeps its hardware frame and full thread navigation.
- All three scripted conversations, per-message HUDs, Replay/Next, compass, stage chain, safety actions, protected links, ten-second Cool-Down Shield, Leaf Sheep vitality, local scoring, and `/phone?debug=1` parity remain available.
- Conversation detail graphs use only already-revealed forecasts. The turn inspector controls risk, family probabilities, and attention. Scripted fixtures are explicitly distinguished from model evaluation. Attention is influence, not proof of fraud.
- The learning journey advances only on matching job events. A chloroplast is ready only after the downloaded manifest and weights validate. Demo responses never claim training occurred.
- Evaluation has an explicit source switch: the published snapshot is bundled from `ml/artifacts/eval_summary.json`, while the service view uses `/v1/metrics` (or its unavailable contract fixture in mock mode). Every source shows provenance. Test-set selection, model toggles, prefix inspection, lead-time bars, calibration/sample-count views, zero-day bars, and sample-efficiency curves expose the underlying measurements.
- Unavailable overall and zero-day evaluations are gated by `pitchMetrics`. Nulls remain gaps. Human-written evaluation stays empty if unmeasured. The reliability graph is labeled as top-family confidence; it is not presented as risk calibration. The diagonal is an ideal reference, not a measured result.

## Content states

Loading keeps the phone frame and graph surface visible with runtime/loading status. Empty conversations prompt selection; empty metrics and adapters show `--` and explain what is missing. Service errors provide Refresh; local runtime failures explicitly confirm that no text was uploaded and allow retry. Partial evaluations show the available measurements with empty unavailable sections. Successful replay, scoring, and adapter validation have visible status feedback. Sending a pattern is an explicit form submission with a privacy reminder; safety/report actions remain labeled simulations. Cool-down requires a separate reveal action and never opens the address.

## Accessibility and verification

Use text alongside risk colors; a high-confidence benign forecast uses the safe color. Keep 44px interaction targets, visible keyboard focus, labeled native controls, a focus-contained native dialog with Escape and focus return, and reduced-motion styles. Charts have keyboard accessibility, exact numeric readouts, and a scrollable measurement table. Decorative artwork has empty alt text; meaningful characters have descriptions. Never persist or upload typed messages as part of visualization.

Local rendered evidence and the design-skill check record are in ignored `web/.qa/`. The progress log records checks and any remaining upstream limitations.
