import type { HistorySessionOut } from "@/lib/api";

// weight_kg / rpe arrive as Decimal-serialized strings (or null) from the API.
const num = (value: string | null): number | null => (value == null ? null : Number(value));

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Format an ISO `YYYY-MM-DD` date as e.g. "Jun 10" without timezone drift. */
export function formatHistoryDate(iso: string): string {
  const [, month, day] = iso.split("-").map(Number);
  const label = MONTHS[(month ?? 1) - 1] ?? "";
  return `${label} ${day}`.trim();
}

export type TopSet = { reps: number; weightKg: number | null; rpe: number | null };

/** Heaviest set of a session (tie-break by reps); null if the session has no sets. */
export function topSet(session: HistorySessionOut): TopSet | null {
  let best: TopSet | null = null;
  for (const set of session.sets) {
    const candidate: TopSet = {
      reps: set.reps,
      weightKg: num(set.weight_kg),
      rpe: num(set.rpe),
    };
    if (
      best == null ||
      (candidate.weightKg ?? 0) > (best.weightKg ?? 0) ||
      ((candidate.weightKg ?? 0) === (best.weightKg ?? 0) && candidate.reps > best.reps)
    ) {
      best = candidate;
    }
  }
  return best;
}

/** Epley estimated 1RM; null for bodyweight (no external load). */
export function estimatedOneRm(reps: number, weightKg: number | null): number | null {
  if (weightKg == null || weightKg <= 0) return null;
  return Math.round(weightKg * (1 + reps / 30) * 10) / 10;
}

/** One-line recap, e.g. "Jun 10: 12,12,10 @ 22.5 kg · RPE 8" or "Jun 10: 15,14 reps". */
export function formatLastTime(session: HistorySessionOut): string {
  if (session.sets.length === 0) return formatHistoryDate(session.date);
  const reps = session.sets.map((set) => set.reps).join(",");
  const weights = session.sets
    .map((set) => num(set.weight_kg))
    .filter((value): value is number => value != null && value > 0);
  const top = topSet(session);
  const loadPart = weights.length > 0 ? `@ ${Math.max(...weights)} kg` : "reps";
  const rpePart = top?.rpe != null ? ` · RPE ${top.rpe}` : "";
  return `${formatHistoryDate(session.date)}: ${reps} ${loadPart}${rpePart}`;
}
