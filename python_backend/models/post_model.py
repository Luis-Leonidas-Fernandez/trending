"""Modelo ORM para la tabla generated_posts.

Representa el contenido generado (copy e imagen) vinculado con su tema y trazabilidad.

Referencias arquitectónicas:
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from python_backend.models.base import Base

if TYPE_CHECKING:
    from python_backend.models.log_model import PublicationLog
    from python_backend.models.topic_model import TrendingTopic


class GeneratedPost(Base):
    """Entidad relacional de posts generados en borrador o finalizados."""

    __tablename__ = "generated_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("trending_topics.id"), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hashtags: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'draft'"))
    created_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    topic: Mapped["TrendingTopic"] = relationship("TrendingTopic", back_populates="generated_posts")
    publication_logs: Mapped[List["PublicationLog"]] = relationship(
        "PublicationLog",
        back_populates="post",
    )
