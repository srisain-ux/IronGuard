import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { text } from "spectrum-ts";
import type { BridgeMessage, BridgeSpace } from "./server.js";

type Turn = { sender: "them" | "me"; text: string };
type Score = {
  risk: number;
  confidence_band: "low" | "uncertain" | "high";
  family: { id: string; label: string };
  next_stage: { stage: string };
  turns_to_strike: { bucket: string };
  evidence: { reason: string }[];
};
type Card = {
  headline: string;
  why: string[];
  entities: { brands: string[]; phones: string[]; urls: string[] };
  checks: { tool: string; ok: boolean; data?: { official_phone?: string } }[];
  next_steps: { reply_code?: string; label: string }[];
};
type State = { turns: Turn[]; seen: Map<string, number>; pending?: { score: Score; card: Card; reported?: boolean }; last: number; expiry?: NodeJS.Timeout };
const IDLE = 30 * 60_000;
const DOWN = "Can't check right now. Don't click links or send money until you verify with the company's official app.";
const maskedPreview = (value: string) => `[TEXT MASKED · ${value.length} chars]`.slice(0, 60);
const hash = (value: string) => createHash("sha256").update(value).digest("hex");

export function photonFlow(config: {
  apiUrl?: string;
  mock?: boolean;
  request?: typeof fetch;
  now?: () => number;
  sendFailed?: () => void;
  replyAccepted?: () => void;
}) {
  const states = new Map<string, State>();
  const queues = new Map<string, Promise<void>>();
  const request = config.request ?? fetch;
  const now = config.now ?? Date.now;
  const base = (config.apiUrl ?? "http://localhost:8000").replace(/\/+$/, "");
  async function post(path: string, body: unknown): Promise<unknown> {
    const response = await request(`${base}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error("API request failed");
    return response.json();
  }
  async function fixture(name: string): Promise<unknown> {
    return JSON.parse(await readFile(new URL(`../../contracts/examples/${name}`, import.meta.url), "utf8"));
  }
  async function publish(spaceId: string, value: string) {
    if (config.mock) return;
    try {
      await post("/v1/events/publish", {
        type: "photon.message", ts: new Date(now()).toISOString(),
        data: { thread_id: spaceId, sender: "them", preview: maskedPreview(value) },
      });
    } catch { /* Event stream is optional; a failed publish must not block a reply. */ }
  }
  async function send(space: BridgeSpace, value: string) {
    await space.send(text(value));
    config.replyAccepted?.();
  }
  async function process(space: BridgeSpace, message: BridgeMessage) {
    if (message.direction !== "inbound") return;
    const content = message.content;
    if (content.type === "text" && (typeof content.text !== "string" || !/[\p{L}\p{N}]/u.test(content.text))) return;
    const time = now();
    for (const [id, state] of states) if (time - state.last >= IDLE) { clearTimeout(state.expiry); states.delete(id); }
    let state = states.get(space.id);
    if (!state) {
      if (states.size >= 1000) {
        const oldest = states.keys().next().value!;
        clearTimeout(states.get(oldest)?.expiry);
        states.delete(oldest);
      }
      state = { turns: [], seen: new Map(), last: time };
      states.set(space.id, state);
    }
    state.last = time;
    clearTimeout(state.expiry);
    const current = state;
    state.expiry = setTimeout(() => { if (states.get(space.id) === current && now() - current.last >= IDLE) states.delete(space.id); }, IDLE).unref();
    const body = content.type === "text" ? content.text!.trim() : "[NON-TEXT]";
    const replyCode = /^[123]$/.test(body) && !!state.pending;
    const messageKey = hash(`${space.id}\0id\0${message.id}`);
    const bodyKey = content.type === "text" && !replyCode ? hash(`${space.id}\0body\0${body}`) : undefined;
    if (state.seen.has(messageKey) || (bodyKey && state.seen.has(bodyKey))) return;
    while (state.seen.size >= 200) state.seen.delete(state.seen.keys().next().value!);
    state.seen.set(messageKey, time);
    if (bodyKey) state.seen.set(bodyKey, time);
    const previousTurns = state.turns;
    try {
      if (content.type !== "text") {
        await send(space, "I can only read text right now.");
        return;
      }
      const code = body.match(/^[123]$/)?.[0];
      if (code && state.pending) {
        const { score, card } = state.pending;
        if (code === "1") {
          const report = {
            consent: true, channel: message.platform === "sms" || message.platform === "imessage" ? message.platform : "other", family_guess: score.family.id,
            stage_sequence: [score.next_stage.stage],
            template_text: "Forwarded text pattern withheld; see family and stage metadata.", source: "photon",
          };
          if (!config.mock && !state.pending.reported) {
            try { await post("/v1/reef/report", report); }
            catch { await send(space, "Report unavailable right now. You can block this sender on your phone."); return; }
            state.pending.reported = true;
          }
          await send(space, config.mock
            ? "Mock report simulated. Block this sender in your phone's Messages app; IronGuard cannot block numbers for you."
            : "Anonymous pattern reported. Block this sender in your phone's Messages app; IronGuard cannot block numbers for you.");
        } else if (code === "2") {
          const official = card.checks.find((check) => check.tool === "lookup_official_contact" && check.ok)?.data?.official_phone;
          await send(space, official && /^\+?[\d ()-]{7,20}$/.test(official)
            ? `Official contact from the curated demo directory: ${official}. Caller ID can be spoofed; verify in the company's official app.`
            : "No verified official number is available. Open the company's official app or type its known website yourself; don't use a number from the forwarded text.");
        } else {
          await send(space, `Why: ${card.why.join("; ") || score.evidence[0]?.reason || "No specific evidence available yet."}`);
        }
        state.pending = undefined;
        return;
      }
      const lines = body.split(/\r?\n/).map((line) => line.trim()).filter((line) => /[\p{L}\p{N}]/u.test(line));
      state.turns = [...state.turns, ...lines.map((line) => ({ sender: "them" as const, text: line.slice(0, 1000) }))].slice(-20);
      // A single forward is opt-in cloud mode. Only this process retains the thread.
      let score: Score;
      let card: Card | undefined;
      try {
        score = (config.mock ? await fixture("score_response.turn3.json") : await post("/v1/score", { thread_id: space.id, turns: state.turns })) as Score;
        if (!score || !Number.isFinite(score.risk) || !["low", "uncertain", "high"].includes(score.confidence_band) ||
          typeof score.family?.label !== "string" || typeof score.family?.id !== "string" ||
          typeof score.next_stage?.stage !== "string" || typeof score.turns_to_strike?.bucket !== "string" ||
          !Array.isArray(score.evidence)) throw new Error("Invalid score response");
        if (score.risk >= 0.35) {
          const allText = state.turns.map((turn) => turn.text).join("\n").slice(0, 20_000);
          const entities = {
            brands: [],
            phones: [...new Set(allText.match(/(?<!\w)\+?\d[\d ().-]{5,}\d(?!\w)/g) ?? [])],
            urls: [...new Set(allText.match(/(?:https?:\/\/|www\.)[^\s<>]+/gi) ?? [])],
          };
          card = (config.mock ? await fixture("safety_card.bank.json") : await post("/v1/agent/safety-card", { score, entities, source: "photon", text: allText })) as Card;
          if (!card || typeof card.headline !== "string" || !Array.isArray(card.why) ||
            !Array.isArray(card.checks) || !Array.isArray(card.next_steps)) throw new Error("Invalid safety card");
        }
      } catch {
        state.seen.delete(messageKey);
        if (bodyKey) state.seen.delete(bodyKey);
        state.turns = previousTurns;
        await send(space, DOWN);
        return;
      }
      if (!card) {
        state.pending = undefined;
        await send(space, "🛡 IronGuard · No clear scam trajectory yet. Forward the next message if you're concerned.\n(Forward mode: this thread was analyzed in the cloud because you sent it to us.)");
        await publish(space.id, body);
        return;
      }
      const officialLabel = card.next_steps.find((step) => step.reply_code === "2")?.label ?? "official contact";
      const reply = [
        `🛡 IronGuard · ${score.confidence_band.toUpperCase()} confidence`,
        card.headline,
        `Trajectory: ${score.family.label} · ${score.next_stage.stage} next · ~${score.turns_to_strike.bucket} turns to strike`,
        `Why: ${card.why[0] ?? score.evidence[0]?.reason ?? "No specific evidence available yet."}`,
        `Reply 1 = block & report anonymously · 2 = ${officialLabel} · 3 = why?`,
        "(Forward mode: this thread was analyzed in the cloud because you sent it to us.)",
      ];
      if (score.confidence_band === "uncertain") reply.splice(4, 0, "Not sure yet. Forward the next message and we'll update the forecast.");
      await send(space, reply.join("\n"));
      state.pending = { score, card };
      await publish(space.id, body);
    } catch {
      state.seen.delete(messageKey);
      if (bodyKey) state.seen.delete(bodyKey);
      state.turns = previousTurns;
      config.sendFailed?.();
    }
  }
  return (space: BridgeSpace, message: BridgeMessage): Promise<void> => {
    const prior = queues.get(space.id) ?? Promise.resolve();
    const job = prior.then(() => process(space, message));
    queues.set(space.id, job);
    void job.finally(() => { if (queues.get(space.id) === job) queues.delete(space.id); });
    return job;
  };
}
