import { describe, expect, it } from "vitest";

import { pivotVolume } from "@/lib/charts";

describe("pivotVolume", () => {
  it("returns empty for no points", () => {
    expect(pivotVolume([])).toEqual({ rows: [], muscles: [] });
  });

  it("pivots weeks into rows with one column per muscle", () => {
    const { rows, muscles } = pivotVolume([
      { week: "2026-W23", muscle: "chest", volume: 600 },
      { week: "2026-W23", muscle: "triceps", volume: 300 },
      { week: "2026-W24", muscle: "chest", volume: 700 },
    ]);
    expect(muscles).toEqual(["chest", "triceps"]);
    expect(rows).toEqual([
      { week: "2026-W23", chest: 600, triceps: 300 },
      { week: "2026-W24", chest: 700 },
    ]);
  });

  it("sorts weeks chronologically and muscles alphabetically", () => {
    const { rows, muscles } = pivotVolume([
      { week: "2026-W24", muscle: "back", volume: 1 },
      { week: "2026-W23", muscle: "abs", volume: 1 },
    ]);
    expect(rows.map((r) => r.week)).toEqual(["2026-W23", "2026-W24"]);
    expect(muscles).toEqual(["abs", "back"]);
  });
});
