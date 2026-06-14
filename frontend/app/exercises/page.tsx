"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, Label, Select } from "@/components/ui";
import { api, type ExerciseOut } from "@/lib/api";
import { cn } from "@/lib/utils";

const EQUIPMENT = ["", "bodyweight", "dumbbell", "pull_up_bar"] as const;
const CATEGORY = ["", "push", "pull", "legs", "core", "conditioning"] as const;

type Equipment = (typeof EQUIPMENT)[number];
type Category = (typeof CATEGORY)[number];

export default function ExercisesPage() {
  const qc = useQueryClient();
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
  const preference = useMutation({
    mutationFn: async ({
      exerciseId,
      status,
    }: {
      exerciseId: number;
      status: NonNullable<ExerciseOut["preference"]> | null;
    }) => {
      if (status == null) {
        const { error } = await api.DELETE("/api/exercises/{exercise_id}/preference", {
          params: { path: { exercise_id: exerciseId } },
        });
        if (error) throw new Error("Could not clear preference");
        return;
      }
      const { error } = await api.PUT("/api/exercises/{exercise_id}/preference", {
        params: { path: { exercise_id: exerciseId } },
        body: { status },
      });
      if (error) throw new Error("Could not save preference");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exercises"] });
      qc.invalidateQueries({ queryKey: ["exercise-substitutions"] });
      qc.invalidateQueries({ queryKey: ["plans"] });
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
        <p className="text-sm text-zinc-500">
          {data.length} exercises · favorites get priority in new plans, avoided moves stay out.
        </p>
      )}

      <ul className="grid gap-3 md:grid-cols-2">
        {data?.map((ex) => (
          <Card
            key={ex.id}
            className={cn(
              "flex flex-col gap-3",
              ex.preference === "avoid" && "border-rose-200 bg-rose-50/70 dark:border-rose-900 dark:bg-rose-950/20",
              ex.preference === "favorite" && "border-emerald-200 bg-emerald-50/70 dark:border-emerald-900 dark:bg-emerald-950/20",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{ex.name}</span>
              <div className="flex shrink-0 flex-wrap justify-end gap-1">
                {ex.preference && <PreferenceBadge preference={ex.preference} />}
                {ex.is_compound && <Badge>compound</Badge>}
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                {ex.equipment.replace(/_/g, " ")}
              </Badge>
              {ex.pattern && <Badge>{ex.pattern.replace(/_/g, " ")}</Badge>}
              {ex.level && <Badge>{ex.level}</Badge>}
            </div>
            <p className="text-xs text-zinc-500">{ex.primary_muscles.join(", ")}</p>
            <div className="mt-auto grid grid-cols-3 gap-2">
              <Button
                type="button"
                variant={ex.preference === "favorite" ? "primary" : "secondary"}
                className="h-9 min-h-0 px-2 text-xs"
                disabled={preference.isPending}
                onClick={() =>
                  preference.mutate({
                    exerciseId: ex.id,
                    status: ex.preference === "favorite" ? null : "favorite",
                  })
                }
              >
                Favorite
              </Button>
              <Button
                type="button"
                variant={ex.preference === "avoid" ? "primary" : "secondary"}
                className="h-9 min-h-0 px-2 text-xs"
                disabled={preference.isPending}
                onClick={() =>
                  preference.mutate({
                    exerciseId: ex.id,
                    status: ex.preference === "avoid" ? null : "avoid",
                  })
                }
              >
                Avoid
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="h-9 min-h-0 px-2 text-xs"
                disabled={preference.isPending || !ex.preference}
                onClick={() => preference.mutate({ exerciseId: ex.id, status: null })}
              >
                Clear
              </Button>
            </div>
          </Card>
        ))}
      </ul>
      {preference.isError && (
        <p className="text-sm text-red-600">Could not update exercise preference.</p>
      )}
    </div>
  );
}

function PreferenceBadge({ preference }: { preference: NonNullable<ExerciseOut["preference"]> }) {
  if (preference === "favorite") {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
        favorite
      </Badge>
    );
  }
  return (
    <Badge className="bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">
      avoid
    </Badge>
  );
}
