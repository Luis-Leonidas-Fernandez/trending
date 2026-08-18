from typing import Optional

from pydantic import BaseModel, Field


class LogCreate(BaseModel):
    post_id: int = Field(gt=0)
    platform: str = Field(min_length=1)
    status: str = Field(min_length=1)
    response_json: Optional[str] = None
    error_message: Optional[str] = None
