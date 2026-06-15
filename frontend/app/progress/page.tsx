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

import { ProgressPhotosCard } from "@/components/progress-photos";
import { Badge, Button, Card, Input, Label, Select } from "@/components/ui";
import {
  api,
  type ExerciseStrengthOut,
  type LoadPredictionOut,
  type MeasurementSeriesOut,
  type MeasurementTypeOut,
  type SessionOut,
} from "@/lib/api";
import { pivotVolume } from "@/lib/charts";
import {
  changeTone,
  formatChange,
  formatLatest,
  measurementChartData,
} from "@/lib/measurements";
import { predictionHeadline, readinessLabel } from "@/lib/prediction";
import { prHeadline, strengthSeries, strengthUnitLabel } from "@/lib/strength";
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
  const strength = useQuery({
    queryKey: ["strength"],
    queryFn: async () => (await api.GET("/api/progress/strength")).data ?? [],
  });
  const prediction = useQuery({
    queryKey: ["prediction"],
    queryFn: async () => (await api.GET("/api/progress/prediction")).data ?? [],
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

      <StrengthSection
        data={strength.data ?? []}
        isLoading={strength.isLoading}
        isError={strength.isError}
      />

      <PredictionSection
        data={prediction.data ?? []}
        isLoading={prediction.isLoading}
        isError={prediction.isError}
      />

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

      <MeasurementsSection />

      <ProgressPhotosCard />
    </div>
  );
}

