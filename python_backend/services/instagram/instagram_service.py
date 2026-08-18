"""Servicio del Participante 6: persistencia/preparación de publicación.

Fase 6A consume el output de Fase 5, persiste el post generado en SQLite y
produce un output versionado auditable. No publica en Instagram todavía y no
marca el tema como usado; eso queda para una subfase posterior cuando la
publicación/preparación final sea exitosa.
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

PARTICIPANT = "participante-6"
STAGE = "instagram"
SOURCE_PARTICIPANT = "participante-5"
SOURCE_STAGE = "ai"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / PARTICIPANT


class InstagramServiceError(ValueError):
    """Error controlado de preparación/persistencia de publicación."""


def publish_post(post: dict[str, Any]) -> dict[str, Any]:
    """Prepara un post persistido para una publicación futura.

    Conserva la interfaz pública histórica del Participante 6, pero esta subfase
    no llama a Instagram externo. Sólo devuelve un contrato operacional claro.
    """

    post_id = post.get("id") if isinstance(post, dict) else None
    if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id <= 0:
        raise InstagramServiceError("post.id debe ser un entero positivo")
    return {
        "post_id": post_id,
        "platform": "instagram",
        "ready_to_publish": False,
        "publication_skipped": True,
        "message": "Post persistido como draft; publicación externa pendiente.",
    }


def simulate_publication(post_id: int) -> dict[str, Any]:
    """Cierra una publicación falsa para auditoría sin llamar a Instagram real."""

    if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id <= 0:
        raise InstagramServiceError("post_id debe ser un entero positivo")

    post = post_repository.get_post_by_id(post_id)
    if post is None:
        raise InstagramServiceError(f"No existe el post {post_id}")

    if _clean_text(post.get("status")) not in {"draft", "published_simulated"}:
        raise InstagramServiceError("Sólo se pueden finalizar posts en estado draft")
    if not _clean_text(post.get("caption")):
        raise InstagramServiceError("El post debe tener caption antes de publicar")
    if not _clean_text(post.get("image_url")):
        raise InstagramServiceError("El post debe tener image_url antes de publicar")

    response = {
        "simulated": True,
        "external_publication": False,
        "provider": "local_audit",
        "message": "Publicación simulada correctamente para auditoría.",
    }
    log = log_repository.create_log(
        {
            "post_id": post_id,
            "platform": "instagram",
            "status": "published_simulated",
            "response_json": json.dumps(response, ensure_ascii=False),
            "error_message": None,
        }
    )
    updated_post = post_repository.update_post_status(post_id, "published_simulated")
    if updated_post is None:
        raise InstagramServiceError("No se pudo actualizar el estado del post")

    topic = topic_repository.mark_topic_used(updated_post["topic_id"])
    if topic is None:
        raise InstagramServiceError("No se pudo marcar el tema como usado")

    return {
        "post": updated_post,
        "publication_log": log,
        "topic": topic,
        "platform": "instagram",
        "simulated": True,
        "external_publication": False,
        "topic_marked_used": True,
        "message": response["message"],
    }


def build_audit_view(post_id: int | None = None) -> dict[str, Any]:
    """Devuelve una vista consolidada del post finalizado para auditoría UI/API."""

    if post_id is None:
        posts = post_repository.get_all_posts()
        finalized = [post for post in posts if _clean_text(post.get("status")) == "published_simulated"]
        if not finalized:
            raise InstagramServiceError("Todavía no hay publicaciones simuladas para auditar")
        post = finalized[0]
    else:
        post = post_repository.get_post_by_id(post_id)
        if post is None:
            raise InstagramServiceError(f"No existe el post {post_id}")

    logs = log_repository.get_logs_by_post_id(post["id"])
    return {
        "post": post,
        "publication_log": logs[0] if logs else None,
        "logs": logs,
        "audit": {
            "ready": _clean_text(post.get("status")) == "published_simulated",
            "simulated": _clean_text(post.get("status")) == "published_simulated",
            "external_publication": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def process_simulated_publication(
    post_id: int,
    output_dir: str | Path | None = None,
) -> Path:
    """Genera un output auditable para la publicación simulada final."""

    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"

    try:
        operation = simulate_publication(post_id)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": str(run_id),
            "participant": PARTICIPANT,
            "stage": STAGE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "data": {
                **operation,
                "post_id": operation["post"]["id"],
                "ready_to_publish": True,
                "publication_skipped": False,
                "mode": "simulated_publication",
            },
            "errors": [],
        }
    except Exception as error:  # noqa: BLE001 - se genera output auditable de fallo.
        payload = _build_error_payload(run_id=run_id, error=error, input_path=Path(f"post:{post_id}"))

    _write_json(output_path=output_path, payload=payload)
    return output_path


def process_ai_output(
    input_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Consume un output de Fase 5, persiste el post y guarda Fase 6A."""

    source_path = Path(input_path)
    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"

    try:
        source_output = _load_phase_5_output(source_path)
        selected_topic = _validate_selected_topic(source_output.data.get("selected_topic"))
        post_payload = _post_payload_from_ai_output(source_output, selected_topic)
        saved_post = post_repository.create_post(post_payload)
        if not saved_post or not isinstance(saved_post.get("id"), int):
            raise InstagramServiceError("No se pudo persistir el post generado")

        operation = publish_post(saved_post)
        upstream_errors = _sanitize_errors(source_output.errors)
        used_fallback = bool(source_output.data.get("used_fallback", False))
        status = "draft" if source_output.status == "draft" or used_fallback else "success"
        payload = _build_payload(
            run_id=run_id,
            status=status,
            errors=upstream_errors,
            source_output=source_output,
            selected_topic=selected_topic,
            saved_post=saved_post,
            operation=operation,
            used_fallback=used_fallback,
        )
    except Exception as error:  # noqa: BLE001 - el output debe auditar fallos de persistencia.
        payload = _build_error_payload(run_id=run_id, error=error, input_path=source_path)

    _write_json(output_path=output_path, payload=payload)
    return output_path


