import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

fd, database_path = tempfile.mkstemp(suffix=".sqlite")
os.close(fd)
os.environ["PYTHON_DB_FILE"] = database_path

from fastapi.testclient import TestClient  # noqa: E402
from python_backend.main import app  # noqa: E402

client = TestClient(app)


def test_health_endpoint_returns_success():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_create_and_list_topic():
    payload = {
        "title": "Tema de prueba",
        "normalized_title": "tema de prueba",
        "source": "test",
        "score": 10,
        "used": 0,
    }

    create_response = client.post("/api/topics", json=payload)
    list_response = client.get("/api/topics")

    assert create_response.status_code == 201
    assert create_response.json()["success"] is True
    assert list_response.status_code == 200
    assert isinstance(list_response.json()["data"], list)


def test_invalid_topic_returns_clear_error():
    response = client.post("/api/topics", json={"title": ""})

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["message"] == "JSON inválido"


def test_create_post_and_log_with_relationships():
    topic_response = client.post(
        "/api/topics",
        json={
            "title": "Tema relación",
            "normalized_title": "tema relación",
            "source": "test",
            "score": 5,
            "used": 0,
        },
    )
    topic_id = topic_response.json()["data"]["id"]

    post_response = client.post(
        "/api/posts",
        json={
            "topic_id": topic_id,
            "caption": "Post de prueba",
            "status": "draft",
        },
    )
    post_data = post_response.json()["data"]

    log_response = client.post(
        "/api/logs",
        json={
            "post_id": post_data["id"],
            "platform": "instagram",
            "status": "pending",
        },
    )

    assert post_response.status_code == 201
    assert post_data["topic_title"] == "Tema relación"
    assert log_response.status_code == 201
    assert log_response.json()["data"]["post_id"] == post_data["id"]


def test_pipeline_state_endpoint_returns_current_state(monkeypatch):
    from python_backend.routers import pipeline_router

    fake_state = {
        "state_version": "1.0",
        "run_id": "00000000-0000-4000-8000-000000000000",
        "status": "idle",
        "current_step": None,
        "selected_steps": [],
        "completed_steps": [],
        "next_step": "descubrir",
        "outputs": {},
        "errors": [],
    }
    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: fake_state)

    response = client.get("/api/pipeline/state")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": fake_state}



def test_pipeline_metrics_latest_uses_state_output(monkeypatch, tmp_path):
    from python_backend.routers import pipeline_router

    metrics_path = tmp_path / "metrics_v1_aaaaaaaa.json"
    metrics_payload = {
        "schema_version": "1.0",
        "participant": "participante-7",
        "stage": "metrics",
        "data": {"score": 100},
    }
    fake_state = {"outputs": {"frontend": str(metrics_path)}}

    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: fake_state)
    monkeypatch.setattr(pipeline_router.Path, "exists", lambda self: True)
    monkeypatch.setattr(pipeline_router, "_read_output", lambda path: metrics_payload)
    monkeypatch.setattr(pipeline_router, "_relative_path", lambda path: "output/participante-7/metrics_v1_aaaaaaaa.json")

    response = client.get("/api/pipeline/metrics/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["data"]["score"] == 100
    assert body["output_path"] == "output/participante-7/metrics_v1_aaaaaaaa.json"

def test_pipeline_run_endpoint_executes_selected_steps(monkeypatch):
    from python_backend.routers import pipeline_router

    initial_state = {
        "status": "running",
        "selected_steps": ["descubrir", "filtrar"],
        "completed_steps": [],
        "current_step": "descubrir",
        "next_step": "descubrir",
    }
    final_states = {
        "descubrir": {**initial_state, "completed_steps": ["descubrir"], "current_step": None},
        "filtrar": {
            **initial_state,
            "status": "success",
            "completed_steps": ["descubrir", "filtrar"],
            "current_step": None,
            "next_step": None,
        },
    }

    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "start_pipeline_run",
        lambda selected_steps: (_ for _ in ()).throw(AssertionError("No debe reiniciar el estado")),
    )
    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda step, selected_steps=None: {
            "step": step,
            "output_path": f"output/{step}.json",
            "output": {"status": "success", "errors": []},
            "state": final_states[step],
        },
    )

    response = client.post("/api/pipeline/run", json={"steps": ["descubrir", "filtrar"]})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert [item["step"] for item in body["data"]["executed"]] == ["descubrir", "filtrar"]
    assert body["data"]["state"]["status"] == "success"


