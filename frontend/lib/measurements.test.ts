import { describe, expect, it } from "vitest";

import { changeTone, formatChange, formatLatest, measurementChartData } from "@/lib/measurements";
import type { MeasurementSeriesOut } from "@/lib/api";

const series: MeasurementSeriesOut = {
  type: { id: 1, key: "chest", label: "Chest", unit: "cm", builtin: true },
  points: [
    { date: "2026-06-01", value: "100.0" },
    { date: "2026-06-08", value: "102.5" },
  ],
  latest: "102.5",
  change: "2.5",
};

describe("measurements helpers", () => {
  it("maps points to numeric chart rows", () => {
    expect(measurementChartData(series)).toEqual([
      { date: "2026-06-01", value: 100 },
      { date: "2026-06-08", value: 102.5 },
    ]);
  });

  it("formats latest and a dash when missing", () => {
    expect(formatLatest("102.5", "cm")).toBe("102.5 cm");
    expect(formatLatest(null, "cm")).toBe("—");
  });

  it("formats signed change with a real minus sign", () => {
    expect(formatChange("2.5", "cm")).toBe("+2.5 cm");
    expect(formatChange("-1.5", "cm")).toBe("−1.5 cm");
    expect(formatChange("0", "cm")).toBe("±0 cm");
    expect(formatChange(null, "cm")).toBe("");
  });

  it("tones gain/loss/flat distinctly", () => {
    expect(changeTone("2")).toContain("emerald");
    expect(changeTone("-2")).toContain("blue");
    expect(changeTone("0")).toBe("text-zinc-400");
    expect(changeTone(null)).toBe("text-zinc-400");
  });
});