def _load_phase_5_output(input_path: Path) -> ParticipantOutput:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise InstagramServiceError(f"No existe el output de Fase 5: {input_path}") from error
    except json.JSONDecodeError as error:
        raise InstagramServiceError(f"JSON inválido en output de Fase 5: {error}") from error

    try:
        output = ParticipantOutput.model_validate(payload)
    except ValidationError as error:
        raise InstagramServiceError(f"Output de Fase 5 inválido: {error}") from error

    if output.participant != SOURCE_PARTICIPANT or output.stage != SOURCE_STAGE:
        raise InstagramServiceError("El input debe pertenecer a participante-5 y stage ai")

    if output.status == "error":
        raise InstagramServiceError("El input de Fase 5 está en status error")

    if output.status not in {"success", "draft"}:
        raise InstagramServiceError("El input de Fase 5 debe estar en status success o draft")

    return output


def _validate_selected_topic(topic: Any) -> dict[str, Any]:
    if not isinstance(topic, dict):
        raise InstagramServiceError("data.selected_topic debe ser un objeto")
    topic_id = topic.get("id")
    title = _clean_text(topic.get("title"))
    normalized_title = _clean_text(topic.get("normalized_title"))
    if not isinstance(topic_id, int) or isinstance(topic_id, bool) or topic_id <= 0:
        raise InstagramServiceError("data.selected_topic.id debe ser un entero positivo")
    if not title or not normalized_title:
        raise InstagramServiceError("data.selected_topic debe tener title y normalized_title")
    return {**topic, "id": topic_id, "title": title, "normalized_title": normalized_title}


def _post_payload_from_ai_output(source_output: ParticipantOutput, selected_topic: dict[str, Any]) -> dict[str, Any]:
    caption = _clean_multiline_text(source_output.data.get("caption"))
    description = _clean_text(source_output.data.get("description"))
    hashtags = _format_hashtags(source_output.data.get("hashtags"))
    image_url = _clean_text(source_output.data.get("image_file")) or None

    if not caption:
        raise InstagramServiceError("data.caption es obligatorio para persistir el post")

    return {
        "topic_id": selected_topic["id"],
        "image_url": image_url,
        "caption": caption,
        "description": description or None,
        "hashtags": hashtags,
        "status": "draft",
    }


def _format_hashtags(value: Any) -> str | None:
    if isinstance(value, list):
        hashtags = [_clean_text(item) for item in value]
        hashtags = [item if item.startswith("#") else f"#{item}" for item in hashtags if item]
        return " ".join(dict.fromkeys(hashtags)) or None
    text = _clean_text(value)
    return text or None


def _build_payload(
    *,
    run_id: uuid.UUID,
    status: str,
    errors: list[str],
    source_output: ParticipantOutput,
    selected_topic: dict[str, Any],
    saved_post: dict[str, Any],
    operation: dict[str, Any],
    used_fallback: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data": {
            "post": saved_post,
            "post_id": saved_post["id"],
            "selected_topic": selected_topic,
            "platform": "instagram",
            "ready_to_publish": False,
            "publication_skipped": True,
            "topic_marked_used": False,
            "operation": operation,
            "source": {
                "participant": source_output.participant,
                "stage": source_output.stage,
                "run_id": str(source_output.run_id),
                "status": source_output.status,
                "used_fallback": used_fallback,
            },
        },
        "errors": errors,
    }


def _build_error_payload(run_id: uuid.UUID, error: Exception, input_path: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "data": {
            "post": None,
            "post_id": None,
            "platform": "instagram",
            "ready_to_publish": False,
            "publication_skipped": True,
            "topic_marked_used": False,
            "source": {"input_path": str(input_path)},
        },
        "errors": [_sanitize_error(error)],
    }


def _write_json(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _clean_multiline_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    for block in re.split(r"\n\s*\n", text):
        cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in block.split("\n")]
        cleaned_block = " ".join(line for line in cleaned_lines if line)
        if cleaned_block:
            blocks.append(cleaned_block)
    return "\n\n".join(blocks).strip()


def _sanitize_errors(errors: Any) -> list[str]:
    if not isinstance(errors, list):
        return []
    return [_sanitize_error(error) for error in errors if _sanitize_error(error)]


def _sanitize_error(error: Any) -> str:
    return " ".join(str(error).split())[:240]
