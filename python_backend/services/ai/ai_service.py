"""Servicio del Participante 5: generación de contenido con IA.

La Fase 5 consume el output de Fase 4, genera contenido textual para un post
con IA y guarda un JSON versionado. La integración real usa Spartan Provider
por HTTP, pero mantiene un fallback determinístico/dry-run para que el pipeline
no quede bloqueado por credenciales o disponibilidad del provider.

Referencias arquitectónicas:
    - ADR-0010: Integración con Spartan Provider para generación de copy e imagen.
    - ADR-0011: Almacenamiento local de assets y esquema canónico de entregables.
    - ADR-0015: Cancelación cooperativa del pipeline y cierre de sockets en vuelo.
    - ADR-0005: Formato versionado y canónico para entregables JSON inter-fases.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from python_backend.schemas.output_schema import SCHEMA_VERSION, ParticipantOutput
from python_backend.services.pipeline.pipeline_cancel_service import registered_closer

PARTICIPANT = "participante-5"
STAGE = "ai"
SOURCE_PARTICIPANT = "participante-4"
SOURCE_STAGE = "topic_selector"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / PARTICIPANT

DEFAULT_PROVIDER = "spartan"
DEFAULT_SPARTAN_BASE_URL = "http://127.0.0.1:20128"
DEFAULT_SPARTAN_MODEL = "gpt-5"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_IMAGE_TIMEOUT_SECONDS = 120.0
DEFAULT_IMAGE_SIZE = "1024x1024"


class AIServiceError(ValueError):
    """Error controlado de validación o generación de contenido."""


@dataclass(frozen=True)
class AIConfig:
    """Configuración mínima inmutable para selección y ejecución de clientes IA."""

    provider: str = DEFAULT_PROVIDER
    dry_run: bool = True
    spartan_base_url: str = DEFAULT_SPARTAN_BASE_URL
    spartan_model: str = DEFAULT_SPARTAN_MODEL
    spartan_app_client_api_key: str = ""
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    fallback_on_error: bool = True
    image_enabled: bool = True
    spartan_image_model: str = ""
    image_timeout_seconds: float = DEFAULT_IMAGE_TIMEOUT_SECONDS
    image_size: str = DEFAULT_IMAGE_SIZE


class AIClient(Protocol):
    """Contrato común para clientes de generación de contenido textual."""

    source: str

    def generate(self, topic: dict[str, Any]) -> dict[str, Any]:
        """Genera contenido para un tema seleccionado."""


class DryRunAIClient:
    """Cliente determinístico para desarrollo, pruebas y fallback."""

    source = "dry_run"

    def generate(self, topic: dict[str, Any]) -> dict[str, Any]:
        """Genera copy estático y hashtags basados en el título del tema sin llamadas externas."""
        title = _clean_text(topic.get("title")) or "tema tendencia"
        normalized_title = _clean_text(topic.get("normalized_title")) or _slugify(title)
        hashtag_seed = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ]+", " ", title)
        hashtag = "#" + "".join(part.capitalize() for part in hashtag_seed.split())[:40]
        if hashtag == "#":
            hashtag = "#Tendencia"

        return {
            "headline": f"{title} está marcando conversación",
            "caption": (
                f"{title} aparece entre las tendencias del momento. "
                "Convertimos la señal en una idea clara, breve y lista para adaptar a Instagram."
            ),
            "description": (
                "Borrador generado en modo seguro para validar el flujo completo "
                "antes de activar generación real con Spartan Provider."
            ),
            "hashtags": [hashtag, "#Tendencias", "#Argentina", "#SocialMedia"],
            "image_prompt": (
                f"Diseño editorial vertical para Instagram sobre '{title}', fondo moderno, "
                "alto contraste, composición limpia, energía de tendencia digital."
            ),
            "normalized_topic": normalized_title,
        }


class SpartanAIClient:
    """Cliente HTTP para Spartan Provider compatible con chat completions."""

    source = "spartan"

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_SPARTAN_BASE_URL,
        model: str = DEFAULT_SPARTAN_MODEL,
        app_client_api_key: str = "",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.app_client_api_key = app_client_api_key
        self.timeout_seconds = timeout_seconds

    def generate(self, topic: dict[str, Any]) -> dict[str, Any]:
        """Invoca el endpoint chat/completions con socket cancelable registrado."""
        if not self.app_client_api_key:
            raise AIServiceError("Spartan Gateway requiere SPARTAN_APP_CLIENT_API_KEY")

        endpoint = f"{self.base_url}/v1/chat/completions"
        client = httpx.Client(timeout=self.timeout_seconds)
        with client, registered_closer(client.close):
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.app_client_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Sos un especialista en contenido para Instagram. "
                                "Respondé únicamente JSON válido con keys: headline, caption, "
                                "description, hashtags, image_prompt. "
                                "Usá español rioplatense claro, informativo y natural. "
                                "headline: máximo 70 caracteres. "
                                "caption: entre 500 y 750 caracteres, OBLIGATORIAMENTE dividido "
                                "en 3 párrafos cortos separados con \n\n dentro del string JSON. "
                                "Párrafo 1: qué pasó. Párrafo 2: por qué importa. "
                                "Párrafo 3: recomendación útil o contexto para no caer en ruido. "
                                "No devuelvas el caption en un solo bloque de texto. "
                                "Sin relleno ni promesas. "
                                "description: entre 180 y 260 caracteres, explicando el enfoque "
                                "editorial del post para auditoría interna. "
                                "hashtags: 2 a 4 etiquetas relevantes."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "task": "Generar contenido breve para un post de tendencia",
                                    "topic": topic,
                                    "language": "es-AR",
                                    },
                                ensure_ascii=False,
                            ),
                        },
                    ],
                },
            )
        response.raise_for_status()
        payload = response.json()
        content = _extract_chat_content(payload)
        return _parse_generated_content(content)


class SpartanImageClient:
    """Cliente HTTP para generación de imágenes mediante Spartan Provider."""

    source = "spartan"

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_SPARTAN_BASE_URL,
        model: str,
        app_client_api_key: str = "",
        timeout_seconds: float = DEFAULT_IMAGE_TIMEOUT_SECONDS,
        size: str = DEFAULT_IMAGE_SIZE,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.app_client_api_key = app_client_api_key
        self.timeout_seconds = timeout_seconds
        self.size = size

    def generate(self, prompt: str) -> dict[str, Any]:
        """Solicita la generación de imagen en base64 mediante images/generations."""
        if not self.app_client_api_key:
            raise AIServiceError("Spartan Gateway requiere SPARTAN_APP_CLIENT_API_KEY")
        clean_prompt = _clean_text(prompt)
        if not clean_prompt:
            raise AIServiceError("image_prompt no puede estar vacío")

        endpoint = f"{self.base_url}/v1/images/generations"
        client = httpx.Client(timeout=self.timeout_seconds)
        with client, registered_closer(client.close):
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.app_client_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "prompt": clean_prompt,
                    "size": self.size,
                    "response_format": "b64_json",
                },
            )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise AIServiceError("Spartan Provider no devolvió data de imagen")
        first = data[0]
        if not isinstance(first, dict):
            raise AIServiceError("Spartan Provider devolvió imagen inválida")
        b64_json = _clean_text(first.get("b64_json"))
        if not b64_json:
            raise AIServiceError("Spartan Provider no devolvió b64_json")
        return {
            "b64_json": b64_json,
            "revised_prompt": _clean_text(first.get("revised_prompt")) or None,
            "model": self.model,
            "source": self.source,
        }


def get_ai_config(environ: dict[str, str] | None = None) -> AIConfig:
    """Lee configuración desde entorno con defaults seguros para desarrollo."""

    env = os.environ if environ is None else environ
    return AIConfig(
        provider=_clean_text(env.get("AI_PROVIDER")) or DEFAULT_PROVIDER,
        dry_run=_env_bool(env.get("AI_DRY_RUN"), default=True),
        spartan_base_url=_clean_text(env.get("SPARTAN_PROVIDER_BASE_URL")) or DEFAULT_SPARTAN_BASE_URL,
        spartan_model=_clean_text(env.get("SPARTAN_PROVIDER_MODEL")) or DEFAULT_SPARTAN_MODEL,
        spartan_app_client_api_key=_clean_text(env.get("SPARTAN_APP_CLIENT_API_KEY")) or _clean_text(env.get("SPARTAN_PROVIDER_API_KEY")),
        timeout_seconds=_env_float(env.get("SPARTAN_PROVIDER_TIMEOUT_SECONDS"), DEFAULT_TIMEOUT_SECONDS),
        fallback_on_error=_env_bool(env.get("AI_FALLBACK_ON_ERROR"), default=True),
        image_enabled=_env_bool(env.get("AI_IMAGE_ENABLED"), default=True),
        spartan_image_model=_clean_text(env.get("SPARTAN_PROVIDER_IMAGE_MODEL")),
        image_timeout_seconds=_env_float(env.get("SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS"), DEFAULT_IMAGE_TIMEOUT_SECONDS),
        image_size=_clean_text(env.get("SPARTAN_PROVIDER_IMAGE_SIZE")) or DEFAULT_IMAGE_SIZE,
    )


def get_ai_client(config: AIConfig | None = None) -> AIClient:
    """Construye el cliente IA activo según la configuración provista."""

    active_config = config or get_ai_config()
    if active_config.dry_run:
        return DryRunAIClient()
    if active_config.provider.lower() != "spartan":
        raise AIServiceError(f"AI_PROVIDER no soportado: {active_config.provider}")
    return SpartanAIClient(
        base_url=active_config.spartan_base_url,
        model=active_config.spartan_model,
        app_client_api_key=active_config.spartan_app_client_api_key,
        timeout_seconds=active_config.timeout_seconds,
    )


def generate_post_content(topic: dict[str, Any]) -> dict[str, Any]:
    """Genera contenido para un tema usando el cliente configurado."""

    selected_topic = _validate_topic(topic)
    config = get_ai_config()
    client = get_ai_client(config)
    return _normalize_content(client.generate(selected_topic), selected_topic)


def process_topic_selector_output(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    client: AIClient | None = None,
    image_client: SpartanImageClient | None = None,
    config: AIConfig | None = None,
) -> Path:
    """Procesa un output de Fase 4 y guarda el entregable de Fase 5.

    Lee el tema elegido en Fase 4, ejecuta la generación de texto e imagen opcional,
    almacena los assets PNG generados y persiste el archivo JSON versionado.
    """

    source_path = Path(input_path)
    run_id = uuid.uuid4()
    destination_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"

    try:
        source_output = _load_phase_4_output(source_path)
        selected_topic = source_output.data.get("selected_topic")
        if selected_topic is None:
            raise AIServiceError("Fase 4 no seleccionó ningún tema")
        topic = _validate_topic(selected_topic)

        active_config = config or get_ai_config()
        active_client = client or get_ai_client(active_config)
        used_fallback = active_client.source == "dry_run"
        errors = _sanitize_errors(source_output.errors)
        provider_error = None

        try:
            generated = _normalize_content(active_client.generate(topic), topic)
        except Exception as error:  # noqa: BLE001 - se convierte en fallback auditable.
            if not active_config.fallback_on_error:
                raise
            provider_error = _sanitize_error(error)
            fallback_client = DryRunAIClient()
            generated = _normalize_content(fallback_client.generate(topic), topic)
            used_fallback = True
            errors.append(provider_error)

        image_result: dict[str, Any] | None = None
        image_error = None
        used_image_fallback = False
        if active_config.image_enabled:
            try:
                active_image_client = image_client or _get_image_client(active_config)
                image_response = active_image_client.generate(generated["image_prompt"])
                image_file = _write_image_asset(
                    b64_json=image_response["b64_json"],
                    run_id=run_id,
                    destination_dir=destination_dir,
                )
                image_result = {
                    "image_file": _relative_project_path(image_file),
                    "image_source": image_response["source"],
                    "image_model": image_response["model"],
                    "image_revised_prompt": image_response.get("revised_prompt"),
                    "image_used_fallback": False,
                }
            except Exception as error:  # noqa: BLE001 - imagen queda como fallback auditable.
                if not active_config.fallback_on_error:
                    raise
                image_error = _sanitize_error(error)
                used_image_fallback = True
                errors.append(f"image_generation: {image_error}")

        inherited_fallback = _source_used_fallback(source_output)
        status = "draft" if source_output.status == "draft" or inherited_fallback or used_fallback or used_image_fallback else "success"
        payload = _build_payload(
            run_id=run_id,
            status=status,
            content=generated,
            errors=errors,
            source_output=source_output,
            selected_topic=topic,
            provider=active_client.source,
            model=active_config.spartan_model if active_client.source == "spartan" else "dry-run",
            used_fallback=used_fallback,
            provider_error=provider_error,
            inherited_fallback=inherited_fallback,
            image_result=image_result,
            image_error=image_error,
            used_image_fallback=used_image_fallback,
        )
    except Exception as error:  # noqa: BLE001 - el output debe dejar fallo auditable.
        payload = _build_error_payload(run_id=run_id, error=error, input_path=source_path)

    _write_json(output_path=output_path, payload=payload)
    return output_path


def _get_image_client(config: AIConfig) -> SpartanImageClient:
    """Instancia el cliente de imagen si la configuración es válida para Spartan."""
    if config.provider.lower() != "spartan" or config.dry_run:
        raise AIServiceError("Generación de imagen real requiere AI_PROVIDER=spartan y AI_DRY_RUN=false")
    image_model = config.spartan_image_model or config.spartan_model
    return SpartanImageClient(
        base_url=config.spartan_base_url,
        model=image_model,
        app_client_api_key=config.spartan_app_client_api_key,
        timeout_seconds=config.image_timeout_seconds,
        size=config.image_size,
    )


def _write_image_asset(*, b64_json: str, run_id: uuid.UUID, destination_dir: Path) -> Path:
    """Decodifica el string base64 y guarda el archivo PNG en el directorio de assets."""
    try:
        image_bytes = base64.b64decode(b64_json, validate=True)
    except (binascii.Error, ValueError) as error:
        raise AIServiceError("Spartan Provider devolvió base64 de imagen inválido") from error

    if not image_bytes:
        raise AIServiceError("Spartan Provider devolvió imagen vacía")

    assets_dir = PROJECT_ROOT / "output" / PARTICIPANT / "assets"
    if destination_dir.resolve() != DEFAULT_OUTPUT_DIR.resolve():
        assets_dir = destination_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    image_path = assets_dir / f"{STAGE}_v1_{str(run_id)[:8]}.png"
    image_path.write_bytes(image_bytes)
    return image_path


def _relative_project_path(path: Path) -> str:
    """Devuelve la ruta relativa al directorio raíz del proyecto."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _load_phase_4_output(input_path: Path) -> ParticipantOutput:
    """Carga y valida el archivo entregable JSON generado por la Fase 4."""
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AIServiceError(f"No existe el output de Fase 4: {input_path}") from error
    except json.JSONDecodeError as error:
        raise AIServiceError(f"JSON inválido en output de Fase 4: {error}") from error

    try:
        output = ParticipantOutput.model_validate(payload)
    except ValidationError as error:
        raise AIServiceError(f"Output de Fase 4 inválido: {error}") from error

    if output.participant != SOURCE_PARTICIPANT or output.stage != SOURCE_STAGE:
        raise AIServiceError("El input debe pertenecer a participante-4 y stage topic_selector")

    if output.status == "error":
        raise AIServiceError("El input de Fase 4 está en status error")

    if output.status not in {"success", "draft"}:
        raise AIServiceError("El input de Fase 4 debe estar en status success o draft")

    return output


