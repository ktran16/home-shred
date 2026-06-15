"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { BarcodeScanner } from "@/components/barcode-scanner";
import { FoodSearchCard } from "@/components/food-search";
import { Button, Card, Input, Label } from "@/components/ui";
import {
  api,
  type DailyFoodLogOut,
  type FoodLogIn,
  type FoodLogRecentOut,
  type NutritionHistoryOut,
} from "@/lib/api";
import {
  EMPTY_FOOD_DRAFT,
  adherenceSummary,
  draftToFoodLog,
  macroPercent,
  nutritionHistoryRows,
  recentFoodToLog,
  remainingLabel,
  todayIsoDate,
  type ManualFoodDraft,
} from "@/lib/food-log";

function MacroCard({ label, grams, kcal, color }: { label: string; grams: number; kcal: number; color: string }) {
  return (
    <Card className="flex flex-col items-center gap-1 py-3">
      <span className={`text-2xl font-bold ${color}`}>{grams}g</span>
      <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">{label}</span>
      <span className="text-[10px] text-zinc-400">{kcal} kcal</span>
    </Card>
  );
}

export default function NutritionPage() {
  const qc = useQueryClient();
  const [logDate, setLogDate] = useState(() => todayIsoDate());
  const { data, isLoading } = useQuery({
    queryKey: ["nutrition"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/nutrition/targets");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });

  const recompute = useMutation({
    mutationFn: async () => {
      await api.POST("/api/nutrition/recompute");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nutrition"] }),
  });

  const adaptive = useQuery({
    queryKey: ["nutrition-adaptive"],
    enabled: !!data,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/nutrition/adaptive");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });

  const foodLog = useQuery({
    queryKey: ["food-log", logDate],
    enabled: !!data,
    queryFn: async () => {
      const { data } = await api.GET("/api/nutrition/log", {
        params: { query: { date: logDate } },
      });
      return data ?? null;
    },
  });

  const recentFoods = useQuery({
    queryKey: ["food-recent"],
    enabled: !!data,
    queryFn: async () => {
      const { data } = await api.GET("/api/nutrition/log/recent", {
        params: { query: { limit: 8 } },
      });
      return data ?? [];
    },
  });

  const history = useQuery({
    queryKey: ["nutrition-history", logDate],
    enabled: !!data,
    queryFn: async () => {
      const { data } = await api.GET("/api/nutrition/log/history", {
        params: { query: { end_date: logDate, days: 7 } },
      });
      return data ?? null;
    },
  });

  const invalidateFoodLog = () => {
    qc.invalidateQueries({ queryKey: ["food-log", logDate] });
    qc.invalidateQueries({ queryKey: ["food-recent"] });
    qc.invalidateQueries({ queryKey: ["nutrition-history"] });
    qc.invalidateQueries({ queryKey: ["nutrition-adaptive"] });
  };

  const addFood = useMutation({
    mutationFn: async (body: FoodLogIn) => {
      const { error } = await api.POST("/api/nutrition/log", { body });
      if (error) throw new Error("Could not add food");
    },
    onSuccess: invalidateFoodLog,
  });

  const copyDay = useMutation({
    mutationFn: async (fromDate: string) => {
      const { error } = await api.POST("/api/nutrition/log/copy-day", {
        body: { from_date: fromDate, to_date: logDate },
      });
      if (error) throw new Error("Nothing logged on that day to copy");
    },
    onSuccess: invalidateFoodLog,
  });

  const deleteFood = useMutation({
    mutationFn: async (entryId: number) => {
      const { error } = await api.DELETE("/api/nutrition/log/{entry_id}", {
        params: { path: { entry_id: entryId } },
      });
      if (error) throw new Error("Could not delete food");
    },
    onSuccess: invalidateFoodLog,
  });

  const applyAdaptive = useMutation({
    mutationFn: async () => {
      await api.POST("/api/nutrition/adaptive/apply");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["nutrition"] });
      qc.invalidateQueries({ queryKey: ["nutrition-adaptive"] });
    },
  });

  if (isLoading) return <p className="text-sm text-zinc-500">Loading…</p>;

  if (!data) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold">Nutrition</h1>
        <Card className="flex flex-col gap-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Set your profile to compute calorie & macro targets.
          </p>
          <Link href="/profile">
            <Button className="w-full">Set up profile</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Nutrition</h1>

      <Card className="flex flex-col items-center gap-1 py-5">
        <span className="text-4xl font-bold text-emerald-600">{data.target_kcal}</span>
        <span className="text-sm text-zinc-600 dark:text-zinc-400">kcal/day target</span>
        <span className="text-xs text-zinc-400">TDEE {data.tdee_kcal} · 20% deficit</span>
      </Card>

      <div className="grid grid-cols-3 gap-2">
        <MacroCard label="Protein" grams={data.protein_g} kcal={data.protein_g * 4} color="text-blue-500" />
        <MacroCard label="Carbs" grams={data.carbs_g} kcal={data.carbs_g * 4} color="text-amber-500" />
        <MacroCard label="Fat" grams={data.fat_g} kcal={data.fat_g * 9} color="text-rose-500" />
      </div>

      <Button
        variant="secondary"
        onClick={() => recompute.mutate()}
        disabled={recompute.isPending}
      >
        {recompute.isPending ? "Recomputing…" : "Recompute from profile"}
      </Button>

      {adaptive.data && (
        <Card className="flex flex-col gap-2">
          <h2 className="font-semibold">Adaptive TDEE</h2>
          {!adaptive.data.enough_data ? (
            <p className="text-sm text-zinc-500">{adaptive.data.reason}</p>
          ) : (
            <>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                From your last {adaptive.data.samples} weigh-ins over {adaptive.data.days_span} days,
                your weight is trending{" "}
                <span className="font-medium">
                  {adaptive.data.weight_change_kg_per_week! <= 0 ? "" : "+"}
                  {adaptive.data.weight_change_kg_per_week} kg/wk
                </span>
                .
              </p>
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-500">Estimated maintenance</span>
                <span className="font-medium">
                  {adaptive.data.estimated_tdee_kcal} kcal
                  <span className="text-xs text-zinc-400">
                    {" "}
                    (static {adaptive.data.static_tdee_kcal})
                  </span>
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-500">Suggested target</span>
                <span className="font-medium text-emerald-600">
                  {adaptive.data.suggested!.target_kcal} kcal
                </span>
              </div>
              {adaptive.data.clamped && (
                <p className="text-xs text-amber-500">
                  Trend looked extreme — estimate capped to ±25% of static TDEE.
                </p>
              )}
              <p className="text-[11px] text-zinc-400">
                Uses logged food when present, otherwise assumes your target (
                {adaptive.data.assumed_intake_kcal} kcal average).
              </p>
              <Button onClick={() => applyAdaptive.mutate()} disabled={applyAdaptive.isPending}>
                {applyAdaptive.isPending ? "Applying…" : "Apply adaptive target"}
              </Button>
            </>
          )}
        </Card>
      )}

      <FoodLogCard
        log={foodLog.data ?? null}
        date={logDate}
        loading={foodLog.isLoading}
        recent={recentFoods.data ?? []}
        onDateChange={setLogDate}
        onAdd={(entry) => addFood.mutate({ ...entry, date: entry.date ?? logDate })}
        onDelete={(id) => deleteFood.mutate(id)}
        onCopyDay={(fromDate) => copyDay.mutate(fromDate)}
        busy={addFood.isPending || deleteFood.isPending || copyDay.isPending}
        error={addFood.error?.message ?? deleteFood.error?.message ?? copyDay.error?.message}
      />

      <NutritionHistoryCard
        history={history.data ?? null}
        loading={history.isLoading}
        error={history.isError}
      />

      <FoodSearchCard
        logging={addFood.isPending}
        onLog={(entry) => addFood.mutate({ ...entry, date: logDate })}
      />

      <BarcodeScanner
        logging={addFood.isPending}
        onLog={(entry) => addFood.mutate({ ...entry, date: logDate })}
      />
    </div>
  );
}

function NutritionHistoryCard({
  history,
  loading,
  error,
}: {
  history: NutritionHistoryOut | null;
  loading: boolean;
  error: boolean;
}) {
  const rows = nutritionHistoryRows(history);

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-semibold">7-day adherence</h2>
          <p className="text-sm text-zinc-500">
            {history
              ? `${history.logged_days} logged days · ${history.start_date} to ${history.end_date}`
              : "Weekly calories and macros against target."}
          </p>
        </div>
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-right dark:bg-emerald-950/40">
          <div className="text-2xl font-bold tabular-nums text-emerald-600">
            {history ? `${history.adherence_pct}%` : "--"}
          </div>
          <div className="text-xs text-emerald-700 dark:text-emerald-300">
            {adherenceSummary(history)}
          </div>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-zinc-500">Loading nutrition history...</p>
      ) : error ? (
        <p className="text-sm text-red-600">Could not load nutrition history.</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-zinc-500">No history yet.</p>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={190}>
            <ComposedChart data={rows} margin={{ left: -12, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Bar dataKey="kcal" name="Logged kcal" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Line
                type="monotone"
                dataKey="target_kcal"
                name="Target kcal"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>

          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={rows} margin={{ left: -12, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="protein_g" name="Protein" stroke="#3b82f6" strokeWidth={2} />
              <Line type="monotone" dataKey="carbs_g" name="Carbs" stroke="#f59e0b" strokeWidth={2} />
              <Line type="monotone" dataKey="fat_g" name="Fat" stroke="#f43f5e" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>

          <div className="grid grid-cols-7 gap-1">
            {history?.days.map((day) => (
              <div
                key={day.date}
                className={[
                  "rounded-md px-1.5 py-2 text-center text-[11px] tabular-nums",
                  day.kcal_adherent
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                    : day.logged
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                      : "bg-zinc-100 text-zinc-500 dark:bg-zinc-900",
                ].join(" ")}
                title={`${day.date}: ${day.kcal} kcal${day.target_kcal ? ` / ${day.target_kcal}` : ""}`}
              >
                <div>{day.date.slice(5)}</div>
                <div className="font-semibold">{day.logged ? day.kcal : "-"}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

function FoodLogCard({
  log,
  date,
  loading,
  recent,
  onDateChange,
  onAdd,
  onDelete,
  onCopyDay,
  busy,
  error,
}: {
  log: DailyFoodLogOut | null;
  date: string;
  loading: boolean;
  recent: FoodLogRecentOut[];
  onDateChange: (date: string) => void;
  onAdd: (entry: FoodLogIn) => void;
  onDelete: (id: number) => void;
  onCopyDay: (fromDate: string) => void;
  busy: boolean;
  error?: string;
}) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-semibold">Food log</h2>
          <p className="text-sm text-zinc-500">
            Logged days feed adaptive TDEE; unlogged days still use your target.
          </p>
        </div>
        <Input
          type="date"
          className="sm:w-44"
          value={date}
          onChange={(event) => onDateChange(event.target.value || todayIsoDate())}
        />
      </div>

      {loading ? (
        <p className="text-sm text-zinc-500">Loading food log...</p>
      ) : (
        <>
          <FoodTotals log={log} />
          <FoodEntries entries={log?.entries ?? []} busy={busy} onDelete={onDelete} />
        </>
      )}

      <QuickAddRecent
        recent={recent}
        busy={busy}
        onAdd={(food) => onAdd(recentFoodToLog(food, date))}
      />
      <CopyDay date={date} busy={busy} onCopyDay={onCopyDay} />
      <ManualFoodForm date={date} busy={busy} onAdd={onAdd} />
      {error && <p className="text-sm text-red-600">{error}</p>}
    </Card>
  );
}

function QuickAddRecent({
  recent,
  busy,
  onAdd,
}: {
  recent: FoodLogRecentOut[];
  busy: boolean;
  onAdd: (food: FoodLogRecentOut) => void;
}) {
  if (recent.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <Label>Quick add</Label>
      <div className="flex flex-wrap gap-2">
        {recent.map((food, index) => (
          <Button
            key={`${food.name}-${food.last_logged_on}-${index}`}
            variant="secondary"
            className="h-auto min-h-0 flex-col items-start gap-0.5 px-3 py-2 text-left"
            disabled={busy}
            onClick={() => onAdd(food)}
            title={`P ${food.protein_g}g · C ${food.carbs_g}g · F ${food.fat_g}g`}
          >
            <span className="max-w-[10rem] truncate text-sm font-medium">{food.name}</span>
            <span className="text-[10px] font-normal text-zinc-500">
              {food.grams}g · {food.kcal} kcal
            </span>
          </Button>
        ))}
      </div>
    </div>
  );
}

function CopyDay({
  date,
  busy,
  onCopyDay,
}: {
  date: string;
  busy: boolean;
  onCopyDay: (fromDate: string) => void;
}) {
  const [fromDate, setFromDate] = useState(() => yesterdayIso(date));
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
      <Label>Copy a day</Label>
      <div className="flex flex-wrap items-end gap-2">
        <Input
          type="date"
          className="w-44"
          value={fromDate}
          max={date}
          onChange={(event) => setFromDate(event.target.value)}
        />
        <Button
          variant="secondary"
          disabled={busy || !fromDate || fromDate === date}
          onClick={() => onCopyDay(fromDate)}
        >
          {busy ? "Copying…" : "Copy into this day"}
        </Button>
      </div>
      <p className="text-xs text-zinc-500">Clones every entry from the chosen day into {date}.</p>
    </div>
  );
}

function yesterdayIso(date: string): string {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() - 1);
  return todayIsoDate(d);
}

function FoodTotals({ log }: { log: DailyFoodLogOut | null }) {
  const target = log?.target;
  const totals = log?.totals;
  return (
    <div className="grid gap-2 sm:grid-cols-4">
      <ProgressTile
        label="Calories"
        total={totals?.kcal ?? 0}
        target={target?.target_kcal}
        remaining={remainingLabel(log?.remaining_kcal)}
        percent={macroPercent(totals?.kcal ?? 0, target?.target_kcal)}
      />
      <ProgressTile
        label="Protein"
        total={Number(totals?.protein_g ?? 0)}
        target={target?.protein_g}
        unit="g"
        remaining={remainingLabel(log?.remaining_protein_g, "g")}
        percent={macroPercent(totals?.protein_g ?? 0, target?.protein_g)}
      />
      <ProgressTile
        label="Carbs"
        total={Number(totals?.carbs_g ?? 0)}
        target={target?.carbs_g}
        unit="g"
        remaining={remainingLabel(log?.remaining_carbs_g, "g")}
        percent={macroPercent(totals?.carbs_g ?? 0, target?.carbs_g)}
      />
      <ProgressTile
        label="Fat"
        total={Number(totals?.fat_g ?? 0)}
        target={target?.fat_g}
        unit="g"
        remaining={remainingLabel(log?.remaining_fat_g, "g")}
        percent={macroPercent(totals?.fat_g ?? 0, target?.fat_g)}
      />
    </div>
  );
}

function ProgressTile({
  label,
  total,
  target,
  unit = "",
  remaining,
  percent,
}: {
  label: string;
  total: number;
  target?: number | string | null;
  unit?: string;
  remaining: string;
  percent: number;
}) {
  return (
    <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-zinc-500">{label}</span>
        <span className="text-xs text-zinc-400">{percent}%</span>
      </div>
      <div className="mt-1 text-xl font-bold tabular-nums">
        {Math.round(total * 10) / 10}
        {unit}
        {target != null && (
          <span className="text-xs font-normal text-zinc-400"> / {target}{unit}</span>
        )}
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-1 text-xs text-zinc-500">{remaining}</div>
    </div>
  );
}

function FoodEntries({
  entries,
  busy,
  onDelete,
}: {
  entries: DailyFoodLogOut["entries"];
  busy: boolean;
  onDelete: (id: number) => void;
}) {
  if (entries.length === 0) {
    return <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500 dark:bg-zinc-950">No food logged for this day.</p>;
  }

  return (
    <div className="flex flex-col divide-y divide-zinc-100 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
      {entries.map((entry) => (
        <div key={entry.id} className="flex items-center justify-between gap-3 p-3">
          <div className="min-w-0">
            <div className="truncate font-medium">{entry.name}</div>
            <div className="text-xs text-zinc-500">
              {entry.grams}g · {entry.kcal} kcal · P {entry.protein_g}g · C {entry.carbs_g}g · F{" "}
              {entry.fat_g}g
            </div>
          </div>
          <Button
            variant="ghost"
            className="h-9 min-h-0 shrink-0 px-3 text-sm"
            disabled={busy}
            onClick={() => onDelete(entry.id)}
          >
            Delete
          </Button>
        </div>
      ))}
    </div>
  );
}

function ManualFoodForm({
  date,
  busy,
  onAdd,
}: {
  date: string;
  busy: boolean;
  onAdd: (entry: FoodLogIn) => void;
}) {
  const [draft, setDraft] = useState<ManualFoodDraft>(EMPTY_FOOD_DRAFT);
  const entry = draftToFoodLog(draft, date);

  const set = (key: keyof ManualFoodDraft, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  return (
    <form
      className="grid gap-3 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950"
      onSubmit={(event) => {
        event.preventDefault();
        if (!entry) return;
        onAdd(entry);
        setDraft(EMPTY_FOOD_DRAFT);
      }}
    >
      <div className="grid gap-3 md:grid-cols-[minmax(0,1.5fr)_repeat(5,minmax(0,1fr))]">
        <div>
          <Label>Name</Label>
          <Input value={draft.name} onChange={(event) => set("name", event.target.value)} />
        </div>
        <NumberInput label="Grams" value={draft.grams} onChange={(value) => set("grams", value)} />
        <NumberInput label="Kcal" value={draft.kcal} onChange={(value) => set("kcal", value)} />
        <NumberInput label="Protein" value={draft.protein_g} onChange={(value) => set("protein_g", value)} />
        <NumberInput label="Carbs" value={draft.carbs_g} onChange={(value) => set("carbs_g", value)} />
        <NumberInput label="Fat" value={draft.fat_g} onChange={(value) => set("fat_g", value)} />
      </div>
      <Button disabled={!entry || busy}>{busy ? "Adding..." : "Add food"}</Button>
    </form>
  );
}

function NumberInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Input
        type="number"
        min="0"
        step="0.1"
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
