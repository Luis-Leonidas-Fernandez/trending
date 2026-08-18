import json
from pathlib import Path
from uuid import UUID

import pytest

from python_backend.services.pipeline import pipeline_state_service as state_service


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_create_pipeline_state_starts_idle_with_selected_steps(tmp_path):
    state_path = tmp_path / "pipeline_state.json"

    state = state_service.create_pipeline_state(
        selected_steps=["elegir", "descubrir", "descubrir"],
        state_path=state_path,
    )

    UUID(state["run_id"])
    assert state["status"] == "idle"
    assert state["selected_steps"] == ["descubrir", "elegir"]
    assert state["completed_steps"] == []
    assert state["next_step"] == "descubrir"
    assert state["outputs"]["trends"] is None
    assert read_json(state_path) == state


def test_start_pipeline_run_resets_outputs_and_marks_first_step_running(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.create_pipeline_state(selected_steps=["descubrir"], state_path=state_path)

    state = state_service.start_pipeline_run(
        selected_steps=["filtrar", "elegir"],
        state_path=state_path,
    )

    assert state["status"] == "running"
    assert state["selected_steps"] == ["filtrar", "elegir"]
    assert state["current_step"] == "filtrar"
    assert state["next_step"] == "filtrar"
    assert all(value is None for value in state["outputs"].values())


def test_mark_step_started_adds_step_when_missing(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.create_pipeline_state(selected_steps=[], state_path=state_path)

    state = state_service.mark_step_started("trends", state_path=state_path)

    assert state["status"] == "running"
    assert state["current_step"] == "descubrir"
    assert state["selected_steps"] == ["descubrir"]


def test_mark_step_completed_records_output_and_next_step(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.start_pipeline_run(
        selected_steps=["descubrir", "filtrar"],
        state_path=state_path,
    )

    state = state_service.mark_step_completed(
        "descubrir",
        output_path="output/participante-2/trends_v1_abcd1234.json",
        status="success",
        state_path=state_path,
    )

    assert state["status"] == "running"
    assert state["completed_steps"] == ["descubrir"]
    assert state["next_step"] == "filtrar"
    assert state["outputs"]["trends"] == "output/participante-2/trends_v1_abcd1234.json"


@pytest.mark.parametrize("status", ["idle", "running", "error"])
def test_mark_step_completed_rejects_non_completion_status(tmp_path, status):
    state_path = tmp_path / "pipeline_state.json"
    state_service.start_pipeline_run(selected_steps=["descubrir"], state_path=state_path)

    with pytest.raises(state_service.PipelineStateError):
        state_service.mark_step_completed("descubrir", status=status, state_path=state_path)


def test_mark_step_completed_with_draft_or_errors_keeps_draft(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.start_pipeline_run(selected_steps=["descubrir"], state_path=state_path)

    state = state_service.mark_step_completed(
        "descubrir",
        status="draft",
        errors=["fallback activo"],
        state_path=state_path,
    )

    assert state["status"] == "draft"
    assert state["completed_steps"] == ["descubrir"]
    assert state["next_step"] is None
    assert state["errors"] == ["fallback activo"]


def test_mark_step_failed_records_error_and_keeps_retry_step(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.start_pipeline_run(selected_steps=["descubrir", "filtrar"], state_path=state_path)

    state = state_service.mark_step_failed(
        "filtrar",
        error="persistencia fallida",
        state_path=state_path,
    )

    assert state["status"] == "error"
    assert state["current_step"] == "filtrar"
    assert state["next_step"] == "filtrar"
    assert state["errors"] == ["persistencia fallida"]


def test_reset_pipeline_state_deletes_and_creates_new_state(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    first = state_service.create_pipeline_state(selected_steps=["descubrir"], state_path=state_path)

    second = state_service.reset_pipeline_state(state_path=state_path)

    assert state_path.exists()
    assert second is not None
    assert second["status"] == "idle"
    assert second["selected_steps"] == []
    assert second["run_id"] != first["run_id"]


def test_delete_pipeline_state_removes_file_and_reports_result(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.create_pipeline_state(state_path=state_path)

    assert state_service.delete_pipeline_state(state_path=state_path) is True
    assert state_service.delete_pipeline_state(state_path=state_path) is False
    assert not state_path.exists()


def test_get_pipeline_state_can_fail_when_missing(tmp_path):
    state_path = tmp_path / "pipeline_state.json"

    with pytest.raises(state_service.PipelineStateError, match="No existe"):
        state_service.get_pipeline_state(state_path=state_path, create_if_missing=False)


def test_get_pipeline_state_rejects_invalid_json(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_path.write_text("{", encoding="utf-8")

    with pytest.raises(state_service.PipelineStateError, match="inválido"):
        state_service.get_pipeline_state(state_path=state_path)


def test_bootstrap_state_from_existing_outputs(tmp_path):
    state_path = tmp_path / "pipeline_state.json"

    state = state_service.bootstrap_state_from_outputs(
        trends_output="output/participante-2/trends_v1_11111111.json",
        duplicates_output="output/participante-3/duplicates_v1_22222222.json",
        topic_selector_output="output/participante-4/topic_selector_v1_33333333.json",
        status="draft",
        errors=["fallback activo"],
        state_path=state_path,
    )

    assert state["status"] == "draft"
    assert state["completed_steps"] == ["descubrir", "filtrar", "elegir"]
    assert state["next_step"] == "crear"
    assert state["outputs"] == {
        "trends": "output/participante-2/trends_v1_11111111.json",
        "duplicates": "output/participante-3/duplicates_v1_22222222.json",
        "topic_selector": "output/participante-4/topic_selector_v1_33333333.json",
        "ai": None,
        "instagram": None,
        "frontend": None,
    }
    assert state["errors"] == ["fallback activo"]


def test_mark_step_completed_success_clears_stale_errors(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.start_pipeline_run(selected_steps=["crear"], state_path=state_path)
    state_service.mark_step_failed("crear", error="fallo anterior", state_path=state_path)

    state = state_service.mark_step_completed("crear", status="success", state_path=state_path)

    assert state["status"] == "success"
    assert state["completed_steps"] == ["crear"]
    assert state["errors"] == []


def test_mark_step_started_invalidates_current_and_downstream_outputs(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.bootstrap_state_from_outputs(
        trends_output="output/participante-2/trends_v1_11111111.json",
        duplicates_output="output/participante-3/duplicates_v1_22222222.json",
        topic_selector_output="output/participante-4/topic_selector_v1_33333333.json",
        status="draft",
        state_path=state_path,
    )
    state = read_json(state_path)
    state["completed_steps"] = ["descubrir", "filtrar", "elegir", "crear", "publicar"]
    state["outputs"]["ai"] = "output/participante-5/ai_v1_44444444.json"
    state["outputs"]["instagram"] = "output/participante-6/instagram_v1_55555555.json"
    state["errors"] = ["error viejo"]
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    updated = state_service.mark_step_started("elegir", state_path=state_path)

    assert updated["status"] == "running"
    assert updated["current_step"] == "elegir"
    assert updated["completed_steps"] == ["descubrir", "filtrar"]
    assert updated["outputs"]["trends"] == "output/participante-2/trends_v1_11111111.json"
    assert updated["outputs"]["duplicates"] == "output/participante-3/duplicates_v1_22222222.json"
    assert updated["outputs"]["topic_selector"] is None
    assert updated["outputs"]["ai"] is None
    assert updated["outputs"]["instagram"] is None
    assert updated["outputs"]["frontend"] is None
    assert updated["errors"] == []


def test_mark_step_started_for_create_preserves_upstream_dependencies(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.bootstrap_state_from_outputs(
        trends_output="output/participante-2/trends_v1_11111111.json",
        duplicates_output="output/participante-3/duplicates_v1_22222222.json",
        topic_selector_output="output/participante-4/topic_selector_v1_33333333.json",
        status="draft",
        state_path=state_path,
    )
    state = read_json(state_path)
    state["completed_steps"] = ["descubrir", "filtrar", "elegir", "crear", "publicar"]
    state["outputs"]["ai"] = "output/participante-5/ai_v1_44444444.json"
    state["outputs"]["instagram"] = "output/participante-6/instagram_v1_55555555.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    updated = state_service.mark_step_started("crear", state_path=state_path)

    assert updated["completed_steps"] == ["descubrir", "filtrar", "elegir"]
    assert updated["outputs"]["topic_selector"] == "output/participante-4/topic_selector_v1_33333333.json"
    assert updated["outputs"]["ai"] is None
    assert updated["outputs"]["instagram"] is None


def test_prepare_topic_reuse_opens_idle_branch_with_only_create_selected(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    old_state = state_service.start_pipeline_run(
        selected_steps=["descubrir", "crear"],
        state_path=state_path,
    )

    prepared = state_service.prepare_topic_reuse(
        topic_selector_output="output/participante-4/topic_selector_v1_reuse.json",
        state_path=state_path,
    )

    assert prepared["run_id"] != old_state["run_id"]
    assert prepared["execution_mode"] == state_service.MANUAL_REUSE_MODE
    assert prepared["status"] == "idle"
    assert prepared["current_step"] is None
    assert prepared["selected_steps"] == ["crear"]
    assert prepared["completed_steps"] == ["elegir"]
    assert prepared["next_step"] == "crear"
    assert prepared["outputs"]["topic_selector"].endswith("topic_selector_v1_reuse.json")
    assert prepared["outputs"]["ai"] is None
    assert prepared["outputs"]["instagram"] is None
    assert prepared["outputs"]["frontend"] is None



def test_mark_pipeline_cancelled_preserves_current_step_and_outputs(tmp_path):
    state_path = tmp_path / "pipeline_state.json"
    state_service.start_pipeline_run(selected_steps=["crear", "publicar"], state_path=state_path)
    state_service.mark_step_started("crear", selected_steps=["crear", "publicar"], state_path=state_path)

    state = state_service.mark_pipeline_cancelled(
        reason="detenido por test",
        state_path=state_path,
    )

    assert state["status"] == "cancelled"
    assert state["current_step"] == "crear"
    assert state["next_step"] == "crear"
    assert state["errors"] == ["detenido por test"]
    assert state_service.is_pipeline_cancelled(run_id=state["run_id"], state_path=state_path) is True
    assert state_service.is_pipeline_cancelled(run_id="00000000-0000-0000-0000-000000000000", state_path=state_path) is False


def test_pipeline_cancel_service_closes_registered_resources_for_active_run():
    from python_backend.services.pipeline.pipeline_cancel_service import (
        cancel_active_run,
        current_run_id,
        pipeline_run_scope,
        registered_closer,
    )

    closed = []

    with pipeline_run_scope("run-123"):
        assert current_run_id() == "run-123"
        with registered_closer(lambda: closed.append("closed")):
            assert cancel_active_run("other-run") == 0
            assert closed == []
            assert cancel_active_run("run-123") == 1
            assert closed == ["closed"]

    assert current_run_id() is None
