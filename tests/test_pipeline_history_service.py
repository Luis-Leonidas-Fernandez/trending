import json

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from python_backend.models import Base
from python_backend.services.pipeline import pipeline_history_service
from python_backend.services.pipeline import pipeline_state_service


@pytest.fixture
def isolated_history_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'history.sqlite'}", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(pipeline_history_service, "get_session", local_session)
    return engine


def write_output(path, data, *, status="success"):
    path.write_text(
        json.dumps({"status": status, "data": data, "errors": []}),
        encoding="utf-8",
    )
    return str(path)


def state_for(
    run_id,
    *,
    created_at,
    updated_at,
    selector_output,
    instagram_output=None,
    metrics_output=None,
    status="success",
):
    return {
        "run_id": run_id,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "selected_steps": ["elegir", "crear", "publicar", "medir"],
        "completed_steps": ["elegir", "crear", "publicar", "medir"],
        "current_step": None,
        "next_step": None,
        "outputs": {
            "trends": None,
            "duplicates": None,
            "topic_selector": selector_output,
            "ai": None,
            "instagram": instagram_output,
            "frontend": metrics_output,
        },
        "errors": [],
    }


def test_pipeline_runs_migration_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.sqlite'}", future=True)

    Base.metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    assert "pipeline_runs" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("pipeline_runs")}
    assert {
        "run_id",
        "started_at",
        "updated_at",
        "finished_at",
        "selected_steps_json",
        "outputs_json",
        "topic_id",
        "post_id",
        "quality_score",
    } <= columns


def test_history_persists_multiple_correlated_runs_and_upserts(
    isolated_history_db,
    tmp_path,
):
    selector_one = write_output(
        tmp_path / "selector-one.json",
        {"selected_topic": {"id": 40, "title": "terremoto en Japón"}},
    )
    instagram_one = write_output(
        tmp_path / "instagram-one.json",
        {
            "post": {
                "id": 11,
                "topic_id": 40,
                "topic_title": "terremoto en Japón",
                "image_url": "output/earthquake.png",
            },
            "publication_log": {"id": 7, "status": "published_simulated"},
            "topic": {"id": 40, "title": "terremoto en Japón"},
        },
    )
    metrics_one = write_output(
        tmp_path / "metrics-one.json",
        {
            "post": {"id": 11, "topic_id": 40, "topic_title": "terremoto en Japón"},
            "topic": {"id": 40, "title": "terremoto en Japón"},
            "publication_log": {"id": 7, "status": "published_simulated"},
            "score": 100,
            "checks": {"has_image": True},
        },
    )
    selector_two = write_output(
        tmp_path / "selector-two.json",
        {"selected_topic": {"id": 43, "title": "desalojo"}},
    )

    first = state_for(
        "00000000-0000-4000-8000-000000000040",
        created_at="2026-07-27T10:00:00+00:00",
        updated_at="2026-07-27T10:05:00+00:00",
        selector_output=selector_one,
        instagram_output=instagram_one,
        metrics_output=metrics_one,
    )
    second = state_for(
        "00000000-0000-4000-8000-000000000043",
        created_at="2026-07-28T10:00:00+00:00",
        updated_at="2026-07-28T10:01:00+00:00",
        selector_output=selector_two,
        status="draft",
    )

    pipeline_history_service.upsert_pipeline_run(first)
    pipeline_history_service.upsert_pipeline_run(second)
    second["updated_at"] = "2026-07-28T10:02:00+00:00"
    second["errors"] = ["fallback activo"]
    pipeline_history_service.upsert_pipeline_run(second)

    history = pipeline_history_service.list_pipeline_runs()
    assert history["meta"]["persistent_history"] is True
    assert history["meta"]["available_runs"] == 2
    assert [item["topic"]["id"] for item in history["items"]] == [43, 40]

    first_detail = pipeline_history_service.get_pipeline_run(first["run_id"])
    second_detail = pipeline_history_service.get_pipeline_run(second["run_id"])
    assert first_detail["post"]["id"] == 11
    assert first_detail["quality"]["score"] == 100
    assert first_detail["publication_log"]["id"] == 7
    assert second_detail["post"] is None
    assert second_detail["errors"] == ["fallback activo"]


def test_history_filters_by_dates_topic_id_and_topic_text(isolated_history_db, tmp_path):
    for topic_id, title, day in (
        (40, "terremoto en Japón", "2026-07-26"),
        (41, "fútbol argentino", "2026-07-27"),
        (42, "terremoto en Chile", "2026-07-28"),
    ):
        selector = write_output(
            tmp_path / f"selector-{topic_id}.json",
            {"selected_topic": {"id": topic_id, "title": title}},
        )
        pipeline_history_service.upsert_pipeline_run(
            state_for(
                f"00000000-0000-4000-8000-{topic_id:012d}",
                created_at=f"{day}T10:00:00+00:00",
                updated_at=f"{day}T10:01:00+00:00",
                selector_output=selector,
            )
        )

    by_date = pipeline_history_service.list_pipeline_runs(
        date_from="2026-07-27",
        date_to="2026-07-27",
    )
    by_id = pipeline_history_service.list_pipeline_runs(topic_id=40)
    by_text = pipeline_history_service.list_pipeline_runs(topic="TERREMOTO")

    assert [item["topic"]["id"] for item in by_date["items"]] == [41]
    assert [item["topic"]["id"] for item in by_id["items"]] == [40]
    assert [item["topic"]["id"] for item in by_text["items"]] == [42, 40]


def test_reset_creates_new_state_without_deleting_persisted_run(
    isolated_history_db,
    monkeypatch,
    tmp_path,
):
    state_path = tmp_path / "pipeline_state.json"
    monkeypatch.setattr(pipeline_state_service, "DEFAULT_STATE_PATH", state_path)

    first = pipeline_state_service.create_pipeline_state(
        selected_steps=["descubrir"],
        state_path=state_path,
    )
    pipeline_state_service.mark_step_started("descubrir", state_path=state_path)
    pipeline_state_service.mark_step_completed("descubrir", state_path=state_path)
    reset = pipeline_state_service.reset_pipeline_state(state_path=state_path)

    history = pipeline_history_service.list_pipeline_runs()
    assert reset["run_id"] != first["run_id"]
    assert history["meta"]["available_runs"] == 1
    assert history["items"][0]["id"] == first["run_id"]


def test_invalid_history_date_is_rejected(isolated_history_db):
    with pytest.raises(ValueError, match="Fecha inválida"):
        pipeline_history_service.list_pipeline_runs(date_from="ayer")
