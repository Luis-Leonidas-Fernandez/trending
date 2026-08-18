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
    schema_version: Literal["1.0"]
    run_id: UUID
    participant: ParticipantName
    stage: OutputStage
    generated_at: datetime
    status: OutputStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
