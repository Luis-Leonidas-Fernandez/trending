import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from python_backend.services.ai import ai_service
from tools.validate_output import validate_output_file


SELECTED_TOPIC = {
    "id": 21,
    "title": "Rosalía",
    "normalized_title": "rosalia",
    "source": "google_trends",
    "score": 500,
    "used": 0,
}
MISSING = object()


def make_phase_4_payload(*, status="success", selected_topic=MISSING, used_fallback=False, errors=None):
    return {
        "schema_version": "1.0",
        "run_id": str(uuid4()),
        "participant": "participante-4",
        "stage": "topic_selector",
        "generated_at": "2026-07-27T12:00:00Z",
        "status": status,
        "data": {
            "selected_topic": SELECTED_TOPIC if selected_topic is MISSING else selected_topic,
            "strategy": "first_valid_unused",
            "counts": {"input": 1, "eligible": 1, "discarded": 0},
            "discarded": [],
            "source": {
                "participant": "participante-3",
                "stage": "duplicates",
                "run_id": str(uuid4()),
                "status": "draft" if used_fallback else "success",
                "used_fallback": used_fallback,
            },
        },
        "errors": errors or [],
    }


def write_phase_4_output(tmp_path: Path, payload: dict) -> Path:
    file_path = tmp_path / f"topic_selector_v1_{payload['run_id'][:8]}.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    return file_path


class StaticClient:
    source = "spartan"

    def generate(self, topic):
        return {
            "headline": f"Headline {topic['title']}",
            "caption": "Caption real generada por provider",
            "description": "Descripción real",
            "hashtags": ["Tendencia", "#Argentina", "#Argentina"],
            "image_prompt": "Prompt visual real",
        }


class FailingClient:
    source = "spartan"

    def generate(self, topic):
        raise httpx.HTTPStatusError(
            "401 Unauthorized",
            request=httpx.Request("POST", "http://127.0.0.1:20128/v1/chat/completions"),
            response=httpx.Response(401, text="Invalid API key"),
        )


def test_dry_run_client_generates_deterministic_content():
    result = ai_service.DryRunAIClient().generate(SELECTED_TOPIC)

    assert "Rosalía" in result["headline"]
    assert result["caption"]
    assert "#Tendencias" in result["hashtags"]
    assert result["image_prompt"]


def test_process_topic_selector_output_with_spartan_success_is_success(tmp_path):
    input_path = write_phase_4_output(tmp_path, make_phase_4_payload())
    config = ai_service.AIConfig(dry_run=False, spartan_model="gpt-test", image_enabled=False)

    output_path = ai_service.process_topic_selector_output(
        input_path,
        output_dir=tmp_path,
        client=StaticClient(),
        config=config,
    )

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.errors == []
    assert output.data["provider"] == "spartan"
    assert output.data["model"] == "gpt-test"
    assert output.data["used_fallback"] is False
    assert output.data["caption"] == "Caption real generada por provider"
    assert output.data["hashtags"] == ["#Tendencia", "#Argentina"]
    assert output_path.name == f"ai_v1_{str(output.run_id)[:8]}.json"


def test_process_topic_selector_output_spartan_error_uses_fallback_and_keeps_error(tmp_path):
    input_path = write_phase_4_output(tmp_path, make_phase_4_payload())
    config = ai_service.AIConfig(dry_run=False, fallback_on_error=True, image_enabled=False)

    output_path = ai_service.process_topic_selector_output(
        input_path,
        output_dir=tmp_path,
        client=FailingClient(),
        config=config,
    )

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.data["provider"] == "spartan"
    assert output.data["used_fallback"] is True
    assert "401 Unauthorized" in output.errors[0]
    assert output.data["caption"]


def test_process_topic_selector_output_draft_input_stays_draft_and_propagates_errors(tmp_path):
    input_path = write_phase_4_output(
        tmp_path,
        make_phase_4_payload(status="draft", used_fallback=True, errors=["fallback previo"]),
    )
    config = ai_service.AIConfig(dry_run=True, image_enabled=False)

    output_path = ai_service.process_topic_selector_output(input_path, output_dir=tmp_path, config=config)

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.errors == ["fallback previo"]
    assert output.data["source"]["used_fallback"] is True
    assert output.data["used_fallback"] is True


