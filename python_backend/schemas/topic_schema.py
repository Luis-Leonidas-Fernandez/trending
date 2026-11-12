"""Esquemas de validación Pydantic para endpoints de temas (TrendingTopic).

Referencias arquitectónicas:
    - ADR-0004: Validación de contratos de entrada con Pydantic.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    """Contrato de entrada para la creación manual de un tema."""

    title: str = Field(min_length=1)
    normalized_title: str = Field(min_length=1)
    source: Optional[str] = None
    score: float = Field(default=0, ge=0)
    used: int = Field(default=0, ge=0, le=1)
