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
    configured_path = os.getenv("PYTHON_DB_FILE")

    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return DEFAULT_DB_FILE


def get_database_url() -> str:
    return f"sqlite:///{get_database_path()}"


def _create_engine():
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
    return SessionLocal()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
