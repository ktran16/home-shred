// Pure helpers for the custom body-measurements section (SPEC §19.8 W1).
import type { MeasurementSeriesOut } from "@/lib/api";

export type MeasurementChartPoint = { date: string; value: number };

/** Map a series' points to numeric chart rows (recharts needs numbers, not Decimal strings). */
export function measurementChartData(series: MeasurementSeriesOut): MeasurementChartPoint[] {
  return series.points.map((p) => ({ date: p.date, value: Number(p.value) }));
}

/** "42.0 cm" or "—" when there is no reading yet. */
export function formatLatest(latest: string | null, unit: string): string {
  if (latest == null) return "—";
  return `${Number(latest)} ${unit}`;
}

/** Signed change since the first reading in the window: "+2.0 cm", "−1.5 cm", or "" if N/A. */
export function formatChange(change: string | null, unit: string): string {
  if (change == null) return "";
  const n = Number(change);
  if (n === 0) return `±0 ${unit}`;
  const sign = n > 0 ? "+" : "−";
  return `${sign}${Math.abs(n)} ${unit}`;
}

/** Tailwind tone for a change value (gain = emerald, loss = blue, flat = zinc). */
export function changeTone(change: string | null): string {
  if (change == null) return "text-zinc-400";
  const n = Number(change);
  if (n > 0) return "text-emerald-600 dark:text-emerald-400";
  if (n < 0) return "text-blue-600 dark:text-blue-400";
  return "text-zinc-400";
}
