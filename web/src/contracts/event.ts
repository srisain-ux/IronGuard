/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

/**
 * Server-sent event on GET /v1/events (text/event-stream, one JSON object per `data:` line). Drives the live /reef dashboard.
 */
export interface Event {
  type:
    | "photon.message"
    | "score"
    | "card"
    | "algae.progress"
    | "train.progress"
    | "chloroplast.ready"
    | "reef.report"
    | "error";
  ts: string;
  job_id?: string;
  /**
   * photon.message: {thread_id, sender, preview(<=60 chars, masked)}; score: ScoreResponse; card: SafetyCard; algae.progress: {stage: plan|generate|critique|dedupe, done, total, sample?}; train.progress: {step, total, loss}; chloroplast.ready: ChloroplastManifest without weights; reef.report: {family_guess}; error: {message}
   */
  data: {
    [k: string]: unknown;
  };
}
