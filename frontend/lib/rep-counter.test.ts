import { describe, expect, it } from "vitest";

import type { TrackConfig } from "@/lib/pose";
import { initialRepState, updateRep, type RepState } from "@/lib/rep-counter";

const SQUAT: TrackConfig = {
  label: "Knee",
  joint: "knee",
  downAngle: 110,
  upAngle: 160,
  targetBottom: 100,
};

/** Feed a sequence of angles through the machine, returning the final state + rep events. */
function run(angles: (number | null)[], config = SQUAT): { state: RepState; completed: number } {
  let state = initialRepState();
  let completed = 0;
  for (const angle of angles) {
    const update = updateRep(state, angle, config);
    state = update.state;
    if (update.completedRep) completed += 1;
  }
  return { state, completed };
}

describe("updateRep", () => {
  it("counts one rep on a full down→up cycle", () => {
    const { state, completed } = run([170, 120, 90, 120, 165]);
    expect(completed).toBe(1);
    expect(state.reps).toBe(1);
    expect(state.lastFullRange).toBe(true); // reached 90 ≤ targetBottom 100
  });

  it("counts multiple reps", () => {
    const { state } = run([170, 90, 165, 95, 162, 80, 170]);
    expect(state.reps).toBe(3);
  });

  it("does not count until lockout is reached again", () => {
    // goes down, comes part-way up but never past upAngle.
    const { completed, state } = run([170, 90, 140, 130]);
    expect(completed).toBe(0);
    expect(state.phase).toBe("down");
  });

  it("flags a partial rep that misses depth", () => {
    // dips below downAngle (110) but not below targetBottom (100), then locks out.
    const { state } = run([170, 105, 165]);
    expect(state.reps).toBe(1);
    expect(state.lastFullRange).toBe(false);
  });

  it("does not double-count jitter at the top", () => {
    const { state } = run([170, 90, 161, 159, 162, 158]);
    expect(state.reps).toBe(1); // hovering near upAngle after a rep doesn't re-trigger
  });

  it("ignores null angles (joint not visible)", () => {
    const { state, completed } = run([170, null, 90, null, 165]);
    expect(completed).toBe(1);
    expect(state.reps).toBe(1);
  });
});
