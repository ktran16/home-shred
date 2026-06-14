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

# rationale (SPEC §16 R4): fraction of bodyweight borne by the prime movers in a
# bodyweight exercise, for the volume proxy. Rough biomechanical estimates; weighted
# (dumbbell) exercises use the logged weight, so their factor is irrelevant. Anything
# not listed defaults to DEFAULT_LOAD_FACTOR.
DEFAULT_LOAD_FACTOR = 1.0
BODYWEIGHT_LOAD_FACTORS: dict[str, float] = {
    # horizontal push
    "Pushups": 0.64,
    "Push-Up_Wide": 0.64,
    "Push-Ups_With_Feet_Elevated": 0.74,
    "Incline_Push-Up": 0.45,
    "Decline_Push-Up": 0.74,
    "Single-Arm_Push-Up": 0.95,
    # vertical push / pull (full bodyweight on the bar)
    "Handstand_Push-Ups": 0.95,
    "Pullups": 1.0,
    "Chin-Up": 1.0,
    "Wide-Grip_Rear_Pull-Up": 1.0,
    "V-Bar_Pullup": 1.0,
    "Inverted_Row": 0.55,
    # squat / hinge (bodyweight)
    "Bodyweight_Squat": 0.65,
    "Bodyweight_Walking_Lunge": 0.85,
    "Natural_Glute_Ham_Raise": 0.6,
    "Hyperextensions_With_No_Hyperextension_Bench": 0.5,
    "Single_Leg_Glute_Bridge": 0.5,
    "Butt_Lift_Bridge": 0.4,
    "Glute_Kickback": 0.3,
    # core
    "Plank": 0.3,
    "Side_Bridge": 0.3,
    "Crunches": 0.3,
    "3_4_Sit-Up": 0.35,
    "Cross-Body_Crunch": 0.3,
    "Decline_Crunch": 0.4,
    "Russian_Twist": 0.3,
    "Bent-Knee_Hip_Raise": 0.35,
    "Flat_Bench_Lying_Leg_Raise": 0.4,
    "Hanging_Leg_Raise": 0.4,
    "Hanging_Pike": 0.5,
    # conditioning (bodyweight)
    "Mountain_Climbers": 0.4,
    "Rocket_Jump": 0.7,
    "Knee_Tuck_Jump": 0.7,
    "Star_Jump": 0.6,
    "Split_Jump": 0.7,
    "Scissors_Jump": 0.6,
    "Wind_Sprints": 0.5,
}


def load_factor(slug: str) -> float:
    return BODYWEIGHT_LOAD_FACTORS.get(slug, DEFAULT_LOAD_FACTOR)


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
