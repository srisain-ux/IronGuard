import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";
import {
  bridgeServer,
  echoHandler,
  type BridgeStatus,
  type WebhookTransport,
} from "./server.js";
import { betaTransport } from "./beta.js";

const projectId = process.env.PHOTON_PROJECT_ID?.trim();
const projectSecret = process.env.PHOTON_SECRET?.trim();
const webhookSecret = process.env.PHOTON_WEBHOOK_SECRET?.trim();
let status: BridgeStatus =
  !projectId || !projectSecret
    ? "needs_credentials"
    : !webhookSecret
      ? "needs_webhook_secret"
      : "connecting";
let sdk: WebhookTransport | undefined;
const api = projectId?.startsWith("pho_prj_") ? "photon-beta" : "spectrum";
const counts = { received_events: 0, replies_accepted: 0, reply_failures: 0 };
const echo = echoHandler(
  () => {
    counts.reply_failures++;
    console.error(
      "Photon reply failed. Check API key permissions and the project's channel status.",
    );
  },
  () => {
    counts.replies_accepted++;
    console.info("Photon reply accepted for delivery.");
  },
);
const server = bridgeServer({
  status: () => status,
  sdk: () => sdk,
  onMessage: async (space, message) => {
    counts.received_events++;
    await echo(space, message);
  },
  diagnostics: () => ({ api, ...counts }),
});
server.requestTimeout = 10_000;
server.on("error", () => {
  console.error(
    "Bridge could not listen on 8787. Close the other bridge process, then run make bridge again.",
  );
  process.exit(1);
});
server.listen(8787, "127.0.0.1", () => {
  console.info(
    "IronGuard echo bridge: http://localhost:8787 · webhook /webhook · health /health",
  );
  if (status === "needs_credentials")
    console.info(
      "Fill PHOTON_PROJECT_ID and PHOTON_SECRET in bridge/.env, then restart make bridge.",
    );
  if (status === "needs_webhook_secret")
    console.info(
      "Register your tunnel URL + /webhook in Photon, save PHOTON_WEBHOOK_SECRET in bridge/.env, then restart make bridge.",
    );
});
if (status === "connecting") {
  try {
    if (api === "photon-beta") {
      const response = await fetch(
        `https://api.photon.codes/v1/projects/${encodeURIComponent(projectId!)}`,
        {
          headers: { Authorization: `Bearer ${projectSecret}` },
          signal: AbortSignal.timeout(15_000),
        },
      );
      if (!response.ok) throw new Error("Photon credentials rejected.");
      sdk = betaTransport({
        projectId: projectId!,
        apiKey: projectSecret!,
        signingSecret: webhookSecret!,
      });
    } else
      sdk = await Spectrum({
        projectId: projectId!,
        projectSecret: projectSecret!,
        webhookSecret,
        providers: [imessage.config()],
        telemetry: false,
        options: { logLevel: "silent" },
        signal: AbortSignal.timeout(15_000),
      });
    status = "ready";
    console.info(
      "Photon ready. Text the Photon number from your phone. Expected reply: IronGuard online 🛡",
    );
  } catch {
    status = "connection_failed";
    console.error(
      "Photon connection failed. Check project ID, secret, enabled channel and network; restart make bridge.",
    );
  }
}
for (const signal of ["SIGINT", "SIGTERM"] as const)
  process.on(signal, () => {
    server.close();
    if (sdk?.stop) void sdk.stop().finally(() => process.exit(0));
    else process.exit(0);
  });
