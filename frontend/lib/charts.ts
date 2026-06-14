import type { VolumePoint } from "@/lib/api";

export type VolumeRow = Record<string, string | number>;

/** Pivot flat {week,muscle,volume} points into stacked-bar rows + the muscle keys. */
export function pivotVolume(points: VolumePoint[]): { rows: VolumeRow[]; muscles: string[] } {
  const weeks = [...new Set(points.map((p) => p.week))].sort();
  const muscles = [...new Set(points.map((p) => p.muscle))].sort();
  const rows = weeks.map((week) => {
    const row: VolumeRow = { week };
    for (const p of points) if (p.week === week) row[p.muscle] = p.volume;
    return row;
  });
  return { rows, muscles };
}
