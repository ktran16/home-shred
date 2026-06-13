"""Curated exercise → (pattern, equipment, is_compound) mapping (SPEC §6, Phase 1).

The free-exercise-db dataset has coarse `equipment` values ("body only", "other",
null) and no movement-pattern field. The seed script (SPEC §1, §5) keeps only
exercises whose equipment maps to our hard-constraint set {bodyweight, dumbbell,
pull_up_bar}. This module is the curation layer: it overrides equipment to the
exact allowed value and assigns the `MovementPattern` + `is_compound` the generator
relies on for balanced selection.

Keyed by the free-exercise-db `id` (which we also use as our `slug`).
Note: the dataset has no "burpee"; conditioning is covered by plyometric jumps,
mountain climbers and a dumbbell swing.
"""

from typing import NamedTuple

from app.enums import Equipment, MovementPattern


class Curation(NamedTuple):
    pattern: MovementPattern
    equipment: Equipment
    is_compound: bool


# rationale: pattern → category buckets (SPEC §5 category column, §6.3 focus slots).
PATTERN_CATEGORY: dict[MovementPattern, str] = {
    MovementPattern.HORIZONTAL_PUSH: "push",
    MovementPattern.VERTICAL_PUSH: "push",
    MovementPattern.HORIZONTAL_PULL: "pull",
    MovementPattern.VERTICAL_PULL: "pull",
    MovementPattern.SQUAT: "legs",
    MovementPattern.HINGE: "legs",
    MovementPattern.CORE: "core",
    MovementPattern.CONDITIONING: "conditioning",
}

_P = MovementPattern
_E = Equipment

# rationale: only equipment ∈ {bodyweight, dumbbell, pull_up_bar} (SPEC §1 hard
# constraint). ≥3 entries per non-conditioning pattern is asserted by the seed.
CURATION: dict[str, Curation] = {
    # --- horizontal push ---
    "Pushups": Curation(_P.HORIZONTAL_PUSH, _E.BODYWEIGHT, True),
    "Push-Up_Wide": Curation(_P.HORIZONTAL_PUSH, _E.BODYWEIGHT, True),
    "Push-Ups_With_Feet_Elevated": Curation(_P.HORIZONTAL_PUSH, _E.BODYWEIGHT, True),
    "Incline_Push-Up": Curation(_P.HORIZONTAL_PUSH, _E.BODYWEIGHT, True),
    "Decline_Push-Up": Curation(_P.HORIZONTAL_PUSH, _E.BODYWEIGHT, True),
    "Single-Arm_Push-Up": Curation(_P.HORIZONTAL_PUSH, _E.BODYWEIGHT, True),
    "Dumbbell_Floor_Press": Curation(_P.HORIZONTAL_PUSH, _E.DUMBBELL, True),
    "Dumbbell_Bench_Press": Curation(_P.HORIZONTAL_PUSH, _E.DUMBBELL, True),
    # --- vertical push ---
    "Dumbbell_Shoulder_Press": Curation(_P.VERTICAL_PUSH, _E.DUMBBELL, True),
    "Standing_Dumbbell_Press": Curation(_P.VERTICAL_PUSH, _E.DUMBBELL, True),
    "Arnold_Dumbbell_Press": Curation(_P.VERTICAL_PUSH, _E.DUMBBELL, True),
    "Seated_Dumbbell_Press": Curation(_P.VERTICAL_PUSH, _E.DUMBBELL, True),
    "Handstand_Push-Ups": Curation(_P.VERTICAL_PUSH, _E.BODYWEIGHT, True),
    # --- horizontal pull ---
    "One-Arm_Dumbbell_Row": Curation(_P.HORIZONTAL_PULL, _E.DUMBBELL, True),
    "Bent_Over_Two-Dumbbell_Row": Curation(_P.HORIZONTAL_PULL, _E.DUMBBELL, True),
    "Bent_Over_Two-Dumbbell_Row_With_Palms_In": Curation(_P.HORIZONTAL_PULL, _E.DUMBBELL, True),
    "Dumbbell_Incline_Row": Curation(_P.HORIZONTAL_PULL, _E.DUMBBELL, True),
    "Inverted_Row": Curation(_P.HORIZONTAL_PULL, _E.PULL_UP_BAR, True),
    # --- vertical pull ---
    "Pullups": Curation(_P.VERTICAL_PULL, _E.PULL_UP_BAR, True),
    "Chin-Up": Curation(_P.VERTICAL_PULL, _E.PULL_UP_BAR, True),
    "Wide-Grip_Rear_Pull-Up": Curation(_P.VERTICAL_PULL, _E.PULL_UP_BAR, True),
    "V-Bar_Pullup": Curation(_P.VERTICAL_PULL, _E.PULL_UP_BAR, True),
    # --- squat (incl. single-leg variants) ---
    "Bodyweight_Squat": Curation(_P.SQUAT, _E.BODYWEIGHT, True),
    "Dumbbell_Squat": Curation(_P.SQUAT, _E.DUMBBELL, True),
    "Plie_Dumbbell_Squat": Curation(_P.SQUAT, _E.DUMBBELL, True),
    "Split_Squat_with_Dumbbells": Curation(_P.SQUAT, _E.DUMBBELL, True),
    "Dumbbell_Lunges": Curation(_P.SQUAT, _E.DUMBBELL, True),
    "Dumbbell_Rear_Lunge": Curation(_P.SQUAT, _E.DUMBBELL, True),
    "Bodyweight_Walking_Lunge": Curation(_P.SQUAT, _E.BODYWEIGHT, True),
    # --- hinge ---
    "Stiff-Legged_Dumbbell_Deadlift": Curation(_P.HINGE, _E.DUMBBELL, True),
    "Natural_Glute_Ham_Raise": Curation(_P.HINGE, _E.BODYWEIGHT, True),
    "Hyperextensions_With_No_Hyperextension_Bench": Curation(_P.HINGE, _E.BODYWEIGHT, True),
    "Single_Leg_Glute_Bridge": Curation(_P.HINGE, _E.BODYWEIGHT, False),
    "Butt_Lift_Bridge": Curation(_P.HINGE, _E.BODYWEIGHT, False),
    "Glute_Kickback": Curation(_P.HINGE, _E.BODYWEIGHT, False),
    # --- core ---
    "Plank": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Side_Bridge": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Crunches": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "3_4_Sit-Up": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Cross-Body_Crunch": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Decline_Crunch": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Russian_Twist": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Bent-Knee_Hip_Raise": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Flat_Bench_Lying_Leg_Raise": Curation(_P.CORE, _E.BODYWEIGHT, False),
    "Hanging_Leg_Raise": Curation(_P.CORE, _E.PULL_UP_BAR, False),
    "Hanging_Pike": Curation(_P.CORE, _E.PULL_UP_BAR, True),
    # --- conditioning (time-based; SPEC §6.7) ---
    "Mountain_Climbers": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Rocket_Jump": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Knee_Tuck_Jump": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Star_Jump": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Split_Jump": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Scissors_Jump": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Wind_Sprints": Curation(_P.CONDITIONING, _E.BODYWEIGHT, True),
    "Vertical_Swing": Curation(_P.CONDITIONING, _E.DUMBBELL, True),
}
