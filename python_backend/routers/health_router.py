"""Router REST de comprobación de salud operacional del backend FastAPI.

Referencias arquitectónicas:
    - ADR-0002: Modularización en FastAPI y desacoplamiento de routers.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def get_health():
    """Retorna el estado de disponibilidad del backend y timestamp UTC actual."""
    return {
        "success": True,
        "message": "Backend FastAPI funcionando correctamente",
        "scope": "Participante 1 migrado a Python",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