def test_discover_starts_a_new_global_run_after_previous_activity(monkeypatch, tmp_path):
    from python_backend.routers import pipeline_router

    output_path = tmp_path / "trends_v1_new.json"
    output_path.write_text(
        json.dumps({"status": "success", "data": {"items": []}, "errors": []}),
        encoding="utf-8",
    )
    previous = {
        "run_id": "00000000-0000-4000-8000-000000000001",
        "status": "success",
        "selected_steps": ["descubrir"],
        "completed_steps": ["descubrir"],
        "outputs": {"trends": "output/old.json"},
    }
    started = {
        "run_id": "00000000-0000-4000-8000-000000000002",
        "status": "running",
        "selected_steps": ["descubrir", "crear"],
        "completed_steps": [],
        "outputs": {},
    }
    completed = {
        **started,
        "status": "running",
        "completed_steps": ["descubrir"],
    }
    start_calls = []
    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: previous)
    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "start_pipeline_run",
        lambda selected_steps: start_calls.append(selected_steps) or started,
    )
    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "mark_step_started",
        lambda *args, **kwargs: started,
    )
    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "mark_step_completed",
        lambda *args, **kwargs: completed,
    )
    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "is_pipeline_cancelled",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(pipeline_router, "save_trends_output", lambda: output_path)

    result = pipeline_router._run_step(  # noqa: SLF001 - verifica frontera de nueva corrida.
        "descubrir",
        selected_steps=["descubrir", "crear"],
    )

    assert start_calls == [["descubrir", "crear"]]
    assert result["state"]["run_id"] == started["run_id"]


def test_pipeline_run_rejects_upstream_steps_during_manual_reuse(monkeypatch):
    from python_backend.routers import pipeline_router

    prepared_state = {
        "status": "idle",
        "execution_mode": "manual_history_reuse",
        "selected_steps": ["crear"],
        "completed_steps": ["elegir"],
        "next_step": "crear",
        "outputs": {"topic_selector": "output/reuse.json"},
    }
    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: prepared_state)
    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No debe ejecutar pasos upstream")),
    )

    response = client.post(
        "/api/pipeline/run",
        json={"steps": ["descubrir", "filtrar", "elegir", "crear"]},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["data"]["blocked_steps"] == ["descubrir", "filtrar", "elegir"]
    assert "Reiniciá el estado" in body["message"]


def test_direct_upstream_endpoint_rejects_manual_reuse(monkeypatch):
    from python_backend.routers import pipeline_router

    prepared_state = {
        "status": "idle",
        "execution_mode": "manual_history_reuse",
        "selected_steps": ["crear"],
        "completed_steps": ["elegir"],
        "next_step": "crear",
        "outputs": {"topic_selector": "output/reuse.json"},
    }
    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: prepared_state)
    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("No debe ejecutar Elegir")),
    )

    response = client.post("/api/pipeline/select")

    assert response.status_code == 409
    assert response.json()["data"]["blocked_steps"] == ["elegir"]


def test_pipeline_run_allows_downstream_steps_during_manual_reuse(monkeypatch):
    from python_backend.routers import pipeline_router

    prepared_state = {
        "status": "idle",
        "execution_mode": "manual_history_reuse",
        "selected_steps": ["crear"],
        "completed_steps": ["elegir"],
        "next_step": "crear",
        "outputs": {"topic_selector": "output/reuse.json"},
    }
    final_state = {
        **prepared_state,
        "status": "success",
        "selected_steps": ["crear"],
        "completed_steps": ["elegir", "crear"],
        "next_step": None,
    }
    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: prepared_state)
    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda step, selected_steps=None: {
            "step": step,
            "output_path": "output/crear.json",
            "output": {"status": "success", "errors": []},
            "state": final_state,
        },
    )

    response = client.post("/api/pipeline/run", json={"steps": ["crear"]})

    assert response.status_code == 200
    assert response.json()["data"]["executed"][0]["step"] == "crear"


def test_pipeline_run_endpoint_accepts_measure_step(monkeypatch):
    from python_backend.routers import pipeline_router

    final_state = {
        "status": "success",
        "selected_steps": ["medir"],
        "completed_steps": ["medir"],
        "current_step": None,
        "next_step": None,
    }

    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda step, selected_steps=None: {
            "step": step,
            "output_path": "output/participante-7/metrics_v1_aaaaaaaa.json",
            "output": {"status": "success", "errors": []},
            "state": final_state,
        },
    )

    response = client.post("/api/pipeline/run", json={"steps": ["medir"]})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["executed"][0]["step"] == "medir"
    assert body["data"]["state"]["status"] == "success"




