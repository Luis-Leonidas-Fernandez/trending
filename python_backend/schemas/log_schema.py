"""Esquemas de validación Pydantic para endpoints de logs (PublicationLog).

Referencias arquitectónicas:
    - ADR-0004: Validación de contratos de entrada con Pydantic.
"""

from typing import Optional

from pydantic import BaseModel, Field


class LogCreate(BaseModel):
    """Contrato de entrada para registrar un log de publicación."""

    post_id: int = Field(gt=0)
    platform: str = Field(min_length=1)
    status: str = Field(min_length=1)
    response_json: Optional[str] = None
    error_message: Optional[str] = None
