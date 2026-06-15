import type { FoodFactsOut } from "@/lib/api";

/** Macros for a serving (SPEC §17.5 B2b). Null fields mean OFF had no value. */
export type ServingMacros = {
  kcal: number | null;
  protein: number | null;
  carbs: number | null;
  fat: number | null;
};

/** Scale per-100 g facts to an arbitrary gram amount. */
export function macrosForGrams(food: FoodFactsOut, grams: number): ServingMacros {
  const scale = grams / 100;
  const round1 = (v: number | null) => (v == null ? null : Math.round(v * scale * 10) / 10);
  return {
    kcal: food.kcal_per_100g == null ? null : Math.round(food.kcal_per_100g * scale),
    protein: round1(food.protein_per_100g),
    carbs: round1(food.carbs_per_100g),
    fat: round1(food.fat_per_100g),
  };
}

/** Display title: name + brand, falling back to the barcode. */
export function foodTitle(food: FoodFactsOut): string {
  if (food.name && food.brand) return `${food.name} (${food.brand})`;
  return food.name ?? food.brand ?? `Barcode ${food.code}`;
}

const BARCODE_RE = /^[0-9]{8,14}$/;

/** EAN/UPC barcodes are 8–14 digits. */
export function isValidBarcode(code: string): boolean {
  return BARCODE_RE.test(code.trim());
}
