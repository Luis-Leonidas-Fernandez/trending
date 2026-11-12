"""Router REST para gestión y auditoría de publicaciones (GeneratedPost).

Referencias arquitectónicas:
    - ADR-0002: Modularización en FastAPI y desacoplamiento de routers.
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
"""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from python_backend.repositories import post_repository
from python_backend.schemas.post_schema import PostCreate
from python_backend.services.instagram import instagram_service
from python_backend.services.pipeline import pipeline_state_service

router = APIRouter(prefix="/posts", tags=["posts"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@router.get("")
def list_posts():
    """Devuelve la lista completa de posts generados en SQLite."""
    posts = post_repository.get_all_posts()
    return {"success": True, "data": posts}


@router.get("/audit/latest")
def get_latest_post_audit():
    """Obtiene la vista de auditoría para el post activo referenciado en el pipeline."""
    try:
        active_post_id = _active_post_id_from_pipeline_state()
        audit = instagram_service.build_audit_view(active_post_id)
    except instagram_service.InstagramServiceError as error:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": str(error)},
        )

    return {"success": True, "data": audit}


def _active_post_id_from_pipeline_state() -> int | None:
    """Extrae el ID del post activo referenciado por el estado del pipeline."""
    state = pipeline_state_service.get_pipeline_state()
    instagram_output = state.get("outputs", {}).get("instagram")
    if not instagram_output:
        return None

    output_path = Path(instagram_output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    if not output_path.exists():
        raise instagram_service.InstagramServiceError(
            "El estado activo referencia una evidencia de Instagram inexistente"
        )

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise instagram_service.InstagramServiceError(
            "La evidencia de Instagram de la rama activa no se puede leer"
        ) from error

    data = payload.get("data")
    if not isinstance(data, dict):
        raise instagram_service.InstagramServiceError(
            "La evidencia de Instagram de la rama activa no contiene datos"
        )
    post = data.get("post")
    post_id = post.get("id") if isinstance(post, dict) else data.get("post_id")
    if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id <= 0:
        raise instagram_service.InstagramServiceError(
            "La evidencia de Instagram de la rama activa no referencia un post válido"
        )
    return post_id


@router.get("/{post_id}/audit")
def get_post_audit(post_id: int):
    """Devuelve la auditoría de un post específico y sus logs de publicación."""
    try:
        audit = instagram_service.build_audit_view(post_id)
    except instagram_service.InstagramServiceError as error:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": str(error)},
        )

    return {"success": True, "data": audit}


@router.post("/{post_id}/publish-simulated")
def publish_post_simulated(post_id: int):
    """Ejecuta la publicación simulada para un post específico (Fase 6B)."""
    output_path = instagram_service.process_simulated_publication(post_id)
    audit = instagram_service.build_audit_view(post_id)
    return {"success": True, "data": {"output_path": str(output_path), "audit": audit}}


@router.get("/{post_id}")
def get_post(post_id: int):
    """Busca una publicación por ID retornando 404 si no existe."""
    post = post_repository.get_post_by_id(post_id)

    if not post:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Post no encontrado"},
        )

    return {"success": True, "data": post}


@router.post("", status_code=201)
def create_post(payload: PostCreate):
    """Crea manualmente una publicación validando claves foráneas."""
    try:
        post = post_repository.create_post(payload.model_dump())
    except IntegrityError as error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(error.orig)},
        )

    return {"success": True, "data": post}
