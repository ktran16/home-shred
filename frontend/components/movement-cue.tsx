import type { ExerciseOut } from "@/lib/api";
import { movementLabel } from "@/lib/exercise-cues";
import { cn } from "@/lib/utils";

export function MovementCue({
  pattern,
  compact = false,
}: {
  pattern: ExerciseOut["pattern"];
  compact?: boolean;
}) {
  return (
    <div
      className={cn(
        "motion-cue relative overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950",
        compact ? "h-16 w-24" : "h-36 w-full",
      )}
      data-pattern={pattern ?? "strength"}
      aria-label={`${movementLabel(pattern)} movement cue`}
    >
      <div className="motion-floor" />
      <div className="motion-figure">
        <span className="motion-head" />
        <span className="motion-torso" />
        <span className="motion-arm motion-arm-left" />
        <span className="motion-arm motion-arm-right" />
        <span className="motion-leg motion-leg-left" />
        <span className="motion-leg motion-leg-right" />
      </div>
      {!compact && (
        <div className="absolute left-3 top-3 rounded-full bg-white/85 px-2 py-1 text-xs font-semibold text-zinc-700 shadow-sm dark:bg-zinc-900/85 dark:text-zinc-200">
          {movementLabel(pattern)}
        </div>
      )}
    </div>
  );
}
