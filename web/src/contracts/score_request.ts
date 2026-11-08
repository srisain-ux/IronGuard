/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

/**
 * POST /v1/score body. The browser normally scores ON DEVICE and never sends this; only the Photon bridge (opt-in forward mode) and dev tools call the API.
 */
export interface ScoreRequest {
  /**
   * Photon space.id or a local thread id.
   */
  thread_id?: string;
  /**
   * @minItems 1
   * @maxItems 20
   */
  turns: {
    sender: "them" | "me";
    text: string;
  }[];
  /**
   * Which chloroplasts to apply; omitted = all active.
   */
  chloroplast_ids?: string[];
}
