import json
from pathlib import Path
from uuid import uuid4

from python_backend.services.metrics import metrics_service


def _instagram_output(path: Path, post_id: int = 10) -> Path:
    payload = {
        "schema_version": "1.0",
        "run_id": str(uuid4()),
        "participant": "participante-6",
        "stage": "instagram",
        "generated_at": "2026-07-28T12:15:22+00:00",
        "status": "success",
        "data": {"post": {"id": post_id}},
        "errors": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_process_instagram_output_scores_success_when_local_audit_is_complete(tmp_path, monkeypatch):
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"png")
    input_path = _instagram_output(tmp_path / "instagram.json")

    monkeypatch.setattr(metrics_service.post_repository, "get_post_by_id", lambda post_id: {
        "id": post_id,
        "topic_id": 25,
        "image_url": str(image_path),
        "caption": "caption",
        "description": "description",
        "hashtags": "#Uno #Dos",
        "status": "published_simulated",
        "created_at": "2026-07-28 12:09:06",
        "topic_title": "inundación",
    })
    monkeypatch.setattr(metrics_service.topic_repository, "get_topic_by_id", lambda topic_id: {
        "id": topic_id,
        "title": "inundación",
        "normalized_title": "inundacion",
        "source": "google_trends",
        "score": 100.0,
        "used": 1,
        "created_at": "2026-07-28 12:07:47",
    })
    monkeypatch.setattr(metrics_service.log_repository, "get_logs_by_post_id", lambda post_id: [{
        "id": 2,
        "post_id": post_id,
        "platform": "instagram",
        "status": "published_simulated",
        "response_json": "{}",
        "error_message": None,
        "created_at": "2026-07-28 12:15:22",
    }])

    output = metrics_service.process_instagram_output(input_path, output_dir=tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["participant"] == "participante-7"
    assert payload["stage"] == "metrics"
    assert payload["status"] == "success"
    assert payload["data"]["score"] == 100
    assert payload["data"]["warnings"] == []
    assert payload["data"]["checks"]["topic_marked_used"] is True
    assert payload["data"]["ready_for_real_publication"] is False


def test_process_instagram_output_returns_draft_when_checks_are_missing(tmp_path, monkeypatch):
    input_path = _instagram_output(tmp_path / "instagram.json")

    monkeypatch.setattr(metrics_service.post_repository, "get_post_by_id", lambda post_id: {
        "id": post_id,
        "topic_id": 25,
        "image_url": "",
        "caption": "caption",
        "description": "description",
        "hashtags": "",
        "status": "draft",
        "created_at": "2026-07-28 12:09:06",
        "topic_title": "inundación",
    })
    monkeypatch.setattr(metrics_service.topic_repository, "get_topic_by_id", lambda topic_id: {
        "id": topic_id,
        "used": 0,
    })
    monkeypatch.setattr(metrics_service.log_repository, "get_logs_by_post_id", lambda post_id: [])

    output = metrics_service.process_instagram_output(input_path, output_dir=tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["status"] == "draft"
    assert payload["data"]["score"] < 100
    assert "El post no está en estado published_simulated" in payload["errors"]
    assert "No hay log de publicación simulada" in payload["errors"]
