import type { ExerciseOut } from "@/lib/api";

type Pattern = NonNullable<ExerciseOut["pattern"]>;

const PATTERN_CUES: Record<NonNullable<ExerciseOut["pattern"]>, string[]> = {
  horizontal_push: ["Brace ribs down.", "Lower under control.", "Drive the floor away."],
  vertical_push: ["Stack ribs over hips.", "Press overhead.", "Finish with biceps near ears."],
  horizontal_pull: ["Hinge and brace.", "Pull elbow past ribs.", "Lower without twisting."],
  vertical_pull: ["Start from a dead hang.", "Pull chest toward the bar.", "Lower to straight arms."],
  squat: ["Brace before descending.", "Knees track over toes.", "Stand tall through midfoot."],
  hinge: ["Push hips back.", "Keep spine long.", "Squeeze glutes to stand."],
  core: ["Lock ribs and pelvis.", "Move slowly.", "Stop before form breaks."],
  conditioning: ["Stay springy.", "Keep breathing steady.", "Move fast without rushing reps."],
};

const PATTERN_LABELS: Record<NonNullable<ExerciseOut["pattern"]>, string> = {
  horizontal_push: "Push",
  vertical_push: "Overhead press",
  horizontal_pull: "Row",
  vertical_pull: "Pull",
  squat: "Squat",
  hinge: "Hinge",
  core: "Core",
  conditioning: "Conditioning",
};

export type MovementGuide = {
  label: string;
  setup: string;
  action: string;
  checkpoint: string;
  tempo: string;
  range: string;
};

const DEFAULT_MOVEMENT_GUIDE: MovementGuide = {
  label: "Strength",
  setup: "Set your brace before each rep.",
  action: "Move through a controlled full range.",
  checkpoint: "Stop the set when position breaks.",
  tempo: "2-1-1",
  range: "start to finish",
};

const PATTERN_GUIDES: Record<Pattern, MovementGuide> = {
  horizontal_push: {
    label: "Push",
    setup: "Hands fixed, ribs down, shoulder blades controlled.",
    action: "Lower chest toward the floor, then press away.",
    checkpoint: "Elbows track about 30-45 degrees from your ribs.",
    tempo: "3-0-1",
    range: "top to chest",
  },
  vertical_push: {
    label: "Overhead press",
    setup: "Brace ribs over hips before the press.",
    action: "Drive the load overhead in a straight line.",
    checkpoint: "Finish stacked with biceps near ears.",
    tempo: "2-0-1",
    range: "shoulders to lockout",
  },
  horizontal_pull: {
    label: "Row",
    setup: "Hinge, brace, and keep the torso quiet.",
    action: "Pull elbow past ribs, then lower with control.",
    checkpoint: "No twisting or shoulder shrug at the top.",
    tempo: "2-1-2",
    range: "reach to ribs",
  },
  vertical_pull: {
    label: "Pull",
    setup: "Start tall from a dead hang.",
    action: "Pull chest toward the bar, then return to straight arms.",
    checkpoint: "Lead with elbows, not the chin.",
    tempo: "2-1-2",
    range: "hang to chest",
  },
  squat: {
    label: "Squat",
    setup: "Brace, feet planted, pressure through midfoot.",
    action: "Sit between the hips, then stand tall.",
    checkpoint: "Knees track over toes through the whole rep.",
    tempo: "3-1-1",
    range: "stand to depth",
  },
  hinge: {
    label: "Hinge",
    setup: "Soften knees and lock in a long spine.",
    action: "Push hips back, then squeeze glutes to stand.",
    checkpoint: "Shins stay nearly vertical as hips travel back.",
    tempo: "3-1-1",
    range: "hips back to tall",
  },
  core: {
    label: "Core",
    setup: "Lock ribs and pelvis before moving.",
    action: "Move slowly without letting the trunk rotate or sag.",
    checkpoint: "Keep breathing behind the brace.",
    tempo: "steady",
    range: "brace maintained",
  },
  conditioning: {
    label: "Conditioning",
    setup: "Pick a pace you can repeat every round.",
    action: "Move fast, but keep reps crisp.",
    checkpoint: "Breathe on rhythm and avoid sloppy landings.",
    tempo: "smooth",
    range: "repeatable pace",
  },
};

export type WarmupDrillGuide = {
  name: string;
  duration: string;
  intent: string;
  cue: string;
};

