"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, Input, Label } from "@/components/ui";
import { api, type MealTemplateOut } from "@/lib/api";
import { TEMPLATE_SCALES, scaledTemplateTotals } from "@/lib/food-log";

// Meal templates (SPEC §19.9 N2): save a day's foods under a name, then log them all into
// the selected day in one tap. Logging adds ordinary food-log rows, one per food.
export function MealTemplatesCard({
  date,
  canSaveDay,
  onFoodLogged,
}: {
  date: string;
  canSaveDay: boolean;
  onFoodLogged: () => void;
}) {
  const qc = useQueryClient();
  const [scale, setScale] = useState<number>(1);
  const [name, setName] = useState("");

  const templates = useQuery({
    queryKey: ["meal-templates"],
    queryFn: async () => (await api.GET("/api/nutrition/templates")).data ?? [],
  });
  const invalidateTemplates = () => qc.invalidateQueries({ queryKey: ["meal-templates"] });

  const logTemplate = useMutation({
    mutationFn: async (templateId: number) => {
      const { error } = await api.POST("/api/nutrition/templates/{template_id}/log", {
        params: { path: { template_id: templateId } },
        body: { date, scale },
      });
      if (error) throw new Error("Could not log that template");
    },
    onSuccess: onFoodLogged,
  });

  const saveDay = useMutation({
    mutationFn: async () => {
      const { error, response } = await api.POST("/api/nutrition/templates", {
        body: { name: name.trim(), from_date: date },
      });
      if (error) {
        throw new Error(
          response.status === 409
            ? "A template with that name already exists"
            : response.status === 404
              ? `Nothing logged on ${date} to save`
              : "Could not save template",
        );
      }
    },
    onSuccess: () => {
      setName("");
      invalidateTemplates();
    },
  });

  const remove = useMutation({
    mutationFn: async (templateId: number) => {
      const { error } = await api.DELETE("/api/nutrition/templates/{template_id}", {
        params: { path: { template_id: templateId } },
      });
      if (error) throw new Error("Could not delete template");
    },
    onSuccess: invalidateTemplates,
  });

  const busy = logTemplate.isPending || saveDay.isPending || remove.isPending;
  const error = logTemplate.error?.message ?? saveDay.error?.message ?? remove.error?.message;
  const list = templates.data ?? [];

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-semibold">Meal templates</h2>
          <p className="text-sm text-zinc-500">Tap a template to log every food in it into {date}.</p>
        </div>
        <div className="flex gap-1" role="group" aria-label="Portion size">
          {TEMPLATE_SCALES.map((value) => (
            <Button
              key={value}
              variant={scale === value ? "primary" : "secondary"}
              className="px-3 text-sm"
              aria-pressed={scale === value}
              onClick={() => setScale(value)}
            >
              ×{value}
            </Button>
          ))}
        </div>
      </div>

      {templates.isLoading ? (
        <p className="text-sm text-zinc-500">Loading templates...</p>
      ) : list.length === 0 ? (
        <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500 dark:bg-zinc-950">
          No templates yet. Log a meal, then save the day below.
        </p>
      ) : (
        <div className="flex flex-col divide-y divide-zinc-100 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {list.map((template) => (
            <TemplateRow
              key={template.id}
              template={template}
              scale={scale}
              busy={busy}
              onLog={() => logTemplate.mutate(template.id)}
              onDelete={() => {
                if (window.confirm(`Delete the "${template.name}" template?`)) {
                  remove.mutate(template.id);
                }
              }}
            />
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
        <Label htmlFor="template-name">Save this day as a template</Label>
        <div className="flex flex-wrap items-end gap-2">
          <Input
            id="template-name"
            className="min-w-0 flex-1"
            placeholder="e.g. Breakfast"
            maxLength={80}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <Button
            variant="secondary"
            disabled={busy || !canSaveDay || !name.trim()}
            onClick={() => saveDay.mutate()}
          >
            {saveDay.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
        <p className="text-xs text-zinc-500">
          {canSaveDay
            ? `Saves every food logged on ${date}, with its macros as they are now.`
            : `Log some food on ${date} first.`}
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </Card>
  );
}

function TemplateRow({
  template,
  scale,
  busy,
  onLog,
  onDelete,
}: {
  template: MealTemplateOut;
  scale: number;
  busy: boolean;
  onLog: () => void;
  onDelete: () => void;
}) {
  const totals = scaledTemplateTotals(template.items, scale);
  const foods = template.items.length;
  return (
    <div className="flex items-center gap-2 p-2">
      <Button
        variant="ghost"
        className="h-auto min-w-0 flex-1 flex-col items-start gap-0.5 px-2 py-2 text-left"
        disabled={busy}
        onClick={onLog}
        title={template.items.map((item) => item.name).join(", ")}
      >
        <span className="w-full truncate font-medium">{template.name}</span>
        <span className="text-xs font-normal text-zinc-500">
          {foods} {foods === 1 ? "food" : "foods"} · {totals.kcal} kcal · P {totals.protein_g}g · C{" "}
          {totals.carbs_g}g · F {totals.fat_g}g
        </span>
      </Button>
      <Button
        variant="ghost"
        className="h-9 min-h-0 shrink-0 px-3 text-sm"
        disabled={busy}
        onClick={onDelete}
      >
        Delete
      </Button>
    </div>
  );
}
