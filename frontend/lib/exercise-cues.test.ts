import { describe, expect, it } from "vitest";

import { exerciseInstructions, movementLabel, primaryMuscleText } from "@/lib/exercise-cues";

const exercise = {
  id: 1,
  name: "Push-Up",
  slug: "push-up",
  equipment: "bodyweight",
  pattern: "horizontal_push",
  category: "push",
  primary_muscles: ["chest", "triceps"],
  secondary_muscles: ["shoulders"],
  level: "beginner",
  is_compound: true,
  instructions: ["Set hands under shoulders.", "Lower chest to floor.", "Press up."],
} as const;

describe("exercise cues", () => {
  it("uses seeded instructions first", () => {
    expect(exerciseInstructions(exercise, 2)).toEqual([
      "Set hands under shoulders.",
      "Lower chest to floor.",
    ]);
  });

  it("falls back to pattern cues", () => {
    expect(exerciseInstructions({ ...exercise, instructions: [] })[0]).toBe("Brace ribs down.");
  });

  it("formats movement metadata", () => {
    expect(movementLabel("horizontal_push")).toBe("Push");
    expect(primaryMuscleText(exercise)).toBe("chest, triceps");
  });
});
