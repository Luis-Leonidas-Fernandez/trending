"""Esquema canónico y versionado para entregables JSON inter-fases.

Define la estructura obligatoria de los artefactos producidos por cada
participante del pipeline para garantizar interoperabilidad desacoplada.

Referencias arquitectónicas:
    - ADR-0004: Validación de contratos de entrada con Pydantic.
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"

ParticipantName = Literal[
    "participante-2",
    "participante-3",
    "participante-4",
    "participante-5",
    "participante-6",
    "participante-7",
]

OutputStage = Literal[
    "trends",
    "duplicates",
    "topic_selector",
    "ai",
    "instagram",
    "metrics",
    "frontend",
]

OutputStatus = Literal["success", "error", "draft"]


class ParticipantOutput(BaseModel):
    """Estructura canónica de un artefacto JSON entregable producido por una fase."""

    schema_version: Literal["1.0"]
    run_id: UUID
    participant: ParticipantName
    stage: OutputStage
    generated_at: datetime
    status: OutputStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
