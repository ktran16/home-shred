from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProgressPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    note: str | None
    content_type: str
    created_at: datetime
    image_url: str
