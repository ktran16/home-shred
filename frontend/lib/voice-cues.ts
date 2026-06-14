import type { PlanExerciseOut } from "@/lib/api";
import { exerciseInstructions, movementLabel } from "@/lib/exercise-cues";

export function exerciseVoiceCue(pe: PlanExerciseOut, sets: number): string {
  const instructions = exerciseInstructions(pe.exercise, 3);
  const prescription = pe.is_conditioning
    ? `${sets} rounds. Work for 40 seconds, then rest for 20 seconds.`
    : `${sets} sets. Target ${pe.target_reps_min} to ${pe.target_reps_max} reps. Rest ${pe.rest_seconds} seconds.`;
  const cues = instructions.length > 0 ? `Cues. ${instructions.join(" ")}` : "";
  return `${pe.exercise.name}. ${movementLabel(pe.exercise.pattern)}. ${prescription} ${cues}`.trim();
}

export function restStartedCue(seconds: number): string {
  return `Set logged. Rest ${seconds} seconds.`;
}

export function restCompleteCue(): string {
  return "Rest complete. Start your next set.";
}
