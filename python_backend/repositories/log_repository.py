from typing import Dict, List, Optional

from python_backend.database.connection import get_session
from python_backend.models.log_model import PublicationLog


def _log_to_dict(log: PublicationLog) -> Dict:
    return {
        "id": log.id,
        "post_id": log.post_id,
        "platform": log.platform,
        "status": log.status,
        "response_json": log.response_json,
        "error_message": log.error_message,
        "created_at": log.created_at,
    }


def get_all_logs() -> List[Dict]:
    with get_session() as session:
        logs = session.query(PublicationLog).order_by(PublicationLog.created_at.desc()).all()

    return [_log_to_dict(log) for log in logs]


def get_log_by_id(log_id: int) -> Optional[Dict]:
    with get_session() as session:
        log = session.get(PublicationLog, log_id)

    if log is None:
        return None

    return _log_to_dict(log)


def create_log(log_data: Dict) -> Optional[Dict]:
    with get_session() as session:
        log = PublicationLog(
            post_id=log_data["post_id"],
            platform=log_data["platform"],
            status=log_data["status"],
            response_json=log_data.get("response_json"),
            error_message=log_data.get("error_message"),
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        return _log_to_dict(log)


def get_logs_by_post_id(post_id: int) -> List[Dict]:
    with get_session() as session:
        logs = (
            session.query(PublicationLog)
            .filter(PublicationLog.post_id == post_id)
            .order_by(PublicationLog.created_at.desc())
            .all()
        )

    return [_log_to_dict(log) for log in logs]
