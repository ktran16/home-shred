import type {
  DailyFoodLogOut,
  FoodLogIn,
  FoodLogRecentOut,
  MealTemplateItemOut,
  NutritionHistoryOut,
} from "@/lib/api";

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

export type NutritionHistoryRow = {
  date: string;
  kcal: number;
  target_kcal: number | null;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  logged: boolean;
  kcal_adherent: boolean;
};

export function nutritionHistoryRows(
  history: NutritionHistoryOut | null | undefined,
): NutritionHistoryRow[] {
  return (history?.days ?? []).map((day) => ({
    date: day.date.slice(5),
    kcal: day.kcal,
    target_kcal: day.target_kcal ?? null,
    protein_g: Number(day.protein_g),
    carbs_g: Number(day.carbs_g),
    fat_g: Number(day.fat_g),
    logged: day.logged,
    kcal_adherent: day.kcal_adherent,
  }));
}

export function adherenceSummary(history: NutritionHistoryOut | null | undefined): string {
  if (!history || history.target_days === 0) return "No target";
  return `${history.adherence_pct}% (${history.adherent_days}/${history.target_days} days)`;
}

// Portion multipliers offered on the meal-templates card; the API accepts 0.25–4 (SPEC §19.9 N2).
export const TEMPLATE_SCALES = [0.5, 1, 2] as const;

export type MacroTotals = { kcal: number; protein_g: number; carbs_g: number; fat_g: number };

/** Preview what logging a template × scale adds. Rounds per item like the backend does
 * (kcal to whole numbers, macros to 0.1 g), so the preview matches the logged totals. */
export function scaledTemplateTotals(
  items: Pick<MealTemplateItemOut, "kcal" | "protein_g" | "carbs_g" | "fat_g">[],
  scale = 1,
): MacroTotals {
  const totals = items.reduce(
    (sum, item) => ({
      kcal: sum.kcal + Math.round(item.kcal * scale),
      protein_g: sum.protein_g + round1(Number(item.protein_g) * scale),
      carbs_g: sum.carbs_g + round1(Number(item.carbs_g) * scale),
      fat_g: sum.fat_g + round1(Number(item.fat_g) * scale),
    }),
    { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
  );
  return {
    kcal: totals.kcal,
    protein_g: round1(totals.protein_g),
    carbs_g: round1(totals.carbs_g),
    fat_g: round1(totals.fat_g),
  };
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}
