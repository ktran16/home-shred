import type { ProfileIn } from "@/lib/api";

const ACTIVITY_FACTORS: Record<ProfileIn["activity_level"], number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  very_active: 1.9,
};

const DEFICIT_FACTOR = 0.8;
const PROTEIN_G_PER_KG = 2;
const FAT_G_PER_KG = 0.8;
const KCAL_PER_G_PROTEIN = 4;
const KCAL_PER_G_CARB = 4;
const KCAL_PER_G_FAT = 9;

export type NutritionPreview = {
  bmr: number;
  tdee_kcal: number;
  target_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

export type RecoveryPreview = {
  restMultiplier: number;
  volumeFactor: number;
  label: string;
};

export function computeNutritionPreview(profile: ProfileIn): NutritionPreview {
  const weightKg = Number(profile.weight_kg);
  const heightCm = Number(profile.height_cm);
  const base = 10 * weightKg + 6.25 * heightCm - 5 * profile.age;
  const bmr = base + (profile.sex === "male" ? 5 : -161);
  const tdee = bmr * ACTIVITY_FACTORS[profile.activity_level];
  const target = Math.round(tdee * DEFICIT_FACTOR);
  const protein = Math.round(PROTEIN_G_PER_KG * weightKg);
  const fat = Math.round(FAT_G_PER_KG * weightKg);
  const remaining = target - (protein * KCAL_PER_G_PROTEIN + fat * KCAL_PER_G_FAT);

  return {
    bmr: Math.round(bmr),
    tdee_kcal: Math.round(tdee),
    target_kcal: target,
    protein_g: protein,
    carbs_g: Math.max(0, Math.round(remaining / KCAL_PER_G_CARB)),
    fat_g: fat,
  };
}

export function computeRecoveryPreview(age: number): RecoveryPreview {
  if (age >= 55) {
    return { restMultiplier: 1.2, volumeFactor: 0.8, label: "Recovery-biased" };
  }
  if (age >= 40) {
    return { restMultiplier: 1.1, volumeFactor: 0.9, label: "Moderated volume" };
  }
  return { restMultiplier: 1, volumeFactor: 1, label: "Baseline volume" };
}

export function profileErrors(profile: ProfileIn): Partial<Record<keyof ProfileIn, string>> {
  const errors: Partial<Record<keyof ProfileIn, string>> = {};
  const height = Number(profile.height_cm);
  const weight = Number(profile.weight_kg);

  if (!Number.isFinite(profile.age) || profile.age < 14 || profile.age > 100) {
    errors.age = "Use 14-100.";
  }
  if (!Number.isFinite(height) || height < 120 || height > 230) {
    errors.height_cm = "Use 120-230 cm.";
  }
  if (!Number.isFinite(weight) || weight < 35 || weight > 250) {
    errors.weight_kg = "Use 35-250 kg.";
  }

  return errors;
}
