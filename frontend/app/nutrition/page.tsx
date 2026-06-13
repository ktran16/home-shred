"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";

import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

function MacroCard({ label, grams, kcal, color }: { label: string; grams: number; kcal: number; color: string }) {
  return (
    <Card className="flex flex-col items-center gap-1 py-3">
      <span className={`text-2xl font-bold ${color}`}>{grams}g</span>
      <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">{label}</span>
      <span className="text-[10px] text-zinc-400">{kcal} kcal</span>
    </Card>
  );
}

export default function NutritionPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["nutrition"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/nutrition/targets");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });

  const recompute = useMutation({
    mutationFn: async () => {
      await api.POST("/api/nutrition/recompute");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nutrition"] }),
  });

  if (isLoading) return <p className="text-sm text-zinc-500">Loading…</p>;

  if (!data) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-bold">Nutrition</h1>
        <Card className="flex flex-col gap-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Set your profile to compute calorie & macro targets.
          </p>
          <Link href="/profile">
            <Button className="w-full">Set up profile</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Nutrition</h1>

      <Card className="flex flex-col items-center gap-1 py-5">
        <span className="text-4xl font-bold text-emerald-600">{data.target_kcal}</span>
        <span className="text-sm text-zinc-600 dark:text-zinc-400">kcal/day target</span>
        <span className="text-xs text-zinc-400">TDEE {data.tdee_kcal} · 20% deficit</span>
      </Card>

      <div className="grid grid-cols-3 gap-2">
        <MacroCard label="Protein" grams={data.protein_g} kcal={data.protein_g * 4} color="text-blue-500" />
        <MacroCard label="Carbs" grams={data.carbs_g} kcal={data.carbs_g * 4} color="text-amber-500" />
        <MacroCard label="Fat" grams={data.fat_g} kcal={data.fat_g * 9} color="text-rose-500" />
      </div>

      <Button
        variant="secondary"
        onClick={() => recompute.mutate()}
        disabled={recompute.isPending}
      >
        {recompute.isPending ? "Recomputing…" : "Recompute from profile"}
      </Button>
    </div>
  );
}
