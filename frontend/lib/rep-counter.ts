import type { TrackConfig } from "@/lib/pose";

/**
 * Pure rep-counting state machine over a stream of joint angles (SPEC §17.5 B2a).
 *
 * Semantics: high angle = extended/locked ("up"), low angle = contracted ("down").
 * A rep is counted on the down → up transition (return to lockout), using the
 * config's hysteresis band so jitter at the turnaround can't double-count. The
 * deepest angle reached during the contraction is checked against `targetBottom`
 * to flag partial range of motion.
 */

export type RepPhase = "up" | "down";

export type RepState = {
  phase: RepPhase;
  reps: number;
  /** deepest (smallest) angle seen so far in the current contraction. */
  deepestAngle: number;
  /** whether the most recently completed rep reached full depth (null before any rep). */
  lastFullRange: boolean | null;
};

export type RepUpdate = {
  state: RepState;
  /** true on the frame a rep completes. */
  completedRep: boolean;
  /** depth of the just-completed rep, else null. */
  fullRange: boolean | null;
};

export function initialRepState(): RepState {
  return { phase: "up", reps: 0, deepestAngle: Number.POSITIVE_INFINITY, lastFullRange: null };
}

/**
 * Advance the state machine by one angle sample. Returns the next state and whether
 * a rep completed on this frame. `null` angles (joint not visible) are ignored.
 */
export function updateRep(state: RepState, angle: number | null, config: TrackConfig): RepUpdate {
  if (angle === null || Number.isNaN(angle)) {
    return { state, completedRep: false, fullRange: null };
  }

  if (state.phase === "up") {
    if (angle <= config.downAngle) {
      return {
        state: { ...state, phase: "down", deepestAngle: angle },
        completedRep: false,
        fullRange: null,
      };
    }
    return { state, completedRep: false, fullRange: null };
  }

  // phase === "down": track the deepest point, count on return to lockout.
  const deepestAngle = Math.min(state.deepestAngle, angle);
  if (angle >= config.upAngle) {
    const fullRange = deepestAngle <= config.targetBottom;
    return {
      state: {
        phase: "up",
        reps: state.reps + 1,
        deepestAngle: Number.POSITIVE_INFINITY,
        lastFullRange: fullRange,
      },
      completedRep: true,
      fullRange,
    };
  }
  return { state: { ...state, deepestAngle }, completedRep: false, fullRange: null };
}
