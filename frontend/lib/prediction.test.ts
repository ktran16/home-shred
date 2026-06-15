import { describe, expect, it } from "vitest";

import type { LoadPredictionOut } from "@/lib/api";
import { predictionHeadline, readinessLabel } from "@/lib/prediction";

function pred(overrides: Partial<LoadPredictionOut> = {}): LoadPredictionOut {
  return {
    exercise_id: 1,
    exercise_name: "Goblet Squat",
    weighted: true,
    sessions: 4,
    current: 26.7,
    predicted_next: 28.5,
    trend_per_session: 0.6,
    avg_recent_rpe: 7.5,
    readiness: "progress",
    confidence: 0.43,
    ...overrides,
  };
}

describe("predictionHeadline", () => {
  it("forecasts e1RM for weighted lifts", () => {
    expect(predictionHeadline(pred())).toBe("~28.5 kg e1RM next");
  });

  it("forecasts reps for bodyweight lifts", () => {
    expect(predictionHeadline(pred({ weighted: false, predicted_next: 16 }))).toBe("~16 reps next");
  });

  it("counts remaining sessions when data is insufficient", () => {
    expect(predictionHeadline(pred({ readiness: "insufficient", predicted_next: null, sessions: 2 }))).toBe(
      "2 more sessions to forecast",
    );
    expect(predictionHeadline(pred({ readiness: "insufficient", predicted_next: null, sessions: 3 }))).toBe(
      "1 more session to forecast",
    );
  });
});

describe("readinessLabel", () => {
  it("maps each readiness state", () => {
    expect(readinessLabel(pred()).tone).toBe("progress");
    expect(readinessLabel(pred({ readiness: "hold" })).tone).toBe("hold");
    expect(readinessLabel(pred({ readiness: "insufficient" })).tone).toBe("building");
  });
});
