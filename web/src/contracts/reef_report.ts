/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

/**
 * An anonymous, consented scam pattern sent to the reef (POST /v1/reef/report). Must already be scrubbed: no names, numbers, URLs, emails, amounts tied to a person.
 */
export interface ReefReport {
  consent: true;
  channel: "sms" | "imessage" | "rcs" | "whatsapp" | "email" | "other";
  family_guess: string;
  /**
   * @maxItems 20
   */
  stage_sequence: ("benign" | "bait" | "pivot" | "hook" | "strike")[];
  /**
   * Scrubbed with placeholders like [PHONE], [URL], [NAME], [AMOUNT], [BRAND].
   */
  template_text: string;
  source?: "photon" | "web";
}
