import type { ExerciseOut } from "@/lib/api";

const PATTERN_CUES: Record<NonNullable<ExerciseOut["pattern"]>, string[]> = {
  horizontal_push: ["Brace ribs down.", "Lower under control.", "Drive the floor away."],
  vertical_push: ["Stack ribs over hips.", "Press overhead.", "Finish with biceps near ears."],
  horizontal_pull: ["Hinge and brace.", "Pull elbow past ribs.", "Lower without twisting."],
  vertical_pull: ["Start from a dead hang.", "Pull chest toward the bar.", "Lower to straight arms."],
  squat: ["Brace before descending.", "Knees track over toes.", "Stand tall through midfoot."],
  hinge: ["Push hips back.", "Keep spine long.", "Squeeze glutes to stand."],
  core: ["Lock ribs and pelvis.", "Move slowly.", "Stop before form breaks."],
  conditioning: ["Stay springy.", "Keep breathing steady.", "Move fast without rushing reps."],
};

const PATTERN_LABELS: Record<NonNullable<ExerciseOut["pattern"]>, string> = {
  horizontal_push: "Push",
  vertical_push: "Overhead press",
  horizontal_pull: "Row",
  vertical_pull: "Pull",
  squat: "Squat",
  hinge: "Hinge",
  core: "Core",
  conditioning: "Conditioning",
};

export function movementLabel(pattern: ExerciseOut["pattern"]): string {
  return pattern ? PATTERN_LABELS[pattern] : "Strength";
}

export function exerciseInstructions(exercise: ExerciseOut, limit = 3): string[] {
  const seeded = exercise.instructions.filter(Boolean).slice(0, limit);
  if (seeded.length > 0) return seeded;
  return exercise.pattern ? PATTERN_CUES[exercise.pattern].slice(0, limit) : [];
}

export function primaryMuscleText(exercise: ExerciseOut): string {
  return exercise.primary_muscles.slice(0, 3).join(", ");
}
