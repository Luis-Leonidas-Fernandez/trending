"""Clase base declarativa de SQLAlchemy 2.0 para modelos del sistema Trending.

Referencias arquitectónicas:
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa común para el mapeo objeto-relacional."""
    pass
