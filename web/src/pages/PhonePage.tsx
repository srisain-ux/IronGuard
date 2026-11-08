import { useEffect, useState } from "react";
import { getExampleScore } from "../api/client";
import type { ScoreResponse } from "../contracts/score_response";
import conversation from "../mocks/conversation.pig_butchering.json";

const stageNames = ["🎣 BAIT", "🎭 PIVOT", "🪝 HOOK", "💸 STRIKE"];

export default function PhonePage() {
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void getExampleScore()
      .then(setScore)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Forecast unavailable"));
  }, []);

  const risk = score ? Math.round(score.risk * 100) : null;
  return (
    <div className="page-content phone-layout">
      <section className="hero-copy">
        <p className="eyebrow">INCIDENT 0x01 // EARLY WARNING SYSTEM</p>
        <h1 className="zd-title">SEE THE STRIKE <em>BEFORE</em> IT HITS.</h1>
        <p className="intro">A conversation can look harmless right up to the link or money ask. Dragonfly tracks where it is heading, turn by turn.</p>
        <div className="kill-chain" aria-label="Scam trajectory stages">{stageNames.map((stage, index) => <span key={stage} className={index === 1 ? "current-stage" : ""}>{stage}</span>)}</div>
        <div className="feature-list">
          <div><strong>01 / FORECAST</strong><span>Family, next stage, and turns until the ask.</span></div>
          <div><strong>02 / CONFIDENCE</strong><span>Clear uncertainty when evidence is thin.</span></div>
          <div><strong>03 / PRIVACY</strong><span>Message text stays on this device in browser mode.</span></div>
        </div>
      </section>

      <section className="phone-frame" aria-label="Phone forecast demo">
        <div className="phone-notch" aria-hidden="true" />
        <div className="phone-top"><span>9:41</span><span>▮▮▮ ◉ ▰</span></div>
        <div className="thread-head"><div className="avatar">?</div><div><strong>UNKNOWN SENDER</strong><small>SMS · thread preview</small></div><span className="thread-more">•••</span></div>
        <div className="thread-body">
          {conversation.turns.slice(0, 3).map((turn, index) => <div className={`bubble ${turn.sender === "me" ? "bubble-me" : "bubble-them"}`} key={index}>{turn.text}</div>)}
        </div>
        <div className="forecast-card zd-panel">
          <div className="card-top"><span>DRAGONFLY // TRAJECTORY</span><span className="live-dot">● LIVE</span></div>
          {score ? <>
            <div className="risk-row"><div><small>FORECAST RISK</small><strong>{risk}%</strong></div><span className="band">{score.confidence_band.toUpperCase()}</span></div>
            <div className="risk-track"><div style={{ width: `${risk}%` }} /></div>
            <p className="trajectory"><strong>{score.family.label}</strong><br />{score.next_stage.stage.toUpperCase()} NEXT · {score.turns_to_strike.bucket === "none" ? "STRIKE UNKNOWN" : `T-${score.turns_to_strike.bucket} TURNS TO STRIKE`}</p>
            <p className="explanation">{score.confidence_band === "uncertain" ? "We're not sure yet. The next message may make the trajectory clearer." : score.evidence[0]?.reason || "Watching this trajectory."}</p>
          </> : <p role="status">{error || "Hatching dragonfly…"}</p>}
        </div>
        <div className="composer" aria-label="Message composer preview">Message <span>＋</span></div>
      </section>
    </div>
  );
}
