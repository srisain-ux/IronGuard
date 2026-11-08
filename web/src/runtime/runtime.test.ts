import assert from "node:assert/strict";
import { test } from "node:test";
import { lockStates } from "./lockon";
import { compileChloroplast, isChloroplastManifest, decodeFloat32, gelu, vitality } from "./chloroplast";
import { roleText, type Turn } from "./embed";
import { confidenceBand, scoreVectors, softmax, type Runner } from "./preynet";
import { compareScores } from "./parity";
import manifestFixture from "../mocks/chloroplast.parking.json";
import type { ChloroplastManifest } from "../contracts/chloroplast";

function encode(values: number[]) {
  const bytes = Buffer.alloc(values.length * 4);
  values.forEach((value, i) => bytes.writeFloatLE(value, 4 * i));
  return bytes.toString("base64");
}
function adapter(): ChloroplastManifest {
  return { ...manifestFixture, feature_dim: 640, hidden_dim: 4, threshold: 0.5, weights: { w1: encode(new Array(4 * 640).fill(0)), b1: encode([0, 0, 0, 0]), w2: encode([0, 0, 0, 0]), b2: encode([0]) } };
}
const turns: Turn[] = [{ sender: "them", text: "wrong number" }, { sender: "me", text: "hello" }, { sender: "them", text: "pay $12" }];
const vectors = turns.map(() => new Float32Array(385));
const temperatures = { family: 2, next_stage: 1, tts: 1 };
const run: Runner = async (_, n) => ({ family_logits: [2 * Math.log(6), 0, 0, 0, 0, 0, 0], stage_logits: [0, 0, 0, 0, 0], tts_logits: [0, 0, 0, 0, 0], features: new Float32Array(640), attention: new Array(n).fill(1 / n) });

