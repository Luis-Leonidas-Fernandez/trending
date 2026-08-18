"""Servicio del Participante 3: validación de duplicados y persistencia.

La Fase 3 consume un output versionado de la Fase 2, descarta temas inválidos
o repetidos por título normalizado exacto, persiste únicamente los temas nuevos
en SQLite y escribe un JSON auditable para la Fase 4.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from python_backend.repositories import topic_repository
from python_backend.schemas.output_schema import SCHEMA_VERSION, ParticipantOutput
from python_backend.services.trends.trends_service import normalize_title

PARTICIPANT = "participante-3"
STAGE = "duplicates"
SOURCE_PARTICIPANT = "participante-2"
SOURCE_STAGE = "trends"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / PARTICIPANT

_DISCARD_INVALID_TITLE = "invalid_title"
_DISCARD_DUPLICATE_INPUT = "duplicate_in_input"
_DISCARD_DUPLICATE_DATABASE = "duplicate_in_database"
_DISCARD_ALREADY_USED = "already_used_in_database"


class DuplicatesServiceError(ValueError):
    """Error controlado de validación del input o de persistencia."""


def filter_new_topics(
    topics: list[dict[str, Any]],
    existing_topics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Devuelve temas válidos y nuevos, conservando el orden de entrada.

    La comparación es por igualdad exacta de ``normalized_title`` tras aplicar
    la misma normalización de la Fase 2. Si ``existing_topics`` es ``None``, se
    consulta SQLite mediante el repositorio actual.
    """

    filtering = _filter_topics(topics=topics, existing_topics=existing_topics)
    return filtering["new_items"]


