from typing import Dict, List, Optional

from sqlalchemy.orm import joinedload

from python_backend.database.connection import get_session
from python_backend.models.post_model import GeneratedPost


def _post_to_dict(post: GeneratedPost) -> Dict:
    return {
        "id": post.id,
        "topic_id": post.topic_id,
        "image_url": post.image_url,
        "caption": post.caption,
        "description": post.description,
        "hashtags": post.hashtags,
        "status": post.status,
        "created_at": post.created_at,
        "topic_title": post.topic.title if post.topic else None,
    }


def get_all_posts() -> List[Dict]:
    with get_session() as session:
        posts = (
            session.query(GeneratedPost)
            .options(joinedload(GeneratedPost.topic))
            .order_by(GeneratedPost.created_at.desc())
            .all()
        )
        return [_post_to_dict(post) for post in posts]


def get_post_by_id(post_id: int) -> Optional[Dict]:
    with get_session() as session:
        post = (
            session.query(GeneratedPost)
            .options(joinedload(GeneratedPost.topic))
            .filter(GeneratedPost.id == post_id)
            .one_or_none()
        )
        if post is None:
            return None
        return _post_to_dict(post)


def create_post(post_data: Dict) -> Optional[Dict]:
    with get_session() as session:
        post = GeneratedPost(
            topic_id=post_data["topic_id"],
            image_url=post_data.get("image_url"),
            caption=post_data.get("caption"),
            description=post_data.get("description"),
            hashtags=post_data.get("hashtags"),
            status=post_data.get("status", "draft"),
        )
        session.add(post)
        session.commit()
        session.refresh(post)
        post = (
            session.query(GeneratedPost)
            .options(joinedload(GeneratedPost.topic))
            .filter(GeneratedPost.id == post.id)
            .one()
        )
        return _post_to_dict(post)


def update_post_status(post_id: int, status: str) -> Optional[Dict]:
    with get_session() as session:
        post = (
            session.query(GeneratedPost)
            .options(joinedload(GeneratedPost.topic))
            .filter(GeneratedPost.id == post_id)
            .one_or_none()
        )
        if post is None:
            return None
        post.status = status
        session.commit()
        session.refresh(post)
        post = (
            session.query(GeneratedPost)
            .options(joinedload(GeneratedPost.topic))
            .filter(GeneratedPost.id == post_id)
            .one()
        )
        return _post_to_dict(post)
