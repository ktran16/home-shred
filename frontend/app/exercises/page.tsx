"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Card, Label, Select } from "@/components/ui";
import { api } from "@/lib/api";

const EQUIPMENT = ["", "bodyweight", "dumbbell", "pull_up_bar"] as const;
const CATEGORY = ["", "push", "pull", "legs", "core", "conditioning"] as const;

type Equipment = (typeof EQUIPMENT)[number];
type Category = (typeof CATEGORY)[number];

export default function ExercisesPage() {
  const [equipment, setEquipment] = useState<Equipment>("");
  const [category, setCategory] = useState<Category>("");

  const { data, isLoading } = useQuery({
    queryKey: ["exercises", equipment, category],
    queryFn: async () => {
      const { data } = await api.GET("/api/exercises", {
        params: {
          query: {
            ...(equipment ? { equipment } : {}),
            ...(category ? { category } : {}),
          },
        },
      });
      return data ?? [];
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Exercises</h1>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Equipment</Label>
          <Select value={equipment} onChange={(e) => setEquipment(e.target.value as Equipment)}>
            {EQUIPMENT.map((v) => (
              <option key={v} value={v}>
                {v === "" ? "All" : v.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Category</Label>
          <Select value={category} onChange={(e) => setCategory(e.target.value as Category)}>
            {CATEGORY.map((v) => (
              <option key={v} value={v}>
                {v === "" ? "All" : v}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-zinc-500">Loading…</p>}
      {data && (
        <p className="text-sm text-zinc-500">{data.length} exercises</p>
      )}

      <ul className="flex flex-col gap-2">
        {data?.map((ex) => (
          <Card key={ex.id} className="flex flex-col gap-1">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{ex.name}</span>
              {ex.is_compound && <Badge>compound</Badge>}
            </div>
            <div className="flex flex-wrap gap-1">
              <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                {ex.equipment.replace(/_/g, " ")}
              </Badge>
              {ex.pattern && <Badge>{ex.pattern.replace(/_/g, " ")}</Badge>}
              {ex.level && <Badge>{ex.level}</Badge>}
            </div>
            <p className="text-xs text-zinc-500">{ex.primary_muscles.join(", ")}</p>
          </Card>
        ))}
      </ul>
    </div>
  );
}
