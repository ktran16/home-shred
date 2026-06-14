"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api, type ProfileIn } from "@/lib/api";
import {
  computeNutritionPreview,
  computeRecoveryPreview,
  profileErrors,
} from "@/lib/profile-targets";
import { cn } from "@/lib/utils";

const ACTIVITY = [
  { value: "sedentary", label: "Sedentary", detail: "Desk day" },
  { value: "light", label: "Light", detail: "1-3 active days" },
  { value: "moderate", label: "Moderate", detail: "3-5 active days" },
  { value: "active", label: "Active", detail: "Most days" },
  { value: "very_active", label: "Very active", detail: "Hard daily work" },
] as const;
const LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
] as const;
const SEX_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
] as const;

const EMPTY: ProfileIn = {
  sex: "male",
  age: 30,
  height_cm: 175,
  weight_kg: 80,
  activity_level: "moderate",
  experience_level: "intermediate",
};

export default function ProfilePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/profile");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Profile</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Your saved profile drives nutrition targets, plan volume, and rest timing.
        </p>
      </div>
      {isLoading ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : (
        <ProfileForm
          key={data ? "loaded" : "empty"}
          initial={
            data
              ? {
                  sex: data.sex,
                  age: data.age,
                  height_cm: Number(data.height_cm),
                  weight_kg: Number(data.weight_kg),
                  activity_level: data.activity_level,
                  experience_level: data.experience_level,
                }
              : EMPTY
          }
        />
      )}
    </div>
  );
}

