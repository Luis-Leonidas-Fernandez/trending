import importlib
import json
from pathlib import Path
from uuid import uuid4

import pytest

from python_backend.services.duplicates import duplicates_service
from tools.validate_output import validate_output_file


def make_phase_2_payload(*, status="success", used_fallback=False, items=None, errors=None):
    return {
        "schema_version": "1.0",
        "run_id": str(uuid4()),
        "participant": "participante-2",
        "stage": "trends",
        "generated_at": "2026-07-27T12:00:00Z",
        "status": status,
        "data": {
            "country": "AR",
            "count": len(items or []),
            "used_fallback": used_fallback,
            "items": items or [],
        },
        "errors": errors or [],
    }


def write_phase_2_output(tmp_path: Path, payload: dict) -> Path:
    file_path = tmp_path / f"trends_v1_{payload['run_id'][:8]}.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    return file_path


def test_filter_new_topics_normalizes_case_accents_punctuation_and_spaces():
    topics = [
        {"title": "  Dólar   blue!!! ", "source": "google_trends", "score": 10},
        {"title": "Inteligencia Artificial", "source": "google_trends", "score": 9},
    ]
    existing = [{"normalized_title": "dolar blue"}]

    result = duplicates_service.filter_new_topics(topics, existing_topics=existing)

    assert result == [
        {
            "title": "Inteligencia Artificial",
            "normalized_title": "inteligencia artificial",
            "source": "google_trends",
            "score": 9.0,
            "used": 0,
            "category": "general",
            "date": None,
        }
    ]


def test_filter_new_topics_discards_duplicates_in_same_input_and_preserves_order():
    topics = [
        {"title": "Tema B", "score": 2},
        {"title": "Tema A", "score": 1},
        {"title": "tema-b", "score": 99},
    ]

    result = duplicates_service.filter_new_topics(topics, existing_topics=[])

    assert [item["title"] for item in result] == ["Tema B", "Tema A"]
    assert [item["normalized_title"] for item in result] == ["tema b", "tema a"]


