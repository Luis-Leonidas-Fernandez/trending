"""Repositorio de persistencia para registros de publicación (PublicationLog).

Almacena la traza de auditoría de los intentos y resultados de publicación,
capturando respuestas JSON estructuradas y mensajes de error.

Referencias arquitectónicas:
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
    - ADR-0013: Auditoría local y chequeos de calidad sin conexión externa a Instagram.
"""

from typing import Dict, List, Optional

from python_backend.database.connection import get_session
from python_backend.models.log_model import PublicationLog


def _log_to_dict(log: PublicationLog) -> Dict:
    """Convierte una entidad PublicationLog a diccionario desacoplado."""
    return {
        "id": log.id,
        "post_id": log.post_id,
        "platform": log.platform,
        "status": log.status,
        "response_json": log.response_json,
        "error_message": log.error_message,
        "created_at": log.created_at,
    }


def get_all_logs() -> List[Dict]:
    """Recupera la totalidad de los logs de auditoría ordenados por fecha descendente."""
    with get_session() as session:
        logs = session.query(PublicationLog).order_by(PublicationLog.created_at.desc()).all()

    return [_log_to_dict(log) for log in logs]


def get_log_by_id(log_id: int) -> Optional[Dict]:
    """Obtiene un registro de log por su identificador primario."""
    with get_session() as session:
        log = session.get(PublicationLog, log_id)

    if log is None:
        return None

    return _log_to_dict(log)


def create_log(log_data: Dict) -> Optional[Dict]:
    """Inserta un nuevo registro de auditoría de publicación confirmando la transacción."""
    with get_session() as session:
        log = PublicationLog(
            post_id=log_data["post_id"],
            platform=log_data["platform"],
            status=log_data["status"],
            response_json=log_data.get("response_json"),
            error_message=log_data.get("error_message"),
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        return _log_to_dict(log)


def get_logs_by_post_id(post_id: int) -> List[Dict]:
    """Obtiene el historial cronológico de auditoría asociado a un post específico."""
    with get_session() as session:
        logs = (
            session.query(PublicationLog)
            .filter(PublicationLog.post_id == post_id)
            .order_by(PublicationLog.created_at.desc())
            .all()
        )

    return [_log_to_dict(log) for log in logs]
