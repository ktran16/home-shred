import type { SessionOut } from "@/lib/api";

export type SessionImpression = NonNullable<SessionOut["impression"]>;

export type CalendarDay = {
  iso: string;
  day: number;
  inMonth: boolean;
  isToday: boolean;
  completed: number;
  started: number;
  impression: SessionImpression | null;
};

export type WorkoutStats = {
  completedSessions: number;
  currentMonthCompleted: number;
  currentWeekCompleted: number;
  totalSets: number;
  totalReps: number;
  currentStreak: number;
};

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function startOfDay(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

function startOfWeek(date: Date): Date {
  return addDays(startOfDay(date), -startOfDay(date).getUTCDay());
}

function uniqueCompletedDates(sessions: SessionOut[]): Set<string> {
  return new Set(sessions.filter((s) => s.completed).map((s) => s.date));
}

export function buildWorkoutStats(sessions: SessionOut[], today = new Date()): WorkoutStats {
  const currentMonth = today.getUTCMonth();
  const currentYear = today.getUTCFullYear();
  const weekStart = startOfWeek(today);
  const completedDates = uniqueCompletedDates(sessions);
  const completedSessions = sessions.filter((s) => s.completed);

  const latestCompleted =
    [...completedDates].sort().at(-1) ?? toIsoDate(startOfDay(today));
  let streak = 0;
  let cursor = new Date(`${latestCompleted}T00:00:00.000Z`);
  while (completedDates.has(toIsoDate(cursor))) {
    streak += 1;
    cursor = addDays(cursor, -1);
  }

  return {
    completedSessions: completedSessions.length,
    currentMonthCompleted: completedSessions.filter((s) => {
      const date = new Date(`${s.date}T00:00:00.000Z`);
      return date.getUTCFullYear() === currentYear && date.getUTCMonth() === currentMonth;
    }).length,
    currentWeekCompleted: completedSessions.filter((s) => {
      const date = new Date(`${s.date}T00:00:00.000Z`);
      return date >= weekStart && date <= startOfDay(today);
    }).length,
    totalSets: sessions.reduce((sum, s) => sum + s.set_logs.length, 0),
    totalReps: sessions.reduce(
      (sum, s) => sum + s.set_logs.reduce((inner, log) => inner + log.reps, 0),
      0,
    ),
    currentStreak: streak,
  };
}

export function buildMonthCalendar(
  sessions: SessionOut[],
  monthDate = new Date(),
  today = new Date(),
): CalendarDay[] {
  const year = monthDate.getUTCFullYear();
  const month = monthDate.getUTCMonth();
  const first = new Date(Date.UTC(year, month, 1));
  const start = addDays(first, -first.getUTCDay());
  const todayIso = toIsoDate(startOfDay(today));

  const byDate = new Map<
    string,
    { completed: number; started: number; impression: SessionImpression | null }
  >();
  for (const session of sessions) {
    const count = byDate.get(session.date) ?? { completed: 0, started: 0, impression: null };
    if (session.completed) count.completed += 1;
    else count.started += 1;
    // first recorded impression for a completed day wins (days rarely have more than one).
    if (session.completed && session.impression && count.impression == null) {
      count.impression = session.impression;
    }
    byDate.set(session.date, count);
  }

  return Array.from({ length: 42 }, (_, index) => {
    const date = addDays(start, index);
    const iso = toIsoDate(date);
    const count = byDate.get(iso) ?? { completed: 0, started: 0, impression: null };
    return {
      iso,
      day: date.getUTCDate(),
      inMonth: date.getUTCMonth() === month,
      isToday: iso === todayIso,
      completed: count.completed,
      started: count.started,
      impression: count.impression,
    };
  });
}
