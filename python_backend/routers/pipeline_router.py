from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from python_backend.repositories import topic_repository
from python_backend.services.ai.ai_service import process_topic_selector_output
from python_backend.services.duplicates.duplicates_service import process_trends_output
from python_backend.services.instagram.instagram_service import process_ai_output, process_simulated_publication
from python_backend.services.metrics.metrics_service import process_instagram_output
from python_backend.services.pipeline import pipeline_state_service as pipeline_state
from python_backend.services.pipeline.pipeline_history_service import (
    get_current_run_history,
    get_pipeline_run,
    list_pipeline_runs,
    sync_current_pipeline_state,
)
from python_backend.services.pipeline.pipeline_cancel_service import cancel_active_run, pipeline_run_scope
from python_backend.services.topic_selector.topic_selector_service import (
    REUSE_STRATEGY,
    create_reuse_topic_output,
    process_duplicates_output,
)
from python_backend.services.trends.trends_service import save_trends_output

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTED_STEPS = {"descubrir", "filtrar", "elegir", "crear", "publicar", "medir"}


class PipelineRunRequest(BaseModel):
    steps: list[str] = Field(default_factory=list)
    run_steps: list[str] = Field(default_factory=list)


class PipelineCancelRequest(BaseModel):
    reason: str = "Ejecución cancelada por el usuario"


class PipelineCancelledError(RuntimeError):
    """Señal cooperativa para detener una ejecución de pipeline."""


@router.get("/state")
def get_state():
    state = pipeline_state.get_pipeline_state()
    return {"success": True, "data": _state_with_execution_mode(state)}


@router.get("/history")
def get_history(
    date_from: str | None = None,
    date_to: str | None = None,
    topic_id: int | None = None,
    topic: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        return {
            "success": True,
            "data": get_current_run_history(
                date_from=date_from,
                date_to=date_to,
                topic_id=topic_id,
                topic=topic,
                limit=limit,
            ),
        }
    except ValueError as error:
        return _error_response(error)


@router.get("/runs")
def get_runs(
    date_from: str | None = None,
    date_to: str | None = None,
    topic_id: int | None = None,
    topic: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        sync_current_pipeline_state()
        return {
            "success": True,
            "data": list_pipeline_runs(
                date_from=date_from,
                date_to=date_to,
                topic_id=topic_id,
                topic=topic,
                limit=limit,
            ),
        }
    except ValueError as error:
        return _error_response(error)


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str):
    sync_current_pipeline_state()
    run = get_pipeline_run(run_id)
    if run is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Corrida no encontrada"},
        )
    return {"success": True, "data": run}


@router.delete("/state")
def reset_state():
    state = pipeline_state.reset_pipeline_state()
    return {"success": True, "data": state}


@router.post("/cancel")
def cancel_pipeline(payload: PipelineCancelRequest):
    state = pipeline_state.mark_pipeline_cancelled(reason=payload.reason)
    closed_resources = cancel_active_run(state.get("run_id"))
    return {"success": True, "message": "Pipeline cancelado", "data": state, "closed_resources": closed_resources}


@router.post("/topics/{topic_id}/reuse")
def reuse_topic(topic_id: int):
    state = pipeline_state.get_pipeline_state()
    if state.get("status") == "running":
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": "No se puede reutilizar un tema mientras el pipeline está ejecutándose",
            },
        )

    topic = topic_repository.get_topic_by_id(topic_id)
    if topic is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Tema no encontrado"},
        )

    if _is_reuse_already_prepared(state, topic_id):
        return {
            "success": True,
            "message": "El tema ya estaba preparado para crear contenido",
            "data": {"topic": topic, "state": state, "already_prepared": True},
        }

    output_path = create_reuse_topic_output(topic)
    prepared_state = pipeline_state.prepare_topic_reuse(
        topic_selector_output=output_path,
    )
    return {
        "success": True,
        "message": "Tema preparado. Crear quedó seleccionado, pero no se ejecutó.",
        "data": {
            "topic": topic,
            "state": prepared_state,
            "output_path": _relative_path(output_path),
            "already_prepared": False,
        },
    }


@router.post("/discover")
def discover_trends():
    return _execute_step("descubrir")


@router.post("/filter")
def filter_duplicates():
    return _execute_step("filtrar")


@router.post("/select")
def select_topic():
    return _execute_step("elegir")


