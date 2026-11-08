import type { EvalSummary } from "./client";

export function pitchMetrics(metrics: EvalSummary | null): EvalSummary | null {
  if (!metrics || metrics.available === false) return null;
  if (metrics.zero_day?.available === false) return { ...metrics, zero_day: null };
  return metrics;
}
