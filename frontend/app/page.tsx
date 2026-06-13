"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

export default function Home() {
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data, response } = await api.GET("/api/profile");
      if (response.status === 404) return null;
      return data ?? null;
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">HomeShred</h1>

      {!isLoading && !profile && (
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
        <h2 className="font-semibold">Your plan</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Generate a rule-based shred plan (3–5 days/week).
        </p>
        <Link href="/plan/new">
          <Button variant="secondary" className="w-full">
            Generate a plan
          </Button>
        </Link>
      </Card>
    </div>
  );
}
