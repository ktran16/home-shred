"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { pivotVolume } from "@/lib/charts";

const COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
];

export default function ProgressPage() {
  const volume = useQuery({
    queryKey: ["volume"],
    queryFn: async () => (await api.GET("/api/progress/volume")).data ?? [],
  });
  const metrics = useQuery({
    queryKey: ["body-metrics"],
    queryFn: async () => (await api.GET("/api/body-metrics")).data ?? [],
  });

  const { rows, muscles } = pivotVolume(volume.data ?? []);
  const weightData = (metrics.data ?? []).map((m) => ({
    date: m.date,
    weight: Number(m.weight_kg),
  }));

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Progress</h1>

      <Card className="flex flex-col gap-2">
        <h2 className="font-semibold">Weekly volume by muscle</h2>
        {rows.length === 0 ? (
          <p className="text-sm text-zinc-500">Log some workouts to see volume.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={rows} margin={{ left: -10, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="week" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {muscles.map((m, i) => (
                <Bar key={m} dataKey={m} stackId="v" fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card className="flex flex-col gap-2">
        <h2 className="font-semibold">Bodyweight</h2>
        {weightData.length === 0 ? (
          <p className="text-sm text-zinc-500">No measurements yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={weightData} margin={{ left: -10, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" fontSize={11} />
              <YAxis domain={["auto", "auto"]} fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="weight" stroke="#10b981" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <AddMetric />
    </div>
  );
}

function AddMetric() {
  const qc = useQueryClient();
  const [weight, setWeight] = useState("");
  const [bf, setBf] = useState("");
  const [waist, setWaist] = useState("");

  const add = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST("/api/body-metrics", {
        body: {
          weight_kg: Number(weight),
          body_fat_pct: bf === "" ? null : Number(bf),
          waist_cm: waist === "" ? null : Number(waist),
        },
      });
      if (error) throw new Error("Could not save measurement");
    },
    onSuccess: () => {
      setWeight("");
      setBf("");
      setWaist("");
      qc.invalidateQueries({ queryKey: ["body-metrics"] });
    },
  });

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-semibold">Log today’s measurement</h2>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <Label>Weight</Label>
          <Input type="number" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} />
        </div>
        <div>
          <Label>Body fat %</Label>
          <Input type="number" step="0.1" value={bf} onChange={(e) => setBf(e.target.value)} />
        </div>
        <div>
          <Label>Waist cm</Label>
          <Input type="number" step="0.1" value={waist} onChange={(e) => setWaist(e.target.value)} />
        </div>
      </div>
      <Button onClick={() => add.mutate()} disabled={add.isPending || weight === ""}>
        {add.isPending ? "Saving…" : "Save measurement"}
      </Button>
      {add.isError && <p className="text-center text-sm text-red-600">{add.error.message}</p>}
    </Card>
  );
}