def _validate_topic(topic: Any) -> dict[str, Any]:
    """Comprueba que el diccionario del tema contenga id entero positivo y títulos no vacíos."""
    if not isinstance(topic, dict):
        raise AIServiceError("selected_topic debe ser un objeto")

    topic_id = topic.get("id")
    title = _clean_text(topic.get("title"))
    normalized_title = _clean_text(topic.get("normalized_title"))

    if not isinstance(topic_id, int) or isinstance(topic_id, bool) or topic_id <= 0:
        raise AIServiceError("selected_topic.id debe ser un entero positivo")
    if not title or not normalized_title:
        raise AIServiceError("selected_topic debe tener title y normalized_title no vacíos")

    return {**topic, "id": topic_id, "title": title, "normalized_title": normalized_title}


def _normalize_content(content: dict[str, Any], topic: dict[str, Any]) -> dict[str, Any]:
    """Valida y normaliza la estructura generada (headline, caption, description, etc.)."""
    if not isinstance(content, dict):
        raise AIServiceError("La respuesta IA debe ser un objeto")

    headline = _clean_text(content.get("headline")) or f"{topic['title']} es tendencia"
    caption = _normalize_caption_text(content.get("caption"))
    description = _clean_text(content.get("description"))
    image_prompt = _clean_text(content.get("image_prompt"))
    hashtags = _normalize_hashtags(content.get("hashtags"))

    if not caption:
        raise AIServiceError("La respuesta IA debe incluir caption")
    if not description:
        description = "Contenido generado para acompañar un post de tendencia."
    if not image_prompt:
        image_prompt = f"Imagen editorial para Instagram sobre {topic['title']}"

    return {
        "headline": headline,
        "caption": caption,
        "description": description,
        "hashtags": hashtags,
        "image_prompt": image_prompt,
    }


