"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { MovementCue } from "@/components/movement-cue";
import { PoseRepCounter } from "@/components/pose-rep-counter";
import { ConditioningTimer, RestTimer } from "@/components/rest-timer";
import { Badge, Button, Card, Input } from "@/components/ui";
import { trackConfigFor } from "@/lib/pose";
import {
  api,
  type ExerciseOut,
  type HistorySessionOut,
  type PlanDayOut,
  type PlanExerciseOut,
  type SuggestedTargetOut,
} from "@/lib/api";
import {
  exerciseInstructions,
  movementLabel,
  primaryMuscleText,
  warmupDrillGuide,
} from "@/lib/exercise-cues";
import {
  estimatedOneRm,
  formatHistoryDate,
  formatLastTime,
  topSet,
} from "@/lib/exercise-history";
import {
  buildSessionSummary,
  formatSessionNotes,
  type LoggedSetSummary,
} from "@/lib/session-summary";
import {
  COACH_STRINGS,
  type CoachLang,
  exerciseVoiceCue,
  pickCoachVoice,
  restCompleteCue,
  restStartedCue,
} from "@/lib/voice-cues";
import {
  readinessRecommendation,
  readinessVoiceCue,
  warmupForExercises,
  warmupVoiceCue,
  type Readiness,
} from "@/lib/workout-assist";
import type { SessionImpression } from "@/lib/workout-stats";

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
  const qc = useQueryClient();
  const voice = useVoiceCoach();
  const createdRef = useRef(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [targets, setTargets] = useState<Record<number, SuggestedTargetOut>>({});
  const [rest, setRest] = useState<{ key: number; seconds: number } | null>(null);
  const [readiness, setReadiness] = useState<Readiness>({ energy: 4, soreness: 2, sleep: 4 });
  const [loggedSets, setLoggedSets] = useState<LoggedSetSummary[]>([]);
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [impression, setImpression] = useState<SessionImpression | null>(null);
  const recommendation = readinessRecommendation(readiness);
  const warmup = warmupForExercises(day.exercises);
  const summary = buildSessionSummary(loggedSets);

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
        body: {
          notes: formatSessionNotes({ notes, tags, summary }),
          impression: impression ?? undefined,
        },
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exercise-history"] });
      qc.invalidateQueries({ queryKey: ["strength"] });
      router.push("/progress");
    },
  });

  const onSetLogged = (restSeconds: number, log: LoggedSetSummary) => {
    setLoggedSets((logs) => [
      ...logs.filter(
        (existing) =>
          !(existing.exerciseId === log.exerciseId && existing.setNumber === log.setNumber),
      ),
      log,
    ]);
    setRest((r) => ({ key: (r?.key ?? 0) + 1, seconds: restSeconds }));
    voice.speak(restStartedCue(restSeconds, voice.lang));
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

      <ReadinessPanel
        readiness={readiness}
        setReadiness={setReadiness}
        recommendation={recommendation}
        speak={voice.speak}
        lang={voice.lang}
      />

      <WarmupPanel drills={warmup} speak={voice.speak} lang={voice.lang} />

      {day.exercises.map((pe) => (
        <ExerciseBlock
          key={pe.id}
          pe={pe}
          target={targets[pe.exercise_id]}
          sessionId={sessionId}
          onSetLogged={onSetLogged}
          speak={voice.speak}
          voiceEnabled={voice.enabled}
          lang={voice.lang}
          setReduction={recommendation.setReduction}
          restBonus={recommendation.restBonus}
        />
      ))}

      <FinishWorkoutPanel
        summary={summary}
        tags={tags}
        setTags={setTags}
        notes={notes}
        setNotes={setNotes}
        impression={impression}
        setImpression={setImpression}
        onComplete={() => complete.mutate()}
        isPending={complete.isPending}
      />

      {rest && (
        <RestTimer
          key={rest.key}
          seconds={rest.seconds}
          onDismiss={() => setRest(null)}
          onComplete={() => voice.speak(restCompleteCue(voice.lang))}
        />
      )}
    </div>
  );
}

