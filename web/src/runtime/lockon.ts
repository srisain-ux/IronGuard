export interface LockParams {
  theta_lock: number;
  theta_release: number;
  release_turns: number;
}
export const DEFAULT_LOCK: LockParams = { theta_lock: 0.70, theta_release: 0.40, release_turns: 2 };

/** Matches infer.lock_states: ME never changes the release counter. */
export function lockStates(risks: number[], senders: string[], params: LockParams = DEFAULT_LOCK): boolean[] {
  if (risks.length !== senders.length) throw new Error("One risk is required per turn");
  const release = Math.min(params.theta_release, params.theta_lock);
  let locked = false;
  let below = 0;
  return risks.map((risk, i) => {
    if (!locked) { locked = risk >= params.theta_lock; below = 0; }
    else if (senders[i] === "them") {
      below = risk < release ? below + 1 : 0;
      if (below >= params.release_turns) { locked = false; below = 0; }
    }
    return locked;
  });
}
