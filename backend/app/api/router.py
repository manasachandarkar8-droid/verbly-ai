from __future__ import annotations

from fastapi import APIRouter

from app.api.extraction import router as extraction_router
from app.api.grammar import router as grammar_router
from app.api.health import router as health_router
from app.api.readability import router as readability_router
from app.api.seo import router as seo_router
from app.api.content_analysis import router as content_analysis_router
from app.api.rewrite import router as rewrite_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(extraction_router, tags=["extraction"])
api_router.include_router(readability_router, tags=["readability"])
api_router.include_router(seo_router, tags=["seo"])
api_router.include_router(grammar_router, tags=["grammar"])
api_router.include_router(content_analysis_router,tags=["content-analysis"],)
api_router.include_router(rewrite_router, tags=["rewrite"])