@router.post("/create")
def create_content():
    return _execute_step("crear")


@router.post("/publish")
def publish_content():
    return _execute_step("publicar")




@router.get("/metrics/latest")
def get_latest_metrics():
    try:
        state = pipeline_state.get_pipeline_state()
        metrics_output = state.get("outputs", {}).get("frontend")
        if metrics_output:
            path = PROJECT_ROOT / metrics_output
            if not path.exists():
                raise ValueError(f"El estado activo referencia métricas inexistentes: {_relative_path(path)}")
            return {"success": True, "data": _read_output(path), "output_path": _relative_path(path)}

        latest = _latest_output("participante-7", "metrics")
        if latest is None:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Todavía no hay métricas de Fase 7"},
            )
        return {"success": True, "data": _read_output(latest), "output_path": _relative_path(latest)}
    except Exception as error:  # noqa: BLE001 - endpoint operacional debe devolver error claro.
        return _error_response(error)




@router.post("/publish-simulated")
def publish_simulated_from_pipeline():
    try:
        state_before_publish = pipeline_state.get_pipeline_state()
        run_id = state_before_publish.get("run_id") if state_before_publish.get("status") == "running" else None
        instagram_output = _required_output_path("instagram", "participante-6", "instagram")
        output_payload = _read_output(instagram_output)
        post = output_payload.get("data", {}).get("post")
        post_id = post.get("id") if isinstance(post, dict) else None
        if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id <= 0:
            raise ValueError("No encontré un post válido para finalizar publicación falsa")

        output_path = process_simulated_publication(post_id)
        _raise_if_cancelled(run_id=run_id)
        output_payload = _read_output(output_path)
        output_status = output_payload.get("status", "error")
        output_errors = output_payload.get("errors", []) if isinstance(output_payload.get("errors"), list) else []

        if output_status == "error":
            state = pipeline_state.mark_step_failed(
                "publicar",
                error="; ".join(str(error) for error in output_errors) or "Output en estado error",
            )
        else:
            state = pipeline_state.mark_step_completed(
                "publicar",
                output_path=output_path,
                status="draft" if output_status == "draft" else "success",
                errors=[str(error) for error in output_errors],
            )

        return JSONResponse(
            status_code=500 if output_status == "error" else 200,
            content={
                "success": output_status != "error",
                "data": {
                    "step": "publicar",
                    "output_path": _relative_path(output_path),
                    "output": output_payload,
                    "state": state,
                },
            },
        )
    except PipelineCancelledError:
        state = pipeline_state.get_pipeline_state()
        return JSONResponse(
            status_code=499,
            content={"success": False, "message": "Pipeline cancelado por el usuario", "data": {"state": state}},
        )
    except Exception as error:  # noqa: BLE001 - endpoint operacional debe devolver error claro.
        return _error_response(error)


@router.post("/run")
def run_pipeline(payload: PipelineRunRequest):
    try:
        selected_steps = _selected_steps_from_payload(payload)
        run_steps = list(
            pipeline_state._normalize_steps(payload.run_steps or selected_steps)  # noqa: SLF001
        )
        reuse_conflict = _manual_reuse_conflict(selected_steps)
        if reuse_conflict is not None:
            return reuse_conflict
        executed: list[dict[str, Any]] = []

        run_id = None

        for step in selected_steps:
            if step not in IMPLEMENTED_STEPS:
                pipeline_state.mark_step_started(step, selected_steps=selected_steps)
                state = pipeline_state.mark_step_failed(
                    step,
                    error=f"El paso '{step}' todavía no tiene implementación backend",
                )
                return JSONResponse(
                    status_code=501,
                    content={
                        "success": False,
                        "message": "El pipeline llegó a un paso no implementado",
                        "data": {"state": state, "executed": executed},
                    },
                )

            result = _run_step(step, selected_steps=run_steps)
            run_id = result["state"].get("run_id")
            _raise_if_cancelled(run_id=run_id)
            executed.append(result)
            state = result["state"]
            if result["output"].get("status") == "error":
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "message": f"Falló el paso {step}",
                        "data": {"state": state, "executed": executed},
                    },
                )

        return {"success": True, "data": {"state": state, "executed": executed}}
    except PipelineCancelledError:
        state = pipeline_state.get_pipeline_state()
        return JSONResponse(
            status_code=499,
            content={
                "success": False,
                "message": "Pipeline cancelado por el usuario",
                "data": {"state": state, "executed": executed},
            },
        )
    except Exception as error:  # noqa: BLE001 - endpoint operacional debe devolver error claro.
        return _error_response(error)


