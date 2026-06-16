from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    body_metrics,
    exercises,
    health,
    measurements,
    nutrition,
    plans,
    profile,
    progress,
    sessions,
    tts,
)
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HomeShred API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_routers = [
        health.router,
        exercises.router,
        profile.router,
        plans.router,
        sessions.router,
        progress.router,
        body_metrics.router,
        measurements.router,
        nutrition.router,
        tts.router,
    ]
    for router in api_routers:
        app.include_router(router, prefix="/api")

    return app


app = create_app()
