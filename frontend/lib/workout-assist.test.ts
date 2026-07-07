import { describe, expect, it } from "vitest";

import type { PlanExerciseOut } from "@/lib/api";
import {
  readinessRecommendation,
  readinessVoiceCue,
  sessionCueTexts,
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

  it("formats Vietnamese voice prompts", () => {
    const recommendation = readinessRecommendation({ energy: 5, sleep: 5, soreness: 1 });
    expect(readinessVoiceCue(recommendation, "vi")).toContain("Mức sẵn sàng 100 phần trăm");
    expect(readinessVoiceCue(recommendation, "vi")).toContain("Sẵn sàng");
    expect(warmupVoiceCue(["Dead bugs"], "vi")).toBe("Khởi động. 1. Bài con bọ.");
  });

  it("collects every session cue for pre-generation, applying targets and readiness", () => {
    const push = pe("horizontal_push");
    const squat = { ...pe("squat"), id: 2, exercise_id: 2 };
    // "Moderate readiness": drop one set, add 15s rest.
    const recommendation = readinessRecommendation({ energy: 3, sleep: 3, soreness: 3 });
    const texts = sessionCueTexts({
      exercises: [push, squat],
      targets: {
        2: { exercise_id: 2, sets: 5, reps_min: 8, reps_max: 12, suggested_weight_kg: 40 },
      },
      recommendation,
      warmupDrills: ["Dead bugs"],
      lang: "en",
    });

    // Suggested target (5 sets) minus the readiness reduction (1) wins over plan sets.
    expect(texts.some((t) => t.startsWith("Test. Squat. 4 sets."))).toBe(true);
    // No target for the push exercise: plan sets (3) minus 1.
    expect(texts.some((t) => t.startsWith("Test. Push. 2 sets."))).toBe(true);
    // Identical rest prescriptions dedupe to a single phrase, with the bonus applied.
    expect(texts.filter((t) => t.startsWith("Set logged."))).toEqual([
      "Set logged. Rest 75 seconds.",
    ]);
    expect(texts).toContain(warmupVoiceCue(["Dead bugs"], "en"));
    expect(texts).toContain(readinessVoiceCue(recommendation, "en"));
    expect(texts).toContain("Rest complete. Start your next set.");
    expect(texts).toContain("Voice coach enabled.");
  });
});