function ProfileForm({ initial }: { initial: ProfileIn }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ProfileIn>(initial);
  const [saved, setSaved] = useState(false);
  const errors = useMemo(() => profileErrors(form), [form]);
  const hasErrors = Object.keys(errors).length > 0;
  const nutrition = useMemo(() => computeNutritionPreview(form), [form]);
  const recovery = useMemo(() => computeRecoveryPreview(form.age), [form.age]);
  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(initial), [form, initial]);

  const mutation = useMutation({
    mutationFn: async (body: ProfileIn) => {
      const { data, error } = await api.PUT("/api/profile", { body });
      if (error) throw new Error("Failed to save profile");
      return data;
    },
    onSuccess: () => {
      setSaved(true);
      qc.invalidateQueries({ queryKey: ["profile"] });
      qc.invalidateQueries({ queryKey: ["nutrition"] });
      qc.invalidateQueries({ queryKey: ["nutrition-adaptive"] });
      qc.invalidateQueries({ queryKey: ["plans"] });
      qc.invalidateQueries({ queryKey: ["plan-coverage"] });
    },
  });

  const set = <K extends keyof ProfileIn>(key: K, value: ProfileIn[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  };

  return (
    <div className="flex flex-col gap-5">
      <section className="overflow-hidden rounded-lg border border-zinc-200 bg-zinc-200 shadow-sm shadow-zinc-200/70 dark:border-zinc-800 dark:bg-zinc-800 dark:shadow-none">
        <div className="grid gap-px sm:grid-cols-4">
          <PreviewMetric label="Target" value={`${nutrition.target_kcal}`} suffix="kcal" />
          <PreviewMetric label="Protein" value={`${nutrition.protein_g}`} suffix="g" tone="blue" />
          <PreviewMetric label="Set target" value={`${Math.round(recovery.volumeFactor * 100)}`} suffix="%" tone="amber" />
          <PreviewMetric label="Rest" value={`${Math.round(recovery.restMultiplier * 100)}`} suffix="%" tone="rose" />
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <form
          className="rounded-lg border border-zinc-200 bg-white shadow-sm shadow-zinc-200/70 dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-none"
          onSubmit={(event) => {
            event.preventDefault();
            if (!hasErrors && dirty) mutation.mutate(form);
          }}
        >
          <div className="flex items-center justify-between gap-3 border-b border-zinc-100 px-4 py-4 dark:border-zinc-800 sm:px-5">
            <div>
              <h2 className="text-base font-semibold">Training profile</h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Save to recompute nutrition and future plans.
              </p>
            </div>
            <Badge
              className={
                dirty
                  ? "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
              }
            >
              {dirty ? "Unsaved" : "Current"}
            </Badge>
          </div>

          <div className="flex flex-col gap-7 p-4 sm:p-5">
            <FormSection title="Identity">
              <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
                <SegmentedField label="Sex">
                  {SEX_OPTIONS.map((option) => (
                    <ChoiceButton
                      key={option.value}
                      selected={form.sex === option.value}
                      onClick={() => set("sex", option.value)}
                    >
                      {option.label}
                    </ChoiceButton>
                  ))}
                </SegmentedField>
                <NumberField
                  label="Age"
                  value={form.age}
                  min={14}
                  max={100}
                  error={errors.age}
                  onChange={(value) => set("age", value)}
                />
              </div>
            </FormSection>

            <FormSection title="Body measures">
              <div className="grid gap-3 sm:grid-cols-2">
                <NumberField
                  label="Height"
                  suffix="cm"
                  value={Number(form.height_cm)}
                  min={120}
                  max={230}
                  step="0.1"
                  error={errors.height_cm}
                  onChange={(value) => set("height_cm", value)}
                />
                <NumberField
                  label="Weight"
                  suffix="kg"
                  value={Number(form.weight_kg)}
                  min={35}
                  max={250}
                  step="0.1"
                  error={errors.weight_kg}
                  onChange={(value) => set("weight_kg", value)}
                />
              </div>
            </FormSection>

            <FormSection title="Training calibration">
              <div className="grid gap-3">
                <div>
                  <Label>Activity level</Label>
                  <div className="grid gap-2 sm:grid-cols-5">
                    {ACTIVITY.map((activity) => (
                      <ActivityButton
                        key={activity.value}
                        label={activity.label}
                        detail={activity.detail}
                        selected={form.activity_level === activity.value}
                        onClick={() => set("activity_level", activity.value)}
                      />
                    ))}
                  </div>
                </div>

                <SegmentedField label="Experience level">
                  {LEVELS.map((level) => (
                    <ChoiceButton
                      key={level.value}
                      selected={form.experience_level === level.value}
                      onClick={() => set("experience_level", level.value)}
                    >
                      {level.label}
                    </ChoiceButton>
                  ))}
                </SegmentedField>
              </div>
            </FormSection>
          </div>

          <div className="flex flex-col gap-2 border-t border-zinc-100 bg-zinc-50 px-4 py-4 dark:border-zinc-800 dark:bg-zinc-950/60 sm:flex-row sm:px-5">
            <Button type="submit" className="flex-1" disabled={mutation.isPending || hasErrors || !dirty}>
              {mutation.isPending ? "Saving..." : dirty ? "Save profile" : "Profile saved"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="sm:w-28"
              onClick={() => {
                setForm(initial);
                setSaved(false);
              }}
              disabled={mutation.isPending || !dirty}
            >
              Reset
            </Button>
          </div>

          {saved && <p className="px-5 pb-4 text-center text-sm text-emerald-600">Saved.</p>}
          {mutation.isError && (
            <p className="px-5 pb-4 text-center text-sm text-red-600">Could not save. Try again.</p>
          )}
        </form>

        <aside className="flex flex-col gap-4 xl:sticky xl:top-6 xl:self-start">
          <TargetPanel nutrition={nutrition} />
          <PlanPanel recovery={recovery} level={form.experience_level} />
        </aside>
      </div>
    </div>
  );
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3 sm:grid-cols-[150px_1fr]">
      <h3 className="pt-1 text-sm font-semibold text-zinc-950 dark:text-zinc-50">{title}</h3>
      <div>{children}</div>
    </section>
  );
}

function SegmentedField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="grid gap-1 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-950 sm:grid-flow-col sm:auto-cols-fr">
        {children}
      </div>
    </div>
  );
}

function ChoiceButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        "min-h-[40px] rounded-md px-3 text-sm font-semibold transition-colors",
        selected
          ? "bg-white text-zinc-950 shadow-sm dark:bg-zinc-800 dark:text-zinc-50"
          : "text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-50",
      )}
    >
      {children}
    </button>
  );
}

