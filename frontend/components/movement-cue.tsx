"use client";

import { useSyncExternalStore } from "react";

import type { ExerciseOut } from "@/lib/api";
import { movementGuide, movementLabel } from "@/lib/exercise-cues";

type Pattern = NonNullable<ExerciseOut["pattern"]>;

// A jointed side-view figure (facing right). Each limb is two segments that
// pivot at the joint above it, so the figure actually performs the lift instead
// of waving a single stick. Angles are degrees of clockwise rotation; segments
// are drawn pointing straight down, so a downward limb at +angle swings toward
// the back and at -angle toward the front. All keyframe lists have three stops
// (start -> peak -> start) so the loop returns home smoothly.
type MovementAnim = {
  dur: number;
  /** whole-figure translate, e.g. drop for a squat or rise for a pull-up */
  figure?: [string, string, string];
  torso?: [number, number, number];
  upperArmNear?: [number, number, number];
  foreArmNear?: [number, number, number];
  upperArmFar?: [number, number, number];
  foreArmFar?: [number, number, number];
  thighNear?: [number, number, number];
  shinNear?: [number, number, number];
  thighFar?: [number, number, number];
  shinFar?: [number, number, number];
};

const ANIMS: Record<Pattern, MovementAnim> = {
  horizontal_push: {
    dur: 2.6,
    upperArmNear: [-82, -82, -82],
    foreArmNear: [-72, 2, -72],
  },
  vertical_push: {
    dur: 2.6,
    upperArmNear: [-150, -180, -150],
    foreArmNear: [-55, 0, -55],
  },
  horizontal_pull: {
    dur: 2.4,
    torso: [28, 28, 28],
    upperArmNear: [-72, -14, -72],
    foreArmNear: [-8, -64, -8],
  },
  vertical_pull: {
    dur: 2.6,
    figure: ["0 0", "0 -20", "0 0"],
    upperArmNear: [-165, -180, -165],
    foreArmNear: [-8, -55, -8],
  },
  squat: {
    dur: 2.8,
    figure: ["0 0", "0 26", "0 0"],
    torso: [4, 20, 4],
    upperArmNear: [0, -72, 0],
    thighNear: [0, -38, 0],
    shinNear: [0, 42, 0],
  },
  hinge: {
    dur: 2.8,
    torso: [2, 70, 2],
    upperArmNear: [0, -56, 0],
    thighNear: [0, 8, 0],
  },
  core: {
    dur: 2.8,
    torso: [2, 34, 2],
    upperArmNear: [-10, -44, -10],
    thighNear: [-6, -46, -6],
    shinNear: [0, 40, 0],
  },
  conditioning: {
    dur: 1.1,
    torso: [8, 8, 8],
    figure: ["0 0", "0 -6", "0 0"],
    upperArmNear: [-28, 20, -28],
    upperArmFar: [20, -28, 20],
    foreArmNear: [-70, -70, -70],
    foreArmFar: [-70, -70, -70],
    thighNear: [26, -26, 26],
    thighFar: [-26, 26, -26],
    shinNear: [52, 14, 52],
    shinFar: [14, 52, 14],
  },
};

const DEFAULT_ANIM: MovementAnim = {
  dur: 3,
  figure: ["0 0", "0 -3", "0 0"],
};

// ease-in-out for both segments of a 3-stop loop
const SPLINES = "0.4 0 0.6 1;0.4 0 0.6 1";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mq = window.matchMedia(REDUCED_MOTION_QUERY);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches,
    () => false,
  );
}

function Rotate({
  vals,
  dur,
  animate,
  children,
}: {
  vals?: [number, number, number];
  dur: number;
  animate: boolean;
  children: React.ReactNode;
}) {
  return (
    <g>
      {animate && vals ? (
        <animateTransform
          attributeName="transform"
          attributeType="XML"
          type="rotate"
          dur={`${dur}s`}
          repeatCount="indefinite"
          calcMode="spline"
          keyTimes="0;0.5;1"
          keySplines={SPLINES}
          values={vals.map((v) => `${v} 0 0`).join(";")}
        />
      ) : null}
      {children}
    </g>
  );
}

/** A rounded limb segment from the joint origin (0,0) downward by `len`. */
function Segment({
  len,
  width,
  color,
  up = false,
}: {
  len: number;
  width: number;
  color: string;
  up?: boolean;
}) {
  return (
    <line
      x1={0}
      y1={0}
      x2={0}
      y2={up ? -len : len}
      stroke={color}
      strokeWidth={width}
      strokeLinecap="round"
    />
  );
}

const MAIN = "var(--figure-main)";
const MUTED = "var(--figure-muted)";

function Leg({
  thigh,
  shin,
  color,
  dur,
  animate,
}: {
  thigh?: [number, number, number];
  shin?: [number, number, number];
  color: string;
  dur: number;
  animate: boolean;
}) {
  return (
    <Rotate vals={thigh} dur={dur} animate={animate}>
      <Segment len={32} width={7} color={color} />
      <circle cx={0} cy={32} r={3} fill={color} />
      <g transform="translate(0,32)">
        <Rotate vals={shin} dur={dur} animate={animate}>
          <Segment len={34} width={7} color={color} />
          <line
            x1={0}
            y1={34}
            x2={13}
            y2={34}
            stroke={color}
            strokeWidth={7}
            strokeLinecap="round"
          />
        </Rotate>
      </g>
    </Rotate>
  );
}

