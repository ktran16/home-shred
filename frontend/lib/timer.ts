// Conditioning interval timer math (SPEC §6.7): rounds × (40s work / 20s rest).
export const WORK = 40;
export const REST = 20;
export const CYCLE = WORK + REST;

export interface IntervalState {
  round: number; // 1-based
  phase: "work" | "rest";
  remaining: number; // seconds left in the current phase
  done: boolean;
}

/** Derive the interval state from elapsed seconds — pure, so it is easy to test. */
export function intervalState(elapsed: number, rounds: number): IntervalState {
  const total = rounds * CYCLE;
  if (elapsed >= total) {
    return { round: rounds, phase: "rest", remaining: 0, done: true };
  }
  const within = elapsed % CYCLE;
  const phase = within < WORK ? "work" : "rest";
  const remaining = within < WORK ? WORK - within : CYCLE - within;
  const round = Math.floor(elapsed / CYCLE) + 1;
  return { round, phase, remaining, done: false };
}

/** True when crossing a phase boundary (work↔rest) or completing — used for the cue. */
export function isBoundary(elapsed: number, rounds: number): boolean {
  if (elapsed >= rounds * CYCLE) return true;
  const within = elapsed % CYCLE;
  return within === 0 || within === WORK;
}
