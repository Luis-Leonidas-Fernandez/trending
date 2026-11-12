"""Configuración y conexión a la base de datos relacional SQLite con SQLAlchemy 2.0.

Gestiona el motor de base de datos, la factoría de sesiones SessionLocal,
la activación de claves foráneas mediante el evento PRAGMA foreign_keys=ON,
y la inicialización declarativa de esquemas.

Referencias arquitectónicas:
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0014: Estado unificado de pipeline y persistencia relacional de ejecuciones.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from python_backend.models import Base

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_FILE = PROJECT_ROOT / "python_backend" / "database" / "trending.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


def get_database_path() -> Path:
    """Obtiene la ruta absoluta al archivo SQLite desde PYTHON_DB_FILE o por defecto."""
    configured_path = os.getenv("PYTHON_DB_FILE")

    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return DEFAULT_DB_FILE


def get_database_url() -> str:
    """Construye la URL de conexión SQLAlchemy para SQLite."""
    return f"sqlite:///{get_database_path()}"


def _create_engine():
    """Crea el motor SQLAlchemy configurando el pragmatismo de foreign keys para SQLite."""
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        get_database_url(),
        future=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Session:
    """Genera una nueva sesión contextual de base de datos."""
    return SessionLocal()


def initialize_database() -> None:
    """Crea todas las tablas declaradas en los modelos si aún no existen en la base de datos."""
    Base.metadata.create_all(bind=engine)
