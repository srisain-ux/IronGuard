import pig from "./mocks/conversation.pig_butchering.json";
import benign from "./mocks/conversation.benign_hard_negative.json";
import bank from "./mocks/conversation.bank.json";
import pigScores from "./mocks/scores.pig.json";
import bankScores from "./mocks/scores.bank.json";
import benignScores from "./mocks/scores.benign.json";
import bankCard from "./mocks/safety_card.bank.json";
import example from "./mocks/score_response.turn3.json";
export type Score = Omit<typeof example, "model"> & {
  model: {
    name: string;
    version: string;
    runtime?: string;
    latency_ms?: number;
  };
};
type Conversation = {
  turns: { sender: string; text: string; stage: string }[];
  strike_turn: number | null;
};
export type Demo = {
  id: string;
  name: string;
  initials: string;
  subtitle: string;
  scenario: string;
  conversation: Conversation;
  scores: Score[];
};
export const demos: Demo[] = [
  {
    id: "pig",
    name: "Anna",
    initials: "AN",
    subtitle: "Unknown sender · SMS",
    scenario: "Relationship / crypto",
    conversation: pig,
    scores: pigScores,
  },
  {
    id: "bank",
    name: "PNC security?",
    initials: "PN",
    subtitle: "Unverified sender · SMS",
    scenario: "Bank impersonation",
    conversation: bank,
    scores: bankScores,
  },
  {
    id: "benign",
    name: "Wrong number",
    initials: "WN",
    subtitle: "Unknown sender · iMessage",
    scenario: "Benign hard negative",
    conversation: benign,
    scores: benignScores,
  },
];
export function safetyCard(id: string, score: Score) {
  if (id === "bank")
    return {
      ...bankCard,
      confidence: score.risk,
      confidence_band: score.confidence_band,
      checks: score.risk < 0.9 ? [] : bankCard.checks,
      privacy_note: "Scripted demo. No message text left this browser.",
      headline:
        score.risk < 0.9
          ? "Verify this fraud alert in your bank’s app."
          : bankCard.headline,
      why:
        score.risk < 0.9 ? score.evidence.map((e) => e.reason) : bankCard.why,
    };
  const safe = id === "benign";
  return {
    ...bankCard,
    confidence: score.risk,
    confidence_band: score.confidence_band,
    verdict: safe ? "safe" : score.locked ? "likely_scam" : "caution",
    headline: safe
      ? "This looks like a normal wrong-number exchange."
      : score.locked
        ? "A friendly opener is becoming an investment pitch."
        : "Too early to tell. Take your time.",
    why: score.evidence.map((e) => e.reason),
    checks: [],
    entities: { brands: [], phones: [], urls: [] },
    locked_links: [],
    cool_down: false,
    next_steps: safe
      ? [{ id: "safe", label: "Mark as safe", action: "mark_safe" }]
      : [
          {
            id: "official",
            label: "How to verify safely",
            action: "open_official_site",
          },
          {
            id: "explain",
            label: "Explain this forecast",
            action: "learn_more",
          },
          {
            id: "report",
            label: "Block & report options",
            action: "block_report",
          },
        ],
    privacy_note: "Scripted demo. No message text left this browser.",
  };
}
