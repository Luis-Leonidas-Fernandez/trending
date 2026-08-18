from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from python_backend.database.connection import initialize_database
from python_backend.routers.ai_router import router as ai_router
from python_backend.routers.health_router import router as health_router
from python_backend.routers.logs_router import router as logs_router
from python_backend.routers.pipeline_router import router as pipeline_router
from python_backend.routers.posts_router import router as posts_router
from python_backend.routers.topics_router import router as topics_router

initialize_database()

app = FastAPI(
    title="Trending Instagram API",
    description="Backend Python + FastAPI para el sistema de posts trending.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


ASSETS_DIR = Path(__file__).resolve().parents[1] / "output" / "participante-5" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/assets/participante-5", StaticFiles(directory=ASSETS_DIR), name="participante_5_assets")


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "JSON inválido",
            "errors": exc.errors(),
        },
    )


@app.get("/")
def root():
    return {
        "success": True,
        "message": "API FastAPI del sistema trending de Instagram",
        "scope": "Backend Python paralelo",
        "availableEndpoints": [
            "GET /api/health",
            "GET /api/topics",
            "GET /api/topics/{id}",
            "POST /api/topics",
            "GET /api/posts",
            "GET /api/posts/{id}",
            "GET /api/posts/audit/latest",
            "GET /api/posts/{id}/audit",
            "POST /api/posts",
            "POST /api/posts/{id}/publish-simulated",
            "GET /assets/participante-5/{filename}",
            "GET /api/logs",
            "GET /api/logs/{id}",
            "POST /api/logs",
            "GET /api/pipeline/state",
            "GET /api/pipeline/history",
            "GET /api/pipeline/runs",
            "GET /api/pipeline/runs/{run_id}",
            "DELETE /api/pipeline/state",
            "POST /api/pipeline/topics/{id}/reuse",
            "POST /api/pipeline/discover",
            "POST /api/pipeline/filter",
            "POST /api/pipeline/select",
            "POST /api/pipeline/create",
            "POST /api/pipeline/publish",
            "POST /api/pipeline/run",
            "GET /api/ai/providers/status",
            "POST /api/ai/providers/{provider}/connect",
        ],
    }


app.include_router(health_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(topics_router, prefix="/api")
app.include_router(posts_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
