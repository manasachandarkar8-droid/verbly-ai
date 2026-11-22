from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api.rewrite_body_limit import RewriteBodyLimitMiddleware
from app.services.rewrite.factory import close_rewrite_resources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.
    AI providers are initialized lazily when content analysis
    requests require them. No local NLP models are loaded.
    """
    yield
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    AI providers are initialized lazily.
    Feature 6 resources are closed during shutdown.
    No local NLP models are loaded.
    """
    try:
        yield
    finally:
        close_rewrite_resources()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RewriteBodyLimitMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()