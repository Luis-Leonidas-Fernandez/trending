"""Puente de autenticación entre Trending y Spartan Provider.

Trending no debe pedirle al usuario que entre a Spartan para reparar credenciales.
Esta capa consulta e inicia los flujos de auth de Spartan desde el backend propio,
manteniendo a Spartan como infraestructura interna.

Referencias arquitectónicas:
    - ADR-0010: Integración con Spartan Provider para generación de copy e imagen.
    - ADR-0002: Arquitectura modular y desacoplamiento de capas.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

DEFAULT_SPARTAN_BASE_URL = "http://127.0.0.1:20128"
DEFAULT_TIMEOUT_SECONDS = 10.0
SUPPORTED_PROVIDERS = {"codex", "gemini"}


class SpartanAuthServiceError(ValueError):
    """Error controlado del puente de autenticación con Spartan."""


@dataclass(frozen=True)
class SpartanAuthConfig:
    """Configuración del puente HTTP hacia los endpoints administrativos de Spartan."""

    base_url: str = DEFAULT_SPARTAN_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


def get_spartan_auth_config(environ: dict[str, str] | None = None) -> SpartanAuthConfig:
    """Lee configuración de base URL y timeout para el servicio de autenticación."""
    env = os.environ if environ is None else environ
    return SpartanAuthConfig(
        base_url=_clean_text(env.get("SPARTAN_PROVIDER_BASE_URL")) or DEFAULT_SPARTAN_BASE_URL,
        timeout_seconds=_env_float(env.get("SPARTAN_AUTH_TIMEOUT_SECONDS"), DEFAULT_TIMEOUT_SECONDS),
    )


def get_provider_status(provider: str, config: SpartanAuthConfig | None = None) -> dict[str, Any]:
    """Devuelve el estado de auth de un provider soportado ('codex' o 'gemini')."""

    normalized_provider = _normalize_provider(provider)
    active_config = config or get_spartan_auth_config()
    if normalized_provider == "codex":
        return _get_codex_legacy_status(active_config)

    payload = _request_spartan(
        "GET",
        f"{_base_url(active_config)}/auth/{normalized_provider}/status",
        timeout=active_config.timeout_seconds,
    )
    return _present_provider_auth_status(normalized_provider, payload)


def list_provider_statuses(config: SpartanAuthConfig | None = None) -> list[dict[str, Any]]:
    """Devuelve estados de auth para los providers visibles desde Trending."""

    active_config = config or get_spartan_auth_config()
    statuses: list[dict[str, Any]] = []
    for provider in sorted(SUPPORTED_PROVIDERS):
        try:
            statuses.append(get_provider_status(provider, active_config))
        except Exception as error:  # noqa: BLE001 - status debe ser resiliente para UI.
            statuses.append(
                {
                    "provider": provider,
                    "connected": False,
                    "reconnect_required": True,
                    "message": _sanitize_error(error),
                    "reason": "status_unavailable",
                    "connection": None,
                }
            )
    return statuses


def start_provider_connection(provider: str, config: SpartanAuthConfig | None = None) -> dict[str, Any]:
    """Inicia el flujo de conexión/reautenticación y devuelve la URL OAuth."""

    normalized_provider = _normalize_provider(provider)
    active_config = config or get_spartan_auth_config()
    if normalized_provider == "codex":
        payload = _start_codex_legacy_oauth(active_config)
    else:
        payload = _request_spartan(
            "GET",
            f"{_base_url(active_config)}/auth/{normalized_provider}/start",
            timeout=active_config.timeout_seconds,
        )

    authorization_url = _clean_text(payload.get("authorizationUrl"))
    if not authorization_url:
        raise SpartanAuthServiceError("Spartan no devolvió authorizationUrl")
    return {
        "provider": normalized_provider,
        "authorization_url": authorization_url,
        "state": _clean_text(payload.get("state")),
    }


def _get_codex_legacy_status(config: SpartanAuthConfig) -> dict[str, Any]:
    """Consulta el estado del proveedor legacy codex_subscription en Spartan."""
    provider_id = _find_provider_id(config, provider_type="codex_subscription")
    payload = _request_spartan(
        "GET",
        f"{_base_url(config)}/providers/{provider_id}/auth/status",
        timeout=config.timeout_seconds,
    )
    return _present_legacy_credential_status("codex", payload)


def _start_codex_legacy_oauth(config: SpartanAuthConfig) -> dict[str, Any]:
    """Inicia el flujo OAuth legacy para suscripción Codex."""
    provider_id = _find_provider_id(config, provider_type="codex_subscription")
    return _request_spartan(
        "GET",
        f"{_base_url(config)}/providers/{provider_id}/oauth/start",
        timeout=config.timeout_seconds,
    )


def _find_provider_id(config: SpartanAuthConfig, *, provider_type: str) -> str:
    """Busca el identificador único habilitado para un tipo de proveedor dado."""
    providers = _request_spartan_list(
        "GET",
        f"{_base_url(config)}/providers",
        timeout=config.timeout_seconds,
    )
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        if provider.get("providerType") == provider_type and provider.get("isEnabled", True):
            provider_id = _clean_text(provider.get("id"))
            if provider_id:
                return provider_id
    raise SpartanAuthServiceError(f"No encontré provider habilitado de tipo {provider_type} en Spartan")


def _request_spartan(method: str, url: str, *, timeout: float) -> dict[str, Any]:
    """Ejecuta una petición HTTP a Spartan y valida que devuelva un diccionario JSON."""
    payload = _request_spartan_json(method, url, timeout=timeout)
    if not isinstance(payload, dict):
        raise SpartanAuthServiceError("Spartan devolvió un contrato inválido")
    return payload


def _request_spartan_list(method: str, url: str, *, timeout: float) -> list[Any]:
    """Ejecuta una petición HTTP a Spartan y valida que devuelva una lista JSON."""
    payload = _request_spartan_json(method, url, timeout=timeout)
    if not isinstance(payload, list):
        raise SpartanAuthServiceError("Spartan devolvió una lista inválida")
    return payload


def _request_spartan_json(method: str, url: str, *, timeout: float) -> Any:
    """Envía la solicitud HTTP procesando excepciones de red y decodificación."""
    try:
        response = httpx.request(method, url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        raise SpartanAuthServiceError(_sanitize_spartan_http_error(error)) from error
    except httpx.RequestError as error:
        raise SpartanAuthServiceError(f"No se pudo conectar con Spartan Provider: {_sanitize_error(error)}") from error
    except ValueError as error:
        raise SpartanAuthServiceError("Spartan devolvió una respuesta no JSON") from error


def _present_provider_auth_status(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Adapta el payload de respuesta de Spartan al contrato estándar de la UI de Trending."""
    return {
        "provider": provider,
        "connected": bool(payload.get("connected", False)),
        "reconnect_required": bool(payload.get("reconnectRequired", True)),
        "message": _clean_text(payload.get("message")) or "Estado de provider desconocido",
        "reason": _clean_text(payload.get("reason")),
        "connection": payload.get("connection") if isinstance(payload.get("connection"), dict) else None,
    }


