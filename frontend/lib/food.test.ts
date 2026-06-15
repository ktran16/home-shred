import { describe, expect, it } from "vitest";

import type { FoodFactsOut } from "@/lib/api";
import { foodTitle, isValidBarcode, macrosForGrams } from "@/lib/food";

function food(overrides: Partial<FoodFactsOut> = {}): FoodFactsOut {
  return {
    code: "737628064502",
    name: "Peanut Butter",
    brand: "Acme",
    serving_size: "32 g",
    kcal_per_100g: 588,
    protein_per_100g: 25,
    carbs_per_100g: 20,
    fat_per_100g: 50,
    ...overrides,
  };
}

describe("macrosForGrams", () => {
  it("scales per-100g facts to a serving", () => {
    expect(macrosForGrams(food(), 50)).toEqual({ kcal: 294, protein: 12.5, carbs: 10, fat: 25 });
  });

  it("keeps null fields null", () => {
    expect(macrosForGrams(food({ protein_per_100g: null, kcal_per_100g: null }), 100)).toEqual({
      kcal: null,
      protein: null,
      carbs: 20,
      fat: 50,
    });
  });
});

describe("foodTitle", () => {
  it("combines name and brand", () => {
    expect(foodTitle(food())).toBe("Peanut Butter (Acme)");
  });

  it("falls back to brand then barcode", () => {
    expect(foodTitle(food({ name: null }))).toBe("Acme");
    expect(foodTitle(food({ name: null, brand: null }))).toBe("Barcode 737628064502");
  });
});

describe("isValidBarcode", () => {
  it("accepts 8–14 digit codes", () => {
    expect(isValidBarcode("737628064502")).toBe(true);
    expect(isValidBarcode("  12345678 ")).toBe(true);
  });

  it("rejects malformed codes", () => {
    expect(isValidBarcode("123")).toBe(false);
    expect(isValidBarcode("abcdefgh")).toBe(false);
  });
});
