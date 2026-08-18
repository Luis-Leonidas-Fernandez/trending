from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from python_backend.models.base import Base

if TYPE_CHECKING:
    from python_backend.models.post_model import GeneratedPost


class PublicationLog(Base):
    __tablename__ = "publication_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("generated_posts.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    response_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    post: Mapped["GeneratedPost"] = relationship("GeneratedPost", back_populates="publication_logs")
