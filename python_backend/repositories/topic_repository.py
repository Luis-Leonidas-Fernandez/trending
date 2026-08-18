from typing import Dict, List, Optional

from python_backend.database.connection import get_session
from python_backend.models.topic_model import TrendingTopic


def _topic_to_dict(topic: TrendingTopic) -> Dict:
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
    with get_session() as session:
        topics = session.query(TrendingTopic).order_by(TrendingTopic.created_at.desc()).all()

    return [_topic_to_dict(topic) for topic in topics]


def get_topic_by_id(topic_id: int) -> Optional[Dict]:
    with get_session() as session:
        topic = session.get(TrendingTopic, topic_id)

    if topic is None:
        return None

    return _topic_to_dict(topic)


def create_topic(topic_data: Dict) -> Optional[Dict]:
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
    with get_session() as session:
        topic = session.get(TrendingTopic, topic_id)
        if topic is None:
            return None
        topic.used = 1
        session.commit()
        session.refresh(topic)
        return _topic_to_dict(topic)