@pytest.mark.parametrize(
    "payload_update, expected_error",
    [
        ({"participant": "participante-3"}, "participante-4"),
        ({"status": "error"}, "status error"),
    ],
)
def test_process_topic_selector_output_invalid_contract_generates_error_output(
    tmp_path,
    payload_update,
    expected_error,
):
    payload = make_phase_4_payload()
    payload.update(payload_update)
    input_path = write_phase_4_output(tmp_path, payload)

    output_path = ai_service.process_topic_selector_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert expected_error in output.errors[0]


def test_process_topic_selector_output_without_selected_topic_generates_error_output(tmp_path):
    input_path = write_phase_4_output(tmp_path, make_phase_4_payload(selected_topic=None))

    output_path = ai_service.process_topic_selector_output(input_path, output_dir=tmp_path)

    output = validate_output_file(output_path)
    assert output.status == "error"
    assert "no seleccionó ningún tema" in output.errors[0]


def test_spartan_client_posts_to_chat_completions(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "headline": "H",
                                    "caption": "C",
                                    "description": "D",
                                    "hashtags": ["#H"],
                                    "image_prompt": "I",
                                }
                            )
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "http://provider/v1/chat/completions"),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = ai_service.SpartanAIClient(base_url="http://provider", model="gpt-test", app_client_api_key="secret")

    result = client.generate(SELECTED_TOPIC)

    assert captured["url"] == "http://provider/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert result["caption"] == "C"


class StaticImageClient:
    source = "spartan"

    def generate(self, prompt):
        return {
            "b64_json": "aW1hZ2UtYnl0ZXM=",
            "source": "spartan",
            "model": "gpt-image-test",
            "revised_prompt": f"revised {prompt}",
        }


def test_spartan_image_client_posts_to_images_generations(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return httpx.Response(
            200,
            json={"data": [{"b64_json": "aW1hZ2U=", "revised_prompt": "prompt revisado"}]},
            request=httpx.Request("POST", "http://provider/v1/images/generations"),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = ai_service.SpartanImageClient(
        base_url="http://provider",
        model="gpt-image-test",
        app_client_api_key="secret",
        size="1024x1024",
    )

    result = client.generate("Prompt visual")

    assert captured["url"] == "http://provider/v1/images/generations"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"] == {
        "model": "gpt-image-test",
        "prompt": "Prompt visual",
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    assert result["b64_json"] == "aW1hZ2U="
    assert result["revised_prompt"] == "prompt revisado"


def test_process_topic_selector_output_writes_image_asset_when_image_client_succeeds(tmp_path):
    input_path = write_phase_4_output(tmp_path, make_phase_4_payload())
    config = ai_service.AIConfig(dry_run=False, spartan_model="gpt-test", image_enabled=True)

    output_path = ai_service.process_topic_selector_output(
        input_path,
        output_dir=tmp_path,
        client=StaticClient(),
        image_client=StaticImageClient(),
        config=config,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    image_file = Path(payload["data"]["image_file"])
    assert payload["status"] == "success"
    assert payload["data"]["image_source"] == "spartan"
    assert payload["data"]["image_model"] == "gpt-image-test"
    assert payload["data"]["image_used_fallback"] is False
    assert image_file.exists()
    assert image_file.read_bytes() == b"image-bytes"


def test_process_topic_selector_output_image_error_marks_draft(tmp_path):
    class FailingImageClient:
        def generate(self, prompt):
            raise RuntimeError("image provider caído")

    input_path = write_phase_4_output(tmp_path, make_phase_4_payload())
    config = ai_service.AIConfig(dry_run=False, spartan_model="gpt-test", image_enabled=True, fallback_on_error=True)

    output_path = ai_service.process_topic_selector_output(
        input_path,
        output_dir=tmp_path,
        client=StaticClient(),
        image_client=FailingImageClient(),
        config=config,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "draft"
    assert payload["data"]["image_used_fallback"] is True
    assert "image_generation: image provider caído" in payload["errors"]
