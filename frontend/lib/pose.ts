import type { ExerciseOut } from "@/lib/api";

/**
 * Pure pose-geometry helpers for on-device rep counting (SPEC §17.5 B2a).
 *
 * These run on MediaPipe Pose / MoveNet landmarks produced in the browser — no
 * video ever leaves the phone. Everything here is deterministic and unit-testable;
 * the camera + model wiring lives in `components/pose-rep-counter.tsx`.
 */

export type Pattern = NonNullable<ExerciseOut["pattern"]>;

export type Landmark = { x: number; y: number; z?: number; visibility?: number };

/** MediaPipe Pose (BlazePose) landmark indices we use. */
export const POSE = {
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
} as const;

export type Joint = "elbow" | "knee" | "hip";

export type TrackConfig = {
  /** human label for the tracked joint, e.g. "Knee". */
  label: string;
  joint: Joint;
  /** below this angle (deg) the lifter is in the contracted/bottom position. */
  downAngle: number;
  /** above this angle (deg) the lifter is extended/locked out. */
  upAngle: number;
  /** full-ROM goal: the bottom angle should reach at or below this. */
  targetBottom: number;
};

// rationale (SPEC §17.5 B2a): each movement maps to one joint whose flexion drives
// the rep. Low angle = contracted (squat bottom, push-up bottom, pull-up top),
// high angle = extended/locked. Thresholds use hysteresis (down < up) to avoid
// double-counting jitter at the turnaround. Core/conditioning aren't single-joint
// reps → not tracked.
export const PATTERN_TRACK: Record<Pattern, TrackConfig | null> = {
  squat: { label: "Knee", joint: "knee", downAngle: 110, upAngle: 160, targetBottom: 100 },
  hinge: { label: "Hip", joint: "hip", downAngle: 120, upAngle: 160, targetBottom: 105 },
  horizontal_push: { label: "Elbow", joint: "elbow", downAngle: 100, upAngle: 155, targetBottom: 95 },
  vertical_push: { label: "Elbow", joint: "elbow", downAngle: 100, upAngle: 155, targetBottom: 95 },
  horizontal_pull: { label: "Elbow", joint: "elbow", downAngle: 95, upAngle: 150, targetBottom: 85 },
  vertical_pull: { label: "Elbow", joint: "elbow", downAngle: 90, upAngle: 150, targetBottom: 80 },
  core: null,
  conditioning: null,
};

const JOINT_TRIPLES: Record<Joint, { left: [number, number, number]; right: [number, number, number] }> = {
  elbow: {
    left: [POSE.LEFT_SHOULDER, POSE.LEFT_ELBOW, POSE.LEFT_WRIST],
    right: [POSE.RIGHT_SHOULDER, POSE.RIGHT_ELBOW, POSE.RIGHT_WRIST],
  },
  knee: {
    left: [POSE.LEFT_HIP, POSE.LEFT_KNEE, POSE.LEFT_ANKLE],
    right: [POSE.RIGHT_HIP, POSE.RIGHT_KNEE, POSE.RIGHT_ANKLE],
  },
  hip: {
    left: [POSE.LEFT_SHOULDER, POSE.LEFT_HIP, POSE.LEFT_KNEE],
    right: [POSE.RIGHT_SHOULDER, POSE.RIGHT_HIP, POSE.RIGHT_KNEE],
  },
};

/** Interior angle (degrees) at vertex `b` of the triangle a-b-c. NaN if degenerate. */
export function jointAngle(a: Landmark, b: Landmark, c: Landmark): number {
  const v1 = { x: a.x - b.x, y: a.y - b.y };
  const v2 = { x: c.x - b.x, y: c.y - b.y };
  const m1 = Math.hypot(v1.x, v1.y);
  const m2 = Math.hypot(v2.x, v2.y);
  if (m1 === 0 || m2 === 0) return NaN;
  const cos = Math.min(1, Math.max(-1, (v1.x * v2.x + v1.y * v2.y) / (m1 * m2)));
  return (Math.acos(cos) * 180) / Math.PI;
}

/**
 * Tracked joint angle for a movement, averaging whichever side(s) are confidently
 * visible. Returns null when neither side is visible enough to trust.
 */
export function trackedAngle(
  landmarks: Landmark[],
  config: TrackConfig,
  minVisibility = 0.5,
): number | null {
  const triples = JOINT_TRIPLES[config.joint];
  const values: number[] = [];
  for (const side of [triples.left, triples.right]) {
    const pts = side.map((i) => landmarks[i]);
    if (pts.some((p) => !p || (p.visibility ?? 1) < minVisibility)) continue;
    const angle = jointAngle(pts[0], pts[1], pts[2]);
    if (!Number.isNaN(angle)) values.push(angle);
  }
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function trackConfigFor(pattern: Pattern | null | undefined): TrackConfig | null {
  return pattern ? PATTERN_TRACK[pattern] : null;
}
