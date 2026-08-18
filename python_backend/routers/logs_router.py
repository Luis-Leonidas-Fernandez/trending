from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from python_backend.repositories import log_repository
from python_backend.schemas.log_schema import LogCreate

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def list_logs():
    logs = log_repository.get_all_logs()
    return {"success": True, "data": logs}


@router.get("/{log_id}")
def get_log(log_id: int):
    log = log_repository.get_log_by_id(log_id)

    if not log:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Log no encontrado"},
        )

    return {"success": True, "data": log}


@router.post("", status_code=201)
def create_log(payload: LogCreate):
    try:
        log = log_repository.create_log(payload.model_dump())
    except IntegrityError as error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(error.orig)},
        )

    return {"success": True, "data": log}
