"""Servicio del Participante 4: selección automática de tema.

La Fase 4 consume el output versionado de la Fase 3, preserva el orden recibido
por ``data.items`` y selecciona el primer tema estructuralmente válido y no usado.
Es un selector puro: no consulta SQLite ni modifica el campo ``used``.

Referencias arquitectónicas:
    - ADR-0009: Selección determinística de tema sin mutación de base de datos.
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
"""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from python_backend.schemas.output_schema import SCHEMA_VERSION, ParticipantOutput

PARTICIPANT = "participante-4"
STAGE = "topic_selector"
SOURCE_PARTICIPANT = "participante-3"
SOURCE_STAGE = "duplicates"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / PARTICIPANT

STRATEGY = "first_valid_unused"
REUSE_STRATEGY = "manual_history_reuse"
_DISCARD_INVALID_TOPIC = "invalid_topic"
_DISCARD_ALREADY_USED = "already_used"


class TopicSelectorServiceError(ValueError):
    """Error controlado de validación del input de Fase 3."""


def select_topic(topics: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Selecciona el primer tema elegible sin mutar la lista recibida.

    Un tema es elegible si es un diccionario, tiene ``id`` entero positivo,
    ``title`` y ``normalized_title`` no vacíos, y ``used`` es exactamente ``0``
    o ``False``.
    """

    selection = _select_from_topics(topics)
    selected_topic = selection["selected_topic"]
    return deepcopy(selected_topic) if selected_topic is not None else None


def process_duplicates_output(
    input_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Procesa un output de Fase 3 y guarda el entregable de Fase 4."""

    source_path = Path(input_path)
    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"

    try:
        source_output = _load_phase_3_output(source_path)
        source_items = source_output.data.get("items", [])
        if not isinstance(source_items, list):
            raise TopicSelectorServiceError("data.items debe ser una lista")

        selection = _select_from_topics(source_items)
        upstream_errors = _sanitize_errors(source_output.errors)
        used_fallback = _source_used_fallback(source_output)
        selected_topic = selection["selected_topic"]
        status = (
            "draft"
            if source_output.status == "draft" or used_fallback or selected_topic is None
            else "success"
        )
        payload = _build_payload(
            run_id=run_id,
            status=status,
            selected_topic=selected_topic,
            errors=upstream_errors,
            source_output=source_output,
            input_count=len(source_items),
            discarded=selection["discarded"],
            eligible_count=selection["eligible_count"],
            used_fallback=used_fallback,
        )
    except Exception as error:  # noqa: BLE001 - el output debe auditar errores controlados.
        payload = _build_error_payload(run_id=run_id, error=error, input_path=source_path)

    _write_json(output_path=output_path, payload=payload)
    return output_path


def create_reuse_topic_output(
    topic: dict[str, Any],
    output_dir: str | Path | None = None,
) -> Path:
    """Crea una selección explícita para reutilizar un tema existente.

    Esta operación no cambia ``topic.used``. Sólo crea una nueva evidencia
    versionada de Fase 4 para que una ejecución posterior pueda comenzar en
    ``crear`` sin volver a ejecutar selección automática.
    """

    selected_topic = _validate_reusable_topic(topic)
    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "data": {
            "selected_topic": selected_topic,
            "strategy": REUSE_STRATEGY,
            "counts": {"input": 1, "eligible": 1, "discarded": 0},
            "discarded": [],
            "source": {
                "type": "history_manual_reuse",
                "topic_id": selected_topic["id"],
                "topic_was_used": not _is_unused(selected_topic.get("used")),
            },
        },
        "errors": [],
    }
    _write_json(output_path=output_path, payload=payload)
    return output_path


def _load_phase_3_output(input_path: Path) -> ParticipantOutput:
    """Carga y valida el archivo entregable de Fase 3."""
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TopicSelectorServiceError(f"No existe el output de Fase 3: {input_path}") from error
    except json.JSONDecodeError as error:
        raise TopicSelectorServiceError(f"JSON inválido en output de Fase 3: {error}") from error

    try:
        output = ParticipantOutput.model_validate(payload)
    except ValidationError as error:
        raise TopicSelectorServiceError(f"Output de Fase 3 inválido: {error}") from error

    if output.participant != SOURCE_PARTICIPANT or output.stage != SOURCE_STAGE:
        raise TopicSelectorServiceError(
            "El input debe pertenecer a participante-3 y stage duplicates"
        )

    if output.status == "error":
        raise TopicSelectorServiceError("El input de Fase 3 está en status error")

    if output.status not in {"success", "draft"}:
        raise TopicSelectorServiceError("El input de Fase 3 debe estar en status success o draft")

    return output


