import type { ScoreResponse } from "../contracts/score_response";
import type { SafetyCard } from "../contracts/safety_card";
import scoreMock from "../mocks/score_response.turn3.json";
import cardMock from "../mocks/safety_card.bank.json";

const useMocks = import.meta.env.VITE_USE_MOCKS === "1";
const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getExampleScore(): Promise<ScoreResponse> {
  if (useMocks) return scoreMock as unknown as ScoreResponse;
  throw new Error("Browser scoring needs the on-device model runtime.");
}

export async function getExampleSafetyCard(): Promise<SafetyCard> {
  if (useMocks) return cardMock as unknown as SafetyCard;
  throw new Error("A live Safety Card needs a local score and verified checks.");
}

export interface EvalSummary {
  models?: Record<string, { ewr_at_k?: number[]; lead_time?: number }>;
  reliability?: { bins?: number[]; acc?: number[]; conf?: number[] };
}

export async function getMetrics(): Promise<EvalSummary | null> {
  if (useMocks) return null;
  const response = await fetch(`${apiUrl}/v1/metrics`);
  if (!response.ok) throw new Error(`Metrics unavailable (${response.status})`);
  return response.json() as Promise<EvalSummary>;
}
