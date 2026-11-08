import { createServer, type IncomingMessage } from "node:http";
import { createHash } from "node:crypto";
import {
  text,
  type Message,
  type Space,
  type SpectrumInstance,
} from "spectrum-ts";

export const ONLINE = "IronGuard online 🛡";
export type BridgeStatus =
  | "needs_credentials"
  | "needs_webhook_secret"
  | "connecting"
  | "ready"
  | "connection_failed";
type EchoMessage = Pick<Message, "id" | "direction" | "content">;
type EchoSpace = Pick<Space, "id" | "send">;

// Hashes only, in memory, bounded and expired after 30 minutes. No thread text is retained.
export function echoHandler(sendFailed: () => void = () => {}) {
  const seen = new Map<string, number>();
  return async (space: EchoSpace, message: EchoMessage) => {
    if (message.direction !== "inbound") return;
    const content = message.content;
    if (content.type === "text" && !/[\p{L}\p{N}]/u.test(content.text)) return;
    const now = Date.now();
    for (const [key, at] of seen) if (now - at > 30 * 60_000) seen.delete(key);
    const digest = createHash("sha256")
      .update(`${space.id}:${message.id}`)
      .digest("hex");
    if (seen.has(digest)) return;
    if (seen.size >= 1000) seen.delete(seen.keys().next().value!);
    seen.set(digest, now);
    try {
      await space.send(
        text(
          content.type === "text" ? ONLINE : "I can only read text right now.",
        ),
      );
    } catch {
      seen.delete(digest);
      sendFailed();
    }
  };
}

async function readBody(request: IncomingMessage) {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 64 * 1024) throw new Error("body_limit");
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

export function bridgeServer(state: {
  status: () => BridgeStatus;
  sdk: () => Pick<SpectrumInstance, "webhook"> | undefined;
  onMessage: ReturnType<typeof echoHandler>;
}) {
  return createServer(async (request, response) => {
    if (
      request.method === "GET" &&
      (request.url === "/health" || request.url === "/")
    ) {
      response.writeHead(200, {
        "content-type": "application/json",
        "cache-control": "no-store",
      });
      response.end(
        JSON.stringify({
          status: state.status(),
          mode: "echo",
          webhook: "/webhook",
        }),
      );
      return;
    }
    if (
      request.method !== "POST" ||
      !["/", "/webhook"].includes(request.url ?? "")
    ) {
      response.writeHead(404).end();
      return;
    }
    const sdk = state.sdk();
    if (!sdk) {
      response
        .writeHead(503)
        .end(
          "Bridge not ready. Check /health and bridge/.env, then restart make bridge.",
        );
      return;
    }
    if (
      !request.headers["x-spectrum-signature"] ||
      !request.headers["x-spectrum-timestamp"]
    ) {
      response.writeHead(401).end("Signed Photon webhook required.");
      return;
    }
    try {
      const body = await readBody(request);
      const headers: Record<string, string> = {};
      for (const [name, value] of Object.entries(request.headers))
        if (typeof value === "string") headers[name] = value;
      // Native Photon/Spectrum JSON only. SDK checks HMAC + freshness using exact request bytes.
      let payload: unknown;
      try {
        payload = JSON.parse(body.toString("utf8"));
      } catch {
        response.writeHead(400).end("JSON webhook required.");
        return;
      }
      if (
        !payload ||
        typeof payload !== "object" ||
        !("message" in payload) ||
        !("event" in payload)
      ) {
        response.writeHead(400).end("Native Photon webhook required.");
        return;
      }
      const result = await sdk.webhook({ body, headers }, (space, message) => {
        // Queue after acknowledgment. Sender and text never enter application logs.
        setImmediate(() => {
          void state.onMessage(space, message);
        });
      });
      response.writeHead(result.status, result.headers).end(result.body);
    } catch (error) {
      response
        .writeHead(
          error instanceof Error && error.message === "body_limit" ? 413 : 400,
        )
        .end("Webhook rejected.");
    }
  });
}
