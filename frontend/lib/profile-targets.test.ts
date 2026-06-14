import { describe, expect, it } from "vitest";

import {
  computeNutritionPreview,
  computeRecoveryPreview,
  profileErrors,
} from "@/lib/profile-targets";

const profile = {
  sex: "male",
  age: 30,
  height_cm: 175,
  weight_kg: 80,
  activity_level: "moderate",
  experience_level: "intermediate",
} as const;

describe("profile target previews", () => {
  it("matches the backend static nutrition formula", () => {
    expect(computeNutritionPreview(profile)).toEqual({
      bmr: 1749,
      tdee_kcal: 2711,
      target_kcal: 2168,
      protein_g: 160,
      carbs_g: 238,
      fat_g: 64,
    });
  });

  it("shows age-based recovery bands", () => {
    expect(computeRecoveryPreview(39)).toEqual({
      restMultiplier: 1,
      volumeFactor: 1,
      label: "Baseline volume",
    });
    expect(computeRecoveryPreview(40).volumeFactor).toBe(0.9);
    expect(computeRecoveryPreview(55).restMultiplier).toBe(1.2);
  });

  it("validates profile ranges before save", () => {
    expect(profileErrors({ ...profile, age: 12 })).toHaveProperty("age");
    expect(profileErrors(profile)).toEqual({});
  });
});
