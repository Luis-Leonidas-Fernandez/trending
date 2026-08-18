from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from python_backend.services.ai import spartan_auth_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/providers/status")
def get_ai_provider_statuses():
    return {"success": True, "data": spartan_auth_service.list_provider_statuses()}


@router.get("/providers/{provider}/status")
def get_ai_provider_status(provider: str):
    try:
        return {"success": True, "data": spartan_auth_service.get_provider_status(provider)}
    except spartan_auth_service.SpartanAuthServiceError as error:
        return _error_response(error)


@router.post("/providers/{provider}/connect")
def connect_ai_provider(provider: str):
    try:
        return {"success": True, "data": spartan_auth_service.start_provider_connection(provider)}
    except spartan_auth_service.SpartanAuthServiceError as error:
        return _error_response(error)


def _error_response(error: Exception) -> JSONResponse:
    message = " ".join(str(error).split())[:240] or "Error desconocido"
    return JSONResponse(status_code=400, content={"success": False, "message": message})
