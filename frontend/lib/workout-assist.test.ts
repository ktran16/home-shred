import { describe, expect, it } from "vitest";

import type { PlanExerciseOut } from "@/lib/api";
import {
  readinessRecommendation,
  readinessVoiceCue,
  warmupForExercises,
  warmupVoiceCue,
} from "@/lib/workout-assist";

function pe(pattern: PlanExerciseOut["exercise"]["pattern"]): PlanExerciseOut {
  return {
    id: 1,
    exercise_id: 1,
    order_index: 1,
    sets: 3,
    target_reps_min: 8,
    target_reps_max: 12,
    rest_seconds: 60,
    is_conditioning: false,
    exercise: {
      id: 1,
      name: "Test",
      slug: "test",
      equipment: "bodyweight",
      pattern,
      category: "push",
      primary_muscles: ["chest"],
      secondary_muscles: [],
      level: "beginner",
      is_compound: true,
      instructions: [],
    },
  };
}

describe("workout assist helpers", () => {
  it("recommends volume and rest adjustments from readiness", () => {
    expect(readinessRecommendation({ energy: 5, sleep: 5, soreness: 1 })).toMatchObject({
      label: "Ready",
      setReduction: 0,
    });
    expect(readinessRecommendation({ energy: 2, sleep: 2, soreness: 5 })).toMatchObject({
      label: "Recovery day",
      setReduction: 2,
      restBonus: 30,
    });
  });

  it("creates a focused warm-up from movement patterns", () => {
    const drills = warmupForExercises([pe("horizontal_push"), pe("squat")]);
    expect(drills).toContain("Scapular push-ups");
    expect(drills).toContain("Bodyweight squats");
    expect(drills.at(-1)).toBe("First exercise ramp-up set");
  });

  it("formats voice prompts", () => {
    const recommendation = readinessRecommendation({ energy: 5, sleep: 5, soreness: 1 });
    expect(readinessVoiceCue(recommendation)).toContain("Readiness 100 percent");
    expect(warmupVoiceCue(["Dead bugs"])).toContain("1. Dead bugs.");
  });
});
