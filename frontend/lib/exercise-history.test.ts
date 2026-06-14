import { describe, expect, it } from "vitest";

import type { HistorySessionOut } from "@/lib/api";
import {
  estimatedOneRm,
  formatHistoryDate,
  formatLastTime,
  topSet,
} from "@/lib/exercise-history";

function session(
  sets: Array<[number, number, string | null, string | null]>,
  date = "2026-06-10",
): HistorySessionOut {
  return {
    session_id: 1,
    date,
    sets: sets.map(([set_number, reps, weight_kg, rpe]) => ({
      set_number,
      reps,
      weight_kg,
      rpe,
    })),
  };
}

describe("formatHistoryDate", () => {
  it("formats ISO dates without timezone drift", () => {
    expect(formatHistoryDate("2026-06-10")).toBe("Jun 10");
    expect(formatHistoryDate("2026-01-01")).toBe("Jan 1");
  });
});

describe("topSet", () => {
  it("returns the heaviest set, tie-broken by reps", () => {
    const top = topSet(session([
      [1, 12, "20.0", "7.0"],
      [2, 10, "22.5", "8.0"],
      [3, 8, "22.5", "9.0"],
    ]));
    expect(top).toEqual({ reps: 10, weightKg: 22.5, rpe: 8 });
  });

  it("handles bodyweight sets (null weight)", () => {
    const top = topSet(session([[1, 15, null, null]]));
    expect(top).toEqual({ reps: 15, weightKg: null, rpe: null });
  });

  it("returns null for an empty session", () => {
    expect(topSet(session([]))).toBeNull();
  });
});

describe("estimatedOneRm", () => {
  it("uses the Epley formula", () => {
    expect(estimatedOneRm(10, 20)).toBe(26.7); // 20 * (1 + 10/30)
  });

  it("is null for bodyweight or zero load", () => {
    expect(estimatedOneRm(15, null)).toBeNull();
    expect(estimatedOneRm(15, 0)).toBeNull();
  });
});

describe("formatLastTime", () => {
  it("recaps a weighted session", () => {
    // top set = heaviest; ties resolve to the first such set, so its RPE (7) is shown.
    expect(formatLastTime(session([
      [1, 12, "22.5", "7.0"],
      [2, 12, "22.5", "8.0"],
      [3, 10, "20.0", "8.0"],
    ]))).toBe("Jun 10: 12,12,10 @ 22.5 kg · RPE 7");
  });

  it("recaps a bodyweight session without a weight or RPE", () => {
    expect(formatLastTime(session([
      [1, 15, null, null],
      [2, 14, null, null],
    ]))).toBe("Jun 10: 15,14 reps");
  });

  it("falls back to just the date for an empty session", () => {
    expect(formatLastTime(session([]))).toBe("Jun 10");
  });
});
