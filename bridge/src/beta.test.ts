import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { betaTransport } from "./beta.js";
import {
  echoHandler,
  ONLINE,
  type EchoMessage,
  type EchoSpace,
} from "./server.js";
const rid = (kind: string, digit: string) =>
  `pho_${kind}_01${digit.repeat(24)}`;
const projectId = rid("prj", "0");
const secret = `whsec_${Buffer.alloc(32, 7).toString("base64")}`;
const event = () => ({
  id: rid("evt", "1"),
  type: "message.received",
  apiVersion: "2026-07-01",
  data: {
    projectId,
    object: {
      id: rid("msg", "2"),
      projectId,
      platform: "imessage",
      status: "received",
      sentBy: {
        id: rid("usr", "3"),
        projectId,
        platform: "imessage",
        kind: "human",
      },
      receivedBy: {
        id: rid("usr", "4"),
        projectId,
        platform: "imessage",
        kind: "agent",
      },
      space: {
        id: rid("spc", "5"),
        projectId,
        platform: "imessage",
        kind: "direct",
      },
      content: { type: "text", format: "plain", text: "test" },
    },
  },
});
function signed(
  body: string,
  timestamp = String(Math.floor(Date.now() / 1000)),
) {
  const id = rid("evt", "1");
  const mac = createHmac("sha256", Buffer.alloc(32, 7))
    .update(`${id}.${timestamp}.${body}`)
    .digest("base64");
  return {
    body: Buffer.from(body),
    headers: {
      "webhook-id": id,
      "webhook-timestamp": timestamp,
      "webhook-signature": `v1,${mac}`,
    },
  };
}
test("Beta verifies Standard Webhooks bytes, timestamp, rotation signatures and event ID", async () => {
  const transport = betaTransport({
    projectId,
    apiKey: "test-key",
    signingSecret: secret,
  });
  let calls = 0;
  const handler = () => {
    calls++;
  };
  const body = JSON.stringify(event());
  assert.equal((await transport.webhook(signed(body), handler)).status, 204);
  assert.equal(calls, 1);
  const tampered = signed(body);
  tampered.body = Buffer.from(body.replace("test", "changed"));
  assert.equal((await transport.webhook(tampered, handler)).status, 401);
  assert.equal(
    (await transport.webhook(signed(body, "1"), handler)).status,
    401,
  );
  assert.equal(
    (
      await transport.webhook(
        signed(body, String(Math.floor(Date.now() / 1000) + 600)),
        handler,
      )
    ).status,
    401,
  );
  assert.equal(
    (await transport.webhook({ body: Buffer.from(body) }, handler)).status,
    401,
  );
  const rotated = signed(body);
  rotated.headers["webhook-signature"] =
    "v1,aW52YWxpZA== " + rotated.headers["webhook-signature"];
  assert.equal((await transport.webhook(rotated, handler)).status, 204);
  const bad = event();
  bad.id = rid("evt", "9");
  assert.equal(
    (await transport.webhook(signed(JSON.stringify(bad)), handler)).status,
    400,
  );
  assert.equal((await transport.webhook(signed("{"), handler)).status, 400);
  assert.equal(calls, 2);
});
test("Beta refuses cross-project/malformed events and ignores agent, group and other events", async () => {
  const transport = betaTransport({
    projectId,
    apiKey: "test-key",
    signingSecret: secret,
  });
  let calls = 0;
  const check = async (
    change: (e: ReturnType<typeof event>) => void,
    status: number,
  ) => {
    const e = event();
    change(e);
    assert.equal(
      (
        await transport.webhook(signed(JSON.stringify(e)), () => {
          calls++;
        })
      ).status,
      status,
    );
  };
  await check((e) => {
    e.data.projectId = rid("prj", "9");
  }, 400);
  await check((e) => {
    e.data.object.receivedBy.projectId = rid("prj", "9");
  }, 400);
  await check((e) => {
    e.data.object.space.id = "invalid";
  }, 400);
  await check((e) => {
    e.data.object.receivedBy.kind = "human";
  }, 204);
  await check((e) => {
    e.data.object.sentBy.kind = "agent";
  }, 204);
  await check((e) => {
    e.data.object.space.kind = "group";
  }, 204);
  await check((e) => {
    e.type = "message.delivered";
  }, 204);
  await check((e) => {
    e.apiVersion = "2099-01-01";
  }, 400);
  assert.equal(calls, 0);
});
test("Beta reply uses the received agent ID, source space, parent message and stable idempotency", async () => {
  const requests: { url: string; init: RequestInit }[] = [];
  const request = (async (url: string | URL | Request, init: RequestInit) => {
    requests.push({ url: String(url), init });
    return new Response("{}", { status: 202 });
  }) as typeof fetch;
  const transport = betaTransport({
    projectId,
    apiKey: "test-key",
    signingSecret: secret,
    request,
  });
  let queued: { space: EchoSpace; message: EchoMessage } | undefined;
  const inbound = event();
  await transport.webhook(signed(JSON.stringify(inbound)), (space, message) => {
    queued = { space, message };
  });
  assert.equal(requests.length, 0);
  assert(queued);
  const echo = echoHandler();
  await echo(queued.space, queued.message);
  await echo(queued.space, queued.message);
  assert.equal(requests.length, 1);
  const sent = requests[0];
  assert.equal(
    sent.url,
    `https://api.photon.codes/v1/projects/${projectId}/messages`,
  );
  assert.equal(
    (sent.init.headers as Record<string, string>)["Idempotency-Key"],
    `ironguard-echo:${inbound.data.object.id}`,
  );
  assert.deepEqual(JSON.parse(String(sent.init.body)), {
    spaceId: inbound.data.object.space.id,
    senderId: inbound.data.object.receivedBy.id,
    parentMessageId: inbound.data.object.id,
    content: { type: "text", format: "plain", text: ONLINE },
  });
});
test("Beta send errors reach the safe failure callback and permit retry", async () => {
  let failures = 0;
  const echo = echoHandler(() => failures++);
  const request = (async () =>
    new Response("{}", { status: 403 })) as typeof fetch;
  const transport = betaTransport({
    projectId,
    apiKey: "test-key",
    signingSecret: secret,
    request,
  });
  let job: Promise<void> | undefined;
  await transport.webhook(signed(JSON.stringify(event())), (space, message) => {
    job = echo(space, message);
  });
  await job;
  assert.equal(failures, 1);
});
