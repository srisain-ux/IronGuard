import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { once } from "node:events";
import { Spectrum } from "spectrum-ts";
import { bridgeServer } from "./server.js";

const secret = "local-test-signing-secret";
const body = JSON.stringify({
  event: "message.received",
  message: {
    id: "message-1", platform: "imessage", direction: "inbound",
    space: { id: "space-1", platform: "imessage" },
    content: { type: "text", text: "hello" },
  },
});
function signed(payload: string, timestamp = String(Math.floor(Date.now() / 1000))) {
  const digest = createHmac("sha256", secret).update(`v0:${timestamp}:${payload}`).digest("hex");
  return { "content-type": "application/json", "x-spectrum-signature": `v0=${digest}`, "x-spectrum-timestamp": timestamp };
}

test("SDK signature validation, prompt acknowledgment and body bounds", async (t) => {
  const sdk = await Spectrum({ providers: [], webhookSecret: secret, telemetry: false, options: { logLevel: "silent" } });
  let finish!: () => void;
  const work = new Promise<void>((resolve) => { finish = resolve; });
  const server = bridgeServer({ status: () => "ready", sdk: () => sdk, onMessage: async () => work });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(async () => {
    finish(); server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
    await sdk.stop();
  });
  const address = server.address();
  assert(address && typeof address !== "string");
  const url = `http://127.0.0.1:${address.port}`;
  const send = (payload: string, headers: Record<string, string> = signed(payload)) =>
    fetch(`${url}/webhook`, { method: "POST", headers, body: payload });
  assert.equal((await send(body)).status, 200);
  assert.equal((await send(body.replace("hello", "tampered"), signed(body))).status, 401);
  assert.equal((await send(body, signed(body, "1"))).status, 401);
  assert.equal((await send(body, {})).status, 401);
  assert.equal((await send("not-json")).status, 400);
  assert.equal((await send("x".repeat(65 * 1024))).status, 413);
  assert.deepEqual(await (await fetch(`${url}/health`)).json(), { status: "ready", mode: "forecast", webhook: "/webhook" });
  assert.equal((await fetch(`${url}/elsewhere`)).status, 404);
});
test("missing configuration returns 503 without accepting messages", async (t) => {
  const server = bridgeServer({ status: () => "needs_webhook_secret", sdk: () => undefined, onMessage: async () => {} });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => { server.closeAllConnections(); server.close(); });
  const address = server.address();
  assert(address && typeof address !== "string");
  const response = await fetch(`http://127.0.0.1:${address.port}/webhook`, { method: "POST", body });
  assert.equal(response.status, 503);
});
