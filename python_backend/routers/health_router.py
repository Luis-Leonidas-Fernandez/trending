from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def get_health():
    return {
        "success": True,
        "message": "Backend FastAPI funcionando correctamente",
        "scope": "Participante 1 migrado a Python",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
