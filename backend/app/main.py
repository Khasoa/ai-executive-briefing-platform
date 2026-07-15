from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    assistant,
    calendar,
    crm,
    health,
    inbox,
    overview,
    projects,
    research,
)
from app.api.routes import settings as settings_routes
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.middleware.logging import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = get_settings()
    setup_logging(app_settings)
    yield


def create_app() -> FastAPI:
    app_settings = get_settings()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="Relay — AI Executive Partner API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health.router)
    app.include_router(overview.router)
    app.include_router(calendar.router)
    app.include_router(inbox.router)
    app.include_router(crm.router)
    app.include_router(projects.router)
    app.include_router(research.router)
    app.include_router(assistant.router)
    app.include_router(settings_routes.router)

    return app


app = create_app()
