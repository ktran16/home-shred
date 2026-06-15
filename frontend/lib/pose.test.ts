import { describe, expect, it } from "vitest";

import {
  jointAngle,
  PATTERN_TRACK,
  POSE,
  trackConfigFor,
  trackedAngle,
  type Landmark,
} from "@/lib/pose";

describe("jointAngle", () => {
  it("measures a right angle", () => {
    const a = { x: 0, y: 1 };
    const b = { x: 0, y: 0 };
    const c = { x: 1, y: 0 };
    expect(jointAngle(a, b, c)).toBeCloseTo(90, 5);
  });

  it("measures a straight (extended) joint as 180", () => {
    expect(jointAngle({ x: -1, y: 0 }, { x: 0, y: 0 }, { x: 1, y: 0 })).toBeCloseTo(180, 5);
  });

  it("returns NaN for a degenerate triple", () => {
    expect(jointAngle({ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 1, y: 0 })).toBeNaN();
  });
});

function bentElbow(angleVisible = true): Landmark[] {
  const lm: Landmark[] = Array.from({ length: 33 }, () => ({ x: 0, y: 0, visibility: 0 }));
  const v = angleVisible ? 0.9 : 0.1;
  // right arm bent to ~90°: shoulder above elbow, wrist to the side of elbow.
  lm[POSE.RIGHT_SHOULDER] = { x: 0, y: 1, visibility: v };
  lm[POSE.RIGHT_ELBOW] = { x: 0, y: 0, visibility: v };
  lm[POSE.RIGHT_WRIST] = { x: 1, y: 0, visibility: v };
  return lm;
}

describe("trackedAngle", () => {
  const elbow = PATTERN_TRACK.horizontal_push!;

  it("computes the tracked joint angle from visible landmarks", () => {
    expect(trackedAngle(bentElbow(), elbow)).toBeCloseTo(90, 5);
  });

  it("returns null when the joint is not visible enough", () => {
    expect(trackedAngle(bentElbow(false), elbow)).toBeNull();
  });
});

describe("trackConfigFor", () => {
  it("returns a config for single-joint movements", () => {
    expect(trackConfigFor("squat")?.joint).toBe("knee");
    expect(trackConfigFor("vertical_pull")?.joint).toBe("elbow");
  });

  it("returns null for untracked patterns and nullish input", () => {
    expect(trackConfigFor("core")).toBeNull();
    expect(trackConfigFor("conditioning")).toBeNull();
    expect(trackConfigFor(null)).toBeNull();
    expect(trackConfigFor(undefined)).toBeNull();
  });
});
