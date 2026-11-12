"""Estado JSON activo para continuar o reiniciar el pipeline.

Esta capa NO reemplaza los outputs versionados por participante. Los referencia
para saber hasta dónde llegó una ejecución y sincroniza cada cambio del estado
real con el historial persistente en SQLite.

Referencias arquitectónicas:
    - ADR-0014: Estado unificado de pipeline y persistencia relacional de ejecuciones.
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
    - ADR-0015: Cancelación cooperativa del pipeline y cierre de sockets en vuelo.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

STATE_VERSION = "1.0"
MANUAL_REUSE_MODE = "manual_history_reuse"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATE_PATH = PROJECT_ROOT / "output" / "pipeline_state.json"

PipelineStep = Literal["descubrir", "filtrar", "elegir", "crear", "publicar", "medir"]
PipelineStatus = Literal["idle", "running", "success", "draft", "error", "cancelled"]

STEP_ORDER: tuple[PipelineStep, ...] = (
    "descubrir",
    "filtrar",
    "elegir",
    "crear",
    "publicar",
    "medir",
)

STEP_LABELS: dict[PipelineStep, str] = {
    "descubrir": "Descubrir trends",
    "filtrar": "Filtrar duplicados",
    "elegir": "Elegir tema",
    "crear": "Crear post",
    "publicar": "Publicar",
    "medir": "Medir",
}

STEP_OUTPUT_KEYS: dict[PipelineStep, str] = {
    "descubrir": "trends",
    "filtrar": "duplicates",
    "elegir": "topic_selector",
    "crear": "ai",
    "publicar": "instagram",
    "medir": "frontend",
}


class PipelineStateError(ValueError):
    """Error controlado de lectura/escritura del estado del pipeline."""


def create_pipeline_state(
    *,
    selected_steps: list[str] | None = None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Crea un estado nuevo en idle y lo persiste en disco y base de datos.

    Args:
        selected_steps: Pasos seleccionados para la corrida o None para vacíos.
        state_path: Ruta del archivo JSON de estado.

    Returns:
        Diccionario con el payload validado del nuevo estado creado.
    """

    selected = _normalize_steps(selected_steps or [])
    now = _now()
    state = {
        "state_version": STATE_VERSION,
        "run_id": str(uuid.uuid4()),
        "status": "idle",
        "current_step": None,
        "selected_steps": selected,
        "completed_steps": [],
        "next_step": selected[0] if selected else STEP_ORDER[0],
        "outputs": _empty_outputs(),
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    _write_state(state, Path(state_path))
    return state


def get_pipeline_state(
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    create_if_missing: bool = True,
) -> dict[str, Any]:
    """Lee el estado actual o crea uno vacío si no existe.

    Args:
        state_path: Ubicación del archivo `pipeline_state.json`.
        create_if_missing: Si es True y el archivo no existe, crea un estado idle inicial.

    Returns:
        Estructura de datos del estado actual validada contra `_validate_state`.

    Raises:
        PipelineStateError: Si el archivo no existe y `create_if_missing=False`, o el JSON está corrupto.
    """

    path = Path(state_path)
    if not path.exists():
        if create_if_missing:
            return create_pipeline_state(state_path=path)
        raise PipelineStateError(f"No existe estado de pipeline: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PipelineStateError(f"Estado de pipeline inválido: {error}") from error

    return _validate_state(payload)


def start_pipeline_run(
    *,
    selected_steps: list[str] | None = None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Inicia una ejecución nueva conservando el archivo de estado.

    Genera un nuevo `run_id` y transiciona el estado a `running`, estableciendo
    el primer paso seleccionado como `current_step`.

    Args:
        selected_steps: Lista de pasos a ejecutar, por defecto todos los pasos canónicos.
        state_path: Ruta destino del archivo de estado.

    Returns:
        Diccionario con el estado inicial de la corrida en progreso.
    """

    selected = _normalize_steps(selected_steps or list(STEP_ORDER))
    now = _now()
    state = {
        "state_version": STATE_VERSION,
        "run_id": str(uuid.uuid4()),
        "status": "running",
        "current_step": selected[0] if selected else None,
        "selected_steps": selected,
        "completed_steps": [],
        "next_step": selected[0] if selected else None,
        "outputs": _empty_outputs(),
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    _write_state(state, Path(state_path))
    return state


def mark_step_started(
    step: str,
    *,
    selected_steps: list[str] | None = None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Marca un paso como paso actual e invalida su rama downstream.

    Re-ejecutar un paso cambia la evidencia de esa etapa. Por eso el estado no
    puede seguir marcando como completados ni referenciando outputs de ese paso
    ni de pasos posteriores. Los archivos versionados no se borran: sólo dejan
    de ser la rama activa del pipeline.

    Args:
        step: Nombre o alias del paso que comienza ejecución.
        selected_steps: Pasos seleccionados para actualizar el plan, opcional.
        state_path: Ubicación del archivo de estado.

    Returns:
        Diccionario con el estado actualizado en `running`.
    """

    normalized_step = _normalize_step(step)
    state = get_pipeline_state(state_path=state_path)
    if selected_steps is not None:
        state["selected_steps"] = _normalize_steps(selected_steps)
    elif normalized_step not in state["selected_steps"]:
        state["selected_steps"].append(normalized_step)
        state["selected_steps"] = _sort_steps(state["selected_steps"])

    _invalidate_from_step(state, normalized_step)

    state["status"] = "running"
    state["current_step"] = normalized_step
    state["next_step"] = normalized_step
    state["errors"] = []
    state["updated_at"] = _now()
    _write_state(state, Path(state_path))
    return state


def mark_step_completed(
    step: str,
    *,
    output_path: str | Path | None = None,
    status: PipelineStatus = "success",
    errors: list[str] | None = None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Registra un paso terminado y calcula el próximo paso pendiente.

    Actualiza el registro de outputs asociando el path relativo generado, limpia
    `current_step` y avanza a `next_step` según los pasos planificados.

    Args:
        step: Paso completado.
        output_path: Ruta al archivo JSON entregable generado por la fase.
        status: Estado de finalización ('success' o 'draft').
        errors: Errores no bloqueantes o advertencias acumuladas.
        state_path: Ruta del archivo de estado.

    Returns:
        Diccionario con el estado actualizado tras la finalización del paso.

    Raises:
        PipelineStateError: Si el status no es 'success' o 'draft'.
    """

    normalized_step = _normalize_step(step)
    if status not in {"success", "draft"}:
        raise PipelineStateError("Un paso completado sólo puede quedar en success o draft")

    state = get_pipeline_state(state_path=state_path)
    completed = list(state["completed_steps"])
    if normalized_step not in completed:
        completed.append(normalized_step)

    output_key = STEP_OUTPUT_KEYS[normalized_step]
    if output_path is not None:
        state["outputs"][output_key] = _normalize_output_path(output_path)

    step_errors = errors or []

    state["completed_steps"] = _sort_steps(completed)
    state["current_step"] = None
    state["next_step"] = _next_pending_step(state["selected_steps"], state["completed_steps"])
    state["status"] = "draft" if status == "draft" or step_errors else _status_from_progress(state)
    state["errors"] = (
        _merge_errors(state.get("errors", []), step_errors)
        if step_errors or status == "draft"
        else []
    )
    state["updated_at"] = _now()
    _write_state(state, Path(state_path))
    return state


def mark_step_failed(
    step: str,
    *,
    error: str,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Registra un fallo de paso y deja el estado en error.

    Args:
        step: Paso en el que ocurrió la falla.
        error: Mensaje descriptivo del error ocurrido.
        state_path: Ruta del archivo de estado.

    Returns:
        Diccionario con el estado transicionado a `error`.
    """

    normalized_step = _normalize_step(step)
    state = get_pipeline_state(state_path=state_path)
    state["status"] = "error"
    state["current_step"] = normalized_step
    state["next_step"] = normalized_step
    state["errors"] = _merge_errors(state.get("errors", []), [error])
    state["updated_at"] = _now()
    _write_state(state, Path(state_path))
    return state


def mark_pipeline_cancelled(
    *,
    reason: str = "Ejecución cancelada por el usuario",
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Marca la ejecución activa como cancelada sin borrar evidencia previa.

    Args:
        reason: Motivo de la cancelación cooperativa.
        state_path: Ubicación del archivo de estado.

    Returns:
        Diccionario con el estado transicionado a `cancelled`.
    """

    state = get_pipeline_state(state_path=state_path)
    current_step = state.get("current_step")
    if current_step is not None:
        state["current_step"] = _normalize_step(current_step)
        state["next_step"] = state["current_step"]
    state["status"] = "cancelled"
    state["errors"] = _merge_errors(state.get("errors", []), [reason])
    state["updated_at"] = _now()
    _write_state(state, Path(state_path))
    return state


def is_pipeline_cancelled(
    *,
    run_id: str | None = None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> bool:
    """Indica si la ejecución actual fue cancelada.

    Permite a los routers y orquestadores consultar si la corrida activa
    recibió una solicitud de cancelación cooperativa.

    Args:
        run_id: Identificador esperado de la corrida a verificar.
        state_path: Ubicación del archivo de estado.

    Returns:
        True si coincide el run_id y el estado es 'cancelled', False en caso contrario.
    """

    if run_id is None:
        return False
    state = get_pipeline_state(state_path=state_path)
    if state.get("run_id") != run_id:
        return False
    return state.get("status") == "cancelled"

def reset_pipeline_state(
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    create_new: bool = True,
) -> dict[str, Any] | None:
    """Elimina el estado actual y opcionalmente crea uno nuevo vacío.

    Args:
        state_path: Ubicación del archivo de estado.
        create_new: Si es True, inicializa y devuelve un nuevo estado en `idle`.

    Returns:
        Diccionario con el nuevo estado si `create_new=True`, o None.
    """

    path = Path(state_path)
    if path.exists():
        path.unlink()

    if not create_new:
        return None

    return create_pipeline_state(state_path=path)


def delete_pipeline_state(*, state_path: str | Path = DEFAULT_STATE_PATH) -> bool:
    """Elimina el archivo de estado. Devuelve True si existía.

    Args:
        state_path: Ubicación del archivo de estado.

    Returns:
        True si el archivo existía y fue desvinculado, False si no existía.
    """

    path = Path(state_path)
    if not path.exists():
        return False
    path.unlink()
    return True


def bootstrap_state_from_outputs(
    *,
    trends_output: str | Path | None = None,
    duplicates_output: str | Path | None = None,
    topic_selector_output: str | Path | None = None,
    status: PipelineStatus = "draft",
    errors: list[str] | None = None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Crea un estado inicial a partir de outputs ya generados.

    Permite reconstruir el estado operativo del pipeline cuando existen
    entregables previos en disco sin un `pipeline_state.json` activo.

    Args:
        trends_output: Ruta al output de Fase 2 (opcional).
        duplicates_output: Ruta al output de Fase 3 (opcional).
        topic_selector_output: Ruta al output de Fase 4 (opcional).
        status: Estado asignado a la corrida reconstruida.
        errors: Lista de errores o advertencias previas.
        state_path: Ubicación de destino del estado reconstruido.

    Returns:
        Diccionario con el estado persistido.
    """

    completed_steps: list[PipelineStep] = []
    outputs = _empty_outputs()

    if trends_output is not None:
        completed_steps.append("descubrir")
        outputs["trends"] = _normalize_output_path(trends_output)
    if duplicates_output is not None:
        completed_steps.append("filtrar")
        outputs["duplicates"] = _normalize_output_path(duplicates_output)
    if topic_selector_output is not None:
        completed_steps.append("elegir")
        outputs["topic_selector"] = _normalize_output_path(topic_selector_output)

    selected_steps = list(STEP_ORDER)
    now = _now()
    state = {
        "state_version": STATE_VERSION,
        "run_id": str(uuid.uuid4()),
        "status": status,
        "current_step": None,
        "selected_steps": selected_steps,
        "completed_steps": _sort_steps(completed_steps),
        "next_step": _next_pending_step(selected_steps, completed_steps),
        "outputs": outputs,
        "errors": _sanitize_errors(errors or []),
        "created_at": now,
        "updated_at": now,
    }
    _write_state(state, Path(state_path))
    return state


def prepare_topic_reuse(
    *,
    topic_selector_output: str | Path,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Abre una rama nueva preparada para crear contenido con un tema existente.

    La preparación es deliberadamente ``idle``: no hay una ejecución activa.
    Fase 4 queda registrada como evidencia explícita y sólo ``crear`` queda
    seleccionado. El usuario debe iniciar esa fase desde el dashboard.

    Args:
        topic_selector_output: Ruta al archivo generado por `create_reuse_topic_output`.
        state_path: Ubicación del archivo de estado.

    Returns:
        Diccionario con el estado configurado en modo `manual_history_reuse`.
    """

    now = _now()
    outputs = _empty_outputs()
    outputs["topic_selector"] = _normalize_output_path(topic_selector_output)
    state = {
        "state_version": STATE_VERSION,
        "run_id": str(uuid.uuid4()),
        "execution_mode": MANUAL_REUSE_MODE,
        "status": "idle",
        "current_step": None,
        "selected_steps": ["crear"],
        "completed_steps": ["elegir"],
        "next_step": "crear",
        "outputs": outputs,
        "errors": [],
        "created_at": now,
        "updated_at": now,
    }
    _write_state(state, Path(state_path))
    return state



def _invalidate_from_step(state: dict[str, Any], step: PipelineStep) -> None:
    """Quita del estado activo el paso indicado y todos sus dependientes.

    Garantiza que no queden referencias a outputs de fases posteriores
    cuando se re-ejecuta un paso intermedio anterior.
    """

    step_index = STEP_ORDER.index(step)
    invalid_steps = set(STEP_ORDER[step_index:])
    invalid_output_keys = {STEP_OUTPUT_KEYS[invalid_step] for invalid_step in invalid_steps}

    state["completed_steps"] = _sort_steps(
        [
            completed_step
            for completed_step in state.get("completed_steps", [])
            if completed_step not in invalid_steps
        ]
    )

    outputs = {**_empty_outputs(), **state.get("outputs", {})}
    for output_key in invalid_output_keys:
        outputs[output_key] = None
    state["outputs"] = outputs


def _empty_outputs() -> dict[str, str | None]:
    """Inicializa el mapa canónico de outputs en None para todas las etapas."""
    return {
        "trends": None,
        "duplicates": None,
        "topic_selector": None,
        "ai": None,
        "instagram": None,
        "frontend": None,
    }


def _validate_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Valida la integridad estructural del diccionario de estado JSON.

    Comprueba versión de esquema, validez de UUID, tipos de datos y normaliza
    listas de pasos seleccionados y completados.
    """
    if not isinstance(payload, dict):
        raise PipelineStateError("El estado debe ser un objeto JSON")
    if payload.get("state_version") != STATE_VERSION:
        raise PipelineStateError(f"state_version debe ser {STATE_VERSION}")
    try:
        uuid.UUID(str(payload.get("run_id")))
    except (TypeError, ValueError) as error:
        raise PipelineStateError("run_id debe ser un UUID válido") from error

    payload["selected_steps"] = _normalize_steps(payload.get("selected_steps", []))
    payload["completed_steps"] = _sort_steps(_normalize_steps(payload.get("completed_steps", [])))
    if payload.get("current_step") is not None:
        payload["current_step"] = _normalize_step(payload["current_step"])
    if payload.get("next_step") is not None:
        payload["next_step"] = _normalize_step(payload["next_step"])

    status = payload.get("status")
    if status not in {"idle", "running", "success", "draft", "error", "cancelled"}:
        raise PipelineStateError("status de pipeline inválido")

    outputs = payload.get("outputs", {})
    if not isinstance(outputs, dict):
        raise PipelineStateError("outputs debe ser un objeto")
    payload["outputs"] = {**_empty_outputs(), **outputs}
    payload["errors"] = _sanitize_errors(payload.get("errors", []))
    return payload


def _write_state(state: dict[str, Any], path: Path) -> None:
    """Escribe el estado JSON en disco y sincroniza con SQLite en la ruta por defecto."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    if path.resolve() == DEFAULT_STATE_PATH.resolve():
        # Import diferido para evitar un ciclo de módulos: history necesita
        # leer/validar el estado, pero state sólo necesita persistir al escribir.
        from python_backend.services.pipeline.pipeline_history_service import (
            upsert_pipeline_run,
        )

        upsert_pipeline_run(state)


def _normalize_step(step: str) -> PipelineStep:
    """Normaliza alias en español e inglés hacia el nombre canónico del paso."""
    if not isinstance(step, str):
        raise PipelineStateError("El paso debe ser texto")
    normalized = step.strip().lower()
    aliases = {
        "discover": "descubrir",
        "trends": "descubrir",
        "duplicates": "filtrar",
        "filter": "filtrar",
        "selector": "elegir",
        "topic_selector": "elegir",
        "choose": "elegir",
        "ai": "crear",
        "content": "crear",
        "instagram": "publicar",
        "publish": "publicar",
        "frontend": "medir",
        "measure": "medir",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in STEP_ORDER:
        raise PipelineStateError(f"Paso de pipeline inválido: {step}")
    return normalized  # type: ignore[return-value]


def _normalize_steps(steps: list[str]) -> list[PipelineStep]:
    """Convierte una lista de nombres o alias de pasos a una lista canónica ordenada."""
    if not isinstance(steps, list):
        raise PipelineStateError("selected_steps debe ser una lista")
    normalized: list[PipelineStep] = []
    for step in steps:
        normalized_step = _normalize_step(step)
        if normalized_step not in normalized:
            normalized.append(normalized_step)
    return _sort_steps(normalized)


def _sort_steps(steps: list[PipelineStep]) -> list[PipelineStep]:
    """Ordena una secuencia de pasos respetando el orden canónico del pipeline."""
    return [step for step in STEP_ORDER if step in steps]


def _next_pending_step(
    selected_steps: list[PipelineStep], completed_steps: list[PipelineStep]
) -> PipelineStep | None:
    """Identifica el primer paso de los seleccionados que aún no fue completado."""
    for step in selected_steps:
        if step not in completed_steps:
            return step
    return None


def _status_from_progress(state: dict[str, Any]) -> PipelineStatus:
    """Calcula el estado global ('success' o 'running') en base a los pasos completados."""
    selected = state.get("selected_steps", [])
    completed = state.get("completed_steps", [])
    if selected and all(step in completed for step in selected):
        return "success"
    return "running"


def _normalize_output_path(output_path: str | Path) -> str:
    """Convierte un path de archivo a ruta relativa al directorio raíz del proyecto."""
    path = Path(output_path)
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _merge_errors(existing: list[str], new_errors: list[str]) -> list[str]:
    """Fusiona dos listas de mensajes de error sin duplicar textos equivalentes."""
    merged = _sanitize_errors(existing)
    for error in _sanitize_errors(new_errors):
        if error not in merged:
            merged.append(error)
    return merged


def _sanitize_errors(errors: list[str]) -> list[str]:
    """Sanitiza y trunca mensajes de error a un formato seguro de longitud acotada."""
    if not isinstance(errors, list):
        return []
    sanitized: list[str] = []
    for error in errors:
        message = re.sub(r"\s+", " ", str(error)).strip()[:240]
        if message:
            sanitized.append(message)
    return sanitized


def _now() -> str:
    """Devuelve la marca temporal UTC actual formateada en ISO 8601."""
    return datetime.now(timezone.utc).isoformat()
