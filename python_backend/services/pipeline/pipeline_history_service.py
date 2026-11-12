"""Persistencia y consulta de corridas correlacionadas del pipeline.

Cada fila representa una rama identificada por el ``run_id`` global del estado.
La evidencia se obtiene exclusivamente de los outputs referenciados por esa
rama; nunca se consulta un archivo o endpoint global ``latest``.

Referencias arquitectónicas:
    - ADR-0014: Estado unificado de pipeline y persistencia relacional de ejecuciones.
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func

from python_backend.database.connection import get_session
from python_backend.models.pipeline_run_model import PipelineRun
from python_backend.services.pipeline import pipeline_state_service

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TERMINAL_STATUSES = {"success", "draft", "error", "cancelled"}
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def sync_current_pipeline_state() -> dict[str, Any] | None:
    """Persiste el estado activo si representa una corrida real.

    Returns:
        Diccionario con el detalle de la corrida sincronizada en SQLite,
        o None si el estado actual está inactivo sin operaciones registradas.
    """

    state = pipeline_state_service.get_pipeline_state()
    return upsert_pipeline_run(state)


def upsert_pipeline_run(state: dict[str, Any]) -> dict[str, Any] | None:
    """Inserta o actualiza una corrida sin tocar filas históricas ajenas.

    Extrae la evidencia de los outputs referenciados por la corrida, actualiza
    los campos agregados en `pipeline_runs` y serializa el detalle en columnas
    JSON para trazabilidad sin alterar corridas anteriores.

    Args:
        state: Diccionario de estado del pipeline.

    Returns:
        Diccionario con la fila persistida en detalle completo, o None si no hay actividad.
    """

    if not _has_activity(state):
        return None

    snapshot = build_run_snapshot(state)
    run_id = str(snapshot["id"])
    with get_session() as session:
        run = session.get(PipelineRun, run_id)
        if run is None:
            run = PipelineRun(
                run_id=run_id,
                started_at=snapshot["created_at"],
                updated_at=snapshot["updated_at"],
                status=snapshot["status"],
            )
            session.add(run)

        run.started_at = snapshot["created_at"]
        run.updated_at = snapshot["updated_at"]
        run.finished_at = (
            snapshot["updated_at"] if snapshot["status"] in TERMINAL_STATUSES else None
        )
        run.status = snapshot["status"]
        run.execution_mode = snapshot.get("execution_mode")
        run.selected_steps_json = _json_dump(snapshot["selected_steps"])
        run.completed_steps_json = _json_dump(snapshot["completed_steps"])
        run.current_step = snapshot.get("current_step")
        run.next_step = snapshot.get("next_step")
        run.outputs_json = _json_dump(snapshot["outputs"])
        run.errors_json = _json_dump(snapshot["errors"])
        run.evidence_json = _json_dump(
            {
                "topic": snapshot.get("topic"),
                "post": snapshot.get("post"),
                "generated_content": snapshot.get("generated_content"),
                "publication_log": snapshot.get("publication_log"),
                "quality": snapshot.get("quality"),
            }
        )
        topic = snapshot.get("topic") or {}
        post = snapshot.get("post") or {}
        run.topic_id = _positive_int(topic.get("id"))
        run.topic_title = _clean_optional_text(topic.get("title"))
        run.post_id = _positive_int(post.get("id"))
        run.quality_score = snapshot.get("quality", {}).get("score")
        session.commit()
        session.refresh(run)
        return _run_to_dict(run, detail=True)


def list_pipeline_runs(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    topic_id: int | None = None,
    topic: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Lista corridas reales, recientes primero, con filtros server-side.

    Args:
        date_from: Fecha o timestamp inferior ISO (inclusive).
        date_to: Fecha o timestamp superior ISO (exclusive en fechas YYYY-MM-DD).
        topic_id: Filtro exacto por ID de tema.
        topic: Filtro parcial case-insensitive por título de tema.
        limit: Cantidad máxima de registros (acotada entre 1 y MAX_LIMIT).

    Returns:
        Diccionario con clave `items` (resumen de corridas) y `meta` (conteo y límites).
    """

    lower_bound = _parse_date_bound(date_from, upper=False)
    upper_bound = _parse_date_bound(date_to, upper=True)
    bounded_limit = max(1, min(int(limit), MAX_LIMIT))
    clean_topic = _clean_optional_text(topic)

    with get_session() as session:
        query = session.query(PipelineRun)
        if lower_bound is not None:
            query = query.filter(PipelineRun.started_at >= lower_bound)
        if upper_bound is not None:
            query = query.filter(PipelineRun.started_at < upper_bound)
        if topic_id is not None:
            query = query.filter(PipelineRun.topic_id == topic_id)
        if clean_topic:
            query = query.filter(func.lower(PipelineRun.topic_title).contains(clean_topic.lower()))

        total = query.count()
        runs = (
            query.order_by(PipelineRun.updated_at.desc(), PipelineRun.run_id.desc())
            .limit(bounded_limit)
            .all()
        )

    return {
        "items": [_run_to_dict(run, detail=False) for run in runs],
        "meta": {
            "persistent_history": True,
            "available_runs": total,
            "returned_runs": len(runs),
            "limit": bounded_limit,
        },
    }