def process_trends_output(
    input_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Procesa un output de Fase 2, persiste temas nuevos y guarda Fase 3."""

    source_path = Path(input_path)
    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"

    try:
        source_output = _load_phase_2_output(source_path)
        source_items = source_output.data.get("items", [])
        if not isinstance(source_items, list):
            raise DuplicatesServiceError("data.items debe ser una lista")

        existing_topics = topic_repository.get_all_topics()
        filtering = _filter_topics(topics=source_items, existing_topics=existing_topics)
        saved_items = _persist_topics(filtering["new_items"])
        candidate_items = [*saved_items, *filtering["reusable_items"]]

        upstream_errors = _sanitize_errors(source_output.errors)
        used_fallback = bool(source_output.data.get("used_fallback", False))
        status = "draft" if source_output.status == "draft" or used_fallback or not candidate_items else "success"
        payload = _build_payload(
            run_id=run_id,
            status=status,
            items=candidate_items,
            saved_count=len(saved_items),
            reused_count=len(filtering["reusable_items"]),
            errors=upstream_errors,
            source_output=source_output,
            input_count=len(source_items),
            discarded=filtering["discarded"],
            duplicate_count=filtering["duplicate_count"],
            invalid_count=filtering["invalid_count"],
            used_fallback=used_fallback,
        )
    except Exception as error:  # noqa: BLE001 - el output debe auditar errores de persistencia/validación.
        payload = _build_error_payload(run_id=run_id, error=error, input_path=source_path)

    _write_json(output_path=output_path, payload=payload)
    return output_path


def _load_phase_2_output(input_path: Path) -> ParticipantOutput:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise DuplicatesServiceError(f"No existe el output de Fase 2: {input_path}") from error
    except json.JSONDecodeError as error:
        raise DuplicatesServiceError(f"JSON inválido en output de Fase 2: {error}") from error

    try:
        output = ParticipantOutput.model_validate(payload)
    except ValidationError as error:
        raise DuplicatesServiceError(f"Output de Fase 2 inválido: {error}") from error

    if output.participant != SOURCE_PARTICIPANT or output.stage != SOURCE_STAGE:
        raise DuplicatesServiceError(
            "El input debe pertenecer a participante-2 y stage trends"
        )

    if output.status not in {"success", "draft"}:
        raise DuplicatesServiceError("El input de Fase 2 debe estar en status success o draft")

    return output


def _filter_topics(
    topics: list[dict[str, Any]],
    existing_topics: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if not isinstance(topics, list):
        raise DuplicatesServiceError("topics debe ser una lista")

    existing = topic_repository.get_all_topics() if existing_topics is None else existing_topics
    existing_by_normalized = _existing_topics_by_normalized_title(existing)
    existing_normalized = set(existing_by_normalized)
    seen_in_input: set[str] = set()
    new_items: list[dict[str, Any]] = []
    reusable_items: list[dict[str, Any]] = []
    discarded: list[dict[str, Any]] = []
    duplicate_count = 0
    invalid_count = 0

    for index, topic in enumerate(topics):
        if not isinstance(topic, dict):
            discarded.append(_discarded_item(index, "", "", _DISCARD_INVALID_TITLE))
            invalid_count += 1
            continue

        title = _clean_title(topic.get("title"))
        normalized = _normalize_topic(topic)

        if not title or not normalized:
            discarded.append(_discarded_item(index, title, normalized, _DISCARD_INVALID_TITLE))
            invalid_count += 1
            continue

        if normalized in seen_in_input:
            discarded.append(_discarded_item(index, title, normalized, _DISCARD_DUPLICATE_INPUT))
            duplicate_count += 1
            continue

        seen_in_input.add(normalized)

        if normalized in existing_normalized:
            existing_topic = existing_by_normalized[normalized]
            if _has_positive_id(existing_topic) and _is_unused(existing_topic.get("used")):
                reusable_items.append(_topic_from_existing(existing_topic, topic, title, normalized))
            elif _has_positive_id(existing_topic):
                discarded.append(_discarded_item(index, title, normalized, _DISCARD_ALREADY_USED))
            else:
                discarded.append(_discarded_item(index, title, normalized, _DISCARD_DUPLICATE_DATABASE))
            duplicate_count += 1
            continue

        new_items.append(_topic_for_persistence(topic, title, normalized))

    return {
        "new_items": new_items,
        "reusable_items": reusable_items,
        "discarded": discarded,
        "duplicate_count": duplicate_count,
        "invalid_count": invalid_count,
    }


def _existing_topics_by_normalized_title(existing_topics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    existing_by_normalized: dict[str, dict[str, Any]] = {}
    for topic in existing_topics:
        if not isinstance(topic, dict):
            continue
        normalized = _clean_title(topic.get("normalized_title"))
        if not normalized:
            normalized = normalize_title(str(topic.get("title", "")))
        if normalized and normalized not in existing_by_normalized:
            existing_by_normalized[normalized] = topic
    return existing_by_normalized


def _normalize_topic(topic: dict[str, Any]) -> str:
    raw_normalized = _clean_title(topic.get("normalized_title"))
    if raw_normalized:
        return normalize_title(raw_normalized)
    return normalize_title(_clean_title(topic.get("title")))


def _topic_from_existing(
    existing_topic: dict[str, Any],
    input_topic: dict[str, Any],
    title: str,
    normalized: str,
) -> dict[str, Any]:
    return {
        "id": existing_topic.get("id"),
        "title": existing_topic.get("title") or title,
        "normalized_title": existing_topic.get("normalized_title") or normalized,
        "source": existing_topic.get("source") or input_topic.get("source") or "unknown",
        "score": float(existing_topic.get("score", input_topic.get("score", 0)) or 0),
        "used": existing_topic.get("used", 0),
        "reused_existing": True,
    }


def _topic_for_persistence(topic: dict[str, Any], title: str, normalized: str) -> dict[str, Any]:
    return {
        "title": title,
        "normalized_title": normalized,
        "source": _clean_optional_text(topic.get("source")) or "unknown",
        "score": _safe_score(topic.get("score")),
        "used": 0,
        "category": _clean_optional_text(topic.get("category")) or "general",
        "date": _clean_optional_text(topic.get("date")),
    }


def _persist_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    saved_items: list[dict[str, Any]] = []
    for topic in topics:
        saved = topic_repository.create_topic(
            {
                "title": topic["title"],
                "normalized_title": topic["normalized_title"],
                "source": topic.get("source"),
                "score": topic.get("score", 0),
                "used": topic.get("used", 0),
            }
        )
        if not saved or saved.get("id") is None:
            raise DuplicatesServiceError(
                f"No se pudo persistir el tema: {topic['normalized_title']}"
            )
        saved_items.append(
            {
                "id": saved["id"],
                "title": saved.get("title", topic["title"]),
                "normalized_title": saved.get("normalized_title", topic["normalized_title"]),
                "source": saved.get("source", topic.get("source")),
                "score": float(saved.get("score", topic.get("score", 0))),
                "used": saved.get("used", topic.get("used", 0)),
            }
        )
    return saved_items


def _build_payload(
    *,
    run_id: uuid.UUID,
    status: str,
    items: list[dict[str, Any]],
    errors: list[str],
    source_output: ParticipantOutput,
    input_count: int,
    discarded: list[dict[str, Any]],
    duplicate_count: int,
    invalid_count: int,
    used_fallback: bool,
    saved_count: int | None = None,
    reused_count: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data": {
            "items": items,
            "counts": {
                "input": input_count,
                "saved": len(items) if saved_count is None else saved_count,
                "reused": reused_count,
                "duplicates": duplicate_count,
                "invalid": invalid_count,
                "discarded": len(discarded),
            },
            "discarded": discarded,
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
            "items": [],
            "counts": {
                "input": 0,
                "saved": 0,
                "reused": 0,
                "duplicates": 0,
                "invalid": 0,
                "discarded": 0,
            },
            "discarded": [],
            "source": {"input_path": str(input_path)},
        },
        "errors": [_sanitize_error(error)],
    }


def _discarded_item(index: int, title: str, normalized_title: str, reason: str) -> dict[str, Any]:
    return {
        "index": index,
        "title": title,
        "normalized_title": normalized_title,
        "reason": reason,
    }


def _write_json(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _clean_title(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _clean_optional_text(value: Any) -> str | None:
    cleaned = _clean_title(value)
    return cleaned or None


def _safe_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(score, 0.0)


def _sanitize_error(error: Exception) -> str:
    message = str(error).strip() or error.__class__.__name__
    message = re.sub(r"\s+", " ", message)
    return message[:240]


def _sanitize_errors(errors: list[str]) -> list[str]:
    sanitized: list[str] = []
    for error in errors:
        message = re.sub(r"\s+", " ", str(error)).strip()[:240]
        if message:
            sanitized.append(message)
    return sanitized


def _is_unused(value: Any) -> bool:
    return value in {0, "0", False, None}


def _has_positive_id(topic: dict[str, Any]) -> bool:
    topic_id = topic.get("id")
    return isinstance(topic_id, int) and not isinstance(topic_id, bool) and topic_id > 0
