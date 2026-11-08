import { createHmac, timingSafeEqual } from "node:crypto";
import { existsSync } from "node:fs";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { loadEnvFile } from "node:process";
import { Spectrum, text } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";

if (existsSync(".env")) loadEnvFile(".env");

const port = 8787;
const signingSecret = process.env.PHOTON_WEBHOOK_SECRET;
const projectId = process.env.PHOTON_PROJECT_ID;
const projectSecret = process.env.PHOTON_SECRET;

type PhotonPayload = {
  message?: { sender?: { id?: string }; content?: { type?: string; text?: string } };
};

const sender = projectId && projectSecret
  ? Spectrum({ projectId, projectSecret, providers: [imessage.config()] })
    .then((app) => imessage(app))
    .catch((error: unknown) => {
      console.error("Photon SDK initialization failed", error instanceof Error ? error.message : "unknown error");
      return null;
    })
  : null;

function verify(body: string, request: IncomingMessage): boolean {
  if (!signingSecret) return false;
  const event = request.headers["x-spectrum-event"];
  const timestamp = request.headers["x-spectrum-timestamp"];
  const signature = request.headers["x-spectrum-signature"];
  if (typeof event !== "string" || typeof timestamp !== "string" || typeof signature !== "string") return false;
  const age = Math.abs(Math.floor(Date.now() / 1000) - Number(timestamp));
  if (!Number.isFinite(age) || age > 300) return false;
  const expected = `v0=${createHmac("sha256", signingSecret).update(`v0:${timestamp}:${body}`).digest("hex")}`;
  const left = Buffer.from(expected);
  const right = Buffer.from(signature);
  return left.length === right.length && timingSafeEqual(left, right);
}

async function readBody(request: IncomingMessage): Promise<string> {
  let body = "";
  for await (const chunk of request) {
    body += chunk.toString();
    if (body.length > 64_000) throw new Error("payload too large");
  }
  return body;
}

function reply(response: ServerResponse, status: number, body: string): void {
  response.writeHead(status, { "content-type": "text/plain; charset=utf-8" });
  response.end(body);
}

createServer(async (request, response) => {
  if (request.method === "GET" && request.url === "/health") return reply(response, 200, "ok");
  if (request.method !== "POST" || request.url !== "/spectrum-webhook") return reply(response, 404, "not found");
  let rawBody: string;
  try { rawBody = await readBody(request); }
  catch { return reply(response, 413, "payload too large"); }
  if (!signingSecret) return reply(response, 503, "webhook secret missing");
  if (!verify(rawBody, request)) return reply(response, 401, "invalid signature");
  let payload: PhotonPayload;
  try { payload = JSON.parse(rawBody) as PhotonPayload; }
  catch { return reply(response, 400, "invalid JSON"); }
  const event = request.headers["x-spectrum-event"];
  const address = payload.message?.sender?.id;
  const message = payload.message?.content;
  reply(response, 200, "ok");
  if (event !== "messages" || !address || message?.type !== "text" || !message.text?.trim() || !sender) return;
  void sender.then(async (sdk) => {
    if (!sdk) return;
    const space = await sdk.space.create(address);
    await space.send(text("OdonataGuard online 🛡"));
  }).catch((error: unknown) => {
    console.error("Photon reply failed", error instanceof Error ? error.message : "unknown error");
  });
}).listen(port, () => {
  console.info(`OdonataGuard bridge listening on ${port}`);
  if (!signingSecret || !sender) console.info("Photon credentials missing; signed webhook replies are unavailable.");
});
