"""Router REST para consulta y registro de logs de publicación (PublicationLog).

Referencias arquitectónicas:
    - ADR-0002: Modularización en FastAPI y desacoplamiento de routers.
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from python_backend.repositories import log_repository
from python_backend.schemas.log_schema import LogCreate

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def list_logs():
    """Devuelve la lista completa de registros de auditoría de publicaciones."""
    logs = log_repository.get_all_logs()
    return {"success": True, "data": logs}


@router.get("/{log_id}")
def get_log(log_id: int):
    """Busca un log de publicación por ID retornando 404 si no existe."""
    log = log_repository.get_log_by_id(log_id)

    if not log:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Log no encontrado"},
        )

    return {"success": True, "data": log}


@router.post("", status_code=201)
def create_log(payload: LogCreate):
    """Inserta un registro de publicación en la base de datos validando el payload."""
    try:
        log = log_repository.create_log(payload.model_dump())
    except IntegrityError as error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(error.orig)},
        )

    return {"success": True, "data": log}
