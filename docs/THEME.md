# THEME.md: the Zero Day look (owner: C)

The goal: a judge should glance at our screen and think it came out of the HackUTD 2026 opening deck. Tokens are in `web/src/theme/zero-day.css`.

## What the deck actually uses (we pulled these from the PDF)
- **Fonts embedded in the slides:** **Orbitron** (Black/SemiBold) for headings, **Roboto Mono** for code and HUD text, **Inter** for body text. All three are on Google Fonts and already imported in the CSS.
- **Palette:** a deep night sky (`#05030e`), indigo and violet blurred city (`#1b1445`, `#2c214a`, `#4f3288`, `#544ea5`, `#2d419b`), lavender glow (`#b9a2cf`), cream titles (`#f8f3ec`), the neon **"ZERO DAY"** sign in pink (`#e83f8f` / `#f576a1`), the T-Mobile challenge slides' **magenta neon grid floor** (`#e20074`), and teal light panels.
- **Motifs:** a neon sign in a rainy cyberpunk city; a cute hacker robot mascot on a motorbike; blurred building interiors behind frosted title cards; **emoji story strips** (`🚨 ➡ 🕶 ➡ 🚪‼`, `🕵 ➡ 👥 ➡ 👀`); a **CTF / breach** vocabulary; "Grand Prizes *With a Twist*".

## How we use them
| Element | Treatment |
|---|---|
| App frame | Night-city gradient background + `.zd-grid-floor` magenta grid at the bottom + faint `.zd-scanlines` |
| Logo / wordmark | `IRONGUARD` in Orbitron 900 inside a `.zd-neon-sign` box with a slow `.zd-flicker`. A small dragonfly glyph replaces the "O" |
| Cards | `.zd-panel` frosted indigo glass, like the slide title cards |
| HUD numbers | Roboto Mono, uppercase, tracked: `RISK 0.74 · UNCERTAIN · T-2 TURNS TO STRIKE` |
| Kill-chain strip | The deck's emoji-strip style, applied to the scam stages: `🎣 BAIT ➡ 🎭 PIVOT ➡ 🪝 HOOK ➡ 💸 STRIKE`. The current stage glows; predicted stages are outlined in dashes |
| Risk colors | teal (low) → podium yellow (uncertain) → neon pink (high). **Never color by the raw score alone**: always show the band word too (accessibility + honesty) |
| Trajectory Compass | A circular HUD with 6 family directions (`compass_deg` in taxonomy.json); the needle length = risk; tick marks in lavender |
| Leaf sheep | A small leaf-sheep avatar whose cerata are chloroplast badges in `--zd-chloro` green. Each badge has a **vitality bar** that fades with the manifest's half-life |
| Incident headers | `INCIDENT 0x01 // TRAJECTORY LOCKED`, `ZERO-DAY DETECTED // FEEDING THE REEF`, `CHLOROPLAST ABSORBED · 82 KB · 4.8 s` |
| Reef Lab | Terminal panel (`> new zero-day alert: _` with a blinking cursor), streaming log lines prefixed `[algae]`, `[critic]`, `[train]`, `[reef]` |
| Loading states | "Hatching dragonfly…", "Grazing algae…", "Absorbing chloroplast…" |

## Copy voice
Short, confident, breach-movie flavored, but **plain-English** on anything a customer reads. Customer text: "This number isn't PNC's. Don't call it." HUD text: `VERDICT: LIKELY SCAM`.

## Accessibility (never cut)
Contrast ≥ 4.5:1 for body text on panels; no information carried by color alone; respect `prefers-reduced-motion` (the CSS already does); every tap target ≥ 44px; locked links announce "link disabled for your safety" to screen readers.
