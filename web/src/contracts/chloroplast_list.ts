/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */

export type ChloroplastListSchemaJson = ChloroplastManifest[];

/**
 * A tiny adapter head for one zero-day scam family. Downloaded by phones; applied to PreyNet's 640-d `features` output. Weights are base64 float32 little-endian, row-major.
 */
export interface ChloroplastManifest {
  id: string;
  family_id: string;
  label: string;
  /**
   * The one-sentence zero-day alert that seeded the algae.
   */
  alert: string;
  created_at: string;
  /**
   * Display-only vitality decay (kleptoplasts degrade); never disables protection.
   */
  half_life_hours: number;
  feature_dim: 640;
  hidden_dim: number;
  weights: {
    /**
     * base64 float32 [hidden_dim x feature_dim]
     */
    w1: string;
    /**
     * base64 float32 [hidden_dim]
     */
    b1: string;
    /**
     * base64 float32 [1 x hidden_dim]
     */
    w2: string;
    /**
     * base64 float32 [1]
     */
    b2: string;
  };
  threshold: number;
  metrics: {
    n_pos: number;
    n_neg: number;
    train_seconds: number;
    generate_seconds?: number;
    val_auc?: number;
    val_recall_at_1fpr?: number;
  };
  size_bytes: number;
  sha256: string;
}