def _normalize_caption_text(value: Any) -> str:
    """Asegura que el caption contenga división en 2 o 3 párrafos limpios."""
    raw_text = _clean_multiline_text(value)
    if not raw_text:
        return ""

    paragraphs = [paragraph for paragraph in raw_text.split("\n\n") if paragraph.strip()]
    paragraphs = [paragraph for paragraph in paragraphs if not _is_hashtag_only_line(paragraph)]
    if 2 <= len(paragraphs) <= 3:
        return "\n\n".join(paragraphs)

    compact_text = _clean_text(raw_text)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact_text) if part.strip()]
    if len(sentences) < 3:
        return compact_text

    grouped_sentences = _split_sentences_in_three_groups(sentences)
    return "\n\n".join(" ".join(group) for group in grouped_sentences if group)


def _clean_multiline_text(value: Any) -> str:
    """Normaliza saltos de línea manteniendo bloques de párrafos."""
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    for block in re.split(r"\n\s*\n", text):
        cleaned_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in block.split("\n")]
        cleaned_block = " ".join(line for line in cleaned_lines if line)
        if cleaned_block:
            blocks.append(cleaned_block)
    return "\n\n".join(blocks).strip()


def _is_hashtag_only_line(value: str) -> bool:
    """Detecta si una línea está compuesta exclusivamente de etiquetas #."""
    text = value.replace("**", "").strip()
    if not text or "#" not in text:
        return False
    return all(part.startswith("#") for part in text.split())


