import type { PlanExerciseOut } from "@/lib/api";
import { warmupDrillGuide } from "@/lib/exercise-cues";
import type { CoachLang } from "@/lib/voice-cues";

type Pattern = NonNullable<PlanExerciseOut["exercise"]["pattern"]>;

export type Readiness = {
  energy: number;
  soreness: number;
  sleep: number;
};

export type ReadinessRecommendation = {
  score: number;
  label: string;
  detail: string;
  setReduction: number;
  restBonus: number;
};

const WARMUP_BY_PATTERN: Record<Pattern, string[]> = {
  horizontal_push: ["Scapular push-ups", "Incline push-up ramp sets"],
  vertical_push: ["Arm circles", "Light dumbbell press ramp sets"],
  horizontal_pull: ["Hip hinge holds", "Light one-arm row ramp sets"],
  vertical_pull: ["Dead hangs", "Scapular pull-ups"],
  squat: ["Bodyweight squats", "Reverse lunges"],
  hinge: ["Hip hinges", "Glute bridges"],
  core: ["Dead bugs", "Plank breathing"],
  conditioning: ["Marching high knees", "Easy mountain climbers"],
};

export function readinessRecommendation(readiness: Readiness): ReadinessRecommendation {
  const score = Math.round(((readiness.energy + readiness.sleep + (6 - readiness.soreness)) / 15) * 100);
  if (score < 45) {
    return {
      score,
      label: "Recovery day",
      detail: "Reduce volume and take longer rests today.",
      setReduction: 2,
      restBonus: 30,
    };
  }
  if (score < 70) {
    return {
      score,
      label: "Moderate readiness",
      detail: "Trim one set from each exercise and add a little rest.",
      setReduction: 1,
      restBonus: 15,
    };
  }
  return {
    score,
    label: "Ready",
    detail: "Run the planned session as written.",
    setReduction: 0,
    restBonus: 0,
  };
}

export function warmupForExercises(exercises: PlanExerciseOut[]): string[] {
  const patterns = new Set<Pattern>();
  for (const pe of exercises) {
    if (pe.exercise.pattern) patterns.add(pe.exercise.pattern);
  }

  const drills: string[] = ["Nasal breathing reset"];
  for (const pattern of patterns) {
    for (const drill of WARMUP_BY_PATTERN[pattern]) {
      if (!drills.includes(drill)) drills.push(drill);
    }
  }
  drills.push("First exercise ramp-up set");
  return drills.slice(0, 6);
}

const VI_READINESS: Record<string, { label: string; detail: string }> = {
  "Recovery day": {
    label: "Ngày phục hồi",
    detail: "Giảm khối lượng và nghỉ lâu hơn hôm nay.",
  },
  "Moderate readiness": {
    label: "Sẵn sàng vừa phải",
    detail: "Bớt một hiệp mỗi bài và nghỉ thêm một chút.",
  },
  Ready: {
    label: "Sẵn sàng",
    detail: "Tập đúng buổi đã lên kế hoạch.",
  },
};

export function warmupVoiceCue(drills: string[], lang: CoachLang = "en"): string {
  const heading = lang === "vi" ? "Khởi động." : "Warm-up.";
  return `${heading} ${drills
    .map((drill, index) => `${index + 1}. ${warmupDrillGuide(drill, lang).name}.`)
    .join(" ")}`;
}

export function readinessVoiceCue(
  recommendation: ReadinessRecommendation,
  lang: CoachLang = "en",
): string {
  if (lang === "vi") {
    const t = VI_READINESS[recommendation.label] ?? {
      label: recommendation.label,
      detail: recommendation.detail,
    };
    return `Mức sẵn sàng ${recommendation.score} phần trăm. ${t.label}. ${t.detail}`;
  }
  return `Readiness ${recommendation.score} percent. ${recommendation.label}. ${recommendation.detail}`;
}
