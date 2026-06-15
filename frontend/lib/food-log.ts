import type { DailyFoodLogOut, FoodLogIn, FoodLogRecentOut } from "@/lib/api";

export type ManualFoodDraft = {
  name: string;
  grams: string;
  kcal: string;
  protein_g: string;
  carbs_g: string;
  fat_g: string;
};

export const EMPTY_FOOD_DRAFT: ManualFoodDraft = {
  name: "",
  grams: "",
  kcal: "",
  protein_g: "",
  carbs_g: "",
  fat_g: "",
};

export function todayIsoDate(now = new Date()): string {
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

export function draftToFoodLog(draft: ManualFoodDraft, date: string): FoodLogIn | null {
  const name = draft.name.trim();
  const grams = Number(draft.grams);
  const kcal = Number(draft.kcal);
  const protein = Number(draft.protein_g);
  const carbs = Number(draft.carbs_g);
  const fat = Number(draft.fat_g);
  if (
    !name ||
    !Number.isFinite(grams) ||
    grams <= 0 ||
    !Number.isFinite(kcal) ||
    kcal < 0 ||
    !Number.isFinite(protein) ||
    protein < 0 ||
    !Number.isFinite(carbs) ||
    carbs < 0 ||
    !Number.isFinite(fat) ||
    fat < 0
  ) {
    return null;
  }
  return {
    date,
    name,
    grams: round1(grams),
    kcal: Math.round(kcal),
    protein_g: round1(protein),
    carbs_g: round1(carbs),
    fat_g: round1(fat),
    source: "manual",
  };
}

export function recentFoodToLog(food: FoodLogRecentOut, date: string): FoodLogIn {
  return {
    date,
    name: food.name,
    grams: Number(food.grams),
    kcal: food.kcal,
    protein_g: Number(food.protein_g),
    carbs_g: Number(food.carbs_g),
    fat_g: Number(food.fat_g),
    source: food.source,
    barcode: food.barcode,
  };
}

export function macroPercent(total: number | string, target: number | string | null | undefined): number {
  const totalNum = Number(total);
  const targetNum = Number(target);
  if (!Number.isFinite(totalNum) || !Number.isFinite(targetNum) || targetNum <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((totalNum / targetNum) * 100)));
}

export function remainingLabel(value: number | string | null | undefined, unit = ""): string {
  if (value == null) return "No target";
  const num = Number(value);
  if (!Number.isFinite(num)) return "No target";
  const rounded = unit ? Math.round(num * 10) / 10 : Math.round(num);
  return `${rounded >= 0 ? "" : "+"}${Math.abs(rounded)}${unit} ${rounded >= 0 ? "left" : "over"}`;
}

export function hasLoggedFood(log: DailyFoodLogOut | null | undefined): boolean {
  return (log?.entries.length ?? 0) > 0;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}
