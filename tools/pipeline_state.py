import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_backend.services.pipeline.pipeline_state_service import (  # noqa: E402
    DEFAULT_STATE_PATH,
    PipelineStateError,
    bootstrap_state_from_outputs,
    delete_pipeline_state,
    get_pipeline_state,
    reset_pipeline_state,
)

CURRENT_TRENDS_OUTPUT = PROJECT_ROOT / "output" / "participante-2" / "trends_v1_600c4017.json"
CURRENT_DUPLICATES_OUTPUT = PROJECT_ROOT / "output" / "participante-3" / "duplicates_v1_7c57590b.json"
CURRENT_SELECTOR_OUTPUT = PROJECT_ROOT / "output" / "participante-4" / "topic_selector_v1_fcb7e995.json"


def print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def load_errors_from_current_selector() -> list[str]:
    if not CURRENT_SELECTOR_OUTPUT.exists():
        return []
    try:
        payload = json.loads(CURRENT_SELECTOR_OUTPUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    errors = payload.get("errors", [])
    return errors if isinstance(errors, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Gestiona output/pipeline_state.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show", help="Muestra el estado actual o crea uno vacío si falta")
    subparsers.add_parser("reset", help="Elimina el estado actual y crea uno nuevo vacío")
    subparsers.add_parser("delete", help="Elimina el archivo de estado sin crear uno nuevo")
    subparsers.add_parser(
        "bootstrap-current",
        help="Crea estado inicial usando los outputs actuales de Fase 2, 3 y 4",
    )

    args = parser.parse_args()

    try:
        if args.command == "show":
            print_json(get_pipeline_state())
            return 0

        if args.command == "reset":
            state = reset_pipeline_state()
            print_json(state or {})
            return 0

        if args.command == "delete":
            deleted = delete_pipeline_state()
            print(f"Estado eliminado: {'sí' if deleted else 'no existía'} ({DEFAULT_STATE_PATH})")
            return 0

        if args.command == "bootstrap-current":
            state = bootstrap_state_from_outputs(
                trends_output=CURRENT_TRENDS_OUTPUT if CURRENT_TRENDS_OUTPUT.exists() else None,
                duplicates_output=CURRENT_DUPLICATES_OUTPUT if CURRENT_DUPLICATES_OUTPUT.exists() else None,
                topic_selector_output=CURRENT_SELECTOR_OUTPUT if CURRENT_SELECTOR_OUTPUT.exists() else None,
                status="draft",
                errors=load_errors_from_current_selector(),
            )
            print_json(state)
            return 0
    except PipelineStateError as error:
        print(f"❌ {error}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
