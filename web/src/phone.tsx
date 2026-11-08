import { Fragment as ReactFragment, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Compass } from "./compass";
import { demos, safetyCard, type Score } from "./demo";
import { getChloroplasts, openEvents, useMocks } from "./api/client";
import { scoreLocal } from "./runtime/browser";
import { LeafSheep } from "./components/LeafSheep";
import { DebugParity, LocalMessage } from "./components/RuntimeTools";
import type { ChloroplastManifest } from "./contracts/chloroplast";

const stages = [
  { id: "bait", label: "🎣 BAIT" },
  { id: "pivot", label: "🎭 PIVOT" },
  { id: "hook", label: "🪝 HOOK" },
  { id: "strike", label: "💸 STRIKE" },
];
const urlPattern =
  /(https?:\/\/[^\s]+|(?:[a-z0-9-]+\.)+(?:example)(?:\/[^\s]*)?|\+1-888-555-0199)/gi;
function tts(score: Score) {
  return score.turns_to_strike.bucket === "none"
    ? "NO STRIKE FORECAST"
    : score.turns_to_strike.bucket === "0"
      ? "STRIKE NEXT TURN"
      : `T-${score.turns_to_strike.bucket} TURNS TO STRIKE`;
}
function Risk({ score, compact = false }: { score: Score; compact?: boolean }) {
  return (
    <div
      className={`risk risk-${score.confidence_band} ${compact ? "compact" : ""}`}
    >
      <div className="risk-label">
        <span className="zd-hud">RISK {score.risk.toFixed(2)}</span>
        <strong>{score.confidence_band.toUpperCase()}</strong>
      </div>
      <meter
        min="0"
        max="1"
        value={score.risk}
        aria-label={`Scam trajectory risk ${score.risk.toFixed(2)}, confidence ${score.confidence_band}`}
      />
      <div className="forecast">
        <span>{tts(score)}</span>
        {score.locked ? (
          <span className="lock zd-pulse">▣ LOCKED</span>
        ) : (
          <span className="observing">OBSERVING</span>
        )}
      </div>
    </div>
  );
}
function CoolDown({ target, close }: { target: string; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef(document.activeElement as HTMLElement | null);
  const [seconds, setSeconds] = useState(10);
  const [revealed, setRevealed] = useState(false);
  useEffect(() => {
    const modal = dialog.current;
    modal?.showModal();
    const end = Date.now() + 10_000;
    const timer = window.setInterval(
      () => setSeconds(Math.max(0, Math.ceil((end - Date.now()) / 1000))),
      200,
    );
    return () => {
      clearInterval(timer);
      modal?.close();
      trigger.current?.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="shield zd-panel"
      aria-labelledby="shield-title"
      onCancel={close}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const buttons = Array.from(
          event.currentTarget.querySelectorAll<HTMLButtonElement>(
            "button:not(:disabled)",
          ),
        );
        const index = buttons.indexOf(
          document.activeElement as HTMLButtonElement,
        );
        if (event.shiftKey && index <= 0) {
          event.preventDefault();
          buttons.at(-1)?.focus();
        } else if (
          !event.shiftKey &&
          (index < 0 || index === buttons.length - 1)
        ) {
          event.preventDefault();
          buttons[0]?.focus();
        }
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="shield-icon" aria-hidden="true">
        ◈
      </div>
      <p className="eyebrow">COOL-DOWN SHIELD</p>
      <h2 id="shield-title">A little space to think.</h2>
      <p>
        Urgency is part of the trap. Breathe in slowly. Breathe out. You can
        verify this through the company’s app instead.
      </p>
      <div className="breath" aria-hidden="true">
        {seconds || "✓"}
      </div>
      <p role="timer" aria-live="polite">
        {seconds
          ? `${seconds} seconds before you can reveal the address`
          : "You can reveal the address when you are ready."}
      </p>
      {revealed && (
        <p className="revealed">
          <code>{target}</code>
          <br />
          <small>Address only. This demo never opens suspicious links.</small>
        </p>
      )}
      <button
        className="primary"
        disabled={seconds > 0 || revealed}
        onClick={() => setRevealed(true)}
      >
        {revealed ? "Address revealed" : "Reveal address"}
      </button>
      <button onClick={close}>Keep me protected</button>
    </dialog>
  );
}
export function Phone() {
  const [selected, setSelected] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({
    pig: 1,
    bank: 1,
    benign: 1,
  });
  const [target, setTarget] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const scroll = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const demo = demos.find((d) => d.id === selected);
  const count = demo ? counts[demo.id] : 1;
  const [manifests, setManifests] = useState<ChloroplastManifest[]>([]);
  const [adapterStatus, setAdapterStatus] = useState("");
  const [runtimeStatus, setRuntimeStatus] = useState("");
  const [liveScores, setLiveScores] = useState<{ id: string; scores: Score[] } | null>(null);
  const scores = useMocks ? demo?.scores : liveScores?.id === demo?.id ? liveScores?.scores : undefined;
  const score = scores?.[count - 1];
  const debug = new URLSearchParams(window.location.search).get("debug") === "1";
  useEffect(() => {
    let active = true;
    const refresh = () => void getChloroplasts().then(value => { if (active) { setManifests(value); setAdapterStatus(""); } }).catch(() => { if (active) setAdapterStatus("Adapter refresh unavailable; existing adapters retained."); });
    refresh();
    const stream = openEvents(event => { if (event.type === "chloroplast.ready") refresh(); }, () => {});
    const poll = window.setInterval(refresh, 60_000);
    return () => { active = false; stream?.close(); clearInterval(poll); };
  }, []);
  useEffect(() => {
    let active = true;
    setLiveScores(null);
    if (!demo || useMocks) return;
    setRuntimeStatus("Hatching dragonfly…");
    void scoreLocal(demo.conversation.turns.slice(0, count), manifests, status => { if (active) setRuntimeStatus(status); })
      .then(result => { if (active) { setLiveScores({ id: demo.id, scores: result }); setRuntimeStatus("ON-DEVICE FORECAST"); } })
      .catch(() => { if (active) setRuntimeStatus("Browser model unavailable. Install A’s exported artifacts and retry. No text was uploaded."); });
    return () => { active = false; };
  }, [demo, count, manifests]);
  const prime = score
    ? score.attention.indexOf(Math.max(...score.attention))
    : -1;
  useEffect(() => {
    heading.current?.focus();
  }, [selected]);
  useEffect(() => {
    scroll.current?.scrollTo({
      top: scroll.current.scrollHeight,
      behavior: "instant",
    });
  }, [selected, count]);
  function choose(id: string) {
    setSelected(id);
    setNotice("");
  }
  function message(text: string) {
    return text.split(urlPattern).map((part, i) =>
      i % 2 ? (
        <span key={i} className="protected-address">
          <span
            className="zd-locked-link"
            role="link"
            aria-disabled="true"
            aria-label={`${part}, link disabled for your safety`}
          >
            {part}
          </span>
          <button
            className="review-link"
            onClick={() => setTarget(part)}
            aria-label={`Review locked address ${part}`}
          >
            Review safely ↗
          </button>
        </span>
      ) : (
        part
      ),
    );
  }
  const card = demo && score ? safetyCard(demo.id, score) : null;
  function action(kind: string) {
    if (kind === "learn_more")
      setNotice(
        score?.evidence.map((e) => e.reason).join(". ") ||
          "Wait for more context.",
      );
    else if (kind === "mark_safe")
      setNotice(
        "Marked safe for this demo. You can still review every forecast.",
      );
    else if (kind === "block_report")
      setNotice(
        "Demo: no sender was blocked and no report was sent. On your phone, use Messages → sender → Block / Report Junk.",
      );
    else
      setNotice(
        "Open the company’s app yourself, or use the number printed on your bank card. Never use the number in this message.",
      );
  }

  return (
    <main className="app-shell zd-scanlines">
      <div className="zd-grid-floor" aria-hidden="true" />
      <a className="skip" href="#phone-content">
        Skip to phone
      </a>
      <header className="site-header">
        <a
          href="/phone"
          className="wordmark zd-neon-sign"
          aria-label="IronGuard home"
        >
          IR
          <svg className="dragonfly" viewBox="0 0 28 28" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="1.6">
              <ellipse cx="8" cy="9" rx="7" ry="3" transform="rotate(28 8 9)" />
              <ellipse
                cx="20"
                cy="9"
                rx="7"
                ry="3"
                transform="rotate(-28 20 9)"
              />
              <ellipse
                cx="8"
                cy="17"
                rx="7"
                ry="3"
                transform="rotate(-28 8 17)"
              />
              <ellipse
                cx="20"
                cy="17"
                rx="7"
                ry="3"
                transform="rotate(28 20 17)"
              />
              <path d="M14 5v21" />
            </g>
            <circle cx="14" cy="4" r="2" fill="currentColor" />
          </svg>
          NGUARD
          <span className="brand-dot" />
        </a>
        <Link className="reef-nav" to="/reef">
          REEF LAB
        </Link>
        <span className="header-status">
          <i /> {useMocks ? "LOCAL DEMO" : "ON-DEVICE"} <span className="divider">/</span> ZERO DAY 2026
        </span>
      </header>
      <div className="workspace">
        <aside className="intro">
          <p className="eyebrow">
            <span className="tiny-line" /> THE LEAF SHEEP PROTOCOL
          </p>
          <h1>
            See the setup.
            <br />
            Stop the <em>strike.</em>
          </h1>
          <p className="intro-copy">
            A scam starts long before the link.
            <br />
            Follow the conversation. Watch its trajectory change.
          </p>
          <div className="demo-selector">
            <p className="zd-hud">
              CHOOSE AN INCIDENT <span>↓</span>
            </p>
            {demos.map((d, i) => (
              <button
                key={d.id}
                className={`scenario ${selected === d.id ? "selected" : ""}`}
                onClick={() => choose(d.id)}
                aria-pressed={selected === d.id}
              >
                <span className="scenario-no">0{i + 1}</span>
                <span>
                  <strong>{d.scenario}</strong>
                  <small>
                    {d.id === "benign"
                      ? "Same opening. A different ending."
                      : d.id === "pig"
                        ? "A wrong number becomes an opportunity."
                        : "A fraud alert becomes a code request."}
                  </small>
                </span>
                <span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
          <div className="privacy">
            <span aria-hidden="true">⌁</span>
            <div>
              <strong>Your messages stay yours.</strong>
              <p>
                These scripts run entirely in your browser. No text is uploaded.
                No customer data trains a model.
              </p>
            </div>
          </div>
          <LocalMessage manifests={manifests} />
          {debug && <DebugParity />}
        </aside>
        <section className="phone-wrap" aria-label="IronGuard phone demo">
          <div className="phone-hardware">
            <div className="phone-status" aria-hidden="true">
              <span>9:41</span>
              <div className="island" />
              <span>▮▮▮ ▰</span>
            </div>
            <div className="phone-content" id="phone-content">
              <div className="phone-top">
                <span className="zd-hud">IRONGUARD / MESSAGES</span>
                <span className="local-pill">◉ LOCAL</span>
              </div>
              {!demo ? (
                <>
                  <div className="list-heading">
                    <p className="eyebrow">YOUR PERIMETER</p>
                    <h2 ref={heading} tabIndex={-1}>
                      Conversations
                    </h2>
                    <p>Three stories. Follow one message at a time.</p>
                  </div>
                  <div className="thread-list">
                    {demos.map((d) => (
                      <button
                        key={d.id}
                        onClick={() => choose(d.id)}
                        className="thread"
                      >
                        <span className={`avatar avatar-${d.id}`}>
                          {d.initials}
                        </span>
                        <span>
                          <strong>{d.name}</strong>
                          <small>{d.conversation.turns[0].text}</small>
                          <span className="thread-tag">{d.scenario}</span>
                        </span>
                        <span aria-hidden="true">›</span>
                      </button>
                    ))}
                  </div>
                  <div className="list-footer">
                    <span aria-hidden="true">◈</span>
                    <p>
                      Protection starts with context.
                      <br />
                      <small>Select a conversation to begin.</small>
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="thread-header">
                    <button
                      className="back"
                      aria-label="Back to conversations"
                      onClick={() => {
                        setSelected(null);
                        setNotice("");
                      }}
                    >
                      ‹
                    </button>
                    <span className={`avatar avatar-${demo.id}`}>
                      {demo.initials}
                    </span>
                    <div>
                      <h2 ref={heading} tabIndex={-1}>
                        {demo.name}
                      </h2>
                      <p>{demo.subtitle}</p>
                    </div>
                    <span aria-label="Protected conversation">◈</span>
                  </div>
                  <div
                    className="messages"
                    ref={scroll}
                    role="region"
                    aria-label="Conversation messages"
                    tabIndex={0}
                  >
                    <p className="date-label">SCRIPTED CONVERSATION · TODAY</p>
                    {demo.conversation.turns.slice(0, count).map((turn, i) => (
                      <article
                        key={i}
                        className={`turn ${turn.sender === "me" ? "outgoing" : "incoming"} ${score?.locked && i === prime ? "primed" : ""}`}
                        aria-label={`Message ${i + 1}, ${turn.sender === "me" ? "you" : demo.name}`}
                      >
                        <div className="bubble">{message(turn.text)}</div>
                        {score?.locked && i === prime && (
                          <p className="prime-label">
                            ↳ this message primed the lock
                          </p>
                        )}
                        {turn.sender === "them" && scores?.[i] && (
                          <div className="message-hud">
                            <Risk score={scores[i]} compact />
                            <details>
                              <summary>Trajectory at this message</summary>
                              <p>{scores[i].family.label}</p>
                              <p>
                                NEXT:{" "}
                                {scores[i].next_stage.stage.toUpperCase()}
                              </p>
                            </details>
                          </div>
                        )}
                      </article>
                    ))}
                  </div>
                  <div className="demo-controls">
                    <div>
                      <span className="zd-hud">
                        TURN {count.toString().padStart(2, "0")} /{" "}
                        {demo.conversation.turns.length
                          .toString()
                          .padStart(2, "0")}
                      </span>
                      <button
                        className="reset"
                        onClick={() => {
                          setCounts((c) => ({ ...c, [demo.id]: 1 }));
                          setNotice("");
                        }}
                      >
                        Replay ↺
                      </button>
                    </div>
                    <button
                      className="primary"
                      disabled={count === demo.conversation.turns.length}
                      onClick={() =>
                        setCounts((c) => ({ ...c, [demo.id]: c[demo.id] + 1 }))
                      }
                    >
                      {count === demo.conversation.turns.length
                        ? "End of conversation"
                        : "Next message"}{" "}
                      <span aria-hidden="true">→</span>
                    </button>
                    <span className="sr-only" role="status">
                      {demo.name}, showing {count} messages.{" "}
                      {score?.confidence_band} confidence. {score && tts(score)}
                      .
                    </span>
                  </div>
                </>
              )}
              <div className="mock-footer" role="status">
                {useMocks ? "SCRIPTED MOCKS · NO NETWORK INFERENCE" : runtimeStatus || "ON-DEVICE RUNTIME"}
              </div>
            </div>
            <div className="home-indicator" aria-hidden="true" />
          </div>
          <p className="phone-caption">
            A LITTLE CONTEXT. A LOT OF PROTECTION.
          </p>
        </section>
        <aside className="analysis" aria-label="Trajectory analysis">
          <div className="analysis-heading">
            <p className="eyebrow">LIVE TRAJECTORY</p>
            <span className="zd-hud">
              {demo
                ? `INCIDENT 0x0${demos.indexOf(demo) + 1}`
                : "AWAITING INCIDENT"}
            </span>
          </div>
          {score && demo ? (
            <>
              <section className="zd-panel trajectory">
                <div className="panel-heading">
                  <h2>Trajectory HUD</h2>
                  <span className="signal-icon" aria-hidden="true">
                    ⌁
                  </span>
                </div>
                <Risk score={score} />
                <p className="confidence-copy">
                  {score.confidence_band === "uncertain"
                    ? "We’re not sure yet. The next message may change this forecast."
                    : demo.id === "benign"
                      ? "No scam trajectory in this scripted exchange."
                      : score.locked
                        ? "This conversation is following a scam trajectory."
                        : "Watch for a change in identity, urgency or a request."}
                </p>
                <Compass score={score} />
                <p className="family-label">{score.family.label}</p>
                <div className="compass-key">
                  <span>ANGLE = FAMILY MIX</span>
                  <span>LENGTH = RISK</span>
                </div>
                <div
                  className="chain"
                  aria-label={`Current stage: ${demo.conversation.turns[count - 1].stage}. Predicted next: ${score.next_stage.stage}.`}
                >
                  {stages.map((s, i) => (
                    <ReactFragment key={s.id}>
                      <span
                        className={`chain-stage ${demo.conversation.turns[count - 1].stage === s.id ? "current" : ""} ${score.next_stage.stage === s.id ? "predicted" : ""}`}
                      >
                        {s.label}
                        {demo.conversation.turns[count - 1].stage === s.id && (
                          <small>NOW</small>
                        )}
                        {score.next_stage.stage === s.id && <small>NEXT</small>}
                      </span>
                      {i < 3 && (
                        <span className="chain-arrow" aria-hidden="true">
                          ➡
                        </span>
                      )}
                    </ReactFragment>
                  ))}
                </div>
                <p className="chain-note">
                  Solid = current script stage · dashed = predicted next
                </p>
              </section>
              <section className="zd-panel safety">
                <p className="eyebrow">
                  ◈ SAFETY CARD <span>MOCK</span>
                </p>
                <h2>{card?.headline}</h2>
                <p>{card?.why[0]}</p>
                <div className="safe-actions">
                  {card?.next_steps.map((step) => (
                    <button key={step.id} onClick={() => action(step.action)}>
                      {step.label}
                      <span aria-hidden="true">↗</span>
                    </button>
                  ))}
                </div>
                <p className="action-notice" role="status">
                  {notice}
                </p>
                <p className="card-privacy">
                  No text left this browser. Verification and reports are
                  simulated.
                </p>
              </section>
            </>
          ) : (
            <section className="zd-panel waiting">
              <div className="radar" aria-hidden="true">
                ⌖
              </div>
              <h2>The forecast lives here.</h2>
              <p>
                Open a conversation and reveal its next message. Each turn adds
                context to the trajectory.
              </p>
              <div className="waiting-line" />
              <span className="zd-hud">MODEL EVALUATION METRICS: --</span>
            </section>
          )}
          <LeafSheep manifests={manifests} status={adapterStatus} />
        </aside>
      </div>
      <footer className="site-footer">
        <span>DESIGNED TO CATCH THE SETUP, BEFORE THE ASK.</span>
        <span>
          HACKUTD <b>ZERO DAY</b> / 2026
        </span>
      </footer>
      {target && <CoolDown target={target} close={() => setTarget(null)} />}
    </main>
  );
}