function ReadinessPanel({
  readiness,
  setReadiness,
  recommendation,
  speak,
  lang,
}: {
  readiness: Readiness;
  setReadiness: React.Dispatch<React.SetStateAction<Readiness>>;
  recommendation: ReturnType<typeof readinessRecommendation>;
  speak: (text: string, force?: boolean) => void;
  lang: CoachLang;
}) {
  return (
    <Card className="grid gap-4 xl:grid-cols-[1fr_260px]">
      <div className="grid gap-3 sm:grid-cols-3">
        <ReadinessScale
          label="Energy"
          value={readiness.energy}
          onChange={(energy) => setReadiness((r) => ({ ...r, energy }))}
        />
        <ReadinessScale
          label="Soreness"
          value={readiness.soreness}
          onChange={(soreness) => setReadiness((r) => ({ ...r, soreness }))}
        />
        <ReadinessScale
          label="Sleep"
          value={readiness.sleep}
          onChange={(sleep) => setReadiness((r) => ({ ...r, sleep }))}
        />
      </div>
      <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Today
            </div>
            <div className="mt-1 font-semibold">{recommendation.label}</div>
          </div>
          <div className="text-3xl font-bold tabular-nums">{recommendation.score}%</div>
        </div>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{recommendation.detail}</p>
        <Button
          variant="secondary"
          className="mt-3 h-9 min-h-0 w-full px-3 text-sm"
          onClick={() => speak(readinessVoiceCue(recommendation, lang), true)}
        >
          Read readiness
        </Button>
      </div>
    </Card>
  );
}

