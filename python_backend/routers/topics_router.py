from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from python_backend.repositories import topic_repository
from python_backend.schemas.topic_schema import TopicCreate

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("")
def list_topics():
    topics = topic_repository.get_all_topics()
    return {"success": True, "data": topics}


@router.get("/{topic_id}")
def get_topic(topic_id: int):
    topic = topic_repository.get_topic_by_id(topic_id)

    if not topic:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Tema no encontrado"},
        )

    return {"success": True, "data": topic}


@router.post("", status_code=201)
def create_topic(payload: TopicCreate):
    try:
        topic = topic_repository.create_topic(payload.model_dump())
    except IntegrityError as error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(error.orig)},
        )

    return {"success": True, "data": topic}
