"""Herramienta CLI y librería de validación para entregables JSON del pipeline.

Verifica la conformidad de los archivos JSON producidos por cada participante
con el esquema ParticipantOutput, validando la nomenclatura del archivo
({stage}_v1_{uuid-corto}.json) y la existencia de los assets declarados.

Referencias arquitectónicas:
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
    - ADR-0011: Almacenamiento local de assets y esquema canónico de entregables.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_backend.schemas.output_schema import ParticipantOutput  # noqa: E402

FILE_NAME_PATTERN = re.compile(
    r"^(?P<stage>[a-z_]+)_v1_(?P<uuid_short>[0-9a-fA-F]{8})\.json$"
)
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class OutputValidationError(ValueError):
    """Excepción controlada ante cualquier discrepancia de validación en el archivo entregable."""
    pass


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Carga y decodifica un archivo JSON desde el sistema de archivos."""
    try:
        with file_path.open("r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except json.JSONDecodeError as error:
        raise OutputValidationError(f"JSON inválido: {error}") from error


def validate_output_filename(file_path: Path, output: ParticipantOutput) -> None:
    """Verifica que el nombre coincida con {stage}_v1_{run_id[:8]}.json."""
    if file_path.suffix != ".json":
        raise OutputValidationError("El archivo debe tener extensión .json")

    match = FILE_NAME_PATTERN.match(file_path.name)
    if not match:
        raise OutputValidationError(
            "El nombre debe respetar el formato {stage}_v1_{uuid-corto}.json"
        )

    file_stage = match.group("stage")
    uuid_short = match.group("uuid_short").lower()

    if file_stage != output.stage:
        raise OutputValidationError(
            "El stage del nombre del archivo debe coincidir con el campo stage del JSON"
        )

    if uuid_short != str(output.run_id)[:8]:
        raise OutputValidationError(
            "El UUID corto del nombre debe coincidir con los primeros 8 caracteres de run_id"
        )


def validate_output_assets(file_path: Path, output: ParticipantOutput) -> None:
    """Comprueba que si se declara image_file, el asset PNG exista físicamente en disco."""
    image_file = output.data.get("image_file")

    if image_file is None:
        return

    if not isinstance(image_file, str) or not image_file.strip():
        raise OutputValidationError("data.image_file debe ser un string no vacío")

    image_path = Path(image_file)
    if not image_path.is_absolute():
        image_path = (PROJECT_ROOT / image_path).resolve()

    expected_assets_dir = (PROJECT_ROOT / "output" / "participante-5" / "assets").resolve()

    if output.participant != "participante-5" or output.stage != "ai":
        raise OutputValidationError(
            "Solo participante-5 en stage ai puede declarar data.image_file"
        )

    if image_path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise OutputValidationError(
            "La imagen referenciada en data.image_file debe ser png, jpg, jpeg o webp"
        )

    if expected_assets_dir not in image_path.parents:
        raise OutputValidationError(
            "data.image_file debe apuntar a output/participante-5/assets/"
        )

    if not image_path.exists():
        raise OutputValidationError("La imagen referenciada en data.image_file no existe")


def validate_output_file(file_path: Path) -> ParticipantOutput:
    """Ejecuta la validación integral del archivo entregable (JSON + filename + assets)."""
    payload = load_json_file(file_path)

    try:
        output = ParticipantOutput.model_validate(payload)
    except ValidationError as error:
        raise OutputValidationError(str(error)) from error

    validate_output_filename(file_path, output)
    validate_output_assets(file_path, output)
    return output


def main() -> int:
    """Punto de entrada de línea de comandos para la validación de archivos de output."""
    parser = argparse.ArgumentParser(description="Valida un JSON de output de participante.")
    parser.add_argument("json_file", help="Ruta del archivo JSON a validar")
    args = parser.parse_args()

    file_path = Path(args.json_file)

    try:
        output = validate_output_file(file_path)
    except OutputValidationError as error:
        print(f"❌ Output inválido: {error}")
        return 1

    print(
        "✅ Output válido "
        f"({output.participant} / {output.stage} / {output.run_id})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
