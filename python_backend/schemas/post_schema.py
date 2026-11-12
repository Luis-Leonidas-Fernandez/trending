"""Esquemas de validación Pydantic para endpoints de posts (GeneratedPost).

Referencias arquitectónicas:
    - ADR-0004: Validación de contratos de entrada con Pydantic.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    """Contrato de entrada para la creación o persistencia de un post generado."""

    topic_id: int = Field(gt=0)
    image_url: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    status: str = Field(default="draft", min_length=1)
