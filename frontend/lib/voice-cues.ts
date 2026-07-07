import type { PlanExerciseOut } from "@/lib/api";
import { type CueLang, exerciseInstructions, movementLabel } from "@/lib/exercise-cues";

// The voice-over text can be read in English or Vietnamese. Vietnamese cue text
// lives alongside the English source in exercise-cues.ts so the on-screen guide
// and the spoken cue stay in sync — CoachLang is the same type, re-exported
// under the name the workout runner uses.
export type CoachLang = CueLang;

export function exerciseVoiceCue(
  pe: PlanExerciseOut,
  sets: number,
  lang: CoachLang = "en",
): string {
  const instructions = exerciseInstructions(pe.exercise, 3, lang);
  const label = movementLabel(pe.exercise.pattern, lang);
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

/** URL of the server-rendered audio for a cue — used to play and to pre-generate. */
export function ttsUrl(text: string, lang: CoachLang): string {
  return `/api/tts?lang=${lang}&text=${encodeURIComponent(text)}`;
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
