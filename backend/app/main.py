from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    ask,
    auth,
    crm,
    daily_brief,
    health,
    inbox,
    integrations,
    meetings,
    morning_brief,
    n8n,
    overview,
    oauth,
    webhooks,
    weekly_digest,
    workspace,
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
        description="Briefly — AI Executive Briefing Platform API",
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
    app.include_router(auth.router)
    app.include_router(oauth.router)
    app.include_router(webhooks.router)
    app.include_router(n8n.router)
    app.include_router(workspace.router)
    app.include_router(overview.router)
    app.include_router(daily_brief.router)
    app.include_router(morning_brief.router)
    app.include_router(weekly_digest.router)
    app.include_router(inbox.router)
    app.include_router(meetings.router)
    app.include_router(crm.router)
    app.include_router(ask.router)
    app.include_router(integrations.router)
    app.include_router(settings_routes.router)

    return app


app = create_app()
