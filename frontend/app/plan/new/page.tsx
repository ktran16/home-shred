"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { days: 3, label: "3 days", desc: "Full body" },
  { days: 4, label: "4 days", desc: "Upper / Lower" },
  { days: 5, label: "5 days", desc: "PPL + Upper + Conditioning" },
] as const;

export default function NewPlanPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [days, setDays] = useState<number>(4);

  const mutation = useMutation({
    mutationFn: async (daysPerWeek: number) => {
      const { data, error, response } = await api.POST("/api/plans", {
        body: { goal: "shred", days_per_week: daysPerWeek, week: 1 },
      });
      if (error) {
        if (response.status === 409) throw new Error("Set up your profile first.");
        throw new Error("Could not generate plan.");
      }
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plans"] });
      router.push("/plan");
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">New plan</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        Pick how many days per week you want to train. We generate a shred plan from your
        available equipment.
      </p>

      <div className="flex flex-col gap-2">
        {OPTIONS.map((o) => (
          <Card
            key={o.days}
            onClick={() => setDays(o.days)}
            className={cn(
              "flex cursor-pointer items-center justify-between",
              days === o.days && "border-emerald-500 ring-1 ring-emerald-500",
            )}
          >
            <span className="font-medium">{o.label}</span>
            <span className="text-sm text-zinc-500">{o.desc}</span>
          </Card>
        ))}
      </div>

      <Button onClick={() => mutation.mutate(days)} disabled={mutation.isPending}>
        {mutation.isPending ? "Generating…" : "Generate plan"}
      </Button>
      {mutation.isError && (
        <p className="text-center text-sm text-red-600">{mutation.error.message}</p>
      )}
    </div>
  );
}