function ReadinessScale({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold">{label}</span>
        <span className="text-sm tabular-nums text-zinc-500">{value}/5</span>
      </div>
      <div className="grid grid-cols-5 gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            aria-label={`${label} ${n}`}
            onClick={() => onChange(n)}
            className={`h-9 rounded-md text-sm font-semibold ${
              n === value
                ? "bg-zinc-950 text-white dark:bg-zinc-50 dark:text-zinc-950"
                : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}

const WARMUP_UI: Record<
  CoachLang,
  {
    heading: string;
    title: string;
    play: string;
    steps: [string, string][];
    footer: string;
  }
> = {
  en: {
    heading: "Warm-up guide",
    title: "Raise, rehearse, ramp",
    play: "Play",
    steps: [
      ["Raise", "breathe and build heat"],
      ["Rehearse", "move through today's patterns"],
      ["Ramp", "one easy set before work"],
    ],
    footer: "Keep every drill easy. The goal is better positions, not fatigue.",
  },
  vi: {
    heading: "Hướng dẫn khởi động",
    title: "Làm nóng, tập thử, tăng dần",
    play: "Phát",
    steps: [
      ["Làm nóng", "thở và tăng nhiệt"],
      ["Tập thử", "đi qua các động tác hôm nay"],
      ["Tăng dần", "một hiệp nhẹ trước khi tập"],
    ],
    footer: "Giữ mọi bài tập nhẹ nhàng. Mục tiêu là tư thế tốt hơn, không phải mệt mỏi.",
  },
};

function WarmupPanel({
  drills,
  speak,
  lang,
}: {
  drills: string[];
  speak: (text: string, force?: boolean) => void;
  lang: CoachLang;
}) {
  const guides = drills.map((drill) => warmupDrillGuide(drill, lang));
  const ui = WARMUP_UI[lang];

  return (
    <Card className="grid gap-4 xl:grid-cols-[280px_1fr]">
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-xs font-medium uppercase text-zinc-500">{ui.heading}</div>
            <h2 className="mt-0.5 font-semibold">{ui.title}</h2>
          </div>
          <Button
            variant="secondary"
            className="h-9 min-h-0 px-3 text-sm"
            onClick={() => speak(warmupVoiceCue(drills, lang), true)}
          >
            {ui.play}
          </Button>
        </div>
        <div className="mt-4 grid gap-3">
          {ui.steps.map(([label, detail], index) => (
            <div key={label} className="grid grid-cols-[34px_1fr] gap-3">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  index === 0
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                    : index === 1
                      ? "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200"
                      : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200"
                }`}
              >
                {index + 1}
              </span>
              <div>
                <div className="text-sm font-semibold">{label}</div>
                <div className="text-xs text-zinc-500">{detail}</div>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">{ui.footer}</p>
      </div>
      <ol className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {guides.map((guide, index) => (
          <li
            key={`${guide.name}-${index}`}
            className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold">{guide.name}</span>
              <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-zinc-500 dark:bg-zinc-900">
                {guide.duration}
              </span>
            </div>
            <div className="my-3 grid grid-cols-[1fr_1fr_1fr] gap-1" aria-hidden="true">
              <span className="h-1.5 rounded-full bg-emerald-500" />
              <span className="h-1.5 rounded-full bg-sky-500" />
              <span className="h-1.5 rounded-full bg-amber-500" />
            </div>
            <p className="text-zinc-600 dark:text-zinc-400">{guide.intent}</p>
            <p className="mt-2 border-l-2 border-emerald-500 pl-2 font-medium text-zinc-800 dark:text-zinc-200">
              {guide.cue}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  );
}

const COACH_LANG_KEY = "homeshred.coachLang";

function useVoiceCoach() {
  const [enabled, setEnabled] = useState(false);
  const [supported] = useState(
    () =>
      typeof window !== "undefined" &&
      "speechSynthesis" in window &&
      "SpeechSynthesisUtterance" in window,
  );
  // The voice coach only renders client-side (the page shows a loading state
  // through hydration), so reading localStorage in the initializer is safe.
  const [lang, setLangState] = useState<CoachLang>(() => {
    if (typeof window === "undefined") return "en";
    return window.localStorage.getItem(COACH_LANG_KEY) === "vi" ? "vi" : "en";
  });
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const setLang = (next: CoachLang) => {
    setLangState(next);
    window.localStorage.setItem(COACH_LANG_KEY, next);
  };

  useEffect(() => {
    if (!supported) return;
    // getVoices() is often empty until the engine fires "voiceschanged".
    const loadVoice = () => {
      voiceRef.current = pickCoachVoice(window.speechSynthesis.getVoices());
    };
    loadVoice();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoice);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoice);
      window.speechSynthesis.cancel();
    };
  }, [supported]);

  // Fallback: the browser's own speech synthesis (quality varies by device).
  const speakBrowser = (text: string) => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    if (lang === "vi") {
      utterance.lang = "vi-VN";
    } else if (voiceRef.current) {
      utterance.voice = voiceRef.current;
      utterance.lang = voiceRef.current.lang;
    } else {
      utterance.lang = "en-US";
    }
    utterance.rate = 1;
    utterance.pitch = 1.05;
    utterance.volume = 1;
    window.speechSynthesis.speak(utterance);
  };

  const speak = (text: string, force = false) => {
    if ((!enabled && !force) || !text.trim()) return;
    window.speechSynthesis?.cancel();
    let audio = audioRef.current;
    if (!audio) {
      audio = new Audio();
      audioRef.current = audio;
    }
    audio.pause();
    // Prefer the server-side neural voice (consistent quality, real Vietnamese);
    // fall back to the browser engine if the endpoint is unavailable (TTS disabled,
    // voice model missing, or offline).
    audio.onerror = () => speakBrowser(text);
    audio.src = `/api/tts?lang=${lang}&text=${encodeURIComponent(text)}`;
    void audio.play().catch(() => speakBrowser(text));
  };

  const stop = () => {
    window.speechSynthesis?.cancel();
    audioRef.current?.pause();
  };

  return { enabled, setEnabled, supported, speak, stop, lang, setLang };
}