def _present_legacy_credential_status(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Normaliza credenciales de proveedores legacy evaluando expiración de token."""
    credential = payload.get("credential") if isinstance(payload.get("credential"), dict) else payload
    if not isinstance(credential, dict):
        return _disconnected_legacy_status(provider, "not_connected")

    login_status = _clean_text(credential.get("loginStatus"))
    token_expires_at = _clean_text(credential.get("tokenExpiresAt"))
    token_expired = _is_past_iso_datetime(token_expires_at)
    connected = login_status in {"authenticated", "connected"} and not token_expired

    if connected:
        return {
            "provider": provider,
            "connected": True,
            "reconnect_required": False,
            "message": "Codex conectado",
            "reason": "",
            "connection": credential,
        }

    reason = "token_expired" if token_expired else login_status or "not_connected"
    return _disconnected_legacy_status(provider, reason)


def _disconnected_legacy_status(provider: str, reason: str) -> dict[str, Any]:
    """Construye un objeto de estado desconectado con mensaje específico de razón."""
    message = "Codex token vencido; reautenticación requerida" if reason == "token_expired" else "Codex necesita reautenticación"
    return {
        "provider": provider,
        "connected": False,
        "reconnect_required": True,
        "message": message,
        "reason": reason,
        "connection": None,
    }


def _is_past_iso_datetime(value: str) -> bool:
    """Evalúa si una fecha ISO 8601 ya transcurrió en comparación con UTC actual."""
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


def _normalize_provider(provider: str) -> str:
    """Valida que el proveedor pertenezca al conjunto de soportados."""
    normalized = _clean_text(provider).lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise SpartanAuthServiceError(f"Provider no soportado desde Trending: {provider}")
    return normalized


def _base_url(config: SpartanAuthConfig) -> str:
    """Limpia la barra final de la URL base."""
    return config.base_url.rstrip("/")


def _env_float(value: str | None, default: float) -> float:
    """Parsea float desde variable de entorno con fallback."""
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _clean_text(value: Any) -> str:
    """Limpia espacios en blanco redundantes."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _sanitize_spartan_http_error(error: httpx.HTTPStatusError) -> str:
    """Extrae el mensaje de error de la respuesta HTTP de Spartan."""
    response_text = ""
    try:
        payload = error.response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        response_text = _clean_text(payload.get("message") or payload.get("error"))
    if not response_text:
        response_text = _clean_text(error.response.text)
    return f"Spartan respondió {error.response.status_code}: {response_text or error.response.reason_phrase}"


def _sanitize_error(error: Any) -> str:
    """Trunca el texto de un error a 240 caracteres."""
    return " ".join(str(error).split())[:240]
