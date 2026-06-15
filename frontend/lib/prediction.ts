import type { LoadPredictionOut } from "@/lib/api";

// must match MIN_SESSIONS_FOR_PREDICTION in backend services/prediction.py.
export const MIN_SESSIONS_FOR_PREDICTION = 4;

export type ReadinessTone = "progress" | "hold" | "building";

/** Short forecast headline, e.g. "~28.5 kg e1RM next" or "2 more sessions to forecast". */
export function predictionHeadline(p: LoadPredictionOut): string {
  if (p.readiness === "insufficient" || p.predicted_next == null) {
    const remaining = Math.max(0, MIN_SESSIONS_FOR_PREDICTION - p.sessions);
    return `${remaining} more session${remaining === 1 ? "" : "s"} to forecast`;
  }
  return `~${p.predicted_next} ${p.weighted ? "kg e1RM" : "reps"} next`;
}

/** Coaching verdict + a tone key for styling. */
export function readinessLabel(p: LoadPredictionOut): { label: string; tone: ReadinessTone } {
  switch (p.readiness) {
    case "progress":
      return { label: "Ready to add load", tone: "progress" };
    case "hold":
      return { label: "Hold — repeat or deload", tone: "hold" };
    default:
      return { label: "Building history", tone: "building" };
  }
}
