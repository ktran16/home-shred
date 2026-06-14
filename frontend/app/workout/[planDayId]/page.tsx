"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { MovementCue } from "@/components/movement-cue";
import { ConditioningTimer, RestTimer } from "@/components/rest-timer";
import { Badge, Button, Card, Input } from "@/components/ui";
import { api, type PlanDayOut, type PlanExerciseOut, type SuggestedTargetOut } from "@/lib/api";
import { exerciseInstructions, movementLabel, primaryMuscleText } from "@/lib/exercise-cues";
import { exerciseVoiceCue, restCompleteCue, restStartedCue } from "@/lib/voice-cues";

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
  const voice = useVoiceCoach();
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

  const onSetLogged = (restSeconds: number) => {
    setRest((r) => ({ key: (r?.key ?? 0) + 1, seconds: restSeconds }));
    voice.speak(restStartedCue(restSeconds));
  };

  if (create.isPending || sessionId == null) {
    return <p className="text-sm text-zinc-500">Starting session…</p>;
  }

  return (
    <div className="flex flex-col gap-4 pb-28">
      <div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Day {day.day_index} workout</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Follow the cue, log each set, then use the rest timer.
            </p>
          </div>
          <VoiceCoachControls voice={voice} />
        </div>
      </div>

      {day.exercises.map((pe) => (
        <ExerciseBlock
          key={pe.id}
          pe={pe}
          target={targets[pe.exercise_id]}
          sessionId={sessionId}
          onSetLogged={onSetLogged}
          speak={voice.speak}
          voiceEnabled={voice.enabled}
        />
      ))}

      <Button onClick={() => complete.mutate()} disabled={complete.isPending}>
        {complete.isPending ? "Finishing…" : "Complete workout"}
      </Button>

      {rest && (
        <RestTimer
          key={rest.key}
          seconds={rest.seconds}
          onDismiss={() => setRest(null)}
          onComplete={() => voice.speak(restCompleteCue())}
        />
      )}
    </div>
  );
}

function useVoiceCoach() {
  const [enabled, setEnabled] = useState(false);
  const [supported] = useState(
    () =>
      typeof window !== "undefined" &&
      "speechSynthesis" in window &&
      "SpeechSynthesisUtterance" in window,
  );

  useEffect(() => {
    return () => window.speechSynthesis?.cancel();
  }, []);

  const speak = (text: string, force = false) => {
    if ((!enabled && !force) || !supported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  };

  const stop = () => window.speechSynthesis?.cancel();

  return { enabled, setEnabled, supported, speak, stop };
}

function VoiceCoachControls({ voice }: { voice: ReturnType<typeof useVoiceCoach> }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white p-2 dark:border-zinc-800 dark:bg-zinc-900">
      <Button
        className="h-9 min-h-0 px-3 text-sm"
        variant={voice.enabled ? "primary" : "secondary"}
        disabled={!voice.supported}
        onClick={() => {
          const next = !voice.enabled;
          voice.setEnabled(next);
          if (!next) voice.stop();
          if (next) setTimeout(() => voice.speak("Voice coach enabled.", true), 0);
        }}
      >
        {voice.enabled ? "Voice on" : "Voice off"}
      </Button>
      <Button
        className="h-9 min-h-0 px-3 text-sm"
        variant="ghost"
        disabled={!voice.supported}
        onClick={() => voice.speak("Voice coach ready.", true)}
      >
        Test
      </Button>
      {!voice.supported && <span className="text-xs text-zinc-500">Not supported</span>}
    </div>
  );
}

function ExerciseBlock({
  pe,
  target,
  sessionId,
  onSetLogged,
  speak,
  voiceEnabled,
}: {
  pe: PlanExerciseOut;
  target?: SuggestedTargetOut;
  sessionId: number;
  onSetLogged: (rest: number) => void;
  speak: (text: string, force?: boolean) => void;
  voiceEnabled: boolean;
}) {
  const sets = target?.sets ?? pe.sets;
  const repsDefault = target?.reps_min ?? pe.target_reps_min;
  const weightDefault = target?.suggested_weight_kg ?? null;
  const instructions = exerciseInstructions(pe.exercise);

  if (pe.is_conditioning) {
    return (
      <Card className="flex flex-col gap-4">
        <div className="grid gap-4 md:grid-cols-[180px_1fr]">
          <MovementCue pattern={pe.exercise.pattern} />
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{pe.exercise.name}</span>
              <Badge>conditioning</Badge>
              <Badge>{movementLabel(pe.exercise.pattern)}</Badge>
              <Button
                variant="secondary"
                className="h-8 min-h-0 px-2 text-xs"
                onClick={() => speak(exerciseVoiceCue(pe, sets), true)}
              >
                Play cues
              </Button>
            </div>
            <p className="text-sm text-zinc-500">{primaryMuscleText(pe.exercise)}</p>
            <InstructionList instructions={instructions} />
          </div>
        </div>
        <ConditioningTimer rounds={sets} />
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-4">
      <div className="grid gap-4 md:grid-cols-[180px_1fr]">
        <MovementCue pattern={pe.exercise.pattern} />
        <div className="flex flex-col gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{pe.exercise.name}</span>
              <Badge>{movementLabel(pe.exercise.pattern)}</Badge>
              {voiceEnabled && <Badge>voice ready</Badge>}
              <Button
                variant="secondary"
                className="h-8 min-h-0 px-2 text-xs"
                onClick={() => speak(exerciseVoiceCue(pe, sets), true)}
              >
                Play cues
              </Button>
            </div>
            <div className="mt-1 text-xs text-zinc-500">
              {pe.target_reps_min}-{pe.target_reps_max} reps · {pe.rest_seconds}s rest ·{" "}
              {primaryMuscleText(pe.exercise)}
            </div>
          </div>
          <InstructionList instructions={instructions} />
        </div>
      </div>

      <div className="flex flex-col gap-2 rounded-lg border border-zinc-100 bg-zinc-50 p-2 dark:border-zinc-800 dark:bg-zinc-950">
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

function InstructionList({ instructions }: { instructions: string[] }) {
  if (instructions.length === 0) return null;
  return (
    <ol className="grid gap-2">
      {instructions.map((instruction, index) => (
        <li key={`${instruction}-${index}`} className="grid grid-cols-[24px_1fr] gap-2 text-sm">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-100 text-xs font-semibold text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
            {index + 1}
          </span>
          <span className="text-zinc-700 dark:text-zinc-300">{instruction}</span>
        </li>
      ))}
    </ol>
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
  const [rpe, setRpe] = useState<string>("");
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
          rpe: rpe === "" ? null : Number(rpe),
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
    <div className="grid grid-cols-[24px_1fr_1fr_74px_48px] items-center gap-2">
      <span className="text-sm font-medium text-zinc-500">{setNumber}</span>
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
      <Input
        type="number"
        step="0.5"
        min="1"
        max="10"
        aria-label="rpe"
        placeholder="RPE"
        className="h-10 min-h-0 w-16"
        value={rpe}
        onChange={(e) => setRpe(e.target.value)}
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
