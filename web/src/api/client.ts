import type { ScoreResponse } from "../contracts/score_response";
import type { SafetyCard } from "../contracts/safety_card";
import type { Event } from "../contracts/event";
import type { ZeroDayResponseSchemaJson } from "../contracts/zero_day_response";
import scoreMock from "../mocks/score_response.turn3.json";
import cardMock from "../mocks/safety_card.bank.json";
import metricsMock from "../mocks/metrics.unavailable.json";
import eventMock from "../mocks/event.train_progress.json";
import chloroplastMock from "../mocks/chloroplast_list.demo.json";
import zeroDayMock from "../mocks/zero_day_response.demo.json";
import exampleThread from "../mocks/conversation.pig_butchering.json";
import { isChloroplastManifest } from "../runtime/chloroplast";
import type { ChloroplastManifest } from "../contracts/chloroplast";

export const useMocks = import.meta.env.VITE_USE_MOCKS !== "0";
const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getExampleScore(): Promise<ScoreResponse> {
  if (useMocks) return scoreMock as unknown as ScoreResponse;
  throw new Error("Browser scoring needs the on-device model runtime.");
}

export async function getExampleSafetyCard(): Promise<SafetyCard> {
  if (useMocks) return cardMock as unknown as SafetyCard;
  throw new Error("A live Safety Card needs a local score and verified checks.");
}

export interface EvaluationRates {
  ewr_at_k?: (number | null)[];
  lead_time?: number | null;
  strike_recall?: number | null;
  fpr?: number | null;
  hard_neg_fpr?: number | null;
}

export interface EvaluationModel extends EvaluationRates {
  ece_before?: number | null;
  ece_after?: number | null;
  ece_risk_before?: number | null;
  ece_risk_after?: number | null;
  flicker_rate?: number | null;
  flicker_rate_no_lock?: number | null;
  lead_time_std?: number | null;
  abstains?: boolean;
  test_human?: EvaluationRates;
}

export interface EvalSummary {
  available?: boolean;
  generated_at?: string;
  dataset?: { version?: string; n_conversations?: number; n_test?: number; n_test_human?: number; notes?: string[]; split_denominators?: Record<string, { scam?: number; benign?: number; hard_negative?: number }> };
  models?: Record<string, EvaluationModel>;
  zero_day?: { available?: boolean; family?: string; base_ewr_at_3?: number | null; chloroplast_ewr_at_3?: number | null; sample_efficiency?: { n: number; ewr_at_3: number | null }[]; time_to_protection_s?: number | null; notes?: string[] } | null;
  reliability?: { bins?: number[]; acc?: (number | null)[]; conf?: (number | null)[]; count?: (number | null)[] };
}

export async function getMetrics(): Promise<EvalSummary | null> {
  if (useMocks) return metricsMock as EvalSummary;
  const response = await fetch(`${apiUrl}/v1/metrics`);
  if (!response.ok) throw new Error(`Metrics unavailable (${response.status})`);
  return response.json() as Promise<EvalSummary>;
}

export function openEvents(onEvent: (event: Event) => void, onConnection: (connected: boolean) => void): EventSource | null {
  if (useMocks) {
    // Contract fixture demonstrates parsing without claiming that a live job ran.
    onEvent(eventMock as Event);
    return null;
  }
  const source = new EventSource(`${apiUrl}/v1/events`);
  source.onopen = () => onConnection(true);
  source.onerror = event => { if (!(event instanceof MessageEvent)) onConnection(false); };
  const handle = (message: MessageEvent<string>) => {
    try {
      const event: Event = JSON.parse(message.data);
      if (event && typeof event.type === "string" && event.data && typeof event.data === "object") onEvent(event);
    } catch { /* Ignore malformed event data. */ }
  };
  for (const type of ["photon.message", "algae.progress", "train.progress", "chloroplast.ready", "reef.report", "error"]) source.addEventListener(type, handle as EventListener);
  return source;
}

export async function submitZeroDay(alert: string): Promise<ZeroDayResponseSchemaJson> {
  if (useMocks) return zeroDayMock as ZeroDayResponseSchemaJson;
  const response = await fetch(`${apiUrl}/v1/zero-day`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ alert }) });
  if (!response.ok) throw new Error(`Zero-day alert failed (${response.status})`);
  return response.json() as Promise<ZeroDayResponseSchemaJson>;
}

// GET-only: no conversation text can enter a manifest request.
export async function getChloroplasts(): Promise<ChloroplastManifest[]> {
  if (useMocks) return chloroplastMock as ChloroplastManifest[];
  const response = await fetch(`${apiUrl}/v1/chloroplasts`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Adapters unavailable (${response.status})`);
  const manifests: unknown = await response.json();
  if (!Array.isArray(manifests)) throw new Error("Invalid adapter list");
  return manifests.filter(isChloroplastManifest);
}

// Developer-only comparison: fixed public fixture; never accepts customer input.
export async function scoreExampleWithApi(): Promise<ScoreResponse> {
  if (useMocks) return structuredClone(scoreMock) as ScoreResponse;
  const response = await fetch(`${apiUrl}/v1/score`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ turns: exampleThread.turns.map(({ sender, text }) => ({ sender, text })), chloroplast_ids: [] }),
  });
  if (!response.ok) throw new Error(`Example comparison failed (${response.status})`);
  return response.json() as Promise<ScoreResponse>;
}