function MeasurementsSection() {
  const qc = useQueryClient();
  const [typeId, setTypeId] = useState<number | null>(null);
  const [value, setValue] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [newLabel, setNewLabel] = useState("");
  const [chartTypeId, setChartTypeId] = useState<number | null>(null);

  const types = useQuery({
    queryKey: ["measurement-types"],
    queryFn: async () => (await api.GET("/api/measurements/types")).data ?? [],
  });
  const series = useQuery({
    queryKey: ["measurement-series"],
    queryFn: async () => (await api.GET("/api/measurements/series")).data ?? [],
  });

  const typeList: MeasurementTypeOut[] = types.data ?? [];
  const seriesList: MeasurementSeriesOut[] = series.data ?? [];
  const activeTypeId = typeId ?? typeList[0]?.id ?? null;
  const activeType = typeList.find((t) => t.id === activeTypeId) ?? null;

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["measurement-types"] });
    qc.invalidateQueries({ queryKey: ["measurement-series"] });
  };

  const logEntry = useMutation({
    mutationFn: async () => {
      if (activeTypeId == null) throw new Error("Pick a measurement");
      const { error } = await api.POST("/api/measurements/entries", {
        body: { type_id: activeTypeId, date, value: Number(value) },
      });
      if (error) throw new Error("Could not save measurement");
    },
    onSuccess: () => {
      setValue("");
      invalidate();
    },
  });

  const addType = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/measurements/types", {
        body: { label: newLabel, unit: "cm" },
      });
      if (error) throw new Error("Name already exists or is invalid");
    },
    onSuccess: () => {
      setNewLabel("");
      invalidate();
    },
  });

  const removeType = useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/measurements/types/{type_id}", {
        params: { path: { type_id: id } },
      });
      if (error) throw new Error("Could not delete");
    },
    onSuccess: invalidate,
  });

  const chartSeries =
    seriesList.find((s) => s.type.id === (chartTypeId ?? seriesList[0]?.type.id)) ?? null;
  const chartData = chartSeries ? measurementChartData(chartSeries) : [];

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-semibold">Body measurements</h2>

      {/* Per-type latest + change tiles */}
      {seriesList.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {seriesList.map((s) => (
            <button
              key={s.type.id}
              onClick={() => setChartTypeId(s.type.id)}
              className="rounded-lg bg-zinc-50 p-3 text-left dark:bg-zinc-950"
            >
              <div className="text-xs text-zinc-500">{s.type.label}</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-lg font-bold tabular-nums">
                  {formatLatest(s.latest, s.type.unit)}
                </span>
                <span className={`text-xs font-medium ${changeTone(s.change)}`}>
                  {formatChange(s.change, s.type.unit)}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Trend chart for the selected type */}
      {chartSeries && chartData.length >= 2 ? (
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
            {chartSeries.type.label} · {chartSeries.type.unit}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ left: -10, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis domain={["auto", "auto"]} fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-sm text-zinc-500">
          Log a measurement on two or more dates to see its trend.
        </p>
      )}

      {/* Log a value */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div>
          <Label>Measurement</Label>
          <Select
            value={activeTypeId ?? ""}
            onChange={(e) => setTypeId(Number(e.target.value))}
            aria-label="Select measurement"
          >
            {typeList.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Value{activeType ? ` (${activeType.unit})` : ""}</Label>
          <Input
            type="number"
            step="0.1"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </div>
        <Button
          onClick={() => logEntry.mutate()}
          disabled={logEntry.isPending || value === "" || activeTypeId == null}
        >
          {logEntry.isPending ? "Saving…" : "Log"}
        </Button>
      </div>
      <div>
        <Label>Date</Label>
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>
      {logEntry.isError && (
        <p className="text-sm text-red-600">{logEntry.error.message}</p>
      )}

      {/* Add a custom measurement type */}
      <div className="border-t border-zinc-100 pt-3 dark:border-zinc-800">
        <Label>Add a custom measurement</Label>
        <div className="flex gap-2">
          <Input
            placeholder="e.g. Forearm"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
          />
          <Button
            variant="secondary"
            onClick={() => addType.mutate()}
            disabled={addType.isPending || newLabel.trim() === ""}
          >
            Add
          </Button>
        </div>
        {addType.isError && <p className="mt-1 text-sm text-red-600">{addType.error.message}</p>}
        <div className="mt-2 flex flex-wrap gap-1">
          {typeList
            .filter((t) => !t.builtin)
            .map((t) => (
              <Badge key={t.id} className="gap-1">
                {t.label}
                <button
                  onClick={() => removeType.mutate(t.id)}
                  aria-label={`Delete ${t.label}`}
                  className="ml-1 text-zinc-400 hover:text-red-600"
                >
                  ×
                </button>
              </Badge>
            ))}
        </div>
      </div>
    </Card>
  );
}

function StrengthSection({
  data,
  isLoading,
  isError,
}: {
  data: ExerciseStrengthOut[];
  isLoading: boolean;
  isError: boolean;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selected = data.find((e) => e.exercise_id === selectedId) ?? data[0] ?? null;
  const series = selected ? strengthSeries(selected) : [];

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold">Personal records & strength</h2>
        {data.length > 0 && (
          <select
            value={selected?.exercise_id ?? ""}
            onChange={(e) => setSelectedId(Number(e.target.value))}
            className="h-9 rounded-lg border border-zinc-300 bg-white px-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            aria-label="Select exercise for strength trend"
          >
            {data.map((exercise) => (
              <option key={exercise.exercise_id} value={exercise.exercise_id}>
                {exercise.exercise_name}
              </option>
            ))}
          </select>
        )}
      </div>

      {isLoading ? (
        <p className="text-sm text-zinc-500">Loading strength...</p>
      ) : isError ? (
        <p className="text-sm text-red-600">Could not load strength.</p>
      ) : data.length === 0 ? (
        <p className="text-sm text-zinc-500">
          Log weighted or bodyweight sets to track PRs and strength.
        </p>
      ) : (
        <>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {data.slice(0, 6).map((exercise) => (
              <div
                key={exercise.exercise_id}
                className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold">{exercise.exercise_name}</span>
                  {exercise.latest_is_pr && (
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                      🏆 PR
                    </Badge>
                  )}
                </div>
                <div className="mt-1 text-lg font-bold tabular-nums">{prHeadline(exercise)}</div>
                {exercise.weighted && exercise.best_weight != null && (
                  <div className="text-xs text-zinc-500">top weight {exercise.best_weight} kg</div>
                )}
              </div>
            ))}
          </div>

          {selected && (
            <div>
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">
                {selected.exercise_name} · {strengthUnitLabel(selected)}
              </div>
              {series.length < 2 ? (
                <p className="text-sm text-zinc-500">
                  Need at least two sessions to chart a trend.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={series} margin={{ left: -10, right: 8, top: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="date" fontSize={11} />
                    <YAxis domain={["auto", "auto"]} fontSize={11} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          )}
        </>
      )}
    </Card>
  );
}

const TONE_CLASS: Record<string, string> = {
  progress: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  hold: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  building: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
};

function PredictionSection({
  data,
  isLoading,
  isError,
}: {
  data: LoadPredictionOut[];
  isLoading: boolean;
  isError: boolean;
}) {
  // forecastable lifts first; cap the list so it stays a glanceable card.
  const ordered = [...data].sort(
    (a, b) => Number(b.predicted_next != null) - Number(a.predicted_next != null),
  );

  return (
    <Card className="flex flex-col gap-3">
      <div>
        <h2 className="font-semibold">Next-session forecast</h2>
        <p className="text-sm text-zinc-500">
          Trend-based load / readiness per lift (a baseline; sharpens with history).
        </p>
      </div>
      {isLoading ? (
        <p className="text-sm text-zinc-500">Loading forecast...</p>
      ) : isError ? (
        <p className="text-sm text-red-600">Could not load forecast.</p>
      ) : data.length === 0 ? (
        <p className="text-sm text-zinc-500">Log a few sessions to forecast next-session load.</p>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {ordered.slice(0, 6).map((p) => {
            const verdict = readinessLabel(p);
            return (
              <div key={p.exercise_id} className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold">{p.exercise_name}</span>
                  <Badge className={TONE_CLASS[verdict.tone]}>{verdict.label}</Badge>
                </div>
                <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                  {predictionHeadline(p)}
                </div>
                {p.predicted_next != null && (
                  <div className="mt-1 text-xs text-zinc-400">
                    confidence {Math.round(p.confidence * 100)}% · {p.sessions} sessions
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
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

const IMPRESSION_EMOJI: Record<string, string> = { good: "🙂", neutral: "😐", bad: "😣" };

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
            title={`${day.iso}: ${day.completed} completed, ${day.started} started${
              day.impression ? ` · felt ${day.impression}` : ""
            }`}
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
            {day.impression ? (
              <span className="mb-0.5 text-sm leading-none" aria-label={`felt ${day.impression}`}>
                {IMPRESSION_EMOJI[day.impression]}
              </span>
            ) : (
              <input
                type="checkbox"
                readOnly
                checked={day.completed > 0}
                aria-label={`${day.iso} completed`}
                className="mb-1 h-4 w-4 accent-emerald-600"
              />
            )}
            <span className="font-semibold">{day.day}</span>
            {day.completed > 1 && <span className="text-[10px]">x{day.completed}</span>}
          </label>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-500">
        <span>🙂 good</span>
        <span>😐 neutral</span>
        <span>😣 rough</span>
        <span>☑︎ done (no rating)</span>
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