def _execute_step(step: str):
    try:
        normalized_step = pipeline_state._normalize_step(step)  # noqa: SLF001 - router acepta aliases públicos.
        reuse_conflict = _manual_reuse_conflict([normalized_step])
        if reuse_conflict is not None:
            return reuse_conflict
        run_id = pipeline_state.get_pipeline_state().get("run_id")
        result = _run_step(normalized_step, run_id=run_id)
        _raise_if_cancelled(run_id=result["state"].get("run_id"))
        output_status = result["output"].get("status")
        status_code = 500 if output_status == "error" else 200
        return JSONResponse(
            status_code=status_code,
            content={"success": output_status != "error", "data": result},
        )
    except PipelineCancelledError:
        state = pipeline_state.get_pipeline_state()
        return JSONResponse(
            status_code=499,
            content={"success": False, "message": "Pipeline cancelado por el usuario", "data": {"state": state}},
        )
    except Exception as error:  # noqa: BLE001 - endpoint operacional debe devolver error claro.
        return _error_response(error)


def _selected_steps_from_payload(payload: PipelineRunRequest) -> list[str]:
    raw_steps = payload.steps or list(pipeline_state.STEP_ORDER)
    return list(pipeline_state._normalize_steps(raw_steps))  # noqa: SLF001 - router acepta aliases públicos.


def _manual_reuse_conflict(selected_steps: list[str]) -> JSONResponse | None:
    state = pipeline_state.get_pipeline_state()
    blocked_steps = [step for step in selected_steps if step in {"descubrir", "filtrar", "elegir"}]
    if not blocked_steps or not _is_manual_reuse_mode(state):
        return None

    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "message": (
                "Hay una reutilización manual preparada. Sólo podés ejecutar Crear, Publicar y Medir. "
                "Reiniciá el estado del pipeline para abandonar ese tema y correr desde cero."
            ),
            "data": {
                "state": _state_with_execution_mode(state),
                "blocked_steps": blocked_steps,
                "reset_endpoint": "/api/pipeline/state",
            },
        },
    )


def _run_step(step: str, selected_steps: list[str] | None = None, run_id: str | None = None) -> dict[str, Any]:
    normalized_step = pipeline_state._normalize_step(step)  # noqa: SLF001 - router acepta aliases públicos.
    if normalized_step not in IMPLEMENTED_STEPS:
        raise ValueError(f"El paso '{normalized_step}' todavía no tiene implementación backend")

    state_before_step = pipeline_state.get_pipeline_state()
    if normalized_step == "descubrir" and _state_has_activity(state_before_step):
        state_before_step = pipeline_state.start_pipeline_run(
            selected_steps=selected_steps or list(pipeline_state.STEP_ORDER),
        )
        run_id = state_before_step.get("run_id")

    pipeline_state.mark_step_started(normalized_step, selected_steps=selected_steps)
    run_id = run_id or pipeline_state.get_pipeline_state().get("run_id")
    _raise_if_cancelled(run_id=run_id)

    with pipeline_run_scope(run_id):
        if normalized_step == "descubrir":
            output_path = save_trends_output()
        elif normalized_step == "filtrar":
            trends_output = _required_output_path("trends", "participante-2", "trends")
            output_path = process_trends_output(trends_output)
        elif normalized_step == "elegir":
            duplicates_output = _required_output_path("duplicates", "participante-3", "duplicates")
            output_path = process_duplicates_output(duplicates_output)
        elif normalized_step == "crear":
            topic_selector_output = _required_output_path("topic_selector", "participante-4", "topic_selector")
            output_path = process_topic_selector_output(topic_selector_output)
        elif normalized_step == "publicar":
            ai_output = _required_output_path("ai", "participante-5", "ai")
            output_path = process_ai_output(ai_output)
        else:
            instagram_output = _required_output_path("instagram", "participante-6", "instagram")
            output_path = process_instagram_output(instagram_output)

    _raise_if_cancelled(run_id=run_id)

    output_payload = _read_output(output_path)
    output_status = output_payload.get("status", "error")
    output_errors = output_payload.get("errors", []) if isinstance(output_payload.get("errors"), list) else []

    if output_status == "error":
        state = pipeline_state.mark_step_failed(
            normalized_step,
            error="; ".join(str(error) for error in output_errors) or "Output en estado error",
        )
    else:
        state = pipeline_state.mark_step_completed(
            normalized_step,
            output_path=output_path,
            status="draft" if output_status == "draft" else "success",
            errors=[str(error) for error in output_errors],
        )

    return {
        "step": normalized_step,
        "output_path": _relative_path(output_path),
        "output": output_payload,
        "state": state,
    }



