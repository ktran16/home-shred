"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Line, LineChart, ResponsiveContainer } from "recharts";

import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

export default function Home() {
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/profile");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });
  const plans = useQuery({
    queryKey: ["plans"],
    queryFn: async () => (await api.GET("/api/plans")).data ?? [],
  });
  const nutrition = useQuery({
    queryKey: ["nutrition"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/nutrition/targets");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });
  const metrics = useQuery({
    queryKey: ["body-metrics"],
    queryFn: async () => (await api.GET("/api/body-metrics")).data ?? [],
  });

  const activePlan = plans.data?.find((p) => p.is_active);
  const weightData = (metrics.data ?? []).map((m) => ({ x: m.date, y: Number(m.weight_kg) }));

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">HomeShred</h1>

      {!profile.isLoading && !profile.data && (
        <Card className="flex flex-col gap-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Set up your profile to get calorie targets and a tailored plan.
          </p>
          <Link href="/profile">
            <Button className="w-full">Set up profile</Button>
          </Link>
        </Card>
      )}

      <Card className="flex flex-col gap-3">
        <h2 className="font-semibold">Today’s workout</h2>
        {activePlan ? (
          <>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{activePlan.name}</p>
            <Link href="/plan">
              <Button className="w-full">Open plan</Button>
            </Link>
          </>
        ) : (
          <>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">No active plan yet.</p>
            <Link href="/plan/new">
              <Button variant="secondary" className="w-full">
                Generate a plan
              </Button>
            </Link>
          </>
        )}
      </Card>

      {nutrition.data && (
        <Link href="/nutrition">
          <Card className="flex items-center justify-between">
            <div>
              <div className="text-xl font-bold text-emerald-600">
                {nutrition.data.target_kcal} kcal
              </div>
              <div className="text-xs text-zinc-500">
                P {nutrition.data.protein_g} · C {nutrition.data.carbs_g} · F {nutrition.data.fat_g}
              </div>
            </div>
            <span className="text-sm text-zinc-400">Today’s targets ›</span>
          </Card>
        </Link>
      )}

      {weightData.length > 1 && (
        <Link href="/progress">
          <Card className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Bodyweight</span>
              <span className="text-sm text-zinc-500">{weightData[weightData.length - 1].y} kg</span>
            </div>
            <ResponsiveContainer width="100%" height={48}>
              <LineChart data={weightData}>
                <Line type="monotone" dataKey="y" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Link>
      )}
    </div>
  );
}
