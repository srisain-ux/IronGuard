import { test } from "node:test";
import assert from "node:assert/strict";
import { text } from "spectrum-ts";
import { photonFlow } from "./flow.js";
import type { BridgeMessage, BridgeSpace } from "./server.js";

const lowScore = { risk: 0.05, confidence_band: "low", family: { id: "benign", label: "Not a scam" }, next_stage: { stage: "benign" }, turns_to_strike: { bucket: "none" }, evidence: [] };

const incoming = (id: string, value: string, spaceId = "space-a"): { space: BridgeSpace; message: BridgeMessage; replies: string[] } => {
  const replies: string[] = [];
  return {
    space: { id: spaceId, send: async (input: ReturnType<typeof text>) => {
      const built = await input.build();
      assert.equal(built.type, "text");
      replies.push(built.text);
    } },
    message: { id, direction: "inbound", platform: "imessage", content: { type: "text", text: value } },
    replies,
  };
};

test("mock mode formats the contract reply, splits turns, and routes codes without API calls", async () => {
  let calls = 0;
  const flow = photonFlow({ mock: true, request: (async () => { calls++; throw new Error("network used"); }) as typeof fetch });
  const forward = incoming("1", "I think you have the wrong number\nOh sorry, Anna here");
  await flow(forward.space, forward.message);
  assert.equal(forward.replies[0], [
    "🛡 IronGuard · UNCERTAIN confidence",
    "This number is not PNC's. Don't call it.",
    "Trajectory: Relationship / crypto (pig butchering) · hook next · ~2 turns to strike",
    "Why: Claims to be PNC fraud team but uses an unlisted number",
    "Not sure yet. Forward the next message and we'll update the forecast.",
    "Reply 1 = block & report anonymously · 2 = Call PNC's official number · 3 = why?",
    "(Forward mode: this thread was analyzed in the cloud because you sent it to us.)",
  ].join("\n"));
  await flow(forward.space, forward.message);
  assert.equal(forward.replies.length, 1);
  for (const code of ["2", "3", "1"] as const) {
    await flow(forward.space, { ...forward.message, id: `code-${code}`, content: { type: "text", text: code } });
    if (code !== "1") await flow(forward.space, { ...forward.message, id: `new-${code}`, content: { type: "text", text: `new turn ${code}` } });
  }
  assert.match(forward.replies[1], /No verified official number/);
  assert.match(forward.replies[3], /Why:/);
  assert.match(forward.replies[5], /Mock report simulated/);
  await flow(forward.space, { ...forward.message, id: "code-1", content: { type: "text", text: "1" } });
  assert.equal(forward.replies.length, 6);
  await flow(forward.space, { ...forward.message, id: "another", content: { type: "text", text: "another forward" } });
  await flow(forward.space, { ...forward.message, id: "repeat-code", content: { type: "text", text: "1" } });
  assert.match(forward.replies[7], /Mock report simulated/);
  assert.equal(calls, 0);
});

test("real mode posts bounded turns, score then card, masked event, and consented report", async () => {
  const calls: { path: string; body: any }[] = [];
  const score = { risk: 0.8, confidence_band: "high", family: { id: "bank_impersonation", label: "Bank impersonation" }, next_stage: { stage: "hook" }, turns_to_strike: { bucket: "2" }, evidence: [] };
  const card = { headline: "Pause and verify.", why: ["Urgent request"], entities: { brands: [], phones: [], urls: [] }, checks: [], next_steps: [{ reply_code: "2", label: "official number" }] };
  const request = (async (url: string | URL | Request, init: RequestInit) => {
    const path = new URL(String(url)).pathname;
    calls.push({ path, body: JSON.parse(String(init.body)) });
    return Response.json(path === "/v1/score" ? score : path === "/v1/agent/safety-card" ? card : { accepted: true }, { status: path === "/v1/reef/report" || path === "/v1/events/publish" ? 202 : 200 });
  }) as typeof fetch;
  const flow = photonFlow({ request });
  const forward = incoming("1", "PNC fraud team: call +1-888-555-0199\nVisit https://bad.example/pay");
  await flow(forward.space, forward.message);
  assert.deepEqual(calls.map((call) => call.path), ["/v1/score", "/v1/agent/safety-card", "/v1/events/publish"]);
  assert.equal(calls[0].body.turns.length, 2);
  assert.equal(calls[0].body.turns[0].sender, "them");
  assert.equal(calls[1].body.source, "photon");
  assert.deepEqual(calls[1].body.entities.urls, ["https://bad.example/pay"]);
  assert(!JSON.stringify(calls[2].body).includes("PNC fraud team"));
  assert.equal(calls[2].body.data.preview.length <= 60, true);
  await flow(forward.space, { ...forward.message, id: "2", content: { type: "text", text: "1" } });
  assert.equal(calls[3].path, "/v1/reef/report");
  assert.equal(calls[3].body.consent, true);
  assert(!JSON.stringify(calls[3].body).includes("555-0199"));
  assert.match(forward.replies[1], /Anonymous pattern reported/);
});

