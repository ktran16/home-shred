"use client";

import { useEffect, useState } from "react";
import { useRef } from "react";

import { Button } from "@/components/ui";
import { CYCLE, intervalState, isBoundary } from "@/lib/timer";

function beep() {
  try {
    const w = window as unknown as { webkitAudioContext?: typeof AudioContext };
    const Ctx = window.AudioContext ?? w.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 880;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.4);
    osc.stop(ctx.currentTime + 0.4);
  } catch {
    /* audio not available */
  }
  navigator.vibrate?.(200);
}

/**
 * Sticky bottom rest countdown. Remount (via a changing `key`) to (re)start it —
 * state initialises from `seconds`, so no syncing effect is needed.
 */
export function RestTimer({
  seconds,
  onDismiss,
  onComplete,
}: {
  seconds: number;
  onDismiss: () => void;
  onComplete?: () => void;
}) {
  const [remaining, setRemaining] = useState(seconds);
  const completedRef = useRef(false);

  useEffect(() => {
    if (remaining <= 0) return;
    const t = setTimeout(() => setRemaining((r) => r - 1), 1000);
    return () => clearTimeout(t);
  }, [remaining]);

  useEffect(() => {
    if (remaining <= 0 && !completedRef.current) {
      completedRef.current = true;
      beep(); // side-effect only; fires once when it hits zero
      onComplete?.();
    }
  }, [onComplete, remaining]);

  return (
    <div className="fixed inset-x-0 bottom-14 z-20 mx-auto w-full max-w-md px-4">
      <div className="flex items-center justify-between rounded-2xl bg-zinc-900 px-4 py-3 text-white shadow-lg">
        <span className="text-sm">Rest</span>
        <span className="text-2xl font-bold tabular-nums">
          {remaining > 0 ? `${remaining}s` : "Go!"}
        </span>
        <Button variant="secondary" className="h-9 min-h-0 px-3 text-sm" onClick={onDismiss}>
          {remaining > 0 ? "Skip" : "Done"}
        </Button>
      </div>
    </div>
  );
}

/** Conditioning interval timer: rounds × (40s work / 20s rest) (SPEC §6.7). */
export function ConditioningTimer({ rounds }: { rounds: number }) {
  const total = rounds * CYCLE;
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const { round, phase, remaining, done } = intervalState(elapsed, rounds);

  useEffect(() => {
    if (!running || done) return;
    const id = setInterval(() => setElapsed((e) => Math.min(e + 1, total)), 1000);
    return () => clearInterval(id);
  }, [running, done, total]);

  useEffect(() => {
    if (running && isBoundary(elapsed, rounds)) beep(); // boundary / completion cue
  }, [elapsed, running, rounds]);

  if (done) return <span className="text-sm text-emerald-600">Finished ✓</span>;

  return (
    <div className="flex items-center gap-3">
      <Button
        className="h-9 min-h-0 px-3 text-sm"
        variant={running ? "secondary" : "primary"}
        onClick={() => setRunning((r) => !r)}
      >
        {running ? "Pause" : elapsed === 0 ? "Start" : "Resume"}
      </Button>
      <span className="text-sm tabular-nums">
        Round {round}/{rounds} · {phase} {remaining}s
      </span>
    </div>
  );
}
