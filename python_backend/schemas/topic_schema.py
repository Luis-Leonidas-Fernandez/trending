from typing import Optional

from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    title: str = Field(min_length=1)
    normalized_title: str = Field(min_length=1)
    source: Optional[str] = None
    score: float = Field(default=0, ge=0)
    used: int = Field(default=0, ge=0, le=1)
