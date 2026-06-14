"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button, Card, Input, Label } from "@/components/ui";
import { api, type SessionOut } from "@/lib/api";
import { pivotVolume } from "@/lib/charts";
import { buildMonthCalendar, buildWorkoutStats, type CalendarDay } from "@/lib/workout-stats";

const COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];

export default function ProgressPage() {
  const volume = useQuery({
    queryKey: ["volume"],
    queryFn: async () => (await api.GET("/api/progress/volume")).data ?? [],
  });
  const metrics = useQuery({
    queryKey: ["body-metrics"],
    queryFn: async () => (await api.GET("/api/body-metrics")).data ?? [],
  });
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => (await api.GET("/api/sessions")).data ?? [],
  });

  const { rows, muscles } = pivotVolume(volume.data ?? []);
  const weightData = (metrics.data ?? []).map((m) => ({
    date: m.date,
    weight: Number(m.weight_kg),
  }));
  const sessionData = sessions.data ?? [];
  const stats = buildWorkoutStats(sessionData);
  const calendar = buildMonthCalendar(sessionData);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Progress</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Calendar, workout stats, volume, and body metrics.
        </p>
      </div>

      <WorkoutSummary
        sessions={sessionData}
        calendar={calendar}
        stats={stats}
        isLoading={sessions.isLoading}
        isError={sessions.isError}
      />

      <Card className="flex flex-col gap-2">
        <h2 className="font-semibold">Weekly volume by muscle</h2>
        {volume.isLoading ? (
          <p className="text-sm text-zinc-500">Loading volume...</p>
        ) : volume.isError ? (
          <p className="text-sm text-red-600">Could not load volume.</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-zinc-500">Log some workouts to see volume.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={rows} margin={{ left: -10, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="week" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {muscles.map((m, i) => (
                <Bar key={m} dataKey={m} stackId="v" fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card className="flex flex-col gap-2">
        <h2 className="font-semibold">Bodyweight</h2>
        {metrics.isLoading ? (
          <p className="text-sm text-zinc-500">Loading measurements...</p>
        ) : metrics.isError ? (
          <p className="text-sm text-red-600">Could not load measurements.</p>
        ) : weightData.length === 0 ? (
          <p className="text-sm text-zinc-500">No measurements yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={weightData} margin={{ left: -10, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis domain={["auto", "auto"]} fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="weight" stroke="#10b981" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <AddMetric />
    </div>
  );
}

function WorkoutSummary({
  sessions,
  calendar,
  stats,
  isLoading,
  isError,
}: {
  sessions: SessionOut[];
  calendar: CalendarDay[];
  stats: ReturnType<typeof buildWorkoutStats>;
  isLoading: boolean;
  isError: boolean;
}) {
  const monthLabel = new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(
    new Date(),
  );

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <Card className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold">{monthLabel}</h2>
          <span className="text-sm text-zinc-500">{stats.currentMonthCompleted} complete</span>
        </div>
        {isLoading ? (
          <p className="text-sm text-zinc-500">Loading calendar...</p>
        ) : isError ? (
          <p className="text-sm text-red-600">Could not load sessions.</p>
        ) : (
          <CalendarGrid days={calendar} />
        )}
      </Card>

      <Card className="flex flex-col gap-3">
        <h2 className="font-semibold">Workout statistics</h2>
        <div className="grid grid-cols-2 gap-2">
          <StatTile label="Streak" value={stats.currentStreak} suffix="days" />
          <StatTile label="This week" value={stats.currentWeekCompleted} suffix="done" />
          <StatTile label="Sessions" value={stats.completedSessions} suffix="total" />
          <StatTile label="Sets" value={stats.totalSets} suffix="logged" />
          <StatTile label="Reps" value={stats.totalReps} suffix="logged" className="col-span-2" />
        </div>
        <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
          <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">Latest</div>
          <div className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
            {latestSessionText(sessions)}
          </div>
        </div>
      </Card>
    </div>
  );
}

function CalendarGrid({ days }: { days: CalendarDay[] }) {
  const weekDays = ["S", "M", "T", "W", "T", "F", "S"];
  return (
    <div>
      <div className="mb-2 grid grid-cols-7 gap-1 text-center text-xs font-semibold text-zinc-400">
        {weekDays.map((day, index) => (
          <span key={`${day}-${index}`}>{day}</span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => (
          <label
            key={day.iso}
            title={`${day.iso}: ${day.completed} completed, ${day.started} started`}
            className={[
              "flex min-h-[48px] cursor-default flex-col items-center justify-center rounded-lg border text-xs transition-colors",
              day.inMonth
                ? "border-zinc-200 bg-white text-zinc-800 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100"
                : "border-zinc-100 bg-zinc-50 text-zinc-300 dark:border-zinc-900 dark:bg-zinc-950 dark:text-zinc-700",
              day.isToday ? "ring-2 ring-emerald-500" : "",
              day.completed > 0
                ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                : "",
            ].join(" ")}
          >
            <input
              type="checkbox"
              readOnly
              checked={day.completed > 0}
              aria-label={`${day.iso} completed`}
              className="mb-1 h-4 w-4 accent-emerald-600"
            />
            <span className="font-semibold">{day.day}</span>
            {day.completed > 1 && <span className="text-[10px]">x{day.completed}</span>}
          </label>
        ))}
      </div>
    </div>
  );
}

function StatTile({
  label,
  value,
  suffix,
  className = "",
}: {
  label: string;
  value: number;
  suffix: string;
  className?: string;
}) {
  return (
    <div className={`rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950 ${className}`}>
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-2xl font-bold tabular-nums">{value}</span>
        <span className="text-xs font-medium text-zinc-500">{suffix}</span>
      </div>
    </div>
  );
}

function latestSessionText(sessions: SessionOut[]): string {
  const latest = [...sessions].sort((a, b) => b.date.localeCompare(a.date))[0];
  if (!latest) return "No workouts logged yet.";
  const status = latest.completed ? "completed" : "started";
  const setCount = latest.set_logs.length;
  return `${latest.date} · ${status} · ${setCount} ${setCount === 1 ? "set" : "sets"}`;
}

function AddMetric() {
  const qc = useQueryClient();
  const [weight, setWeight] = useState("");
  const [bf, setBf] = useState("");
  const [waist, setWaist] = useState("");

  const add = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/body-metrics", {
        body: {
          weight_kg: Number(weight),
          body_fat_pct: bf === "" ? null : Number(bf),
          waist_cm: waist === "" ? null : Number(waist),
        },
      });
      if (error) throw new Error("Could not save measurement");
    },
    onSuccess: () => {
      setWeight("");
      setBf("");
      setWaist("");
      qc.invalidateQueries({ queryKey: ["body-metrics"] });
    },
  });

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-semibold">Log today’s measurement</h2>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <Label>Weight</Label>
          <Input type="number" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} />
        </div>
        <div>
          <Label>Body fat %</Label>
          <Input type="number" step="0.1" value={bf} onChange={(e) => setBf(e.target.value)} />
        </div>
        <div>
          <Label>Waist cm</Label>
          <Input type="number" step="0.1" value={waist} onChange={(e) => setWaist(e.target.value)} />
        </div>
      </div>
      <Button onClick={() => add.mutate()} disabled={add.isPending || weight === ""}>
        {add.isPending ? "Saving…" : "Save measurement"}
      </Button>
      {add.isError && <p className="text-center text-sm text-red-600">{add.error.message}</p>}
    </Card>
  );
}
