from pydantic import BaseModel, ConfigDict

from app.enums import Equipment, Level, MovementPattern


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    equipment: Equipment
    pattern: MovementPattern | None
    category: str | None
    primary_muscles: list[str]
    secondary_muscles: list[str]
    level: Level | None
    is_compound: bool
    instructions: list[str]
