from typing import Optional

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    topic_id: int = Field(gt=0)
    image_url: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    status: str = Field(default="draft", min_length=1)