test("low risk, API down, unsupported and emoji content, and idle expiration", async () => {
  let time = 0;
  const bodies: any[] = [];
  let fail = false;
  const request = (async (url: string | URL | Request, init: RequestInit) => {
    const path = new URL(String(url)).pathname;
    if (fail && path === "/v1/score") throw new Error("secret response");
    if (path === "/v1/score") bodies.push(JSON.parse(String(init.body)));
    return Response.json(path === "/v1/score" ? lowScore : { accepted: true });
  }) as typeof fetch;
  const flow = photonFlow({ request, now: () => time });
  const forward = incoming("1", "hello");
  await flow(forward.space, { ...forward.message, content: { type: "text", text: "🛡" } });
  assert.equal(forward.replies.length, 0);
  await flow(forward.space, { ...forward.message, id: "image", content: { type: "image" } });
  assert.equal(forward.replies[0], "I can only read text right now.");
  await flow(forward.space, forward.message);
  assert.match(forward.replies[1], /No clear scam trajectory/);
  fail = true;
  await flow(forward.space, { ...forward.message, id: "2", content: { type: "text", text: "second" } });
  assert.match(forward.replies[2], /Can't check right now/);
  fail = false;
  time = 30 * 60_000;
  await flow(forward.space, { ...forward.message, id: "3", content: { type: "text", text: "fresh" } });
  assert.deepEqual(bodies.map((body) => body.turns.length), [1, 1]);
});

test("same-space forwards serialize, cap at 20 turns, and retry after an API outage", async () => {
  const sizes: number[] = [];
  let fail = false;
  const request = (async (url: string | URL | Request, init: RequestInit) => {
    if (new URL(String(url)).pathname === "/v1/score") {
      if (fail) throw new Error("upstream message must stay private");
      sizes.push(JSON.parse(String(init.body)).turns.length);
      await new Promise((resolve) => setTimeout(resolve, 2));
      return Response.json(lowScore);
    }
    return Response.json({ accepted: true });
  }) as typeof fetch;
  const flow = photonFlow({ request });
  const forward = incoming("1", Array.from({ length: 15 }, (_, i) => `line ${i}`).join("\n"));
  await Promise.all([
    flow(forward.space, forward.message),
    flow(forward.space, { ...forward.message, id: "2", content: { type: "text", text: Array.from({ length: 10 }, (_, i) => `next ${i}`).join("\n") } }),
  ]);
  assert.deepEqual(sizes, [15, 20]);
  fail = true;
  const retry = { ...forward.message, id: "3", content: { type: "text", text: "retry me" } };
  await flow(forward.space, retry);
  assert.match(forward.replies[2], /Can't check right now/);
  fail = false;
  await flow(forward.space, retry);
  assert.equal(sizes.at(-1), 20);
  assert.equal(forward.replies.length, 4);
});

test("failed Photon send can retry without resubmitting a consented report", async () => {
  let sends = 0, failures = 0, reports = 0;
  const score = { risk: 0.8, confidence_band: "high", family: { id: "bank_impersonation", label: "Bank impersonation" }, next_stage: { stage: "hook" }, turns_to_strike: { bucket: "2" }, evidence: [] };
  const card = { headline: "Pause.", why: ["Urgency"], checks: [], next_steps: [] };
  const request = (async (url: string | URL | Request) => {
    const path = new URL(String(url)).pathname;
    if (path === "/v1/reef/report") reports++;
    return Response.json(path === "/v1/score" ? score : path === "/v1/agent/safety-card" ? card : { accepted: true });
  }) as typeof fetch;
  const flow = photonFlow({ request, sendFailed: () => failures++ });
  const space: BridgeSpace = { id: "send-retry", send: async () => { if (++sends === 2) throw new Error("private Photon error"); } };
  await flow(space, { id: "forward", direction: "inbound", content: { type: "text", text: "fraud team" } });
  const code: BridgeMessage = { id: "report", direction: "inbound", content: { type: "text", text: "1" } };
  await flow(space, code);
  assert.equal(failures, 1);
  await flow(space, code);
  assert.equal(reports, 1);
  assert.equal(sends, 3);
});
