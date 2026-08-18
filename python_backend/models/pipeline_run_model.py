from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from python_backend.models.base import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    started_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, index=True)
    finished_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    execution_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    selected_steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    completed_steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    current_step: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    next_step: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    outputs_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    topic_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    topic_title: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    post_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