function Arm({
  upper,
  fore,
  color,
  dur,
  animate,
}: {
  upper?: [number, number, number];
  fore?: [number, number, number];
  color: string;
  dur: number;
  animate: boolean;
}) {
  return (
    <Rotate vals={upper} dur={dur} animate={animate}>
      <Segment len={26} width={6} color={color} />
      <g transform="translate(0,26)">
        <Rotate vals={fore} dur={dur} animate={animate}>
          <Segment len={24} width={6} color={color} />
        </Rotate>
      </g>
    </Rotate>
  );
}

function Figure({ anim, animate }: { anim: MovementAnim; animate: boolean }) {
  const thighFar = anim.thighFar ?? anim.thighNear;
  const shinFar = anim.shinFar ?? anim.shinNear;
  const upperArmFar = anim.upperArmFar ?? anim.upperArmNear;
  const foreArmFar = anim.foreArmFar ?? anim.foreArmNear;

  const root = (
    <g transform="translate(100,120)">
      {/* far (back) leg, drawn behind everything */}
      <g opacity={0.4}>
        <Leg thigh={thighFar} shin={shinFar} color={MUTED} dur={anim.dur} animate={animate} />
      </g>

      {/* torso assembly pivots at the hip; head + arms ride along with it */}
      <Rotate vals={anim.torso} dur={anim.dur} animate={animate}>
        <Segment len={52} width={9} color={MAIN} up />
        <circle
          cx={0}
          cy={-64}
          r={12}
          fill="var(--cue-accent)"
          stroke={MAIN}
          strokeWidth={2}
        />
        <g transform="translate(0,-50)">
          <circle cx={0} cy={0} r={3.5} fill={MAIN} />
          {/* far arm */}
          <g opacity={0.4}>
            <Arm
              upper={upperArmFar}
              fore={foreArmFar}
              color={MUTED}
              dur={anim.dur}
              animate={animate}
            />
          </g>
          {/* near arm */}
          <Arm
            upper={anim.upperArmNear}
            fore={anim.foreArmNear}
            color={MAIN}
            dur={anim.dur}
            animate={animate}
          />
        </g>
      </Rotate>

      {/* hip joint + near (front) leg */}
      <circle cx={0} cy={0} r={4} fill={MAIN} />
      <Leg
        thigh={anim.thighNear}
        shin={anim.shinNear}
        color={MAIN}
        dur={anim.dur}
        animate={animate}
      />
    </g>
  );

  if (!animate || !anim.figure) return root;

  return (
    <g>
      <animateTransform
        attributeName="transform"
        attributeType="XML"
        type="translate"
        dur={`${anim.dur}s`}
        repeatCount="indefinite"
        calcMode="spline"
        keyTimes="0;0.5;1"
        keySplines={SPLINES}
        values={anim.figure.join(";")}
      />
      {root}
    </g>
  );
}

function MovementStage({ pattern }: { pattern: ExerciseOut["pattern"] }) {
  const reduced = usePrefersReducedMotion();
  const anim = pattern ? ANIMS[pattern] : DEFAULT_ANIM;

  return (
    <svg
      viewBox="0 0 200 210"
      className="absolute inset-0 h-full w-full"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      <line
        x1={40}
        y1={186}
        x2={160}
        y2={186}
        stroke="var(--cue-accent)"
        strokeWidth={3}
        strokeLinecap="round"
        opacity={0.5}
      />
      <Figure anim={anim} animate={!reduced} />
    </svg>
  );
}

export function MovementCue({
  pattern,
  compact = false,
}: {
  pattern: ExerciseOut["pattern"];
  compact?: boolean;
}) {
  const guide = movementGuide(pattern);

  if (compact) {
    return (
      <div
        className="motion-cue relative h-16 w-24 overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
        data-pattern={pattern ?? "strength"}
        aria-label={`${movementLabel(pattern)} movement cue`}
      >
        <MovementStage pattern={pattern} />
        <div className="absolute bottom-1.5 left-2 right-2 truncate rounded-full bg-white/90 px-2 py-0.5 text-center text-[10px] font-semibold text-zinc-700 shadow-sm dark:bg-zinc-900/90 dark:text-zinc-200">
          {guide.label}
        </div>
      </div>
    );
  }

  return (
    <div
      className="motion-cue overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950"
      data-pattern={pattern ?? "strength"}
      aria-label={`${movementLabel(pattern)} movement cue`}
    >
      <div className="relative h-48 w-full">
        <MovementStage pattern={pattern} />
        <div className="absolute left-3 right-3 top-3 flex items-start justify-between gap-2">
          <div>
            <div className="text-xs font-medium uppercase text-zinc-500">Movement guide</div>
            <div className="mt-0.5 text-lg font-bold">{guide.label}</div>
          </div>
          <div className="rounded-full border border-zinc-200 bg-white/90 px-2 py-1 text-xs font-semibold text-zinc-700 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90 dark:text-zinc-200">
            tempo {guide.tempo}
          </div>
        </div>
      </div>
      <div className="border-t border-zinc-200 p-3 dark:border-zinc-800">
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
  );
}
