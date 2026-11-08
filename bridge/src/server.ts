import { createServer, type IncomingMessage } from "node:http";
import { createHash } from "node:crypto";
import {
  text,
  type WebhookRawRequest,
  type WebhookRawResult,
} from "spectrum-ts";

export const ONLINE = "IronGuard online 🛡";
export type BridgeStatus =
  | "needs_credentials"
  | "needs_webhook_secret"
  | "connecting"
  | "ready"
  | "connection_failed";
export type EchoMessage = {
  id: string;
  direction: "inbound" | "outbound";
  content: { type: string; text?: string };
};
export type EchoSpace = {
  id: string;
  send(input: ReturnType<typeof text>): Promise<unknown>;
};
export type WebhookTransport = {
  signatureHeaders?: string[];
  webhook(
    request: WebhookRawRequest,
    handler: (space: EchoSpace, message: EchoMessage) => void,
  ): Promise<WebhookRawResult>;
  stop?(): Promise<void>;
};

// Hashes only, in memory, bounded and expired after 30 minutes. No thread text is retained.
export function echoHandler(
  sendFailed: () => void = () => {},
  replyAccepted: () => void = () => {},
  onAccepted: (message: EchoMessage) => void = () => {},
) {
  const seen = new Map<string, number>();
  return async (space: EchoSpace, message: EchoMessage) => {
    if (message.direction !== "inbound") return;
    const content = message.content;
    if (
      content.type === "text" &&
      (typeof content.text !== "string" || !/[\p{L}\p{N}]/u.test(content.text))
    )
      return;
    const now = Date.now();
    for (const [key, at] of seen) if (now - at > 30 * 60_000) seen.delete(key);
    const digest = createHash("sha256")
      .update(`${space.id}:${message.id}`)
      .digest("hex");
    if (seen.has(digest)) return;
    if (seen.size >= 1000) seen.delete(seen.keys().next().value!);
    seen.set(digest, now);
    try { onAccepted(message); } catch { /* The optional feed cannot interrupt replies. */ }
    try {
      await space.send(
        text(
          content.type === "text" ? ONLINE : "I can only read text right now.",
        ),
      );
      replyAccepted();
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
  sdk: () => WebhookTransport | undefined;
  onMessage: ReturnType<typeof echoHandler>;
  diagnostics?: () => Record<string, string | number>;
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
          ...state.diagnostics?.(),
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
    const requiredHeaders = Array.isArray(sdk.signatureHeaders)
      ? sdk.signatureHeaders
      : ["x-spectrum-signature", "x-spectrum-timestamp"];
    if (requiredHeaders.some((name) => !request.headers[name])) {
      response.writeHead(401).end("Signed Photon webhook required.");
      return;
    }
    try {
      const body = await readBody(request);
      const headers: Record<string, string> = {};
      for (const [name, value] of Object.entries(request.headers))
        if (typeof value === "string") headers[name] = value;
      // Each transport verifies its own signature format over the exact bytes.
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
