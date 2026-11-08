import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { once } from "node:events";
import { Spectrum, text, type Message, type Space } from "spectrum-ts";
import { bridgeServer, echoHandler, ONLINE } from "./server.js";

const secret = "local-test-signing-secret";
const body = JSON.stringify({
  event: "message.received",
  message: {
    id: "message-1",
    platform: "imessage",
    direction: "inbound",
    space: { id: "space-1", platform: "imessage" },
    content: { type: "text", text: "hello" },
  },
});
function signed(
  payload: string,
  timestamp = String(Math.floor(Date.now() / 1000)),
) {
  const digest = createHmac("sha256", secret)
    .update(`v0:${timestamp}:${payload}`)
    .digest("hex");
  return {
    "content-type": "application/json",
    "x-spectrum-signature": `v0=${digest}`,
    "x-spectrum-timestamp": timestamp,
  };
}
test("SDK signature validation: valid, tampered, stale, missing; server bounds bodies", async (t) => {
  const sdk = await Spectrum({
    providers: [],
    webhookSecret: secret,
    telemetry: false,
    options: { logLevel: "silent" },
  });
  const server = bridgeServer({
    status: () => "ready",
    sdk: () => sdk,
    onMessage: echoHandler(),
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(async () => {
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
    await sdk.stop();
  });
  const address = server.address();
  assert(address && typeof address !== "string");
  const url = `http://127.0.0.1:${address.port}`;
  const request = (
    payload: string,
    headers: Record<string, string> = signed(payload),
  ) => fetch(`${url}/webhook`, { method: "POST", headers, body: payload });
  assert.equal((await request(body)).status, 200);
  assert.equal(
    (await request(body.replace("hello", "tampered"), signed(body))).status,
    401,
  );
  assert.equal((await request(body, signed(body, "1"))).status, 401);
  assert.equal((await request(body, {})).status, 401);
  assert.equal((await request("not-json")).status, 400);
  assert.equal((await request("x".repeat(65 * 1024))).status, 413);
  const health = await (await fetch(`${url}/health`)).json();
  assert.deepEqual(health, {
    status: "ready",
    mode: "echo",
    webhook: "/webhook",
  });
  assert.equal((await fetch(`${url}/elsewhere`)).status, 404);
});
test("echo deduplicates inbound deliveries, ignores outbound/emoji, handles unsupported content", async () => {
  const sent: unknown[] = [];
  const space = {
    id: "chat-a",
    send: async (input: ReturnType<typeof text>) => {
      sent.push(await input.build());
    },
  } as unknown as Space;
  const handler = echoHandler();
  const message = {
    id: "1",
    direction: "inbound",
    content: { type: "text", text: "test" },
  } as Message;
  await handler(space, message);
  await handler(space, message);
  assert.deepEqual(sent, [await text(ONLINE).build()]);
  await handler(space, { ...message, id: "2", direction: "outbound" });
  await handler(space, {
    ...message,
    id: "3",
    content: { type: "text", text: " 🛡 " },
  });
  assert.equal(sent.length, 1);
  await handler(space, {
    ...message,
    id: "4",
    content: { type: "image" },
  } as unknown as Message);
  assert.deepEqual(
    sent[1],
    await text("I can only read text right now.").build(),
  );
});
test("failed send permits a retry without leaking raw errors", async () => {
  let tries = 0,
    errors = 0;
  const handler = echoHandler(() => errors++);
  const space = {
    id: "chat-a",
    send: async () => {
      if (++tries === 1) throw new Error("private upstream error");
    },
  } as unknown as Space;
  const message = {
    id: "1",
    direction: "inbound",
    content: { type: "text", text: "test" },
  } as Message;
  await handler(space, message);
  await handler(space, message);
  assert.equal(tries, 2);
  assert.equal(errors, 1);
});
test("missing configuration returns a useful 503 without accepting messages", async (t) => {
  const server = bridgeServer({
    status: () => "needs_webhook_secret",
    sdk: () => undefined,
    onMessage: echoHandler(),
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => {
    server.closeAllConnections();
    server.close();
  });
  const address = server.address();
  assert(address && typeof address !== "string");
  const response = await fetch(`http://127.0.0.1:${address.port}/webhook`, {
    method: "POST",
    body,
  });
  assert.equal(response.status, 503);
});
