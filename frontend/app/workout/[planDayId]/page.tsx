"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ConditioningTimer, RestTimer } from "@/components/rest-timer";
import { Badge, Button, Card, Input } from "@/components/ui";
import { api, type PlanDayOut, type PlanExerciseOut, type SuggestedTargetOut } from "@/lib/api";

export default function WorkoutPage() {
  const params = useParams<{ planDayId: string }>();
  const planDayId = Number(params.planDayId);

  // Find the plan day (with exercise details) inside the active plan.
  const { data: day, isLoading } = useQuery({
    queryKey: ["plan-day", planDayId],
    queryFn: async () => {
      const list = (await api.GET("/api/plans")).data ?? [];
      const active = list.find((p) => p.is_active) ?? list[0];
      if (!active) return null;
      const { data } = await api.GET("/api/plans/{plan_id}", {
        params: { path: { plan_id: active.id } },
      });
      return data?.days.find((d) => d.id === planDayId) ?? null;
    },
  });

  if (isLoading) return <p className="text-sm text-zinc-500">Loading…</p>;
  if (!day) return <p className="text-sm text-zinc-500">Workout not found.</p>;
  return <Runner day={day} />;
}

function Runner({ day }: { day: PlanDayOut }) {
  const router = useRouter();
  const createdRef = useRef(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [targets, setTargets] = useState<Record<number, SuggestedTargetOut>>({});
  const [rest, setRest] = useState<{ key: number; seconds: number } | null>(null);

  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/sessions", {
        body: { plan_day_id: day.id },
      });
      if (error || !data) throw new Error("Could not start session");
      return data;
    },
    onSuccess: (data) => {
      setSessionId(data.id);
      const map: Record<number, SuggestedTargetOut> = {};
      for (const t of data.suggested_targets) map[t.exercise_id] = t;
      setTargets(map);
    },
  });

  useEffect(() => {
    if (!createdRef.current) {
      createdRef.current = true;
      create.mutate();
    }
  }, [create]);

  const complete = useMutation({
    mutationFn: async () => {
      if (sessionId == null) return;
      await api.PATCH("/api/sessions/{session_id}/complete", {
        params: { path: { session_id: sessionId } },
      });
    },
    onSuccess: () => router.push("/progress"),
  });

  const onSetLogged = (restSeconds: number) =>
    setRest((r) => ({ key: (r?.key ?? 0) + 1, seconds: restSeconds }));

  if (create.isPending || sessionId == null) {
    return <p className="text-sm text-zinc-500">Starting session…</p>;
  }

  return (
    <div className="flex flex-col gap-4 pb-28">
      <h1 className="text-xl font-bold">Day {day.day_index} workout</h1>

      {day.exercises.map((pe) => (
        <ExerciseBlock
          key={pe.id}
          pe={pe}
          target={targets[pe.exercise_id]}
          sessionId={sessionId}
          onSetLogged={onSetLogged}
        />
      ))}

      <Button onClick={() => complete.mutate()} disabled={complete.isPending}>
        {complete.isPending ? "Finishing…" : "Complete workout"}
      </Button>

      {rest && (
        <RestTimer key={rest.key} seconds={rest.seconds} onDismiss={() => setRest(null)} />
      )}
    </div>
  );
}

function ExerciseBlock({
  pe,
  target,
  sessionId,
  onSetLogged,
}: {
  pe: PlanExerciseOut;
  target?: SuggestedTargetOut;
  sessionId: number;
  onSetLogged: (rest: number) => void;
}) {
  const sets = target?.sets ?? pe.sets;
  const repsDefault = target?.reps_min ?? pe.target_reps_min;
  const weightDefault = target?.suggested_weight_kg ?? null;

  if (pe.is_conditioning) {
    return (
      <Card className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="font-medium">{pe.exercise.name}</span>
          <Badge>conditioning</Badge>
        </div>
        <ConditioningTimer rounds={sets} />
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-medium">{pe.exercise.name}</span>
        <span className="text-xs text-zinc-500">
          {pe.target_reps_min}–{pe.target_reps_max} reps · {pe.rest_seconds}s
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {Array.from({ length: sets }, (_, i) => (
          <SetRow
            key={i}
            setNumber={i + 1}
            exerciseId={pe.exercise_id}
            sessionId={sessionId}
            restSeconds={pe.rest_seconds}
            defaultReps={repsDefault}
            defaultWeight={weightDefault}
            onLogged={onSetLogged}
          />
        ))}
      </div>
    </Card>
  );
}

function SetRow({
  setNumber,
  exerciseId,
  sessionId,
  restSeconds,
  defaultReps,
  defaultWeight,
  onLogged,
}: {
  setNumber: number;
  exerciseId: number;
  sessionId: number;
  restSeconds: number;
  defaultReps: number;
  defaultWeight: number | null;
  onLogged: (rest: number) => void;
}) {
  const [reps, setReps] = useState<number>(defaultReps);
  const [weight, setWeight] = useState<string>(defaultWeight != null ? String(defaultWeight) : "");
  const [done, setDone] = useState(false);

  const log = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/sessions/{session_id}/sets", {
        params: { path: { session_id: sessionId } },
        body: {
          exercise_id: exerciseId,
          set_number: setNumber,
          reps,
          weight_kg: weight === "" ? null : Number(weight),
        },
      });
      if (error) throw new Error("log failed");
    },
    onSuccess: () => {
      setDone(true);
      onLogged(restSeconds);
    },
  });

  return (
    <div className="flex items-center gap-2">
      <span className="w-6 text-sm text-zinc-500">{setNumber}</span>
      <Input
        type="number"
        aria-label="reps"
        className="h-10 min-h-0"
        value={reps}
        onChange={(e) => setReps(Number(e.target.value))}
      />
      <Input
        type="number"
        step="0.5"
        aria-label="weight"
        placeholder="kg"
        className="h-10 min-h-0"
        value={weight}
        onChange={(e) => setWeight(e.target.value)}
      />
      <Button
        className="h-10 min-h-0 w-12 px-0"
        variant={done ? "secondary" : "primary"}
        disabled={log.isPending}
        onClick={() => log.mutate()}
      >
        {done ? "✓" : "✓"}
      </Button>
    </div>
  );
}
