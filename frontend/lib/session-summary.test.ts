import { describe, expect, it } from "vitest";

import { buildSessionSummary, formatSessionNotes } from "@/lib/session-summary";

describe("session summary", () => {
  it("summarizes logged sets", () => {
    const summary = buildSessionSummary([
      {
        exerciseId: 1,
        exerciseName: "Push-Up",
        setNumber: 1,
        reps: 12,
        weightKg: null,
        rpe: 8,
      },
      {
        exerciseId: 2,
        exerciseName: "Goblet Squat",
        setNumber: 1,
        reps: 10,
        weightKg: 20,
        rpe: 9,
      },
    ]);

    expect(summary).toEqual({
      totalSets: 2,
      totalReps: 22,
      weightedSets: 1,
      averageRpe: 8.5,
      hardestExercise: "Push-Up",
    });
  });

  it("formats notes with tags and summary", () => {
    const notes = formatSessionNotes({
      notes: "Felt strong.",
      tags: ["felt strong"],
      summary: {
        totalSets: 2,
        totalReps: 22,
        weightedSets: 1,
        averageRpe: 8.5,
        hardestExercise: "Push-Up",
      },
    });

    expect(notes).toContain("Tags: felt strong");
    expect(notes).toContain("Summary: 2 sets, 22 reps, avg RPE 8.5");
    expect(notes).toContain("Felt strong.");
  });
});