function VoiceCoachControls({ voice }: { voice: ReturnType<typeof useVoiceCoach> }) {
  const t = COACH_STRINGS[voice.lang];
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-zinc-200 bg-white p-2 dark:border-zinc-800 dark:bg-zinc-900">
      <Button
        className="h-9 min-h-0 px-3 text-sm"
        variant={voice.enabled ? "primary" : "secondary"}
        disabled={!voice.supported}
        onClick={() => {
          const next = !voice.enabled;
          voice.setEnabled(next);
          if (!next) voice.stop();
          if (next) setTimeout(() => voice.speak(COACH_STRINGS[voice.lang].enabled, true), 0);
        }}
      >
        {voice.enabled ? t.on : t.off}
      </Button>
      <Button
        className="h-9 min-h-0 px-3 text-sm"
        variant="ghost"
        disabled={!voice.supported}
        onClick={() => voice.speak(t.ready, true)}
      >
        {t.test}
      </Button>
      <div
        className="flex overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-700"
        role="group"
        aria-label="Cue language"
      >
        {(["en", "vi"] as const).map((code) => (
          <button
            key={code}
            type="button"
            onClick={() => voice.setLang(code)}
            className={`px-2.5 py-1.5 text-xs font-semibold uppercase transition-colors ${
              voice.lang === code
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "bg-transparent text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
            }`}
            aria-pressed={voice.lang === code}
          >
            {code === "en" ? "EN" : "VI"}
          </button>
        ))}
      </div>
      {!voice.supported && <span className="text-xs text-zinc-500">{t.notSupported}</span>}
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
  lang,
  setReduction,
  restBonus,
}: {
  pe: PlanExerciseOut;
  target?: SuggestedTargetOut;
  sessionId: number;
  onSetLogged: (rest: number, log: LoggedSetSummary) => void;
  speak: (text: string, force?: boolean) => void;
  voiceEnabled: boolean;
  lang: CoachLang;
  setReduction: number;
  restBonus: number;
}) {
  const [exercise, setExercise] = useState<ExerciseOut>(pe.exercise);
  const effectivePe: PlanExerciseOut = { ...pe, exercise_id: exercise.id, exercise };
  const sets = Math.max(1, (target?.sets ?? pe.sets) - setReduction);
  const repsDefault = target?.reps_min ?? pe.target_reps_min;

  // Per-exercise history — re-fetched when substituted (keyed on the live exercise id).
  const history = useQuery({
    queryKey: ["exercise-history", exercise.id],
    queryFn: async () => {
      const { data } = await api.GET("/api/exercises/{exercise_id}/history", {
        params: { path: { exercise_id: exercise.id }, query: { sessions: 3 } },
      });
      return data ?? null;
    },
  });
  const lastSession = history.data?.sessions[0] ?? null;
  const lastTopWeight = lastSession ? (topSet(lastSession)?.weightKg ?? null) : null;
  // Fall back to last session's top-set weight when progression gives no suggestion.
  const weightDefault = target?.suggested_weight_kg ?? lastTopWeight;
  const instructions = exerciseInstructions(exercise, 3, lang);
  const restSeconds = pe.rest_seconds + restBonus;

  if (pe.is_conditioning) {
    return (
      <Card className="flex flex-col gap-4">
        <div className="grid gap-4 md:grid-cols-[280px_1fr]">
          <MovementCue pattern={exercise.pattern} lang={lang} />
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{exercise.name}</span>
              <Badge>conditioning</Badge>
              <Badge>{movementLabel(exercise.pattern, lang)}</Badge>
              {setReduction > 0 && <Badge>adjusted</Badge>}
              <Button
                variant="secondary"
                className="h-8 min-h-0 px-2 text-xs"
                onClick={() => speak(exerciseVoiceCue(effectivePe, sets, lang), true)}
              >
                Play cues
              </Button>
            </div>
            <p className="text-sm text-zinc-500">{primaryMuscleText(exercise)}</p>
            <InstructionList instructions={instructions} />
            <HistoryPanel data={history.data} isLoading={history.isLoading} />
            <SubstitutionPanel current={exercise} onSelect={setExercise} />
          </div>
        </div>
        <ConditioningTimer rounds={sets} />
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-4">
      <div className="grid gap-4 md:grid-cols-[280px_1fr]">
        <MovementCue pattern={exercise.pattern} lang={lang} />
        <div className="flex flex-col gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{exercise.name}</span>
              <Badge>{movementLabel(exercise.pattern, lang)}</Badge>
              {voiceEnabled && <Badge>voice ready</Badge>}
              {setReduction > 0 && <Badge>adjusted</Badge>}
              <Button
                variant="secondary"
                className="h-8 min-h-0 px-2 text-xs"
                onClick={() => speak(exerciseVoiceCue(effectivePe, sets, lang), true)}
              >
                Play cues
              </Button>
            </div>
            <div className="mt-1 text-xs text-zinc-500">
              {sets} sets · {pe.target_reps_min}-{pe.target_reps_max} reps · {restSeconds}s rest ·{" "}
              {primaryMuscleText(exercise)}
            </div>
          </div>
          <InstructionList instructions={instructions} />
          <HistoryPanel data={history.data} isLoading={history.isLoading} />
          <SubstitutionPanel current={exercise} onSelect={setExercise} />
        </div>
      </div>

      <div className="flex flex-col gap-2 rounded-lg border border-zinc-100 bg-zinc-50 p-2 dark:border-zinc-800 dark:bg-zinc-950">
        {Array.from({ length: sets }, (_, i) => (
          <SetRow
            key={i}
            setNumber={i + 1}
            exercise={exercise}
            sessionId={sessionId}
            restSeconds={restSeconds}
            defaultReps={repsDefault}
            defaultWeight={weightDefault}
            onLogged={onSetLogged}
          />
        ))}
      </div>
    </Card>
  );
}

function HistoryPanel({
  data,
  isLoading,
}: {
  data: { sessions: HistorySessionOut[] } | null | undefined;
  isLoading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const sessions = data?.sessions ?? [];
  const last = sessions[0];

  return (
    <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Last time
          </div>
          <div className="truncate text-sm text-zinc-600 dark:text-zinc-400">
            {isLoading
              ? "Loading history…"
              : last
                ? formatLastTime(last)
                : "No history yet — first time logged here."}
          </div>
        </div>
        {sessions.length > 0 && (
          <Button
            type="button"
            variant="secondary"
            className="h-9 min-h-0 px-3 text-sm"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? "Hide" : "History"}
          </Button>
        )}
      </div>
      {open && (
        <ol className="mt-3 grid gap-2">
          {sessions.map((session) => {
            const top = topSet(session);
            const e1rm = top ? estimatedOneRm(top.reps, top.weightKg) : null;
            return (
              <li
                key={session.session_id}
                className="rounded-lg border border-zinc-200 bg-white p-2 text-sm dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{formatHistoryDate(session.date)}</span>
                  {e1rm != null && (
                    <span className="text-xs text-zinc-500">est. 1RM {e1rm} kg</span>
                  )}
                </div>
                <div className="mt-1 text-zinc-600 dark:text-zinc-400">
                  {session.sets
                    .map((set) =>
                      set.weight_kg != null && Number(set.weight_kg) > 0
                        ? `${set.reps}×${Number(set.weight_kg)}kg`
                        : `${set.reps} reps`,
                    )
                    .join(" · ")}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

function SubstitutionPanel({
  current,
  onSelect,
}: {
  current: ExerciseOut;
  onSelect: (exercise: ExerciseOut) => void;
}) {
  const [open, setOpen] = useState(false);
  const alternatives = useQuery({
    queryKey: ["exercise-substitutions", current.pattern],
    enabled: open && current.pattern != null,
    queryFn: async () => {
      const { data } = await api.GET("/api/exercises", {
        params: { query: { pattern: current.pattern } },
      });
      return (data ?? []).filter((exercise) => exercise.id !== current.id).slice(0, 5);
    },
  });

  return (
    <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Substitute
          </div>
          <div className="text-sm text-zinc-600 dark:text-zinc-400">
            Same pattern if this movement does not fit today.
          </div>
        </div>
        <Button
          type="button"
          variant="secondary"
          className="h-9 min-h-0 px-3 text-sm"
          onClick={() => setOpen((value) => !value)}
          disabled={current.pattern == null}
        >
          {open ? "Hide" : "Swap"}
        </Button>
      </div>
      {open && (
        <div className="mt-3 grid gap-2">
          {alternatives.isLoading ? (
            <p className="text-sm text-zinc-500">Loading alternatives...</p>
          ) : alternatives.data?.length ? (
            alternatives.data.map((exercise) => (
              <button
                key={exercise.id}
                type="button"
                onClick={() => {
                  onSelect(exercise);
                  setOpen(false);
                }}
                className="rounded-lg border border-zinc-200 bg-white p-3 text-left hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="font-medium">{exercise.name}</div>
                <div className="text-xs capitalize text-zinc-500">
                  {exercise.equipment.replace("_", " ")} · {primaryMuscleText(exercise)}
                </div>
              </button>
            ))
          ) : (
            <p className="text-sm text-zinc-500">No alternatives found.</p>
          )}
        </div>
      )}
    </div>
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
  exercise,
  sessionId,
  restSeconds,
  defaultReps,
  defaultWeight,
  onLogged,
}: {
  setNumber: number;
  exercise: ExerciseOut;
  sessionId: number;
  restSeconds: number;
  defaultReps: number;
  defaultWeight: number | null;
  onLogged: (rest: number, log: LoggedSetSummary) => void;
}) {
  const [reps, setReps] = useState<number>(defaultReps);
  const [weight, setWeight] = useState<string>(defaultWeight != null ? String(defaultWeight) : "");
  const [rpe, setRpe] = useState<string>("");
  const [done, setDone] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const repConfig = trackConfigFor(exercise.pattern);
  const onCameraRep = useCallback((total: number) => setReps(total), []);
  // History-based prefill can arrive after mount; apply it once while still untouched.
  const prefilledRef = useRef(false);
  useEffect(() => {
    if (!prefilledRef.current && defaultWeight != null && weight === "") {
      prefilledRef.current = true;
      setWeight(String(defaultWeight));
    }
  }, [defaultWeight, weight]);

  const log = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/sessions/{session_id}/sets", {
        params: { path: { session_id: sessionId } },
        body: {
          exercise_id: exercise.id,
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
      onLogged(restSeconds, {
        exerciseId: exercise.id,
        exerciseName: exercise.name,
        setNumber,
        reps,
        weightKg: weight === "" ? null : Number(weight),
        rpe: rpe === "" ? null : Number(rpe),
      });
    },
  });

  return (
    <div className="flex flex-col gap-2">
    <div className="grid gap-2 rounded-lg bg-white p-2 dark:bg-zinc-900 sm:grid-cols-[56px_180px_1fr_84px_52px] sm:items-center">
      <span className="text-sm font-semibold text-zinc-500">Set {setNumber}</span>
      <div className="grid grid-cols-[44px_1fr_44px] items-center gap-1">
        <Button
          type="button"
          variant="secondary"
          className="h-11 min-h-0 px-0 text-xl"
          onClick={() => setReps((r) => Math.max(0, r - 1))}
        >
          -
        </Button>
        <button
          type="button"
          aria-label="tap to count rep"
          onClick={() => setReps((r) => r + 1)}
          className="flex h-14 flex-col items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 font-bold tabular-nums dark:border-zinc-800 dark:bg-zinc-950"
        >
          <span className="text-2xl">{reps}</span>
          <span className="text-[10px] font-medium text-zinc-500">tap rep</span>
        </button>
        <Button
          type="button"
          className="h-11 min-h-0 px-0 text-xl"
          onClick={() => setReps((r) => r + 1)}
        >
          +
        </Button>
      </div>
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
        className="h-10 min-h-0"
        value={rpe}
        onChange={(e) => setRpe(e.target.value)}
      />
      <Button
        className="h-10 min-h-0 px-0"
        variant={done ? "secondary" : "primary"}
        disabled={log.isPending}
        onClick={() => log.mutate()}
      >
        {done ? "✓" : "Log"}
      </Button>
    </div>
      {repConfig && (
        <button
          type="button"
          onClick={() => setCameraOpen((open) => !open)}
          className="self-start text-xs font-medium text-emerald-600 hover:underline"
        >
          {cameraOpen ? "Hide camera counter" : "📷 Count reps with camera"}
        </button>
      )}
      {repConfig && cameraOpen && (
        <PoseRepCounter config={repConfig} onRep={onCameraRep} onClose={() => setCameraOpen(false)} />
      )}
    </div>
  );
}

const TAGS = ["felt strong", "low energy", "joint pain", "rushed", "great pump", "bad sleep"];

const IMPRESSIONS: { value: SessionImpression; emoji: string; label: string }[] = [
  { value: "good", emoji: "🙂", label: "Good" },
  { value: "neutral", emoji: "😐", label: "Okay" },
  { value: "bad", emoji: "😣", label: "Rough" },
];

function FinishWorkoutPanel({
  summary,
  tags,
  setTags,
  notes,
  setNotes,
  impression,
  setImpression,
  onComplete,
  isPending,
}: {
  summary: ReturnType<typeof buildSessionSummary>;
  tags: string[];
  setTags: React.Dispatch<React.SetStateAction<string[]>>;
  notes: string;
  setNotes: (notes: string) => void;
  impression: SessionImpression | null;
  setImpression: React.Dispatch<React.SetStateAction<SessionImpression | null>>;
  onComplete: () => void;
  isPending: boolean;
}) {
  const toggleTag = (tag: string) =>
    setTags((current) =>
      current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag],
    );

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <h2 className="font-semibold">Finish summary</h2>
        <p className="text-sm text-zinc-500">Review the work and add notes before saving.</p>
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        <SummaryTile label="Sets" value={summary.totalSets} />
        <SummaryTile label="Reps" value={summary.totalReps} />
        <SummaryTile label="Weighted" value={summary.weightedSets} />
        <SummaryTile label="Avg RPE" value={summary.averageRpe ?? "—"} />
      </div>
      {summary.hardestExercise && (
        <div className="rounded-lg bg-zinc-50 p-3 text-sm dark:bg-zinc-950">
          Hardest by reps: <span className="font-semibold">{summary.hardestExercise}</span>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {TAGS.map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => toggleTag(tag)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              tags.includes(tag)
                ? "bg-zinc-950 text-white dark:bg-zinc-50 dark:text-zinc-950"
                : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {tag}
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          How did it feel?
        </span>
        <div className="flex gap-2">
          {IMPRESSIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() =>
                setImpression((current) => (current === opt.value ? null : opt.value))
              }
              aria-pressed={impression === opt.value}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium ${
                impression === opt.value
                  ? "border-emerald-500 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "border-zinc-200 bg-white text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
              }`}
            >
              <span className="text-base">{opt.emoji}</span>
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <textarea
        className="min-h-24 rounded-lg border border-zinc-300 bg-white p-3 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 dark:border-zinc-700 dark:bg-zinc-950"
        placeholder="Session notes"
        value={notes}
        maxLength={1200}
        onChange={(event) => setNotes(event.target.value)}
      />
      <Button onClick={onComplete} disabled={isPending}>
        {isPending ? "Finishing..." : "Complete workout"}
      </Button>
    </Card>
  );
}

function SummaryTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
