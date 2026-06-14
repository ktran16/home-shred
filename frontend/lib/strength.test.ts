import { describe, expect, it } from "vitest";

import type { ExerciseStrengthOut } from "@/lib/api";
import { prHeadline, strengthSeries, strengthUnitLabel } from "@/lib/strength";

function weighted(): ExerciseStrengthOut {
  return {
    exercise_id: 1,
    exercise_name: "Goblet Squat",
    pattern: "squat",
    weighted: true,
    best_e1rm: 33.3,
    best_weight: 25,
    best_reps: 10,
    latest_is_pr: true,
    points: [
      { date: "2026-06-01", e1rm: 26.7, top_weight: 20, top_reps: 10 },
      { date: "2026-06-08", e1rm: 33.3, top_weight: 25, top_reps: 10 },
    ],
  };
}

function bodyweight(): ExerciseStrengthOut {
  return {
    exercise_id: 2,
    exercise_name: "Push-Up",
    pattern: "horizontal_push",
    weighted: false,
    best_e1rm: null,
    best_weight: null,
    best_reps: 15,
    latest_is_pr: true,
    points: [
      { date: "2026-06-01", e1rm: null, top_weight: null, top_reps: 12 },
      { date: "2026-06-08", e1rm: null, top_weight: null, top_reps: 15 },
    ],
  };
}

describe("strengthSeries", () => {
  it("uses e1RM for weighted exercises", () => {
    expect(strengthSeries(weighted())).toEqual([
      { date: "2026-06-01", value: 26.7 },
      { date: "2026-06-08", value: 33.3 },
    ]);
  });

  it("uses top-set reps for bodyweight exercises", () => {
    expect(strengthSeries(bodyweight())).toEqual([
      { date: "2026-06-01", value: 12 },
      { date: "2026-06-08", value: 15 },
    ]);
  });

  it("drops points without a usable value", () => {
    const ex = weighted();
    ex.points = [{ date: "2026-06-01", e1rm: null, top_weight: null, top_reps: 0 }];
    expect(strengthSeries(ex)).toEqual([]);
  });
});

describe("strengthUnitLabel", () => {
  it("labels weighted vs bodyweight", () => {
    expect(strengthUnitLabel(weighted())).toBe("est. 1RM (kg)");
    expect(strengthUnitLabel(bodyweight())).toBe("top-set reps");
  });
});

describe("prHeadline", () => {
  it("formats the headline PR", () => {
    expect(prHeadline(weighted())).toBe("33.3 kg e1RM");
    expect(prHeadline(bodyweight())).toBe("15 reps");
  });
});
