"""Repositorio de persistencia para temas de tendencia (TrendingTopic).

Implementa el patrón repositorio desacoplando la lógica de negocio de la
sesión de base de datos. Transforma los modelos ORM en diccionarios desacoplados
dentro del bloque with get_session() para evitar DetachedInstanceError fuera del scope.

Referencias arquitectónicas:
    - ADR-0003: Persistencia relacional con SQLite y SQLAlchemy 2.0.
    - ADR-0008: Deduplicación por normalized_title exacto y persistencia relacional.
    - ADR-0012: Flujo en dos etapas para publicación en Instagram.
"""

from typing import Dict, List, Optional

from python_backend.database.connection import get_session
from python_backend.models.topic_model import TrendingTopic


def _topic_to_dict(topic: TrendingTopic) -> Dict:
    """Convierte una entidad TrendingTopic a un diccionario desacoplado de la sesión."""
    return {
        "id": topic.id,
        "title": topic.title,
        "normalized_title": topic.normalized_title,
        "source": topic.source,
        "score": float(topic.score),
        "used": topic.used,
        "created_at": topic.created_at,
    }


def get_all_topics() -> List[Dict]:
    """Obtiene todos los temas registrados ordenados por fecha de creación descendente."""
    with get_session() as session:
        topics = session.query(TrendingTopic).order_by(TrendingTopic.created_at.desc()).all()

    return [_topic_to_dict(topic) for topic in topics]


def get_topic_by_id(topic_id: int) -> Optional[Dict]:
    """Busca un tema por su clave primaria entera."""
    with get_session() as session:
        topic = session.get(TrendingTopic, topic_id)

    if topic is None:
        return None

    return _topic_to_dict(topic)


def create_topic(topic_data: Dict) -> Optional[Dict]:
    """Inserta un nuevo tema en SQLite confirmando la transacción atómicamente."""
    with get_session() as session:
        topic = TrendingTopic(
            title=topic_data["title"],
            normalized_title=topic_data["normalized_title"],
            source=topic_data.get("source"),
            score=topic_data.get("score", 0),
            used=topic_data.get("used", 0),
        )
        session.add(topic)
        session.commit()
        session.refresh(topic)

        return _topic_to_dict(topic)


def mark_topic_used(topic_id: int) -> Optional[Dict]:
    """Marca un tema como utilizado (used = 1) tras una publicación simulada exitosa."""
    with get_session() as session:
        topic = session.get(TrendingTopic, topic_id)
        if topic is None:
            return None
        topic.used = 1
        session.commit()
        session.refresh(topic)
        return _topic_to_dict(topic)
