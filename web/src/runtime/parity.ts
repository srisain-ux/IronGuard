import type { ScoreResponse } from "../contracts/score_response";
export function compareScores(browser: ScoreResponse, api: ScoreResponse) {
  const rows = [
    { field: "risk", browser: browser.risk, api: api.risk },
    ...Array.from(new Set([...Object.keys(browser.family_probs), ...Object.keys(api.family_probs)])).map(id => ({ field: id, browser: browser.family_probs[id], api: api.family_probs[id] })),
    { field: "next_stage.p", browser: browser.next_stage.p, api: api.next_stage.p },
    { field: "turns_to_strike.p", browser: browser.turns_to_strike.p, api: api.turns_to_strike.p },
    ...Array.from({ length: Math.max(browser.attention.length, api.attention.length) }, (_, i) => ({ field: `attention[${i}]`, browser: browser.attention[i], api: api.attention[i] })),
  ].map(row => ({ ...row, delta: Math.abs(row.browser - row.api) }));
  const labelsMatch = browser.family.id === api.family.id && browser.confidence_band === api.confidence_band && browser.next_stage.stage === api.next_stage.stage && browser.turns_to_strike.bucket === api.turns_to_strike.bucket && browser.locked === api.locked;
  return { rows, labelsMatch, passed: labelsMatch && rows.every(row => Number.isFinite(row.delta) && row.delta <= 0.02) };
}