test("role prefixes exactly match MiniLM training inputs", () => {
  assert.equal(roleText(turns[0]), "[THEM] wrong number");
  assert.equal(roleText(turns[1]), "[ME] hello");
});
test("lock-on boundaries, interrupted low streak, ME turns and tuned threshold", () => {
  assert.deepEqual(lockStates([.7, .39, .99, .39], ["them", "them", "me", "them"]), [true, true, true, false]);
  assert.deepEqual(lockStates([.7, .39, .4, .39, .39], new Array(5).fill("them")), [true, true, true, true, false]);
  assert.deepEqual(lockStates([.9, .9864, .39, .39], new Array(4).fill("them"), { theta_lock: .9863448143, theta_release: .4, release_turns: 2 }), [false, true, true, false]);
});
test("stable calibrated softmax and confidence boundaries", () => {
  assert.deepEqual(softmax([1000, 1000], 2), [.5, .5]);
  assert.throws(() => softmax([1], 0));
  assert.throws(() => softmax([NaN], 1));
  assert.equal(confidenceBand(.1, .2), "high");
  assert.equal(confidenceBand(.35, .9), "uncertain");
  assert.equal(confidenceBand(.2, .5), "low");
  assert.equal(confidenceBand(.8, .2), "high");
});
test("float32 little endian, finite values, dimensions and base64 validation", () => {
  assert.deepEqual(Array.from(decodeFloat32(encode([1.5, -2.25]), 2)), [1.5, -2.25]);
  assert.throws(() => decodeFloat32("AAAA", 1));
  assert.throws(() => decodeFloat32("!!!!", 1));
  assert.throws(() => decodeFloat32(encode([Infinity]), 1));
  assert.throws(() => compileChloroplast({ ...adapter(), hidden_dim: 129 }));
});
test("GELU agrees with independent PyTorch erf reference values", () => {
  for (const [x, expected] of [[-2, -.04550026389635842], [-1, -.15865525393145707], [0, 0], [1, .8413447460685429], [2, 1.9544997361036416]]) assert.ok(Math.abs(gelu(x) - expected) < 2e-7);
});
test("row-major nonzero adapter, sigmoid and inclusive threshold", () => {
  const cp = adapter();
  const w1 = new Array(4 * 640).fill(0); w1[639] = 2;
  cp.weights.w1 = encode(w1); cp.weights.w2 = encode([1, 0, 0, 0]);
  const f = new Float32Array(640); f[639] = .5;
  const hit = compileChloroplast(cp)(f);
  assert.ok(Math.abs(hit.p - .6987484358773136) < 2e-7);
  assert.equal(hit.fired, true);
  assert.equal(compileChloroplast(adapter())(new Float32Array(640)).fired, true);
});
test("vitality halves at the half-life and never disables a firing adapter", () => {
  const cp = adapter(); const created = Date.parse(cp.created_at);
  assert.equal(vitality(cp, created - 1), 1);
  assert.equal(vitality(cp, created + cp.half_life_hours * 3_600_000), .5);
  assert.ok(vitality(cp, created + cp.half_life_hours * 3_600_000 * 100) < 1e-20);
  assert.equal(compileChloroplast(cp)(new Float32Array(640)).fired, true);
});
test("score response uses calibrated heads, causal prefix runs, evidence and browser runtime", async () => {
  const calls: number[] = [];
  const scores = await scoreVectors(turns, vectors, async (input, n) => { assert.equal(input.length, n * 385); calls.push(n); return run(input, n); }, temperatures);
  assert.deepEqual(calls, [1, 2, 3]);
  const score = scores.at(-1)!;
  assert.ok(Math.abs(score.risk - .5) < 1e-10);
  assert.equal(score.model.runtime, "browser");
  assert.deepEqual(score.next_stage, { stage: "benign", p: .2 });
  assert.deepEqual(score.evidence, [{ turn_idx: 0, reason: "Identity switch or unexpected sender" }, { turn_idx: 2, reason: "Asks for money, crypto or a gift card" }]);
  assert.equal(Object.keys(score.family_probs).length, 7);
});
test("adapter overrides family/risk and locks even below tuned lock threshold; bad adapter contained", async () => {
  const cp = adapter(); cp.weights.b2 = encode([Math.log(4)]);
  const scores = await scoreVectors(turns, vectors, run, { ...temperatures, theta_lock: .99 }, [manifestFixture as ChloroplastManifest, cp]);
  assert.ok(Math.abs(scores[0].risk - .8) < 1e-7);
  assert.equal(scores[0].family.source, "chloroplast");
  assert.equal(scores[0].locked, true);
  assert.equal(scores[0].chloroplast_hits!.length, 1);
});
test("last 12 turns are left-truncated and attention indices stay global", async () => {
  const longTurns = new Array(15).fill(turns[0]);
  const longVectors = longTurns.map((_, i) => { const v = new Float32Array(385); v[0] = i; return v; });
  const scores = await scoreVectors(longTurns, longVectors, async (input, n) => { if (n === 12 && input[0] === 3) assert.equal(input.at(-385), 14); return run(input, n); }, temperatures);
  assert.deepEqual(scores.at(-1)!.attention.slice(0, 3), [0, 0, 0]);
  assert.equal(scores.at(-1)!.attention.length, 15);
});
test("parity rejects missing probabilities, label differences and delta above .02", async () => {
  const score = (await scoreVectors(turns, vectors, run, temperatures)).at(-1)!;
  assert.equal(compareScores(score, structuredClone(score)).passed, true);
  assert.equal(compareScores(score, { ...score, risk: score.risk + .0201 }).passed, false);
  assert.equal(compareScores(score, { ...score, locked: !score.locked }).passed, false);
  const missing = structuredClone(score); delete missing.family_probs.benign;
  assert.equal(compareScores(score, missing).passed, false);
});
test("malformed model tensors fail explicitly", async () => {
  await assert.rejects(scoreVectors(turns, vectors, async (input, n) => ({ ...await run(input, n), features: [0] }), temperatures), /shape mismatch/);
  await assert.rejects(scoreVectors(turns, vectors, async (input, n) => ({ ...await run(input, n), attention: new Array(n).fill(NaN) }), temperatures), /attention/);
  await assert.rejects(scoreVectors(turns, vectors, run, { ...temperatures, theta_lock: NaN }), /parameters/);
});

test("downloaded manifest metadata cannot inject invalid score labels or vitality", () => {
  assert.equal(isChloroplastManifest(adapter()), true);
  assert.equal(isChloroplastManifest({ ...adapter(), family_id: null }), false);
  assert.equal(isChloroplastManifest({ ...adapter(), half_life_hours: Infinity }), false);
  assert.equal(isChloroplastManifest({ ...adapter(), metrics: null }), false);
});
