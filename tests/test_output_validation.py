import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_backend.schemas.output_schema import ParticipantOutput  # noqa: E402
from tools.validate_output import OutputValidationError, validate_output_file  # noqa: E402


def make_payload(**overrides):
    run_id = overrides.pop("run_id", uuid4())
    payload = {
        "schema_version": "1.0",
        "run_id": str(run_id),
        "participant": "participante-2",
        "stage": "trends",
        "generated_at": "2026-05-31T12:00:00Z",
        "status": "success",
        "data": {"items": []},
        "errors": [],
    }
    payload.update(overrides)
    return payload


def write_output_file(tmp_path: Path, payload: dict, file_name: str) -> Path:
    file_path = tmp_path / file_name
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    return file_path


def test_valid_output_json_passes(tmp_path):
    payload = make_payload()
    file_name = f"trends_v1_{payload['run_id'][:8]}.json"
    file_path = write_output_file(tmp_path, payload, file_name)

    output = validate_output_file(file_path)

    assert output.schema_version == "1.0"
    assert output.participant == "participante-2"
    assert output.stage == "trends"


def test_output_without_schema_version_fails():
    payload = make_payload()
    payload.pop("schema_version")

    with pytest.raises(ValidationError):
        ParticipantOutput.model_validate(payload)


def test_output_without_run_id_fails():
    payload = make_payload()
    payload.pop("run_id")

    with pytest.raises(ValidationError):
        ParticipantOutput.model_validate(payload)


def test_output_with_invalid_uuid_fails():
    payload = make_payload(run_id="no-es-uuid")

    with pytest.raises(ValidationError):
        ParticipantOutput.model_validate(payload)


def test_output_with_invalid_participant_fails():
    payload = make_payload(participant="participante-99")

    with pytest.raises(ValidationError):
        ParticipantOutput.model_validate(payload)


def test_output_with_invalid_stage_fails():
    payload = make_payload(stage="otra_etapa")

    with pytest.raises(ValidationError):
        ParticipantOutput.model_validate(payload)


def test_output_with_invalid_status_fails():
    payload = make_payload(status="finished")

    with pytest.raises(ValidationError):
        ParticipantOutput.model_validate(payload)


def test_output_file_without_v1_in_name_fails(tmp_path):
    payload = make_payload()
    file_path = write_output_file(tmp_path, payload, f"trends_{payload['run_id'][:8]}.json")

    with pytest.raises(OutputValidationError, match="formato"):
        validate_output_file(file_path)


def test_output_file_with_different_uuid_short_fails(tmp_path):
    payload = make_payload()
    file_path = write_output_file(tmp_path, payload, "trends_v1_aaaaaaaa.json")

    with pytest.raises(OutputValidationError, match="UUID corto"):
        validate_output_file(file_path)


def test_ai_output_with_existing_asset_passes(tmp_path):
    asset_dir = PROJECT_ROOT / "output" / "participante-5" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / "ai_v1_preview.png"
    asset_path.write_bytes(b"fake-image")

    payload = make_payload(
        participant="participante-5",
        stage="ai",
        data={
            "image_file": "output/participante-5/assets/ai_v1_preview.png",
            "caption": "caption",
            "description": "descripcion",
        },
    )
    file_name = f"ai_v1_{payload['run_id'][:8]}.json"
    file_path = write_output_file(tmp_path, payload, file_name)

    output = validate_output_file(file_path)

    assert output.participant == "participante-5"
    assert output.stage == "ai"


def test_ai_output_with_missing_asset_fails(tmp_path):
    payload = make_payload(
        participant="participante-5",
        stage="ai",
        data={"image_file": "output/participante-5/assets/no-existe.png"},
    )
    file_name = f"ai_v1_{payload['run_id'][:8]}.json"
    file_path = write_output_file(tmp_path, payload, file_name)

    with pytest.raises(OutputValidationError, match="no existe"):
        validate_output_file(file_path)
