"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, Input, Label, Select } from "@/components/ui";
import { api, type ProfileIn } from "@/lib/api";

const ACTIVITY = ["sedentary", "light", "moderate", "active", "very_active"] as const;
const LEVELS = ["beginner", "intermediate", "advanced"] as const;

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
      <h1 className="text-2xl font-bold">Profile</h1>
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
    },
  });

  const set = <K extends keyof ProfileIn>(key: K, value: ProfileIn[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  };

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <Label>Sex</Label>
        <Select value={form.sex} onChange={(e) => set("sex", e.target.value as ProfileIn["sex"])}>
          <option value="male">Male</option>
          <option value="female">Female</option>
        </Select>
      </div>

      <div>
        <Label>Age</Label>
        <Input type="number" value={form.age} onChange={(e) => set("age", Number(e.target.value))} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Height (cm)</Label>
          <Input
            type="number"
            step="0.1"
            value={form.height_cm}
            onChange={(e) => set("height_cm", Number(e.target.value))}
          />
        </div>
        <div>
          <Label>Weight (kg)</Label>
          <Input
            type="number"
            step="0.1"
            value={form.weight_kg}
            onChange={(e) => set("weight_kg", Number(e.target.value))}
          />
        </div>
      </div>

      <div>
        <Label>Activity level</Label>
        <Select
          value={form.activity_level}
          onChange={(e) => set("activity_level", e.target.value as ProfileIn["activity_level"])}
        >
          {ACTIVITY.map((a) => (
            <option key={a} value={a}>
              {a.replace("_", " ")}
            </option>
          ))}
        </Select>
      </div>

      <div>
        <Label>Experience level</Label>
        <Select
          value={form.experience_level}
          onChange={(e) =>
            set("experience_level", e.target.value as ProfileIn["experience_level"])
          }
        >
          {LEVELS.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </Select>
      </div>

      <Button onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Save profile"}
      </Button>
      {saved && <p className="text-center text-sm text-emerald-600">Saved.</p>}
      {mutation.isError && (
        <p className="text-center text-sm text-red-600">Could not save. Try again.</p>
      )}
    </Card>
  );
}