def _validate_reusable_topic(topic: Any) -> dict[str, Any]:
    """Comprueba que el tema manual contenga ID entero positivo y títulos."""
    if not isinstance(topic, dict):
        raise TopicSelectorServiceError("El tema a reutilizar debe ser un objeto")

    topic_id = topic.get("id")
    title = _clean_text(topic.get("title"))
    normalized_title = _clean_text(topic.get("normalized_title"))
    if not _is_positive_int(topic_id):
        raise TopicSelectorServiceError("El tema a reutilizar debe tener id entero positivo")
    if not title or not normalized_title:
        raise TopicSelectorServiceError(
            "El tema a reutilizar debe tener title y normalized_title"
        )

    return {
        **deepcopy(topic),
        "id": topic_id,
        "title": title,
        "normalized_title": normalized_title,
        "manual_reuse": True,
    }


def _select_from_topics(topics: list[dict[str, Any]]) -> dict[str, Any]:
    """Evalúa secuencialmente la lista y selecciona el primer tema no usado."""
    if not isinstance(topics, list):
        raise TopicSelectorServiceError("topics debe ser una lista")

    selected_topic: dict[str, Any] | None = None
    discarded: list[dict[str, Any]] = []
    eligible_count = 0

    for index, topic in enumerate(topics):
        if not isinstance(topic, dict):
            discarded.append(_discarded_item(index, "", "", _DISCARD_INVALID_TOPIC))
            continue

        title = _clean_text(topic.get("title"))
        normalized_title = _clean_text(topic.get("normalized_title"))
        topic_id = topic.get("id")
        used = topic.get("used")

        if not _is_positive_int(topic_id) or not title or not normalized_title:
            discarded.append(
                _discarded_item(index, title, normalized_title, _DISCARD_INVALID_TOPIC)
            )
            continue

        if not _is_unused(used):
            discarded.append(
                _discarded_item(index, title, normalized_title, _DISCARD_ALREADY_USED)
            )
            continue

        eligible_count += 1
        if selected_topic is None:
            selected_topic = deepcopy(topic)

    return {
        "selected_topic": selected_topic,
        "eligible_count": eligible_count,
        "discarded": discarded,
    }


def _build_payload(
    *,
    run_id: uuid.UUID,
    status: str,
    selected_topic: dict[str, Any] | None,
    errors: list[str],
    source_output: ParticipantOutput,
    input_count: int,
    discarded: list[dict[str, Any]],
    eligible_count: int,
    used_fallback: bool,
) -> dict[str, Any]:
    """Construye el entregable para el Participante 4."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data": {
            "selected_topic": selected_topic,
            "strategy": STRATEGY,
            "counts": {
                "input": input_count,
                "eligible": eligible_count,
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
    """Construye entregable de status error ante fallo."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "data": {
            "selected_topic": None,
            "strategy": STRATEGY,
            "counts": {
                "input": 0,
                "eligible": 0,
                "discarded": 0,
            },
            "discarded": [],
            "source": {"input_path": str(input_path)},
        },
        "errors": [_sanitize_error(error)],
    }


def _source_used_fallback(source_output: ParticipantOutput) -> bool:
    """Verifica si el output de origen usó fallback."""
    source = source_output.data.get("source", {})
    if isinstance(source, dict):
        return bool(source.get("used_fallback", False))
    return False


def _discarded_item(index: int, title: str, normalized_title: str, reason: str) -> dict[str, Any]:
    """Crea registro de descarte descriptivo."""
    return {
        "index": index,
        "title": title,
        "normalized_title": normalized_title,
        "reason": reason,
    }


def _write_json(output_path: Path, payload: dict[str, Any]) -> None:
    """Persiste entregable JSON en disco."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _is_positive_int(value: Any) -> bool:
    """Valida entero positivo descartando booleanos."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_unused(value: Any) -> bool:
    """Valida si el valor representa topic no usado (0 o False)."""
    return value is False or (isinstance(value, int) and not isinstance(value, bool) and value == 0)


def _clean_text(value: Any) -> str:
    """Elimina espacios en blanco redundantes."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _sanitize_error(error: Exception) -> str:
    """Sanitiza mensaje de error."""
    message = str(error).strip() or error.__class__.__name__
    message = re.sub(r"\s+", " ", message)
    return message[:240]


def _sanitize_errors(errors: list[str]) -> list[str]:
    """Sanitiza lista de mensajes de error."""
    sanitized: list[str] = []
    for error in errors:
        message = re.sub(r"\s+", " ", str(error)).strip()[:240]
        if message:
            sanitized.append(message)
    return sanitized
