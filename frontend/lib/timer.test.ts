import { describe, expect, it } from "vitest";

import { CYCLE, intervalState, isBoundary } from "@/lib/timer";

describe("intervalState", () => {
  it("starts in work phase, round 1", () => {
    expect(intervalState(0, 3)).toEqual({ round: 1, phase: "work", remaining: 40, done: false });
  });

  it("counts down within the work phase", () => {
    expect(intervalState(10, 3)).toMatchObject({ phase: "work", remaining: 30 });
  });

  it("switches to rest after 40s", () => {
    expect(intervalState(40, 3)).toMatchObject({ phase: "rest", remaining: 20, round: 1 });
  });

  it("advances to the next round after a full cycle", () => {
    expect(intervalState(CYCLE, 3)).toMatchObject({ round: 2, phase: "work", remaining: 40 });
  });

  it("is done after all rounds", () => {
    expect(intervalState(3 * CYCLE, 3).done).toBe(true);
    expect(intervalState(3 * CYCLE + 5, 3).done).toBe(true);
  });
});

describe("isBoundary", () => {
  it("fires at start, phase switch, and round rollover", () => {
    expect(isBoundary(0, 3)).toBe(true); // start of work
    expect(isBoundary(40, 3)).toBe(true); // work -> rest
    expect(isBoundary(60, 3)).toBe(true); // next round
    expect(isBoundary(15, 3)).toBe(false);
  });

  it("fires on completion", () => {
    expect(isBoundary(3 * CYCLE, 3)).toBe(true);
  });
});
