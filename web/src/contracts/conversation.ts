/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

/**
 * One synthetic or hand-written multi-turn conversation. One JSON object per line in data/** /*.jsonl.
 */
export interface Conversation {
  id: string;
  family: string;
  channel: "sms" | "imessage" | "rcs" | "whatsapp" | "email" | "other";
  /**
   * Benign conversation written to look like a scam opening.
   */
  hard_negative?: boolean;
  /**
   * @minItems 1
   * @maxItems 20
   */
  turns: {
    sender: "them" | "me";
    text: string;
    stage: "benign" | "bait" | "pivot" | "hook" | "strike";
  }[];
  /**
   * 0-based index of the first strike turn; null for benign.
   */
  strike_turn: number | null;
  split?: "train" | "val" | "test" | "test_human";
  source: {
    generator: "nemotron" | "human" | "other_llm";
    model?: string;
    prompt_id?: string;
    seed?: number;
    critic_realism?: number;
    zero_day_alert?: string;
  };
}
