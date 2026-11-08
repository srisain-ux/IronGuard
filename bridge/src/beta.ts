import { createHmac, timingSafeEqual } from "node:crypto";
import type { WebhookTransport } from "./server.js";

// Photon Beta (2.0), payload API version 2026-07-01. No message payload is persisted.
const record = (value: unknown): Record<string, unknown> | undefined =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
const validId = (value: unknown, kind: string): value is string =>
  typeof value === "string" &&
  new RegExp(`^pho_${kind}_[0-7][0-9a-hjkmnp-tv-z]{25}$`).test(value);

export function betaTransport(config: {
  projectId: string;
  apiKey: string;
  signingSecret: string;
  request?: typeof fetch;
}): WebhookTransport {
  const encodedKey = config.signingSecret.replace(/^whsec_/, "");
  if (
    !config.signingSecret.startsWith("whsec_") ||
    !/^[A-Za-z0-9+/]+={0,2}$/.test(encodedKey)
  )
    throw new Error("Invalid Photon signing secret.");
  const signingKey = Buffer.from(encodedKey, "base64");
  if (signingKey.length < 16) throw new Error("Invalid Photon signing secret.");
  const request = config.request ?? fetch;
  return {
    signatureHeaders: ["webhook-id", "webhook-timestamp", "webhook-signature"],
    async webhook(input, handler) {
      const result = (status: number) => ({
        status,
        headers: {},
        body: new Uint8Array(),
      });
      const headers = input.headers ?? {};
      const id = headers["webhook-id"],
        timestamp = headers["webhook-timestamp"],
        signatures = headers["webhook-signature"];
      if (!id || !timestamp || !signatures || !/^\d+$/.test(timestamp))
        return result(401);
      const seconds = Number(timestamp);
      if (
        !Number.isSafeInteger(seconds) ||
        Math.abs(Date.now() / 1000 - seconds) > 300
      )
        return result(401);
      const bytes = Buffer.from(
        input.body instanceof ArrayBuffer
          ? new Uint8Array(input.body)
          : input.body,
      );
      const expected = createHmac("sha256", signingKey)
        .update(`${id}.${timestamp}.`)
        .update(bytes)
        .digest();
      const verified = signatures.split(/\s+/).some((signature) => {
        const [version, mac] = signature.split(",");
        if (version !== "v1" || !mac) return false;
        const actual = Buffer.from(mac, "base64");
        return (
          actual.length === expected.length && timingSafeEqual(actual, expected)
        );
      });
      if (!verified) return result(401);
      let event: Record<string, unknown> | undefined;
      try {
        event = record(JSON.parse(bytes.toString("utf8")));
      } catch {
        return result(400);
      }
      if (!event || event.id !== id || typeof event.type !== "string")
        return result(400);
      if (event.type !== "message.received") return result(204);
      const data = record(event.data),
        message = record(data?.object);
      if (
        event.apiVersion !== "2026-07-01" ||
        data?.projectId !== config.projectId ||
        message?.projectId !== config.projectId
      )
        return result(400);
      if (
        !message ||
        message.status !== "received" ||
        !["imessage", "sms"].includes(String(message.platform))
      )
        return result(204);
      const sender = record(message.sentBy),
        agent = record(message.receivedBy),
        space = record(message.space),
        content = record(message.content);
      if (
        !validId(message.id, "msg") ||
        !validId(space?.id, "spc") ||
        !validId(agent?.id, "usr") ||
        !validId(sender?.id, "usr") ||
        space?.projectId !== config.projectId ||
        sender?.projectId !== config.projectId ||
        agent?.projectId !== config.projectId ||
        space?.platform !== message.platform ||
        sender?.platform !== message.platform ||
        agent?.platform !== message.platform ||
        agent?.id === sender?.id ||
        !content ||
        typeof content.type !== "string"
      )
        return result(400);
      if (
        sender?.kind !== "human" ||
        agent?.kind !== "agent" ||
        space?.kind !== "direct"
      )
        return result(204);
      if (
        content.type === "text" &&
        (content.format !== "plain" || typeof content.text !== "string")
      )
        return result(400);
      const messageId = message.id,
        spaceId = space.id,
        senderId = agent.id;
      handler(
        {
          id: spaceId,
          async send(input) {
            const reply = await input.build();
            if (reply.type !== "text")
              throw new Error("Echo supports text replies only.");
            const response = await request(
              `https://api.photon.codes/v1/projects/${encodeURIComponent(config.projectId)}/messages`,
              {
                method: "POST",
                headers: {
                  Authorization: `Bearer ${config.apiKey}`,
                  "Content-Type": "application/json",
                  "Idempotency-Key": `ironguard-forecast:${messageId}`,
                },
                body: JSON.stringify({
                  spaceId,
                  senderId,
                  parentMessageId: messageId,
                  content: { type: "text", format: "plain", text: reply.text },
                }),
                signal: AbortSignal.timeout(15_000),
              },
            );
            if (!response.ok)
              throw new Error(`Photon send failed (${response.status}).`);
          },
        },
        {
          id: messageId,
          direction: "inbound",
          platform: message.platform as "sms" | "imessage",
          content:
            content.type === "text"
              ? { type: "text", text: content.text as string }
              : { type: "unsupported" },
        },
      );
      return result(204);
    },
  };
}
