from enum import StrEnum


class Equipment(StrEnum):
    BODYWEIGHT = "bodyweight"
    DUMBBELL = "dumbbell"
    PULL_UP_BAR = "pull_up_bar"


class MovementPattern(StrEnum):
    """Used by the generator for balanced selection (SPEC §4)."""

    HORIZONTAL_PUSH = "horizontal_push"  # push-up, DB floor press
    VERTICAL_PUSH = "vertical_push"  # DB shoulder press, pike push-up
    HORIZONTAL_PULL = "horizontal_pull"  # DB row, inverted row
    VERTICAL_PULL = "vertical_pull"  # pull-up, chin-up
    SQUAT = "squat"  # goblet squat, split squat
    HINGE = "hinge"  # DB RDL, single-leg RDL
    CORE = "core"  # plank, hanging leg raise
    CONDITIONING = "conditioning"  # burpee, DB complex, mountain climber


class Focus(StrEnum):
    FULL_BODY = "full_body"
    UPPER = "upper"
    LOWER = "lower"
    PUSH = "push"
    PULL = "pull"
    LEGS = "legs"
    CONDITIONING = "conditioning"


class Level(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Goal(StrEnum):
    SHRED = "shred"  # only goal for MVP; enum leaves room to grow


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"  # ×1.2
    LIGHT = "light"  # ×1.375
    MODERATE = "moderate"  # ×1.55
    ACTIVE = "active"  # ×1.725
    VERY_ACTIVE = "very_active"  # ×1.9


# rationale: TDEE multipliers per activity level (SPEC §4, §8).
ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}
