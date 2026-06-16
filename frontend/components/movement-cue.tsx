import type { ExerciseOut } from "@/lib/api";
import { movementGuide, movementLabel } from "@/lib/exercise-cues";
import { cn } from "@/lib/utils";

export function MovementCue({
  pattern,
  compact = false,
}: {
  pattern: ExerciseOut["pattern"];
  compact?: boolean;
}) {
  const guide = movementGuide(pattern);

  return (
    <div
      className={cn(
        "motion-cue relative overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950",
        compact ? "h-16 w-24" : "min-h-64 w-full",
      )}
      data-pattern={pattern ?? "strength"}
      aria-label={`${movementLabel(pattern)} movement cue`}
    >
      <div className="motion-stage" aria-hidden="true">
        <div className="motion-range">
          <span className="motion-range-marker motion-range-start" />
          <span className="motion-range-marker motion-range-end" />
          <span className="motion-range-tracer" />
        </div>
        <div className="motion-floor" />
        <div className="motion-figure">
          <span className="motion-head" />
          <span className="motion-torso" />
          <span className="motion-arm motion-arm-left" />
          <span className="motion-arm motion-arm-right" />
          <span className="motion-leg motion-leg-left" />
          <span className="motion-leg motion-leg-right" />
        </div>
      </div>
      {compact ? (
        <div className="absolute bottom-1.5 left-2 right-2 truncate rounded-full bg-white/90 px-2 py-0.5 text-center text-[10px] font-semibold text-zinc-700 shadow-sm dark:bg-zinc-900/90 dark:text-zinc-200">
          {guide.label}
        </div>
      ) : (
        <div className="relative z-10 flex min-h-64 flex-col justify-between p-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-xs font-medium uppercase text-zinc-500">Movement guide</div>
              <div className="mt-0.5 text-lg font-bold">{guide.label}</div>
            </div>
            <div className="rounded-full border border-zinc-200 bg-white/90 px-2 py-1 text-xs font-semibold text-zinc-700 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90 dark:text-zinc-200">
              tempo {guide.tempo}
            </div>
          </div>
          <div className="mt-28 grid gap-2">
            <div className="grid grid-cols-3 gap-1 text-center text-[10px] font-semibold uppercase text-zinc-500">
              <span>Setup</span>
              <span>Move</span>
              <span>Check</span>
            </div>
            <div className="grid grid-cols-3 gap-1">
              <span className="h-1.5 rounded-full bg-emerald-500" />
              <span className="h-1.5 rounded-full bg-sky-500" />
              <span className="h-1.5 rounded-full bg-amber-500" />
            </div>
            <div className="rounded-lg border border-zinc-200 bg-white/90 p-3 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90">
              <dl className="grid gap-2 text-sm">
                <div>
                  <dt className="text-xs font-semibold uppercase text-zinc-500">Setup</dt>
                  <dd className="text-zinc-800 dark:text-zinc-200">{guide.setup}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-zinc-500">Action</dt>
                  <dd className="text-zinc-800 dark:text-zinc-200">{guide.action}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-zinc-500">Range</dt>
                  <dd className="text-zinc-800 dark:text-zinc-200">
                    {guide.range}. {guide.checkpoint}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
