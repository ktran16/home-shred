"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, Input } from "@/components/ui";
import { api, type FoodFactsOut, type FoodLogIn } from "@/lib/api";
import { foodTitle, macrosForGrams } from "@/lib/food";

// Search foods by name via Open Food Facts (cached locally; SPEC §19.8 W2). Closes the
// gap where logging needed a barcode or fully manual macros. Reuses lib/food scaling and
// the same FoodLogIn shape the barcode path uses.
export function FoodSearchCard({
  onLog,
  logging = false,
}: {
  onLog?: (entry: FoodLogIn) => void;
  logging?: boolean;
}) {
  const [term, setTerm] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [selected, setSelected] = useState<FoodFactsOut | null>(null);
  const [grams, setGrams] = useState("100");

  const search = useQuery({
    queryKey: ["food-search", submitted],
    enabled: submitted.trim().length > 0,
    retry: false,
    queryFn: async () => {
      const { data } = await api.GET("/api/nutrition/food/search", {
        params: { query: { q: submitted.trim(), limit: 10 } },
      });
      return data ?? [];
    },
  });

  const results = search.data ?? [];
  const gramsNum = Number(grams) || 0;
  const macros = selected ? macrosForGrams(selected, gramsNum) : null;
  const canLog =
    !!selected &&
    gramsNum > 0 &&
    macros?.kcal != null &&
    macros.protein != null &&
    macros.carbs != null &&
    macros.fat != null;

  return (
    <Card className="flex flex-col gap-3">
      <div>
        <h2 className="font-semibold">Search a food</h2>
        <p className="text-sm text-zinc-500">
          Find foods by name (Open Food Facts, cached locally) — no barcode needed.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="e.g. chicken breast"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") setSubmitted(term);
          }}
        />
        <Button className="shrink-0" disabled={term.trim() === ""} onClick={() => setSubmitted(term)}>
          Search
        </Button>
      </div>

      {submitted.trim() !== "" && (
        <div className="flex flex-col gap-2">
          {search.isLoading ? (
            <p className="text-sm text-zinc-500">Searching “{submitted}”…</p>
          ) : search.isError ? (
            <p className="text-sm text-amber-600">Search failed. Try again later.</p>
          ) : results.length === 0 ? (
            <p className="text-sm text-zinc-500">No foods found for “{submitted}”.</p>
          ) : (
            <div className="flex flex-col divide-y divide-zinc-100 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
              {results.map((food) => (
                <button
                  key={food.code}
                  onClick={() => setSelected(food)}
                  className={[
                    "flex items-center justify-between gap-3 p-3 text-left",
                    selected?.code === food.code ? "bg-emerald-50 dark:bg-emerald-950/40" : "",
                  ].join(" ")}
                >
                  <div className="min-w-0">
                    <div className="truncate font-medium">{foodTitle(food)}</div>
                    <div className="text-xs text-zinc-500">
                      {food.kcal_per_100g == null ? "—" : `${food.kcal_per_100g} kcal`} / 100g
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {selected && (
        <div className="flex flex-col gap-2 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
          <div className="font-medium">{foodTitle(selected)}</div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-500">Amount</span>
            <Input
              type="number"
              inputMode="numeric"
              className="h-9 w-24"
              value={grams}
              onChange={(e) => setGrams(e.target.value)}
            />
            <span className="text-sm text-zinc-500">g</span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-center">
            <Macro label="kcal" value={macros?.kcal} />
            <Macro label="P" value={macros?.protein} unit="g" />
            <Macro label="C" value={macros?.carbs} unit="g" />
            <Macro label="F" value={macros?.fat} unit="g" />
          </div>
          {onLog && (
            <Button
              disabled={!canLog || logging}
              onClick={() => {
                if (!selected || !canLog) return;
                onLog({
                  name: foodTitle(selected),
                  grams: Math.round(gramsNum * 10) / 10,
                  kcal: macros.kcal!,
                  protein_g: macros.protein!,
                  carbs_g: macros.carbs!,
                  fat_g: macros.fat!,
                  source: "barcode",
                  barcode: selected.code || null,
                });
              }}
            >
              {logging ? "Adding..." : "Add to log"}
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}

function Macro({ label, value, unit = "" }: { label: string; value: number | null | undefined; unit?: string }) {
  return (
    <div className="rounded-lg bg-white p-2 dark:bg-zinc-900">
      <div className="text-lg font-bold tabular-nums">{value == null ? "—" : `${value}${unit}`}</div>
      <div className="text-[10px] text-zinc-500">{label}</div>
    </div>
  );
}
