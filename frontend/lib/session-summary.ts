export type LoggedSetSummary = {
  exerciseId: number;
  exerciseName: string;
  setNumber: number;
  reps: number;
  weightKg: number | null;
  rpe: number | null;
};

export type SessionSummary = {
  totalSets: number;
  totalReps: number;
  weightedSets: number;
  averageRpe: number | null;
  hardestExercise: string | null;
};

export function buildSessionSummary(logs: LoggedSetSummary[]): SessionSummary {
  const rpes = logs.map((log) => log.rpe).filter((rpe): rpe is number => rpe != null);
  const byExercise = new Map<string, number>();
  for (const log of logs) {
    byExercise.set(log.exerciseName, (byExercise.get(log.exerciseName) ?? 0) + log.reps);
  }
  const hardestExercise =
    [...byExercise.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;

  return {
    totalSets: logs.length,
    totalReps: logs.reduce((sum, log) => sum + log.reps, 0),
    weightedSets: logs.filter((log) => log.weightKg != null && log.weightKg > 0).length,
    averageRpe:
      rpes.length > 0
        ? Math.round((rpes.reduce((sum, rpe) => sum + rpe, 0) / rpes.length) * 10) / 10
        : null,
    hardestExercise,
  };
}

export function formatSessionNotes({
  notes,
  tags,
  summary,
}: {
  notes: string;
  tags: string[];
  summary: SessionSummary;
}): string {
  const parts = [
    tags.length > 0 ? `Tags: ${tags.join(", ")}` : null,
    `Summary: ${summary.totalSets} sets, ${summary.totalReps} reps${
      summary.averageRpe != null ? `, avg RPE ${summary.averageRpe}` : ""
    }`,
    notes.trim() || null,
  ].filter(Boolean);
  return parts.join("\n\n");
}
