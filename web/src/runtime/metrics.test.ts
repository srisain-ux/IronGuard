import assert from "node:assert/strict";
import { test } from "node:test";
import { pitchMetrics } from "../api/metrics";

test("unavailable evaluation never exposes numeric pitch evidence", () => {
  assert.equal(pitchMetrics({ available: false, models: { PreyNet: { ewr_at_k: [0.9] } }, zero_day: { base_ewr_at_3: 0.4, chloroplast_ewr_at_3: 0.8 } }), null);
  assert.equal(pitchMetrics(null), null);
});

test("unavailable zero-day evaluation hides all its evidence but retains measured base metrics", () => {
  const metrics = { available: true, models: { PreyNet: { ewr_at_k: [0.9] } }, zero_day: { available: false, base_ewr_at_3: 0.4, chloroplast_ewr_at_3: 0.8, sample_efficiency: [{ n: 32, ewr_at_3: 0.8 }], time_to_protection_s: 2 } };
  assert.deepEqual(pitchMetrics(metrics), { ...metrics, zero_day: null });
  assert.equal(metrics.zero_day.available, false);
});

test("available and legacy measured evaluation remains visible", () => {
  for (const available of [true, undefined]) {
    const metrics = { available, models: {}, zero_day: { base_ewr_at_3: 0.4, chloroplast_ewr_at_3: 0.8 } };
    assert.equal(pitchMetrics(metrics), metrics);
  }
});
