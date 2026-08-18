"""Servicio del Participante 2: búsqueda y normalización de tendencias.

La Fase 2 consulta el RSS de Google Trends para un mercado dado, normaliza los
resultados y puede escribir un JSON versionado para que lo consuma la Fase 3.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from python_backend.schemas.output_schema import SCHEMA_VERSION

GOOGLE_TRENDS_RSS_URL = "https://trends.google.com/trending/rss"
DEFAULT_COUNTRY = "AR"
DEFAULT_LIMIT = 10
MAX_LIMIT = 10
REQUEST_TIMEOUT_SECONDS = 10.0
PARTICIPANT = "participante-2"
STAGE = "trends"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / PARTICIPANT

_FALLBACK_TITLES = (
    "economía argentina",
    "tecnología",
    "deportes argentina",
    "música latina",
    "inteligencia artificial",
    "mercado financiero",
    "turismo argentina",
    "cine y series",
    "salud y bienestar",
    "educación digital",
)


class TrendsServiceError(RuntimeError):
    """Error controlado al consultar o interpretar tendencias externas."""


@dataclass(frozen=True)
class TrendsResult:
    """Resultado completo de la Fase 2 antes de escribir el entregable."""

    items: list[dict[str, Any]]
    country: str
    used_fallback: bool
    error: str | None = None


def get_trending_topics(country: str = DEFAULT_COUNTRY, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """Devuelve tendencias normalizadas para el país indicado.

    Si Google Trends falla por timeout, HTTP, XML inválido o respuesta vacía,
    devuelve un fallback determinístico identificado con ``source='fallback'``.
    """

    return collect_trending_topics(country=country, limit=limit).items


def collect_trending_topics(country: str = DEFAULT_COUNTRY, limit: int = DEFAULT_LIMIT) -> TrendsResult:
    """Consulta tendencias y conserva metadatos de fallback/error."""

    normalized_country = _validate_country(country)
    normalized_limit = _validate_limit(limit)

    try:
        rss_text = _fetch_google_trends_rss(normalized_country)
        items = _parse_google_trends_rss(rss_text, normalized_limit)
        if not items:
            raise TrendsServiceError("Google Trends devolvió una lista vacía")
        return TrendsResult(
            items=items,
            country=normalized_country,
            used_fallback=False,
            error=None,
        )
    except (httpx.TimeoutException, httpx.HTTPError, ET.ParseError, TrendsServiceError) as error:
        sanitized_error = _sanitize_error(error)
        return TrendsResult(
            items=_build_fallback_items(normalized_limit),
            country=normalized_country,
            used_fallback=True,
            error=sanitized_error,
        )


def save_trends_output(
    country: str = DEFAULT_COUNTRY,
    limit: int = DEFAULT_LIMIT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Ejecuta la Fase 2 y guarda el JSON versionado del Participante 2."""

    result = collect_trending_topics(country=country, limit=limit)
    run_id = uuid.uuid4()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "participant": PARTICIPANT,
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "draft" if result.used_fallback else "success",
        "data": {
            "country": result.country,
            "count": len(result.items),
            "used_fallback": result.used_fallback,
            "items": result.items,
        },
        "errors": [result.error] if result.error else [],
    }

    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / f"{STAGE}_v1_{str(run_id)[:8]}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def _fetch_google_trends_rss(country: str) -> str:
    response = httpx.get(
        GOOGLE_TRENDS_RSS_URL,
        params={"geo": country},
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def _parse_google_trends_rss(rss_text: str, limit: int) -> list[dict[str, Any]]:
    root = ET.fromstring(rss_text)
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    for raw_item in root.findall(".//item"):
        title = _clean_text(_find_child_text(raw_item, "title"))
        if not title:
            continue

        normalized_title = normalize_title(title)
        if not normalized_title or normalized_title in seen_titles:
            continue

        seen_titles.add(normalized_title)
        score = _extract_score(raw_item, fallback_score=MAX_LIMIT - len(items))
        items.append(
            {
                "title": title,
                "normalized_title": normalized_title,
                "source": "google_trends",
                "category": _clean_text(_find_child_text(raw_item, "category")) or "general",
                "date": _extract_date(raw_item),
                "score": score,
            }
        )

        if len(items) == limit:
            break

    return items


def normalize_title(title: str) -> str:
    """Normaliza un título para comparación simple entre fases."""

    without_accents = unicodedata.normalize("NFKD", title)
    ascii_title = "".join(
        character for character in without_accents if not unicodedata.combining(character)
    )
    lowered = ascii_title.lower()
    comparable = re.sub(r"[^a-z0-9ñ ]+", " ", lowered)
    return re.sub(r"\s+", " ", comparable).strip()


def _extract_score(item: ET.Element, fallback_score: int) -> int:
    for child in item.iter():
        if _local_name(child.tag) == "approx_traffic":
            parsed_score = _parse_traffic_score(child.text or "")
            if parsed_score is not None:
                return parsed_score
    return fallback_score


def _parse_traffic_score(raw_score: str) -> int | None:
    cleaned_score = raw_score.strip().lower().replace("+", "")
    if not cleaned_score:
        return None

    multiplier = 1
    if cleaned_score.endswith("k"):
        multiplier = 1_000
        cleaned_score = cleaned_score[:-1]
    elif cleaned_score.endswith("m"):
        multiplier = 1_000_000
        cleaned_score = cleaned_score[:-1]

    numeric_part = re.sub(r"[^0-9.]", "", cleaned_score.replace(",", ""))
    if not numeric_part:
        return None

    try:
        return int(float(numeric_part) * multiplier)
    except ValueError:
        return None


def _extract_date(item: ET.Element) -> str:
    pub_date = _find_child_text(item, "pubDate")
    if pub_date:
        try:
            return parsedate_to_datetime(pub_date).date().isoformat()
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc).date().isoformat()


def _find_child_text(item: ET.Element, expected_name: str) -> str:
    for child in item:
        if _local_name(child.tag) == expected_name:
            return child.text or ""
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _build_fallback_items(limit: int) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date().isoformat()
    return [
        {
            "title": title,
            "normalized_title": normalize_title(title),
            "source": "fallback",
            "category": "general",
            "date": today,
            "score": MAX_LIMIT - index,
        }
        for index, title in enumerate(_FALLBACK_TITLES[:limit])
    ]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sanitize_error(error: Exception) -> str:
    message = str(error).strip() or error.__class__.__name__
    message = re.sub(r"\s+", " ", message)
    return message[:240]


def _validate_country(country: str) -> str:
    if not isinstance(country, str):
        raise ValueError("country debe ser un string con código ISO de 2 letras")

    normalized_country = country.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", normalized_country):
        raise ValueError("country debe ser un código ISO de 2 letras, por ejemplo 'AR'")
    return normalized_country


def _validate_limit(limit: int) -> int:
    if not isinstance(limit, int):
        raise ValueError("limit debe ser un entero")

    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit debe estar entre 1 y {MAX_LIMIT}")
    return limit
