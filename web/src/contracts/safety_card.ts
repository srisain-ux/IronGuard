/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

/**
 * Output of the Nemotron Safeguard Agent (POST /v1/agent/safety-card). Rendered as a card in /phone and as a text reply in Photon.
 */
export interface SafetyCard {
  verdict: "safe" | "caution" | "likely_scam";
  /**
   * Copied from ScoreResponse.risk; the agent may NOT invent or inflate it.
   */
  confidence: number;
  confidence_band?: "low" | "uncertain" | "high";
  headline: string;
  /**
   * @maxItems 4
   */
  why: string[];
  entities: {
    brands: string[];
    phones: string[];
    urls: string[];
  };
  checks: {
    tool: "lookup_official_contact" | "check_domain" | "check_number" | "scrub_and_report";
    input: string;
    /**
     * true = matches official / looks safe; false = mismatch / risky.
     */
    ok: boolean;
    summary: string;
    data?: {
      [k: string]: unknown;
    };
  }[];
  /**
   * @minItems 1
   * @maxItems 4
   */
  next_steps: {
    id: string;
    label: string;
    /**
     * Photon: what the user texts back to pick this.
     */
    reply_code?: string;
    action: "call_official" | "open_official_site" | "block_report" | "mark_safe" | "cool_down" | "learn_more";
    payload?: {
      [k: string]: unknown;
    };
  }[];
  /**
   * URLs / numbers the UI must render non-clickable.
   */
  locked_links?: string[];
  /**
   * Show the Cool-Down Shield (high-urgency language detected).
   */
  cool_down?: boolean;
  /**
   * Exactly what left the device for this card.
   */
  privacy_note: string;
}
