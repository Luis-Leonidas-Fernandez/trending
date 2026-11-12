"""Modelo ORM para la tabla publication_logs.

Registra las operaciones y respuestas de auditoría para cada publicación.

Referencias arquitectónicas:
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
    - ADR-0013: Auditoría local y chequeos de calidad sin conexión externa a Instagram.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from python_backend.models.base import Base

if TYPE_CHECKING:
    from python_backend.models.post_model import GeneratedPost


class PublicationLog(Base):
    """Entidad relacional de bitácora y auditoría de publicaciones."""

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
