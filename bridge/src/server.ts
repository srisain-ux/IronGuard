import { createServer, type IncomingMessage } from "node:http";
import {
  text,
  type WebhookRawRequest,
  type WebhookRawResult,
} from "spectrum-ts";

export type BridgeStatus =
  | "needs_credentials"
  | "needs_webhook_secret"
  | "connecting"
  | "ready"
  | "connection_failed";
export type BridgeMessage = {
  id: string;
  direction: "inbound" | "outbound";
  platform?: string;
  content: { type: string; text?: string };
};
export type BridgeSpace = {
  id: string;
  send(input: ReturnType<typeof text>): Promise<unknown>;
};
export type WebhookTransport = {
  signatureHeaders?: string[];
  webhook(
    request: WebhookRawRequest,
    handler: (space: BridgeSpace, message: BridgeMessage) => void,
  ): Promise<WebhookRawResult>;
  stop?(): Promise<void>;
};

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
  onMessage: (space: BridgeSpace, message: BridgeMessage) => Promise<void>;
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
          mode: "forecast",
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
