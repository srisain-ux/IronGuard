/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

/**
 * PreyNet forecast for a conversation prefix. Produced by ironguard_ml.infer (Python) and by the browser runtime (JS); both must emit this exact shape.
 */
export interface ScoreResponse {
  /**
   * Calibrated P(conversation is on a scam trajectory) = 1 - P(benign).
   */
  risk: number;
  confidence_band: "low" | "uncertain" | "high";
  family: {
    id: string;
    label: string;
    p: number;
    source?: "base" | "chloroplast";
  };
  family_probs: {
    [k: string]: number;
  };
  next_stage: {
    stage: "benign" | "bait" | "pivot" | "hook" | "strike";
    p: number;
  };
  turns_to_strike: {
    bucket: "0" | "1" | "2" | "3+" | "none";
    p: number;
  };
  /**
   * CSTMD1-style lock-on (hysteresis) state after this turn.
   */
  locked: boolean;
  /**
   * One weight per turn seen; sums to ~1.
   */
  attention: number[];
  /**
   * @maxItems 3
   */
  evidence: {
    turn_idx: number;
    reason: string;
  }[];
  chloroplast_hits?: {
    id: string;
    p: number;
    fired: boolean;
  }[];
  model: {
    name: "preynet" | "stub";
    version: string;
    runtime?: "python" | "browser";
    latency_ms?: number;
  };
}
