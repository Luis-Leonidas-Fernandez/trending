"""Servicio del Participante 7: medición/auditoría local final.

Fase 7 no consulta Instagram real. Consolida la publicación simulada, el post,
el log local y el topic usado para producir una evidencia auditable de calidad.

Referencias arquitectónicas:
    - ADR-0013: Auditoría local y chequeos de calidad sin conexión externa a Instagram.
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from python_backend.repositories import log_repository, post_repository, topic_repository
from python_backend.schemas.output_schema import SCHEMA_VERSION, ParticipantOutput

PARTICIPANT = "participante-7"
STAGE = "metrics"
SOURCE_PARTICIPANT = "participante-6"
SOURCE_STAGE = "instagram"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / PARTICIPANT


class MetricsServiceError(ValueError):
    """Error controlado de medición/auditoría final."""


def process_instagram_output(
    input_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Consume un output de Fase 6B y guarda métricas locales de Fase 7.

    Ejecuta los 8 chequeos locales de integridad sobre el post y topic asociados,
    asigna un score de 0 a 100 y emite el entregable JSON versionado.
    """

    source_path = Path(input_path)
    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"

    try:
        source_output = _load_instagram_output(source_path)
        audit = _build_metrics(source_output)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": str(run_id),
            "participant": PARTICIPANT,
            "stage": STAGE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "success" if audit["score"] == 100 else "draft",
            "data": audit,
            "errors": audit["warnings"],
        }
    except Exception as error:  # noqa: BLE001 - Fase 7 debe dejar evidencia de fallo.
        payload = _build_error_payload(run_id=run_id, error=error, input_path=source_path)

    _write_json(output_path=output_path, payload=payload)
    return output_path


def _load_instagram_output(input_path: Path) -> ParticipantOutput:
    """Carga y valida el entregable de Fase 6B asegurando pertenencia de stage."""
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise MetricsServiceError(f"No existe el output de Fase 6: {input_path}") from error
    except json.JSONDecodeError as error:
        raise MetricsServiceError(f"JSON inválido en output de Fase 6: {error}") from error

    try:
        output = ParticipantOutput.model_validate(payload)
    except ValidationError as error:
        raise MetricsServiceError(f"Output de Fase 6 inválido: {error}") from error

    if output.participant != SOURCE_PARTICIPANT or output.stage != SOURCE_STAGE:
        raise MetricsServiceError("El input debe pertenecer a participante-6 y stage instagram")
    if output.status == "error":
        raise MetricsServiceError("El input de Fase 6 está en status error")
    return output


def _build_metrics(source_output: ParticipantOutput) -> dict[str, Any]:
    """Evalúa los 8 chequeos de consistencia local y calcula el puntaje de calidad."""
    post_payload = source_output.data.get("post")
    if not isinstance(post_payload, dict):
        raise MetricsServiceError("data.post debe ser un objeto")

    post_id = post_payload.get("id")
    if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id <= 0:
        raise MetricsServiceError("data.post.id debe ser un entero positivo")

    post = post_repository.get_post_by_id(post_id)
    if post is None:
        raise MetricsServiceError(f"No existe el post {post_id}")

    topic_id = post.get("topic_id")
    topic = topic_repository.get_topic_by_id(topic_id) if isinstance(topic_id, int) else None
    logs = log_repository.get_logs_by_post_id(post_id)
    latest_log = logs[0] if logs else None

    checks = {
        "post_published_simulated": _clean_text(post.get("status")) == "published_simulated",
        "has_image": bool(_clean_text(post.get("image_url"))),
        "image_file_exists": _asset_exists(post.get("image_url")),
        "has_caption": bool(_clean_text(post.get("caption"))),
        "has_hashtags": bool(_clean_text(post.get("hashtags"))),
        "has_publication_log": bool(latest_log),
        "publication_log_success": bool(latest_log and _clean_text(latest_log.get("status")) == "published_simulated"),
        "topic_marked_used": bool(topic and topic.get("used") == 1),
    }
    warnings = _warnings_from_checks(checks)
    passed = sum(1 for value in checks.values() if value)
    score = round((passed / len(checks)) * 100) if checks else 0

    return {
        "post_id": post_id,
        "topic_id": topic_id,
        "topic_title": post.get("topic_title"),
        "post": post,
        "publication_log": latest_log,
        "topic": topic,
        "checks": checks,
        "score": score,
        "warnings": warnings,
        "ready_for_real_publication": False,
        "external_metrics_available": False,
        "next_action": "Revisión humana antes de integrar publicación real con Instagram.",
        "source": {
            "participant": source_output.participant,
            "stage": source_output.stage,
            "run_id": str(source_output.run_id),
            "status": source_output.status,
        },
    }


def _warnings_from_checks(checks: dict[str, bool]) -> list[str]:
    """Genera advertencias legibles para los chequeos que no pasaron satisfactoriamente."""
    labels = {
        "post_published_simulated": "El post no está en estado published_simulated",
        "has_image": "El post no tiene image_url",
        "image_file_exists": "El archivo de imagen referenciado no existe",
        "has_caption": "El post no tiene caption",
        "has_hashtags": "El post no tiene hashtags",
        "has_publication_log": "No hay log de publicación simulada",
        "publication_log_success": "El último log no confirma published_simulated",
        "topic_marked_used": "El topic no está marcado como usado",
    }
    return [message for key, message in labels.items() if not checks.get(key)]


def _asset_exists(path: Any) -> bool:
    """Verifica si la imagen referenciada es una URL remota o existe como archivo local."""
    clean_path = _clean_text(path)
    if not clean_path:
        return False
    if re.match(r"^https?://", clean_path):
        return True
    candidate = PROJECT_ROOT / clean_path
    return candidate.exists() and candidate.is_file()


def _write_json(*, output_path: Path, payload: dict[str, Any]) -> None:
    """Valida contra esquema y persiste el archivo JSON con indentación."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ParticipantOutput.model_validate(payload)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_error_payload(*, run_id: uuid.UUID, error: Exception, input_path: Path) -> dict[str, Any]:
    """Genera un entregable con status error para trazabilidad en caso de falla."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "data": {"input_path": str(input_path)},
        "errors": [_sanitize_error(error)],
    }


def _sanitize_error(error: Exception) -> str:
    """Sanitiza y acota el texto del error."""
    return re.sub(r"\s+", " ", str(error)).strip()[:240] or error.__class__.__name__


def _clean_text(value: Any) -> str:
    """Limpia espacios en blanco."""
    if value is None:
        return ""
    return str(value).strip()
