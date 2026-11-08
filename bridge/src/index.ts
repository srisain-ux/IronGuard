import { Spectrum, type SpectrumInstance } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";
import { bridgeServer, echoHandler, type BridgeStatus } from "./server.js";

const projectId = process.env.PHOTON_PROJECT_ID?.trim();
const projectSecret = process.env.PHOTON_SECRET?.trim();
const webhookSecret = process.env.PHOTON_WEBHOOK_SECRET?.trim();
let status: BridgeStatus =
  !projectId || !projectSecret
    ? "needs_credentials"
    : !webhookSecret
      ? "needs_webhook_secret"
      : "connecting";
let sdk: SpectrumInstance | undefined;
const server = bridgeServer({
  status: () => status,
  sdk: () => sdk,
  onMessage: echoHandler(() =>
    console.error(
      "Photon reply failed. Check project/channel status in the dashboard, then send a fresh test text.",
    ),
  ),
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
    void sdk?.stop().finally(() => process.exit(0));
    if (!sdk) process.exit(0);
  });