def test_pipeline_metrics_latest_prefers_active_draft_over_historical_success(monkeypatch):
    from python_backend.routers import pipeline_router

    draft_path = Path("output/participante-7/metrics_v1_draft.json")
    success_path = Path("output/participante-7/metrics_v1_success.json")

    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: {"outputs": {"frontend": str(draft_path)}})
    monkeypatch.setattr(pipeline_router.Path, "exists", lambda self: True)

    def fake_read_output(path):
        if str(path).endswith("metrics_v1_draft.json"):
            return {"status": "draft", "data": {"score": 50}}
        return {"status": "success", "data": {"score": 100}}

    monkeypatch.setattr(pipeline_router, "_read_output", fake_read_output)
    monkeypatch.setattr(pipeline_router, "_latest_output", lambda participant, stage, preferred_status=None: success_path if preferred_status == "success" else draft_path)
    monkeypatch.setattr(pipeline_router, "_relative_path", lambda path: str(path))

    response = client.get("/api/pipeline/metrics/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "draft"
    assert body["data"]["data"]["score"] == 50
    assert body["output_path"].endswith(str(draft_path))


def test_posts_audit_latest_uses_active_draft_instead_of_historical_published(monkeypatch, tmp_path):
    from python_backend.routers import posts_router

    instagram_path = tmp_path / "instagram_v1_active.json"
    instagram_path.write_text(
        json.dumps({"status": "success", "data": {"post": {"id": 11}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        posts_router.pipeline_state_service,
        "get_pipeline_state",
        lambda: {"outputs": {"instagram": str(instagram_path)}},
    )
    monkeypatch.setattr(
        posts_router.instagram_service,
        "build_audit_view",
        lambda post_id=None: {
            "post": {"id": post_id, "topic_id": 46, "status": "draft"},
            "publication_log": None,
            "logs": [],
            "audit": {"ready": False},
        },
    )

    response = client.get("/api/posts/audit/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["post"]["id"] == 11
    assert body["data"]["post"]["topic_id"] == 46
    assert body["data"]["post"]["status"] == "draft"


def test_posts_audit_latest_only_uses_global_fallback_without_active_evidence(monkeypatch):
    from python_backend.routers import posts_router

    requested_post_ids = []
    monkeypatch.setattr(
        posts_router.pipeline_state_service,
        "get_pipeline_state",
        lambda: {"outputs": {}},
    )
    monkeypatch.setattr(
        posts_router.instagram_service,
        "build_audit_view",
        lambda post_id=None: requested_post_ids.append(post_id)
        or {"post": {"id": 9, "status": "published_simulated"}},
    )

    response = client.get("/api/posts/audit/latest")

    assert response.status_code == 200
    assert requested_post_ids == [None]
    assert response.json()["data"]["post"]["id"] == 9

def test_pipeline_publish_simulated_endpoint_updates_state(monkeypatch):
    from python_backend.routers import pipeline_router

    simulated_path = Path("output/participante-6/instagram_v1_simulado.json")
    completed_state = {
        "status": "success",
        "outputs": {"instagram": str(simulated_path)},
    }

    def fake_read_output(path):
        if str(path).endswith("draft.json"):
            return {"data": {"post": {"id": 42}}, "status": "success", "errors": []}
        return {"data": {"post": {"id": 42, "status": "published_simulated"}}, "status": "success", "errors": []}

    monkeypatch.setattr(pipeline_router, "_required_output_path", lambda *args: Path("output/participante-6/instagram_v1_draft.json"))
    monkeypatch.setattr(pipeline_router, "_read_output", fake_read_output)
    monkeypatch.setattr(pipeline_router, "process_simulated_publication", lambda post_id: simulated_path)
    monkeypatch.setattr(pipeline_router.pipeline_state, "mark_step_completed", lambda *args, **kwargs: completed_state)
    monkeypatch.setattr(pipeline_router, "_relative_path", lambda path: str(path))

    response = client.post("/api/pipeline/publish-simulated")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["step"] == "publicar"
    assert body["data"]["state"] == completed_state

def test_pipeline_run_endpoint_accepts_create_step(monkeypatch):
    from python_backend.routers import pipeline_router

    final_state = {
        "status": "draft",
        "selected_steps": ["crear"],
        "completed_steps": ["crear"],
        "current_step": None,
        "next_step": None,
    }

    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda step, selected_steps=None: {
            "step": step,
            "output_path": "output/participante-5/ai_v1_aaaaaaaa.json",
            "output": {"status": "draft", "errors": ["Spartan Gateway requiere auth"]},
            "state": final_state,
        },
    )

    response = client.post("/api/pipeline/run", json={"steps": ["crear"]})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["executed"][0]["step"] == "crear"
    assert body["data"]["state"]["status"] == "draft"


def test_ai_provider_status_endpoint(monkeypatch):
    from python_backend.routers import ai_router

    monkeypatch.setattr(
        ai_router.spartan_auth_service,
        "list_provider_statuses",
        lambda: [{"provider": "codex", "connected": False}],
    )

    response = client.get("/api/ai/providers/status")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": [{"provider": "codex", "connected": False}]}


def test_ai_provider_connect_endpoint(monkeypatch):
    from python_backend.routers import ai_router

    monkeypatch.setattr(
        ai_router.spartan_auth_service,
        "start_provider_connection",
        lambda provider: {"provider": provider, "authorization_url": "https://auth.example", "state": "abc"},
    )

    response = client.post("/api/ai/providers/codex/connect")

    assert response.status_code == 200
    assert response.json()["data"]["authorization_url"] == "https://auth.example"


def test_pipeline_run_endpoint_accepts_publish_step(monkeypatch):
    from python_backend.routers import pipeline_router

    final_state = {
        "status": "success",
        "selected_steps": ["publicar"],
        "completed_steps": ["publicar"],
        "current_step": None,
        "next_step": None,
    }

    monkeypatch.setattr(
        pipeline_router,
        "_run_step",
        lambda step, selected_steps=None: {
            "step": step,
            "output_path": "output/participante-6/instagram_v1_aaaaaaaa.json",
            "output": {"status": "success", "errors": []},
            "state": final_state,
        },
    )

    response = client.post("/api/pipeline/run", json={"steps": ["publicar"]})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["executed"][0]["step"] == "publicar"
    assert body["data"]["state"]["status"] == "success"


def test_pipeline_history_endpoint_keeps_compatibility_with_persistent_runs(monkeypatch):
    from python_backend.routers import pipeline_router

    history = {
        "items": [],
        "meta": {
            "persistent_history": True,
            "available_runs": 0,
        },
    }
    monkeypatch.setattr(
        pipeline_router,
        "get_current_run_history",
        lambda **filters: history,
    )

    response = client.get("/api/pipeline/history")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": history}


def test_pipeline_runs_endpoint_forwards_server_side_filters(monkeypatch):
    from python_backend.routers import pipeline_router

    received = {}
    monkeypatch.setattr(pipeline_router, "sync_current_pipeline_state", lambda: None)

    def fake_list(**filters):
        received.update(filters)
        return {
            "items": [{"id": "run-filtered", "topic": {"id": 40, "title": "terremoto"}}],
            "meta": {"persistent_history": True, "available_runs": 1},
        }

    monkeypatch.setattr(pipeline_router, "list_pipeline_runs", fake_list)

    response = client.get(
        "/api/pipeline/runs",
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "topic_id": 40,
            "topic": "terremoto",
            "limit": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["id"] == "run-filtered"
    assert received == {
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "topic_id": 40,
        "topic": "terremoto",
        "limit": 20,
    }


def test_pipeline_run_detail_endpoint_returns_correlated_run(monkeypatch):
    from python_backend.routers import pipeline_router

    run_id = "00000000-0000-4000-8000-000000000040"
    monkeypatch.setattr(pipeline_router, "sync_current_pipeline_state", lambda: None)
    monkeypatch.setattr(
        pipeline_router,
        "get_pipeline_run",
        lambda requested: {
            "id": requested,
            "topic": {"id": 40, "title": "terremoto en Japón"},
            "post": {"id": 11, "topic_id": 40},
        }
        if requested == run_id
        else None,
    )

    response = client.get(f"/api/pipeline/runs/{run_id}")
    missing = client.get("/api/pipeline/runs/missing")

    assert response.status_code == 200
    assert response.json()["data"]["post"]["id"] == 11
    assert missing.status_code == 404


def test_reuse_topic_rejects_mutation_while_pipeline_is_running(monkeypatch):
    from python_backend.routers import pipeline_router

    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "get_pipeline_state",
        lambda: {"status": "running"},
    )

    response = client.post("/api/pipeline/topics/8/reuse")

    assert response.status_code == 409
    assert "ejecutándose" in response.json()["message"]


def test_reuse_topic_prepares_create_without_executing_pipeline(monkeypatch, tmp_path):
    from python_backend.routers import pipeline_router

    topic = {
        "id": 8,
        "title": "Tema reutilizable",
        "normalized_title": "tema reutilizable",
        "used": 1,
    }
    selector_output = tmp_path / "topic_selector_v1_reuse.json"
    selector_output.write_text("{}", encoding="utf-8")
    prepared_state = {
        "status": "idle",
        "selected_steps": ["crear"],
        "completed_steps": ["elegir"],
        "next_step": "crear",
        "outputs": {"topic_selector": str(selector_output), "ai": None},
    }

    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "get_pipeline_state",
        lambda: {"status": "success", "selected_steps": [], "outputs": {}},
    )
    monkeypatch.setattr(
        pipeline_router.topic_repository,
        "get_topic_by_id",
        lambda topic_id: topic if topic_id == 8 else None,
    )
    monkeypatch.setattr(
        pipeline_router,
        "create_reuse_topic_output",
        lambda selected_topic: selector_output,
    )
    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "prepare_topic_reuse",
        lambda topic_selector_output: prepared_state,
    )
    monkeypatch.setattr(pipeline_router, "_relative_path", lambda path: str(path))

    response = client.post("/api/pipeline/topics/8/reuse")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["topic"]["used"] == 1
    assert body["data"]["state"]["status"] == "idle"
    assert body["data"]["state"]["selected_steps"] == ["crear"]
    assert body["data"]["already_prepared"] is False


def test_get_post_by_id_includes_topic_title_without_detached_error():
    topic_response = client.post(
        "/api/topics",
        json={
            "title": "Tema detached",
            "normalized_title": "tema detached",
            "source": "test",
            "score": 1,
            "used": 0,
        },
    )
    topic_id = topic_response.json()["data"]["id"]
    post_response = client.post(
        "/api/posts",
        json={"topic_id": topic_id, "caption": "Caption detached", "status": "draft"},
    )
    post_id = post_response.json()["data"]["id"]

    response = client.get(f"/api/posts/{post_id}")

    assert response.status_code == 200
    assert response.json()["data"]["topic_title"] == "Tema detached"



def test_pipeline_cancel_endpoint_marks_state_cancelled(monkeypatch):
    from python_backend.routers import pipeline_router

    cancelled_state = {
        "status": "cancelled",
        "selected_steps": ["crear", "publicar"],
        "completed_steps": [],
        "current_step": "crear",
        "next_step": "crear",
        "errors": ["detenido desde test"],
    }

    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "mark_pipeline_cancelled",
        lambda reason: {**cancelled_state, "errors": [reason]},
    )

    response = client.post("/api/pipeline/cancel", json={"reason": "detenido desde test"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "cancelled"
    assert body["data"]["errors"] == ["detenido desde test"]


def test_pipeline_run_endpoint_stops_when_cancelled_between_steps(monkeypatch):
    from python_backend.routers import pipeline_router

    current_state = {
        "run_id": "11111111-1111-1111-1111-111111111111",
        "status": "cancelled",
        "selected_steps": ["descubrir", "filtrar"],
        "completed_steps": ["descubrir"],
        "current_step": "filtrar",
        "next_step": "filtrar",
    }
    calls = []

    monkeypatch.setattr(pipeline_router.pipeline_state, "get_pipeline_state", lambda: current_state)
    monkeypatch.setattr(
        pipeline_router.pipeline_state,
        "is_pipeline_cancelled",
        lambda run_id=None: len(calls) >= 1,
    )

    def fake_run_step(step, selected_steps=None):
        calls.append(step)
        return {
            "step": step,
            "output_path": f"output/{step}.json",
            "output": {"status": "success", "errors": []},
            "state": current_state,
        }

    monkeypatch.setattr(pipeline_router, "_run_step", fake_run_step)

    response = client.post("/api/pipeline/run", json={"steps": ["descubrir", "filtrar"]})

    assert response.status_code == 499
    body = response.json()
    assert body["success"] is False
    assert body["data"]["state"] == current_state
    assert calls == ["descubrir"]