def _split_sentences_in_three_groups(sentences: list[str]) -> list[list[str]]:
    """Distribuye una lista de oraciones en 3 bloques balanceados."""
    group_count = 3
    base_size, remainder = divmod(len(sentences), group_count)
    groups: list[list[str]] = []
    cursor = 0
    for index in range(group_count):
        size = base_size + (1 if index < remainder else 0)
        groups.append(sentences[cursor : cursor + size])
        cursor += size
    return groups


def _normalize_hashtags(value: Any) -> list[str]:
    """Garantiza formato #etiqueta y limita a 10 hashtags."""
    raw_items = value if isinstance(value, list) else []
    hashtags: list[str] = []
    for item in raw_items:
        text = _clean_text(item)
        if not text:
            continue
        if not text.startswith("#"):
            text = f"#{text}"
        text = re.sub(r"\s+", "", text)
        if text not in hashtags:
            hashtags.append(text[:60])
    return hashtags[:10] or ["#Tendencias", "#Argentina"]


def _extract_chat_content(payload: dict[str, Any]) -> str:
    """Extrae el contenido textual del primer choice retornado por chat/completions."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIServiceError("Spartan Provider no devolvió choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise AIServiceError("Spartan Provider devolvió choice inválido")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise AIServiceError("Spartan Provider no devolvió message")
    content = _clean_text(message.get("content"))
    if not content:
        raise AIServiceError("Spartan Provider devolvió contenido vacío")
    return content


def _parse_generated_content(content: str) -> dict[str, Any]:
    """Parsea la respuesta JSON retornada por el modelo de lenguaje."""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise AIServiceError(f"Spartan Provider devolvió JSON inválido: {error}") from error
    if not isinstance(parsed, dict):
        raise AIServiceError("Spartan Provider debe devolver un objeto JSON")
    return parsed


def _build_payload(
    *,
    run_id: uuid.UUID,
    status: str,
    content: dict[str, Any],
    errors: list[str],
    source_output: ParticipantOutput,
    selected_topic: dict[str, Any],
    provider: str,
    model: str,
    used_fallback: bool,
    provider_error: str | None,
    inherited_fallback: bool,
    image_result: dict[str, Any] | None = None,
    image_error: str | None = None,
    used_image_fallback: bool = False,
) -> dict[str, Any]:
    """Construye el entregable conforme al esquema ParticipantOutput para Fase 5."""
    image_metadata = {
        "image_enabled": True,
        "image_used_fallback": used_image_fallback,
        "image_error": image_error,
    }
    if image_result:
        image_metadata.update(image_result)
        content = {**content, "image_file": image_result["image_file"]}

    data = {
        "selected_topic": selected_topic,
        "content": content,
        "headline": content["headline"],
        "caption": content["caption"],
        "description": content["description"],
        "hashtags": content["hashtags"],
        "image_prompt": content["image_prompt"],
        **image_metadata,
        "provider": provider,
        "model": model,
        "used_fallback": used_fallback,
        "provider_error": provider_error,
        "source": {
            "participant": source_output.participant,
            "stage": source_output.stage,
            "run_id": str(source_output.run_id),
            "status": source_output.status,
            "used_fallback": inherited_fallback,
        },
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "data": data,
        "errors": errors,
    }


def _build_error_payload(run_id: uuid.UUID, error: Exception, input_path: Path) -> dict[str, Any]:
    """Construye un entregable con status error para auditoría ante fallas no recuperables."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "data": {
            "selected_topic": None,
            "content": None,
            "used_fallback": False,
            "source": {"input_path": str(input_path)},
        },
        "errors": [_sanitize_error(error)],
    }


def _source_used_fallback(source_output: ParticipantOutput) -> bool:
    """Verifica si el output antecesor declaró haber utilizado fallback."""
    source = source_output.data.get("source", {})
    if isinstance(source, dict):
        return bool(source.get("used_fallback", False))
    return False


def _write_json(output_path: Path, payload: dict[str, Any]) -> None:
    """Persiste el payload en formato JSON con indentación en la ruta destino."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _env_bool(value: str | None, *, default: bool) -> bool:
    """Parsea variables de entorno booleanas con variantes comunes (1, true, yes, si)."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}


def _env_float(value: str | None, default: float) -> float:
    """Parsea variables de entorno numéricas flotantes con valor por defecto."""
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _clean_text(value: Any) -> str:
    """Elimina espacios redundantes y retorna string limpio."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _slugify(value: str) -> str:
    """Genera una versión alfanumérica simple de un texto."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _sanitize_errors(errors: Any) -> list[str]:
    """Limpia y trunca una lista de errores."""
    if not isinstance(errors, list):
        return []
    return [_sanitize_error(error) for error in errors if _sanitize_error(error)]


def _sanitize_error(error: Any) -> str:
    """Trunca mensajes de error a 240 caracteres."""
    message = " ".join(str(error).split())
    return message[:240]
