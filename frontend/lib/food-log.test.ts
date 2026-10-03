import { describe, expect, it } from "vitest";

import {
  EMPTY_FOOD_DRAFT,
  adherenceSummary,
  draftToFoodLog,
  hasLoggedFood,
  macroPercent,
  nutritionHistoryRows,
  recentFoodToLog,
  remainingLabel,
  scaledTemplateTotals,
  todayIsoDate,
} from "@/lib/food-log";

describe("food log helpers", () => {
  it("normalizes a valid manual draft", () => {
    expect(
      draftToFoodLog(
        {
          name: "  Greek yogurt  ",
          grams: "199.96",
          kcal: "190.2",
          protein_g: "20",
          carbs_g: "12.04",
          fat_g: "5",
        },
        "2026-06-15",
      ),
    ).toEqual({
      date: "2026-06-15",
      name: "Greek yogurt",
      grams: 200,
      kcal: 190,
      protein_g: 20,
      carbs_g: 12,
      fat_g: 5,
      source: "manual",
    });
  });

  it("rejects incomplete or invalid manual drafts", () => {
    expect(draftToFoodLog(EMPTY_FOOD_DRAFT, "2026-06-15")).toBeNull();
    expect(draftToFoodLog({ ...EMPTY_FOOD_DRAFT, name: "x", grams: "-1" }, "2026-06-15")).toBeNull();
  });

  it("formats progress and remaining labels", () => {
    expect(macroPercent(50, 200)).toBe(25);
    expect(macroPercent(500, 200)).toBe(100);
    expect(remainingLabel(120)).toBe("120 left");
    expect(remainingLabel(-30, "g")).toBe("+30g over");
  });

  it("uses local calendar date", () => {
    const now = new Date("2026-06-15T23:30:00.000Z");
    expect(todayIsoDate(now)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("detects entries", () => {
    expect(hasLoggedFood(null)).toBe(false);
    expect(hasLoggedFood({ entries: [{}] } as never)).toBe(true);
  });

  it("rebuilds a FoodLogIn from a recent food, preserving source/barcode and target date", () => {
    expect(
      recentFoodToLog(
        {
          name: "Banana",
          grams: "118.0",
          kcal: 105,
          protein_g: "1.3",
          carbs_g: "27.0",
          fat_g: "0.4",
          source: "barcode",
          barcode: "0123456789012",
          last_logged_on: "2026-06-10",
        },
        "2026-06-15",
      ),
    ).toEqual({
      date: "2026-06-15",
      name: "Banana",
      grams: 118,
      kcal: 105,
      protein_g: 1.3,
      carbs_g: 27,
      fat_g: 0.4,
      source: "barcode",
      barcode: "0123456789012",
    });
  });

  it("previews scaled template totals with per-item rounding like the backend", () => {
    const items = [
      { kcal: 300, protein_g: "10.0", carbs_g: "54.0", fat_g: "5.0" },
      { kcal: 121, protein_g: "24.0", carbs_g: "2.5", fat_g: "1.5" },
    ];
    expect(scaledTemplateTotals(items)).toEqual({ kcal: 421, protein_g: 34, carbs_g: 56.5, fat_g: 6.5 });
    // 121 × 1.5 = 181.5 → 182; 2.5 × 1.5 = 3.75 → 3.8; 1.5 × 1.5 = 2.25 → 2.3 (per item)
    expect(scaledTemplateTotals(items, 1.5)).toEqual({
      kcal: 632,
      protein_g: 51,
      carbs_g: 84.8,
      fat_g: 9.8,
    });
    expect(scaledTemplateTotals([], 2)).toEqual({ kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 });
  });

  it("normalizes nutrition history for summaries and charts", () => {
    const history = {
      start_date: "2026-06-09",
      end_date: "2026-06-15",
      logged_days: 2,
      target_days: 7,
      adherent_days: 1,
      adherence_pct: 14,
      days: [
        {
          date: "2026-06-13",
          logged: true,
          kcal: 1900,
          protein_g: "100.0",
          carbs_g: "150.0",
          fat_g: "50.0",
          target_kcal: 2000,
          target_protein_g: 160,
          target_carbs_g: 200,
          target_fat_g: 60,
          kcal_adherent: true,
        },
      ],
    };

    expect(adherenceSummary(history)).toBe("14% (1/7 days)");
    expect(nutritionHistoryRows(history)).toEqual([
      {
        date: "06-13",
        kcal: 1900,
        target_kcal: 2000,
        protein_g: 100,
        carbs_g: 150,
        fat_g: 50,
        logged: true,
        kcal_adherent: true,
      },
    ]);
  });
});