def get_pipeline_run(run_id: str) -> dict[str, Any] | None:
    """Obtiene el detalle completo de una corrida por su run_id.

    Args:
        run_id: Identificador UUID de la corrida.

    Returns:
        Diccionario detallado de la corrida con outputs y evidencia, o None.
    """
    with get_session() as session:
        run = session.get(PipelineRun, run_id)
        return _run_to_dict(run, detail=True) if run is not None else None


def get_current_run_history(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    topic_id: int | None = None,
    topic: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Compatibilidad de ``/pipeline/history`` sobre el historial persistente.

    Sincroniza primero el estado JSON actual y luego consulta la base de datos
    aplicando los filtros solicitados.
    """

    sync_current_pipeline_state()
    return list_pipeline_runs(
        date_from=date_from,
        date_to=date_to,
        topic_id=topic_id,
        topic=topic,
        limit=limit,
    )


def build_run_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Reconstruye un snapshot consolidado leyendo los archivos referenciados en outputs.

    Inspecciona cada output de fase alcanzado por la corrida para extraer metadatos
    de tema, post generado, logs y puntuación de calidad sin consultar endpoints
    globales `latest`.
    """
    output_payloads = {
        key: _read_referenced_output(path)
        for key, path in state.get("outputs", {}).items()
        if path
    }
    selector_data = _data(output_payloads.get("topic_selector"))
    ai_data = _data(output_payloads.get("ai"))
    instagram_data = _data(output_payloads.get("instagram"))
    metrics_data = _data(output_payloads.get("frontend"))

    post = _first_dict(metrics_data.get("post"), instagram_data.get("post"))
    topic = _first_dict(
        metrics_data.get("topic"),
        instagram_data.get("topic"),
        instagram_data.get("selected_topic"),
        ai_data.get("selected_topic"),
        selector_data.get("selected_topic"),
    )
    if not topic and post:
        topic = {
            "id": post.get("topic_id"),
            "title": post.get("topic_title"),
            "normalized_title": post.get("topic_title"),
        }

    publication_log = _first_dict(
        metrics_data.get("publication_log"),
        instagram_data.get("publication_log"),
    )
    score = metrics_data.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        score = None
    generated_content = _first_dict(ai_data.get("content"))

    created_at = state.get("created_at") or state.get("updated_at") or _now()
    updated_at = state.get("updated_at") or created_at
    return {
        "id": state.get("run_id"),
        "status": state.get("status", "idle"),
        "execution_mode": state.get("execution_mode"),
        "created_at": created_at,
        "updated_at": updated_at,
        "finished_at": updated_at if state.get("status") in TERMINAL_STATUSES else None,
        "selected_steps": state.get("selected_steps", []),
        "completed_steps": state.get("completed_steps", []),
        "current_step": state.get("current_step"),
        "next_step": state.get("next_step"),
        "topic": topic,
        "post": post,
        "generated_content": generated_content,
        "publication_log": publication_log,
        "quality": {
            "score": score,
            "checks": metrics_data.get("checks", {}),
            "warnings": metrics_data.get("warnings", []),
        },
        "outputs": state.get("outputs", {}),
        "errors": state.get("errors", []),
    }


def _run_to_dict(run: PipelineRun, *, detail: bool) -> dict[str, Any]:
    """Serializa una entidad PipelineRun a un diccionario de respuesta API."""
    evidence = _json_load(run.evidence_json, {})
    topic = evidence.get("topic") if isinstance(evidence.get("topic"), dict) else None
    post = evidence.get("post") if isinstance(evidence.get("post"), dict) else None
    quality = evidence.get("quality") if isinstance(evidence.get("quality"), dict) else {}
    if topic is None and run.topic_id is not None:
        topic = {"id": run.topic_id, "title": run.topic_title}
    if post is None and run.post_id is not None:
        post = {"id": run.post_id, "topic_id": run.topic_id, "topic_title": run.topic_title}
    if not quality:
        quality = {"score": run.quality_score, "checks": {}, "warnings": []}

    payload = {
        "id": run.run_id,
        "status": run.status,
        "execution_mode": run.execution_mode,
        "created_at": run.started_at,
        "updated_at": run.updated_at,
        "finished_at": run.finished_at,
        "selected_steps": _json_load(run.selected_steps_json, []),
        "completed_steps": _json_load(run.completed_steps_json, []),
        "current_step": run.current_step,
        "next_step": run.next_step,
        "topic": topic,
        "post": post,
        "quality": quality,
    }
    if detail:
        payload.update(
            {
                "generated_content": evidence.get("generated_content"),
                "publication_log": evidence.get("publication_log"),
                "outputs": _json_load(run.outputs_json, {}),
                "errors": _json_load(run.errors_json, []),
            }
        )
    return payload


def _read_referenced_output(path: Any) -> dict[str, Any]:
    """Lee de forma segura un archivo JSON de output referenciado."""
    if not isinstance(path, str) or not path.strip():
        return {}
    concrete = Path(path)
    if not concrete.is_absolute():
        concrete = PROJECT_ROOT / concrete
    try:
        payload = json.loads(concrete.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _data(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Extrae el objeto `data` de un payload entregable de forma segura."""
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else {}


def _first_dict(*values: Any) -> dict[str, Any] | None:
    """Devuelve el primer valor que sea un diccionario no vacío."""
    for value in values:
        if isinstance(value, dict) and value:
            return value
    return None


def _has_activity(state: dict[str, Any]) -> bool:
    """Verifica si el estado contiene información significativa que justifique persistir."""
    if state.get("execution_mode"):
        return True
    if state.get("status") != "idle":
        return True
    if state.get("selected_steps") or state.get("completed_steps"):
        return True
    return any(state.get("outputs", {}).values())


def _parse_date_bound(value: str | None, *, upper: bool) -> str | None:
    """Parsea límites de fecha en formato ISO para filtrado de base de datos."""
    clean = _clean_optional_text(value)
    if not clean:
        return None
    try:
        if len(clean) == 10:
            parsed_date = date.fromisoformat(clean)
            parsed = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
            if upper:
                parsed += timedelta(days=1)
        else:
            parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc)
    except ValueError as error:
        raise ValueError(f"Fecha inválida: {clean}") from error
    return parsed.isoformat()


def _json_dump(value: Any) -> str:
    """Serializa un valor a string JSON compacto sin espacios innecesarios."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_load(value: str | None, fallback: Any) -> Any:
    """Deserializa de forma segura un string JSON devolviendo el fallback ante error."""
    try:
        parsed = json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
    return parsed


def _positive_int(value: Any) -> int | None:
    """Valida y extrae un entero positivo descartando booleanos."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _clean_optional_text(value: Any) -> str | None:
    """Limpia espacios en blanco múltiples y devuelve texto limpio o None."""
    clean = " ".join(str(value or "").split()).strip()
    return clean or None


def _now() -> str:
    """Devuelve la marca temporal UTC actual formateada en ISO 8601."""
    return datetime.now(timezone.utc).isoformat()
