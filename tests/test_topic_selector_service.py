import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from python_backend.services.topic_selector import topic_selector_service
from tools.validate_output import validate_output_file


def make_phase_3_payload(*, status="success", used_fallback=False, items=None, errors=None):
    return {
        "schema_version": "1.0",
        "run_id": str(uuid4()),
        "participant": "participante-3",
        "stage": "duplicates",
        "generated_at": "2026-07-27T12:00:00Z",
        "status": status,
        "data": {
            "items": items or [],
            "counts": {
                "input": len(items or []),
                "saved": len(items or []),
                "duplicates": 0,
                "invalid": 0,
                "discarded": 0,
            },
            "discarded": [],
            "source": {
                "participant": "participante-2",
                "stage": "trends",
                "run_id": str(uuid4()),
                "status": "draft" if used_fallback else "success",
                "used_fallback": used_fallback,
            },
        },
        "errors": errors or [],
    }


def write_phase_3_output(tmp_path: Path, payload: dict) -> Path:
    file_path = tmp_path / f"duplicates_v1_{payload['run_id'][:8]}.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    return file_path


def test_select_topic_returns_first_valid_unused_and_preserves_input_order():
    topics = [
        {"id": 1, "title": "Tema B", "normalized_title": "tema b", "score": 1, "used": 1},
        {"id": 2, "title": "Tema A", "normalized_title": "tema a", "score": 1, "used": 0},
        {"id": 3, "title": "Tema C", "normalized_title": "tema c", "score": 99, "used": 0},
    ]

    result = topic_selector_service.select_topic(topics)

    assert result == topics[1]
    assert result["title"] == "Tema A"


def test_select_topic_does_not_prioritize_by_score():
    topics = [
        {"id": 1, "title": "Score bajo", "normalized_title": "score bajo", "score": 1, "used": False},
        {"id": 2, "title": "Score alto", "normalized_title": "score alto", "score": 999, "used": 0},
    ]

    result = topic_selector_service.select_topic(topics)

    assert result["title"] == "Score bajo"


def test_select_topic_ignores_invalid_structures_invalid_ids_empty_titles_and_used_topics():
    topics = [
        "no dict",
        {"id": True, "title": "Bool id", "normalized_title": "bool id", "used": 0},
        {"id": 0, "title": "Id cero", "normalized_title": "id cero", "used": 0},
        {"id": 1, "title": "   ", "normalized_title": "titulo", "used": 0},
        {"id": 2, "title": "Usado", "normalized_title": "usado", "used": 1},
        {"id": 3, "title": "Válido", "normalized_title": "valido", "used": False},
    ]

    result = topic_selector_service.select_topic(topics)

    assert result["id"] == 3
    assert result["title"] == "Válido"


def test_select_topic_does_not_mutate_received_items():
    topics = [
        {"id": 1, "title": "Tema", "normalized_title": "tema", "used": 0, "nested": {"a": 1}}
    ]
    original = deepcopy(topics)

    result = topic_selector_service.select_topic(topics)
    result["nested"]["a"] = 99

    assert topics == original


def test_process_duplicates_output_success_matches_schema_filename_and_counts(tmp_path):
    payload = make_phase_3_payload(
        items=[
            {"id": 1, "title": "Usado", "normalized_title": "usado", "score": 10, "used": 1},
            {"id": 2, "title": "Primero válido", "normalized_title": "primero valido", "score": 1, "used": 0},
            {"id": 3, "title": "Score mayor", "normalized_title": "score mayor", "score": 100, "used": 0},
        ]
    )
    input_path = write_phase_3_output(tmp_path, payload)

    output_path = topic_selector_service.process_duplicates_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.errors == []
    assert output.data["selected_topic"]["id"] == 2
    assert output.data["strategy"] == "first_valid_unused"
    assert output.data["counts"] == {"input": 3, "eligible": 2, "discarded": 1}
    assert output.data["discarded"] == [
        {
            "index": 0,
            "title": "Usado",
            "normalized_title": "usado",
            "reason": "already_used",
        }
    ]
    assert output.data["source"]["run_id"] == payload["run_id"]
    assert output_path.name == f"topic_selector_v1_{str(output.run_id)[:8]}.json"


def test_process_duplicates_output_draft_input_produces_draft_and_propagates_errors(tmp_path):
    payload = make_phase_3_payload(
        status="draft",
        used_fallback=True,
        errors=["timeout de prueba"],
        items=[{"id": 1, "title": "Fallback", "normalized_title": "fallback", "score": 10, "used": 0}],
    )
    input_path = write_phase_3_output(tmp_path, payload)

    output_path = topic_selector_service.process_duplicates_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.errors == ["timeout de prueba"]
    assert output.data["source"]["used_fallback"] is True
    assert output.data["selected_topic"]["id"] == 1


def test_process_duplicates_output_without_eligible_topics_is_draft(tmp_path):
    payload = make_phase_3_payload(
        items=[
            {"id": 1, "title": "Usado", "normalized_title": "usado", "used": 1},
            {"id": 0, "title": "Inválido", "normalized_title": "invalido", "used": 0},
        ]
    )
    input_path = write_phase_3_output(tmp_path, payload)

    output_path = topic_selector_service.process_duplicates_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.data["selected_topic"] is None
    assert output.data["counts"] == {"input": 2, "eligible": 0, "discarded": 2}
    assert [item["reason"] for item in output.data["discarded"]] == [
        "already_used",
        "invalid_topic",
    ]


def test_process_duplicates_output_phase_3_error_generates_error_output(tmp_path):
    payload = make_phase_3_payload(status="error", errors=["falló persistencia"])
    input_path = write_phase_3_output(tmp_path, payload)

    output_path = topic_selector_service.process_duplicates_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert output.data["selected_topic"] is None
    assert "status error" in output.errors[0]


def test_process_duplicates_output_rejects_wrong_contract(tmp_path):
    payload = make_phase_3_payload()
    payload["participant"] = "participante-2"
    input_path = write_phase_3_output(tmp_path, payload)

    output_path = topic_selector_service.process_duplicates_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert "participante-3" in output.errors[0]


def test_process_duplicates_output_invalid_json_generates_error_output(tmp_path):
    input_path = tmp_path / "duplicates_v1_aaaaaaaa.json"
    input_path.write_text("{", encoding="utf-8")

    output_path = topic_selector_service.process_duplicates_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert "JSON inválido" in output.errors[0]


def test_create_reuse_topic_output_preserves_used_and_is_explicit(tmp_path):
    topic = {
        "id": 27,
        "title": "Tema histórico",
        "normalized_title": "tema historico",
        "score": 15,
        "used": 1,
    }

    output_path = topic_selector_service.create_reuse_topic_output(
        topic,
        output_dir=tmp_path,
    )

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.data["strategy"] == "manual_history_reuse"
    assert output.data["selected_topic"]["id"] == 27
    assert output.data["selected_topic"]["used"] == 1
    assert output.data["selected_topic"]["manual_reuse"] is True
    assert output.data["source"]["topic_was_used"] is True
    assert output.errors == []
