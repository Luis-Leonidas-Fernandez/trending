from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Float, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from python_backend.models.base import Base

if TYPE_CHECKING:
    from python_backend.models.post_model import GeneratedPost


class TrendingTopic(Base):
    __tablename__ = "trending_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    normalized_title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    generated_posts: Mapped[List["GeneratedPost"]] = relationship(
        "GeneratedPost",
        back_populates="topic",
    )