const WARMUP_GUIDES: Record<string, Omit<WarmupDrillGuide, "name">> = {
  "Nasal breathing reset": {
    duration: "4-5 breaths",
    intent: "Downshift and find a full exhale before loading.",
    cue: "Exhale until ribs drop, then inhale quietly through the nose.",
  },
  "Scapular push-ups": {
    duration: "8-10 reps",
    intent: "Warm shoulder blade control for pressing.",
    cue: "Keep elbows straight and move only the shoulder blades.",
  },
  "Incline push-up ramp sets": {
    duration: "1 easy set",
    intent: "Rehearse the press pattern without fatigue.",
    cue: "Use a higher hand position and stop with reps in reserve.",
  },
  "Arm circles": {
    duration: "20 sec each way",
    intent: "Open the shoulders before overhead work.",
    cue: "Keep ribs down while circles gradually get larger.",
  },
  "Light dumbbell press ramp sets": {
    duration: "1-2 easy sets",
    intent: "Groove the overhead line before work sets.",
    cue: "Start light enough that every rep finishes stacked.",
  },
  "Hip hinge holds": {
    duration: "3 x 5 sec",
    intent: "Find a stable hinge for rows.",
    cue: "Push hips back and hold a long spine.",
  },
  "Light one-arm row ramp sets": {
    duration: "8 reps each",
    intent: "Wake up lats and upper-back tension.",
    cue: "Pause with elbow by ribs without rotating.",
  },
  "Dead hangs": {
    duration: "2 x 10-20 sec",
    intent: "Prepare grip and overhead shoulder position.",
    cue: "Let arms straighten while ribs stay controlled.",
  },
  "Scapular pull-ups": {
    duration: "6-8 reps",
    intent: "Prime the first pull from the shoulder blades.",
    cue: "Pull shoulders away from ears before bending elbows.",
  },
  "Bodyweight squats": {
    duration: "10-12 reps",
    intent: "Warm knees, hips, and squat depth.",
    cue: "Pause briefly at depth and keep feet heavy.",
  },
  "Reverse lunges": {
    duration: "6 each side",
    intent: "Prepare single-leg control and hip stability.",
    cue: "Step back softly and drive through the front foot.",
  },
  "Hip hinges": {
    duration: "10 reps",
    intent: "Practice hip travel before loaded hinges.",
    cue: "Reach hips back while shins stay almost vertical.",
  },
  "Glute bridges": {
    duration: "10-12 reps",
    intent: "Turn on glutes before hinge or squat work.",
    cue: "Tuck pelvis slightly and pause at the top.",
  },
  "Dead bugs": {
    duration: "6 each side",
    intent: "Coordinate breathing with trunk control.",
    cue: "Keep low back quiet while limbs move.",
  },
  "Plank breathing": {
    duration: "20-30 sec",
    intent: "Build a brace you can breathe behind.",
    cue: "Push the floor away and take small controlled breaths.",
  },
  "Marching high knees": {
    duration: "30 sec",
    intent: "Raise temperature without rushing.",
    cue: "Stay tall and land softly under the hips.",
  },
  "Easy mountain climbers": {
    duration: "30 sec",
    intent: "Prepare hands, trunk, and breathing.",
    cue: "Move at a pace where hips do not bounce.",
  },
  "First exercise ramp-up set": {
    duration: "1-2 sets",
    intent: "Bridge from warm-up to the first work set.",
    cue: "Use about half effort, then rest before logging set one.",
  },
};

export function movementLabel(pattern: ExerciseOut["pattern"]): string {
  return pattern ? PATTERN_LABELS[pattern] : "Strength";
}

export function movementGuide(pattern: ExerciseOut["pattern"]): MovementGuide {
  return pattern ? PATTERN_GUIDES[pattern] : DEFAULT_MOVEMENT_GUIDE;
}

export function exerciseInstructions(exercise: ExerciseOut, limit = 3): string[] {
  const seeded = exercise.instructions.filter(Boolean).slice(0, limit);
  if (seeded.length > 0) return seeded;
  return exercise.pattern ? PATTERN_CUES[exercise.pattern].slice(0, limit) : [];
}

export function primaryMuscleText(exercise: ExerciseOut): string {
  return exercise.primary_muscles.slice(0, 3).join(", ");
}

export function warmupDrillGuide(name: string): WarmupDrillGuide {
  return {
    name,
    ...(WARMUP_GUIDES[name] ?? {
      duration: "30-45 sec",
      intent: "Prepare the movement without fatigue.",
      cue: "Keep it easy and controlled.",
    }),
  };
}
