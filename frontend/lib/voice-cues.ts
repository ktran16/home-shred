import type { ExerciseOut, PlanExerciseOut } from "@/lib/api";
import { exerciseInstructions, movementLabel } from "@/lib/exercise-cues";

// The voice-over text can be read in English or Vietnamese. The synthesized
// voice itself stays whatever the browser picks (typically English) — only the
// wording changes.
export type CoachLang = "en" | "vi";

type Pattern = NonNullable<ExerciseOut["pattern"]>;

const VI_PATTERN_LABELS: Record<Pattern, string> = {
  horizontal_push: "Đẩy ngang",
  vertical_push: "Đẩy qua đầu",
  horizontal_pull: "Kéo ngang",
  vertical_pull: "Kéo xà",
  squat: "Squat",
  hinge: "Gập hông",
  core: "Cơ lõi",
  conditioning: "Thể lực",
};

// Vietnamese equivalents of the pattern coaching cues in exercise-cues.ts.
// Seeded exercise instructions are English-only, so for Vietnamese we speak the
// pattern-based cues instead.
const VI_PATTERN_CUES: Record<Pattern, string[]> = {
  horizontal_push: ["Siết bụng, hạ sườn.", "Hạ người có kiểm soát.", "Đẩy mạnh khỏi sàn."],
  vertical_push: ["Xếp sườn trên hông.", "Đẩy thẳng qua đầu.", "Kết thúc với tay sát tai."],
  horizontal_pull: ["Gập người và siết cơ.", "Kéo khuỷu tay qua sườn.", "Hạ xuống, không xoay người."],
  vertical_pull: ["Bắt đầu từ tư thế treo thẳng tay.", "Kéo ngực về phía xà.", "Hạ đến khi tay thẳng."],
  squat: ["Siết cơ trước khi hạ.", "Đầu gối theo hướng mũi chân.", "Đứng thẳng qua giữa bàn chân."],
  hinge: ["Đẩy hông ra sau.", "Giữ lưng thẳng dài.", "Siết mông để đứng lên."],
  core: ["Khóa sườn và xương chậu.", "Di chuyển chậm rãi.", "Dừng trước khi sai tư thế."],
  conditioning: ["Giữ độ nảy.", "Thở đều.", "Nhanh nhưng giữ nhịp chuẩn."],
};

function voiceMovementLabel(pattern: ExerciseOut["pattern"], lang: CoachLang): string {
  if (lang === "vi") return pattern ? VI_PATTERN_LABELS[pattern] : "Sức mạnh";
  return movementLabel(pattern);
}

function voiceInstructions(exercise: ExerciseOut, lang: CoachLang, limit = 3): string[] {
  if (lang === "vi") {
    return exercise.pattern ? VI_PATTERN_CUES[exercise.pattern].slice(0, limit) : [];
  }
  return exerciseInstructions(exercise, limit);
}

export function exerciseVoiceCue(
  pe: PlanExerciseOut,
  sets: number,
  lang: CoachLang = "en",
): string {
  const instructions = voiceInstructions(pe.exercise, lang, 3);
  const label = voiceMovementLabel(pe.exercise.pattern, lang);
  if (lang === "vi") {
    const prescription = pe.is_conditioning
      ? `${sets} hiệp. Tập 40 giây, nghỉ 20 giây.`
      : `${sets} hiệp. Mục tiêu ${pe.target_reps_min} đến ${pe.target_reps_max} lần. Nghỉ ${pe.rest_seconds} giây.`;
    const cues = instructions.length > 0 ? `Lưu ý. ${instructions.join(" ")}` : "";
    return `${pe.exercise.name}. ${label}. ${prescription} ${cues}`.trim();
  }
  const prescription = pe.is_conditioning
    ? `${sets} rounds. Work for 40 seconds, then rest for 20 seconds.`
    : `${sets} sets. Target ${pe.target_reps_min} to ${pe.target_reps_max} reps. Rest ${pe.rest_seconds} seconds.`;
  const cues = instructions.length > 0 ? `Cues. ${instructions.join(" ")}` : "";
  return `${pe.exercise.name}. ${label}. ${prescription} ${cues}`.trim();
}

export function restStartedCue(seconds: number, lang: CoachLang = "en"): string {
  return lang === "vi"
    ? `Đã ghi hiệp. Nghỉ ${seconds} giây.`
    : `Set logged. Rest ${seconds} seconds.`;
}

export function restCompleteCue(lang: CoachLang = "en"): string {
  return lang === "vi"
    ? "Hết giờ nghỉ. Bắt đầu hiệp tiếp theo."
    : "Rest complete. Start your next set.";
}

// UI labels + spoken confirmations for the voice-coach widget.
export const COACH_STRINGS: Record<
  CoachLang,
  { enabled: string; ready: string; on: string; off: string; test: string; notSupported: string }
> = {
  en: {
    enabled: "Voice coach enabled.",
    ready: "Voice coach ready.",
    on: "Voice on",
    off: "Voice off",
    test: "Test",
    notSupported: "Not supported",
  },
  vi: {
    enabled: "Đã bật trợ lý giọng nói.",
    ready: "Trợ lý giọng nói sẵn sàng.",
    on: "Bật giọng",
    off: "Tắt giọng",
    test: "Thử",
    notSupported: "Không hỗ trợ",
  },
};

// rationale: the default SpeechSynthesis voice is usually a low-quality robotic
// formant voice. Modern OS/browsers ship far more natural neural voices (Apple
// "Samantha", Microsoft "... (Natural)" / "Online", Google) — pick the best
// available English one so the coach sounds human instead of robotic.
const VOICE_PREFERENCE: readonly string[] = [
  "natural", // Microsoft neural voices, e.g. "Microsoft Aria Online (Natural)"
  "neural",
  "premium",
  "enhanced",
  "google", // "Google US English"
  "samantha", // Apple en-US default, far better than the formant fallback
  "ava",
  "allison",
  "serena",
  "karen",
  "moira",
  "daniel",
];

export function pickCoachVoice(
  voices: SpeechSynthesisVoice[],
): SpeechSynthesisVoice | null {
  if (voices.length === 0) return null;
  const english = voices.filter((v) => v.lang?.toLowerCase().startsWith("en"));
  const pool = english.length > 0 ? english : voices;

  // Prefer voices whose name matches our quality ranking, earliest match wins.
  for (const token of VOICE_PREFERENCE) {
    const hit = pool.find((v) => v.name.toLowerCase().includes(token));
    if (hit) return hit;
  }
  // Otherwise prefer a network/neural ("non-local") voice, then en-US, then any.
  return (
    pool.find((v) => !v.localService) ??
    pool.find((v) => v.lang?.toLowerCase() === "en-us") ??
    pool[0]
  );
}