def _raise_if_cancelled(*, run_id: str | None = None) -> None:
    if pipeline_state.is_pipeline_cancelled(run_id=run_id):
        raise PipelineCancelledError("Pipeline cancelado por el usuario")


def _state_has_activity(state: dict[str, Any]) -> bool:
    if state.get("execution_mode"):
        return True
    if state.get("status") != "idle":
        return True
    if state.get("selected_steps") or state.get("completed_steps"):
        return True
    return any(state.get("outputs", {}).values())


def _is_reuse_already_prepared(state: dict[str, Any], topic_id: int) -> bool:
    if state.get("status") != "idle":
        return False
    if state.get("selected_steps") != ["crear"] or state.get("next_step") != "crear":
        return False
    output_path = state.get("outputs", {}).get("topic_selector")
    if not output_path:
        return False
    concrete = Path(output_path)
    if not concrete.is_absolute():
        concrete = PROJECT_ROOT / concrete
    if not concrete.exists():
        return False
    try:
        output = _read_output(concrete)
    except (OSError, json.JSONDecodeError):
        return False
    data = output.get("data", {})
    selected_topic = data.get("selected_topic") if isinstance(data, dict) else None
    return (
        data.get("strategy") == REUSE_STRATEGY
        and isinstance(selected_topic, dict)
        and selected_topic.get("id") == topic_id
    )


def _is_manual_reuse_mode(state: dict[str, Any]) -> bool:
    if state.get("execution_mode") == pipeline_state.MANUAL_REUSE_MODE:
        return True
    if "elegir" not in state.get("completed_steps", []):
        return False

    output_path = state.get("outputs", {}).get("topic_selector")
    if not output_path:
        return False
    concrete = Path(output_path)
    if not concrete.is_absolute():
        concrete = PROJECT_ROOT / concrete
    if not concrete.exists():
        return False
    try:
        output = _read_output(concrete)
    except (OSError, json.JSONDecodeError):
        return False
    data = output.get("data", {})
    return isinstance(data, dict) and data.get("strategy") == REUSE_STRATEGY


def _state_with_execution_mode(state: dict[str, Any]) -> dict[str, Any]:
    if not _is_manual_reuse_mode(state):
        return state
    return {**state, "execution_mode": pipeline_state.MANUAL_REUSE_MODE}

def _required_output_path(output_key: str, participant: str, stage: str) -> Path:
    state = pipeline_state.get_pipeline_state()
    state_output = state.get("outputs", {}).get(output_key)
    if state_output:
        path = PROJECT_ROOT / state_output
        if path.exists():
            return path

    latest = _latest_output(participant, stage)
    if latest is not None:
        return latest

    raise ValueError(f"No existe un output previo requerido para {output_key}")


def _latest_output(participant: str, stage: str, preferred_status: str | None = None) -> Path | None:
    output_dir = PROJECT_ROOT / "output" / participant
    candidates = sorted(
        output_dir.glob(f"{stage}_v1_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if preferred_status is None:
        return candidates[0] if candidates else None

    for candidate in candidates:
        try:
            payload = _read_output(candidate)
        except Exception:  # noqa: BLE001 - ignora outputs corruptos al buscar fallback visual.
            continue
        if payload.get("status") == preferred_status:
            return candidate
    return None


def _read_output(output_path: Path) -> dict[str, Any]:
    return json.loads(output_path.read_text(encoding="utf-8"))


def _relative_path(path: str | Path) -> str:
    concrete = Path(path)
    try:
        return str(concrete.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(concrete)


def _error_response(error: Exception) -> JSONResponse:
    message = " ".join(str(error).split())[:240] or "Error desconocido"
    return JSONResponse(
        status_code=400,
        content={"success": False, "message": message},
    )
