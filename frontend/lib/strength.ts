import type { ExerciseStrengthOut } from "@/lib/api";

export type StrengthSeriesPoint = { date: string; value: number };

/**
 * Chart series for an exercise: estimated 1RM for weighted movements, top-set reps
 * for bodyweight ones. Points without a usable value are dropped.
 */
export function strengthSeries(exercise: ExerciseStrengthOut): StrengthSeriesPoint[] {
  return exercise.points
    .map((point) => ({
      date: point.date,
      value: exercise.weighted ? point.e1rm : point.top_reps,
    }))
    .filter((point): point is StrengthSeriesPoint => point.value != null);
}

/** Y-axis / tooltip label for the trend chart. */
export function strengthUnitLabel(exercise: ExerciseStrengthOut): string {
  return exercise.weighted ? "est. 1RM (kg)" : "top-set reps";
}

/** Headline personal record, e.g. "33.3 kg e1RM" or "15 reps". */
export function prHeadline(exercise: ExerciseStrengthOut): string {
  if (exercise.weighted && exercise.best_e1rm != null) {
    return `${exercise.best_e1rm} kg e1RM`;
  }
  return `${exercise.best_reps} reps`;
}
