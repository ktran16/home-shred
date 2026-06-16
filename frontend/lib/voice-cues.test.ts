import { describe, expect, it } from "vitest";

import type { PlanExerciseOut } from "@/lib/api";
import {
  exerciseVoiceCue,
  pickCoachVoice,
  restCompleteCue,
  restStartedCue,
} from "@/lib/voice-cues";

const voice = (
  name: string,
  lang: string,
  localService = true,
): SpeechSynthesisVoice =>
  ({ name, lang, localService, default: false, voiceURI: name }) as SpeechSynthesisVoice;

const pe = {
  id: 1,
  exercise_id: 1,
  order_index: 1,
  sets: 3,
  target_reps_min: 8,
  target_reps_max: 12,
  rest_seconds: 75,
  is_conditioning: false,
  exercise: {
    id: 1,
    name: "Push-Up",
    slug: "push-up",
    equipment: "bodyweight",
    pattern: "horizontal_push",
    category: "push",
    primary_muscles: ["chest"],
    secondary_muscles: ["triceps"],
    level: "beginner",
    is_compound: true,
    instructions: ["Brace.", "Lower with control."],
  },
} satisfies PlanExerciseOut;

describe("voice cues", () => {
  it("formats an exercise voice-over cue", () => {
    expect(exerciseVoiceCue(pe, 3)).toContain("Push-Up. Push. 3 sets.");
    expect(exerciseVoiceCue(pe, 3)).toContain("Brace.");
  });

  it("formats rest cues", () => {
    expect(restStartedCue(75)).toBe("Set logged. Rest 75 seconds.");
    expect(restCompleteCue()).toBe("Rest complete. Start your next set.");
  });

  it("formats Vietnamese cues when lang is vi", () => {
    const cue = exerciseVoiceCue(pe, 3, "vi");
    expect(cue).toContain("Push-Up. Đẩy ngang. 3 hiệp.");
    expect(cue).toContain("Lưu ý.");
    // seeded English instructions are not spoken in Vietnamese
    expect(cue).not.toContain("Brace.");
    expect(restStartedCue(75, "vi")).toBe("Đã ghi hiệp. Nghỉ 75 giây.");
    expect(restCompleteCue("vi")).toBe("Hết giờ nghỉ. Bắt đầu hiệp tiếp theo.");
  });
});

describe("pickCoachVoice", () => {
  it("returns null when no voices are available", () => {
    expect(pickCoachVoice([])).toBeNull();
  });

  it("prefers a natural/neural English voice over a robotic default", () => {
    const voices = [
      voice("English (robotic)", "en-US"),
      voice("Microsoft Aria Online (Natural)", "en-US", false),
    ];
    expect(pickCoachVoice(voices)?.name).toBe("Microsoft Aria Online (Natural)");
  });

  it("falls back to a network voice, then any English voice", () => {
    const network = voice("SomeCloud Voice", "en-GB", false);
    expect(pickCoachVoice([voice("Local en", "en-US"), network])?.name).toBe(
      "SomeCloud Voice",
    );
    expect(pickCoachVoice([voice("Local en", "en-GB")])?.name).toBe("Local en");
  });

  it("ignores non-English voices when an English one exists", () => {
    const voices = [voice("Google US English", "en-US", false), voice("Amélie", "fr-FR")];
    expect(pickCoachVoice(voices)?.lang).toBe("en-US");
  });
});
