"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { Badge, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

const FOCUS_LABEL: Record<string, string> = {
  full_body: "Full Body",
  upper: "Upper",
  lower: "Lower",
  push: "Push",
  pull: "Pull",
  legs: "Legs",
  conditioning: "Conditioning",
};

function useActivePlan() {
  const plans = useQuery({
    queryKey: ["plans"],
    queryFn: async () => (await api.GET("/api/plans")).data ?? [],
  });
  const active = plans.data?.find((p) => p.is_active) ?? plans.data?.[0];
  const detail = useQuery({
    queryKey: ["plan", active?.id],
    enabled: active != null,
    queryFn: async () => {
      const { data } = await api.GET("/api/plans/{plan_id}", {
        params: { path: { plan_id: active!.id } },
      });
      return data ?? null;
    },
  });
  const coverage = useQuery({
    queryKey: ["plan-coverage", active?.id],
    enabled: active != null,
    queryFn: async () => {
      const { data } = await api.GET("/api/plans/{plan_id}/coverage", {
        params: { path: { plan_id: active!.id } },
      });
      return data ?? [];
    },
  });
  return {
    isLoading: plans.isLoading || detail.isLoading,
    plan: detail.data,
    coverage: coverage.data ?? [],
    hasAny: !!active,
  };
}

export default function PlanPage() {
  const { isLoading, plan, coverage, hasAny } = useActivePlan();
  const qc = useQueryClient();

  const nextWeek = useMutation({
    mutationFn: async () => {
      if (!plan) return;
      const { error } = await api.POST("/api/plans", {
        body: { goal: "shred", days_per_week: plan.days_per_week, week: plan.mesocycle_week + 1 },
      });
      if (error) throw new Error("Could not advance week");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plans"] });
      qc.invalidateQueries({ queryKey: ["plan-coverage"] });
    },
  });

  if (isLoading) return <p className="text-sm text-zinc-500">Loading…</p>;

  if (!hasAny || !plan) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold">Plan</h1>
        <Card className="flex flex-col gap-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">No plan yet.</p>
          <Link href="/plan/new">
            <Button className="w-full">Generate a plan</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold">{plan.name}</h1>
        </div>
        <Link href="/plan/new">
          <Button variant="ghost" className="px-3 text-sm">
            New
          </Button>
        </Link>
      </div>

      <Card className="flex items-center justify-between gap-2">
        <div className="flex flex-col">
          <span className="text-sm font-medium">Mesocycle week {plan.mesocycle_week}</span>
          <span className="text-xs text-zinc-500">
            Volume periodises (deload every 4th week) and exercises rotate each week.
          </span>
        </div>
        <Button
          className="h-9 min-h-0 px-3 text-sm"
          onClick={() => nextWeek.mutate()}
          disabled={nextWeek.isPending}
        >
          {nextWeek.isPending ? "…" : "Next week"}
        </Button>
      </Card>

      {coverage.length > 0 && (
        <Card className="flex flex-col gap-2">
          <span className="font-semibold">Weekly volume coverage</span>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {coverage.map((c) => (
              <div key={c.muscle} className="flex items-center justify-between text-sm">
                <span className="capitalize text-zinc-600 dark:text-zinc-400">{c.muscle}</span>
                <span className={c.met ? "text-emerald-600" : "text-amber-500"}>
                  {c.sets}/{c.target} {c.met ? "✓" : "↓"}
                </span>
              </div>
            ))}
          </div>
          <p className="text-xs text-zinc-400">credited sets/week (secondary muscles count ½)</p>
        </Card>
      )}

      <div className="flex flex-col gap-2">
        {plan.days.map((day) => (
          <Card key={day.id} className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold">
                Day {day.day_index} · {FOCUS_LABEL[day.focus] ?? day.focus}
              </span>
              <Link href={`/workout/${day.id}`}>
                <Button className="h-9 min-h-0 px-3 text-sm">Start</Button>
              </Link>
            </div>
            <ul className="flex flex-col divide-y divide-zinc-100 dark:divide-zinc-800">
              {day.exercises.map((pe) => (
                <li key={pe.id} className="flex items-center justify-between gap-2 py-2">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{pe.exercise.name}</span>
                    <span className="text-xs text-zinc-500">
                      {pe.is_conditioning
                        ? `${pe.sets} rounds · 40s work / 20s rest`
                        : `${pe.sets} × ${pe.target_reps_min}–${pe.target_reps_max} · ${pe.rest_seconds}s rest`}
                    </span>
                  </div>
                  {pe.is_conditioning && <Badge>conditioning</Badge>}
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  );
}
