import { useMocks } from "../api/client";
import fixture from "../mocks/score_response.turn3.json";
import type { ScoreResponse } from "../contracts/score_response";
import type { ChloroplastManifest } from "../contracts/chloroplast";
import type { Turn } from "./embed";

export async function scoreLocal(turns: Turn[], manifests: ChloroplastManifest[] = [], onStatus?: (status: string) => void): Promise<ScoreResponse[]> {
  if (useMocks) return turns.map(() => ({ ...structuredClone(fixture) as ScoreResponse, model: { name: "stub", version: "contract-fixture", runtime: "browser" } }));
  const { scoreBrowser } = await import("./preynet");
  return scoreBrowser(turns, manifests, onStatus);
}