def test_process_trends_output_persists_only_new_topics_with_mocked_repository(monkeypatch, tmp_path):
    created = []

    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "get_all_topics",
        lambda: [{"normalized_title": "dolar blue"}],
    )

    def fake_create_topic(topic):
        created.append(topic)
        return {**topic, "id": len(created)}

    monkeypatch.setattr(duplicates_service.topic_repository, "create_topic", fake_create_topic)

    payload = make_phase_2_payload(
        items=[
            {"title": "Dólar blue", "normalized_title": "dolar blue", "source": "google_trends", "score": 10},
            {"title": "Selección Argentina", "source": "google_trends", "score": 9},
            {"title": "seleccion argentina", "source": "google_trends", "score": 8},
            {"title": "   ", "source": "google_trends", "score": 7},
        ]
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.errors == []
    assert output.data["source"]["run_id"] == payload["run_id"]
    assert output.data["items"] == [
        {
            "id": 1,
            "title": "Selección Argentina",
            "normalized_title": "seleccion argentina",
            "source": "google_trends",
            "score": 9.0,
            "used": 0,
        }
    ]
    assert output.data["counts"] == {
        "input": 4,
        "saved": 1,
        "reused": 0,
        "duplicates": 2,
        "invalid": 1,
        "discarded": 3,
    }
    assert [item["reason"] for item in output.data["discarded"]] == [
        "duplicate_in_database",
        "duplicate_in_input",
        "invalid_title",
    ]
    assert output_path.name == f"duplicates_v1_{str(output.run_id)[:8]}.json"
    assert created == [
        {
            "title": "Selección Argentina",
            "normalized_title": "seleccion argentina",
            "source": "google_trends",
            "score": 9.0,
            "used": 0,
        }
    ]


def test_process_trends_output_draft_input_produces_draft_and_propagates_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(duplicates_service.topic_repository, "get_all_topics", lambda: [])
    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "create_topic",
        lambda topic: {**topic, "id": 1},
    )
    payload = make_phase_2_payload(
        status="draft",
        used_fallback=True,
        errors=["timeout de prueba"],
        items=[{"title": "economía argentina", "source": "fallback", "score": 10}],
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.errors == ["timeout de prueba"]
    assert output.data["source"]["used_fallback"] is True
    assert output.data["items"][0]["id"] == 1


def test_process_trends_output_without_new_topics_is_draft(monkeypatch, tmp_path):
    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "get_all_topics",
        lambda: [{"normalized_title": "economia argentina"}],
    )
    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "create_topic",
        lambda topic: pytest.fail("No debería persistir duplicados"),
    )
    payload = make_phase_2_payload(
        items=[{"title": "economía argentina", "source": "google_trends", "score": 10}]
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.data["counts"]["saved"] == 0
    assert output.data["discarded"][0]["reason"] == "duplicate_in_database"



def test_process_trends_output_reuses_existing_unused_topics_as_candidates(monkeypatch, tmp_path):
    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "get_all_topics",
        lambda: [
            {
                "id": 7,
                "title": "Economía Argentina",
                "normalized_title": "economia argentina",
                "source": "google_trends",
                "score": 42,
                "used": 0,
            }
        ],
    )
    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "create_topic",
        lambda topic: pytest.fail("No debería persistir temas existentes reutilizables"),
    )
    payload = make_phase_2_payload(
        items=[{"title": "economía argentina", "source": "google_trends", "score": 10}]
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.data["items"] == [
        {
            "id": 7,
            "title": "Economía Argentina",
            "normalized_title": "economia argentina",
            "source": "google_trends",
            "score": 42.0,
            "used": 0,
            "reused_existing": True,
        }
    ]
    assert output.data["counts"]["saved"] == 0
    assert output.data["counts"]["reused"] == 1
    assert output.data["counts"]["duplicates"] == 1
    assert output.data["discarded"] == []


def test_process_trends_output_discards_existing_used_topics(monkeypatch, tmp_path):
    monkeypatch.setattr(
        duplicates_service.topic_repository,
        "get_all_topics",
        lambda: [
            {
                "id": 7,
                "title": "Economía Argentina",
                "normalized_title": "economia argentina",
                "source": "google_trends",
                "score": 42,
                "used": 1,
            }
        ],
    )
    monkeypatch.setattr(duplicates_service.topic_repository, "create_topic", lambda topic: pytest.fail("No debería persistir duplicados"))
    payload = make_phase_2_payload(
        items=[{"title": "economía argentina", "source": "google_trends", "score": 10}]
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.data["items"] == []
    assert output.data["discarded"][0]["reason"] == "already_used_in_database"

def test_process_trends_output_persistence_error_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(duplicates_service.topic_repository, "get_all_topics", lambda: [])

    def fail_create_topic(topic):
        raise RuntimeError("sqlite bloqueado")

    monkeypatch.setattr(duplicates_service.topic_repository, "create_topic", fail_create_topic)
    payload = make_phase_2_payload(
        items=[{"title": "Tema nuevo", "source": "google_trends", "score": 10}]
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert output.data["items"] == []
    assert output.errors == ["sqlite bloqueado"]


def test_process_trends_output_rejects_non_phase_2_input(tmp_path):
    payload = make_phase_2_payload()
    payload["participant"] = "participante-3"
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert "participante-2" in output.errors[0]


def test_process_trends_output_integration_with_temporary_sqlite(monkeypatch, tmp_path):
    db_path = tmp_path / "trending.sqlite"
    monkeypatch.setenv("PYTHON_DB_FILE", str(db_path))

    import python_backend.database.connection as connection
    import python_backend.repositories.topic_repository as topic_repository

    reloaded_connection = importlib.reload(connection)
    reloaded_connection.initialize_database()
    reloaded_repository = importlib.reload(topic_repository)
    monkeypatch.setattr(duplicates_service, "topic_repository", reloaded_repository)

    payload = make_phase_2_payload(
        items=[
            {"title": "Tema SQLite", "source": "google_trends", "score": 10},
            {"title": "tema sqlite", "source": "google_trends", "score": 9},
            {"title": "Otro tema", "source": "google_trends", "score": 8},
        ]
    )
    input_path = write_phase_2_output(tmp_path, payload)

    output_path = duplicates_service.process_trends_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    persisted = reloaded_repository.get_all_topics()
    assert output.status == "success"
    assert [item["normalized_title"] for item in output.data["items"]] == [
        "tema sqlite",
        "otro tema",
    ]
    assert {topic["normalized_title"] for topic in persisted} == {"tema sqlite", "otro tema"}
    assert output.data["counts"]["duplicates"] == 1