function ActivityButton({
  label,
  detail,
  selected,
  onClick,
}: {
  label: string;
  detail: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        "min-h-[68px] rounded-lg border p-3 text-left transition-colors",
        selected
          ? "border-zinc-950 bg-zinc-950 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-950"
          : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-zinc-600",
      )}
    >
      <span className="block text-sm font-semibold leading-tight">{label}</span>
      <span className={cn("mt-1 block text-[11px]", selected ? "text-zinc-300 dark:text-zinc-600" : "text-zinc-500")}>
        {detail}
      </span>
    </button>
  );
}

function NumberField({
  label,
  suffix,
  value,
  min,
  max,
  step = "1",
  error,
  onChange,
}: {
  label: string;
  suffix?: string;
  value: number;
  min: number;
  max: number;
  step?: string;
  error?: string;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="relative">
        <Input
          type="number"
          min={min}
          max={max}
          step={step}
          value={Number.isFinite(value) ? value : ""}
          onChange={(e) => onChange(Number(e.target.value))}
          className={cn(suffix && "pr-11", error && "border-red-400 focus:border-red-500")}
        />
        {suffix && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-zinc-400">
            {suffix}
          </span>
        )}
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

function PreviewMetric({
  label,
  value,
  suffix,
  tone = "emerald",
}: {
  label: string;
  value: string;
  suffix: string;
  tone?: "emerald" | "blue" | "amber" | "rose";
}) {
  const tones = {
    emerald: "text-emerald-700 dark:text-emerald-300",
    blue: "text-sky-700 dark:text-sky-300",
    amber: "text-amber-700 dark:text-amber-300",
    rose: "text-rose-700 dark:text-rose-300",
  };
  return (
    <div className="bg-white p-4 dark:bg-zinc-900">
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={cn("mt-1 flex items-baseline gap-1 text-2xl font-bold", tones[tone])}>
        {value}
        <span className="text-xs font-semibold text-zinc-500">{suffix}</span>
      </div>
    </div>
  );
}

function TargetPanel({ nutrition }: { nutrition: ReturnType<typeof computeNutritionPreview> }) {
  const macroTotal = nutrition.protein_g + nutrition.carbs_g + nutrition.fat_g;
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">Targets</h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Live preview</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold tabular-nums">{nutrition.target_kcal}</div>
          <div className="text-xs font-medium text-zinc-500">kcal/day</div>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <MacroBar label="Protein" value={nutrition.protein_g} total={macroTotal} color="bg-sky-500" />
        <MacroBar label="Carbs" value={nutrition.carbs_g} total={macroTotal} color="bg-amber-500" />
        <MacroBar label="Fat" value={nutrition.fat_g} total={macroTotal} color="bg-rose-500" />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat label="BMR" value={`${nutrition.bmr}`} />
        <Stat label="TDEE" value={`${nutrition.tdee_kcal}`} />
      </div>
    </Card>
  );
}

function MacroBar({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const width = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums text-zinc-500">{value}g</span>
      </div>
      <div className="h-2 rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div className={cn("h-2 rounded-full", color)} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function PlanPanel({
  recovery,
  level,
}: {
  recovery: ReturnType<typeof computeRecoveryPreview>;
  level: ProfileIn["experience_level"];
}) {
  return (
    <Card className="flex flex-col gap-3">
      <div>
        <h2 className="font-semibold">Plan settings</h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">Applied to the next generated plan</p>
      </div>
      <div className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-800">
        <div className="text-xs text-zinc-500">Recovery band</div>
        <div className="mt-1 font-semibold">{recovery.label}</div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Rest" value={`${Math.round(recovery.restMultiplier * 100)}%`} />
        <Stat label="Volume" value={`${Math.round(recovery.volumeFactor * 100)}%`} />
      </div>
      <div className="flex items-center justify-between rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
        <span className="text-sm text-zinc-500">Experience</span>
        <span className="text-sm font-semibold capitalize">{level}</span>
      </div>
    </Card>
  );
}
