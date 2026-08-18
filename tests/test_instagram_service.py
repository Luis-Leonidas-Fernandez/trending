import json
from pathlib import Path
from uuid import uuid4

import pytest

from python_backend.services.instagram import instagram_service
from tools.validate_output import validate_output_file


SELECTED_TOPIC = {
    "id": 21,
    "title": "Rosalía",
    "normalized_title": "rosalia",
    "source": "google_trends",
    "score": 500,
    "used": 0,
}


def make_phase_5_payload(*, status="success", used_fallback=False, errors=None, selected_topic=None):
    return {
        "schema_version": "1.0",
        "run_id": str(uuid4()),
        "participant": "participante-5",
        "stage": "ai",
        "generated_at": "2026-07-27T12:00:00Z",
        "status": status,
        "data": {
            "selected_topic": SELECTED_TOPIC if selected_topic is None else selected_topic,
            "caption": "Caption real",
            "description": "Descripción real",
            "hashtags": ["#Rosalia", "Tendencias", "#Rosalia"],
            "image_prompt": "Prompt visual",
            "provider": "spartan",
            "model": "codex/gpt-5.5",
            "used_fallback": used_fallback,
            "source": {
                "participant": "participante-4",
                "stage": "topic_selector",
                "run_id": str(uuid4()),
                "status": "success",
                "used_fallback": False,
            },
        },
        "errors": errors or [],
    }


def write_phase_5_output(tmp_path: Path, payload: dict) -> Path:
    file_path = tmp_path / f"ai_v1_{payload['run_id'][:8]}.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    return file_path


def test_process_ai_output_persists_post_and_generates_success_output(monkeypatch, tmp_path):
    input_path = write_phase_5_output(tmp_path, make_phase_5_payload())
    captured = {}

    def fake_create_post(payload):
        captured.update(payload)
        return {
            "id": 99,
            **payload,
            "created_at": "2026-07-27 12:00:00",
            "topic_title": "Rosalía",
        }

    monkeypatch.setattr(instagram_service.post_repository, "create_post", fake_create_post)

    output_path = instagram_service.process_ai_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.errors == []
    assert captured == {
        "topic_id": 21,
        "image_url": None,
        "caption": "Caption real",
        "description": "Descripción real",
        "hashtags": "#Rosalia #Tendencias",
        "status": "draft",
    }
    assert output.data["post_id"] == 99
    assert output.data["ready_to_publish"] is False
    assert output.data["publication_skipped"] is True
    assert output.data["topic_marked_used"] is False
    assert output_path.name == f"instagram_v1_{str(output.run_id)[:8]}.json"


def test_process_ai_output_draft_input_stays_draft_and_propagates_errors(monkeypatch, tmp_path):
    input_path = write_phase_5_output(
        tmp_path,
        make_phase_5_payload(status="draft", used_fallback=True, errors=["fallback IA"]),
    )
    monkeypatch.setattr(
        instagram_service.post_repository,
        "create_post",
        lambda payload: {"id": 1, **payload, "created_at": "now", "topic_title": "Rosalía"},
    )

    output_path = instagram_service.process_ai_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.errors == ["fallback IA"]
    assert output.data["source"]["used_fallback"] is True


def test_process_ai_output_persistence_error_generates_error_output(monkeypatch, tmp_path):
    input_path = write_phase_5_output(tmp_path, make_phase_5_payload())

    def fail_create_post(payload):
        raise RuntimeError("sqlite caído")

    monkeypatch.setattr(instagram_service.post_repository, "create_post", fail_create_post)

    output_path = instagram_service.process_ai_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert "sqlite caído" in output.errors[0]
    assert output.data["post_id"] is None


@pytest.mark.parametrize(
    "payload_update, expected_error",
    [
        ({"participant": "participante-4"}, "participante-5"),
        ({"status": "error"}, "status error"),
    ],
)
def test_process_ai_output_invalid_contract_generates_error_output(tmp_path, payload_update, expected_error):
    payload = make_phase_5_payload()
    payload.update(payload_update)
    input_path = write_phase_5_output(tmp_path, payload)

    output_path = instagram_service.process_ai_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert expected_error in output.errors[0]


def test_process_ai_output_requires_caption(tmp_path):
    payload = make_phase_5_payload()
    payload["data"]["caption"] = "   "
    input_path = write_phase_5_output(tmp_path, payload)

    output_path = instagram_service.process_ai_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert "caption" in output.errors[0]


def test_publish_post_requires_positive_id():
    with pytest.raises(instagram_service.InstagramServiceError, match="post.id"):
        instagram_service.publish_post({"id": 0})


def test_simulate_publication_creates_log_updates_post_and_marks_topic(monkeypatch):
    calls = {}

    monkeypatch.setattr(
        instagram_service.post_repository,
        "get_post_by_id",
        lambda post_id: {
            "id": post_id,
            "topic_id": 21,
            "image_url": "output/participante-5/assets/profile.jpg",
            "caption": "Caption real",
            "description": "Descripción real",
            "hashtags": "#Rosalia",
            "status": "draft",
            "topic_title": "Rosalía",
        },
    )

    def fake_create_log(payload):
        calls["log_payload"] = payload
        return {"id": 7, **payload, "created_at": "now"}

    def fake_update_post_status(post_id, status):
        calls["updated_post"] = (post_id, status)
        return {
            "id": post_id,
            "topic_id": 21,
            "image_url": "output/participante-5/assets/profile.jpg",
            "caption": "Caption real",
            "description": "Descripción real",
            "hashtags": "#Rosalia",
            "status": status,
            "topic_title": "Rosalía",
        }

    def fake_mark_topic_used(topic_id):
        calls["topic_id"] = topic_id
        return {"id": topic_id, "title": "Rosalía", "normalized_title": "rosalia", "used": 1}

    monkeypatch.setattr(instagram_service.log_repository, "create_log", fake_create_log)
    monkeypatch.setattr(instagram_service.post_repository, "update_post_status", fake_update_post_status)
    monkeypatch.setattr(instagram_service.topic_repository, "mark_topic_used", fake_mark_topic_used)

    result = instagram_service.simulate_publication(99)

    assert result["simulated"] is True
    assert result["external_publication"] is False
    assert result["topic_marked_used"] is True
    assert result["post"]["status"] == "published_simulated"
    assert result["publication_log"]["status"] == "published_simulated"
    assert calls["updated_post"] == (99, "published_simulated")
    assert calls["topic_id"] == 21


def test_simulate_publication_requires_image(monkeypatch):
    monkeypatch.setattr(
        instagram_service.post_repository,
        "get_post_by_id",
        lambda post_id: {"id": post_id, "topic_id": 21, "caption": "Caption", "image_url": None, "status": "draft"},
    )

    with pytest.raises(instagram_service.InstagramServiceError, match="image_url"):
        instagram_service.simulate_publication(99)


def test_process_simulated_publication_generates_valid_output(monkeypatch, tmp_path):
    monkeypatch.setattr(
        instagram_service,
        "simulate_publication",
        lambda post_id: {
            "post": {"id": post_id, "topic_id": 21, "status": "published_simulated"},
            "publication_log": {"id": 5, "post_id": post_id, "status": "published_simulated"},
            "topic": {"id": 21, "used": 1},
            "platform": "instagram",
            "simulated": True,
            "external_publication": False,
            "topic_marked_used": True,
            "message": "ok",
        },
    )

    output_path = instagram_service.process_simulated_publication(99, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.data["post_id"] == 99
    assert output.data["mode"] == "simulated_publication"
    assert output.data["publication_skipped"] is False
    assert output.data["topic_marked_used"] is True
