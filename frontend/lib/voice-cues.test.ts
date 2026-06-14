import { describe, expect, it } from "vitest";

import type { PlanExerciseOut } from "@/lib/api";
import { exerciseVoiceCue, restCompleteCue, restStartedCue } from "@/lib/voice-cues";

const pe = {
  id: 1,
  exercise_id: 1,
  order_index: 1,
  sets: 3,
  target_reps_min: 8,
  target_reps_max: 12,
  rest_seconds: 75,
  is_conditioning: false,
  exercise: {
    id: 1,
    name: "Push-Up",
    slug: "push-up",
    equipment: "bodyweight",
    pattern: "horizontal_push",
    category: "push",
    primary_muscles: ["chest"],
    secondary_muscles: ["triceps"],
    level: "beginner",
    is_compound: true,
    instructions: ["Brace.", "Lower with control."],
  },
} satisfies PlanExerciseOut;

describe("voice cues", () => {
  it("formats an exercise voice-over cue", () => {
    expect(exerciseVoiceCue(pe, 3)).toContain("Push-Up. Push. 3 sets.");
    expect(exerciseVoiceCue(pe, 3)).toContain("Brace.");
  });

  it("formats rest cues", () => {
    expect(restStartedCue(75)).toBe("Set logged. Rest 75 seconds.");
    expect(restCompleteCue()).toBe("Rest complete. Start your next set.");
  });
});
