import { describe, expect, it } from "vitest";

import type { SessionOut } from "@/lib/api";
import {
  buildMonthCalendar,
  buildWorkoutStats,
  type SessionImpression,
} from "@/lib/workout-stats";

const baseSession = {
  id: 1,
  plan_day_id: 1,
  notes: null,
  impression: null,
  created_at: "2026-06-10T00:00:00Z",
  suggested_targets: [],
} satisfies Omit<SessionOut, "date" | "completed" | "set_logs">;

function session(
  date: string,
  completed = true,
  reps = 10,
  impression: SessionImpression | null = null,
): SessionOut {
  return {
    ...baseSession,
    date,
    completed,
    impression,
    set_logs: completed
      ? [
          {
            id: 1,
            session_id: 1,
            exercise_id: 1,
            set_number: 1,
            reps,
            weight_kg: null,
            rpe: null,
          },
        ]
      : [],
  };
}

describe("workout stats", () => {
  it("summarizes sessions, sets, reps, and streak", () => {
    const stats = buildWorkoutStats(
      [
        session("2026-06-12", true, 8),
        session("2026-06-13", true, 10),
        session("2026-06-14", true, 12),
        session("2026-06-11", false),
      ],
      new Date("2026-06-14T12:00:00.000Z"),
    );

    expect(stats).toEqual({
      completedSessions: 3,
      currentMonthCompleted: 3,
      currentWeekCompleted: 1,
      totalSets: 3,
      totalReps: 30,
      currentStreak: 3,
    });
  });

  it("builds a six-week month calendar with checked days", () => {
    const days = buildMonthCalendar(
      [session("2026-06-14"), session("2026-06-15", false)],
      new Date("2026-06-14T00:00:00.000Z"),
      new Date("2026-06-14T00:00:00.000Z"),
    );

    expect(days).toHaveLength(42);
    expect(days.find((d) => d.iso === "2026-06-14")).toMatchObject({
      completed: 1,
      isToday: true,
    });
    expect(days.find((d) => d.iso === "2026-06-15")).toMatchObject({ started: 1 });
  });

  it("surfaces a completed day's impression on the calendar", () => {
    const days = buildMonthCalendar(
      [session("2026-06-14", true, 10, "good"), session("2026-06-13", false)],
      new Date("2026-06-14T00:00:00.000Z"),
      new Date("2026-06-14T00:00:00.000Z"),
    );
    expect(days.find((d) => d.iso === "2026-06-14")?.impression).toBe("good");
    // a started-only day carries no impression
    expect(days.find((d) => d.iso === "2026-06-13")?.impression).toBeNull();
  });
});
