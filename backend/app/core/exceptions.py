"""
Centralized exception handling (foundation layer).

Feature-specific exceptions (e.g. app/services/extraction/exceptions.py)
stay defined close to their domain. This module maps them to HTTP
responses in one place and registers a catch-all fallback, so individual
routers don't each need their own try/except/HTTPException boilerplate.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.encoders import jsonable_encoder

from app.services.extraction.exceptions import (
    ExtractionError,
    FetchConnectionError,
    FetchTimeoutError,
    InsufficientContentError,
    InvalidURLError,
    ResponseTooLargeError,
    SSRFBlockedError,
    TooManyRedirectsError,
    UnsupportedContentTypeError,
)

from app.services.grammar.exceptions import (
    GrammarEngineError,
    GrammarEngineResponseError,
    GrammarEngineTimeoutError,
    GrammarEngineUnavailableError,
)

logger = logging.getLogger("verbly.exceptions")

_EXTRACTION_ERROR_STATUS_MAP: dict[type[ExtractionError], int] = {
    InvalidURLError: 400,
    SSRFBlockedError: 400,
    UnsupportedContentTypeError: 422,
    ResponseTooLargeError: 413,
    TooManyRedirectsError: 400,
    FetchTimeoutError: 504,
    FetchConnectionError: 502,
    InsufficientContentError: 422,
}
_GRAMMAR_ERROR_STATUS_MAP: dict[type[GrammarEngineError], int] = {
    GrammarEngineTimeoutError: 504,
    GrammarEngineUnavailableError: 502,
    GrammarEngineResponseError: 502,
}

async def extraction_error_handler(request: Request, exc: ExtractionError) -> JSONResponse:
    status_code = _EXTRACTION_ERROR_STATUS_MAP.get(type(exc), 400)
    return JSONResponse(
        status_code=status_code,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )

async def grammar_error_handler(
    request: Request,
    exc: GrammarEngineError,
) -> JSONResponse:
    status_code = _GRAMMAR_ERROR_STATUS_MAP.get(type(exc), 502)
    return JSONResponse(
        status_code=status_code,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "ValidationError", "detail": jsonable_encoder(exc.errors())}
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "detail": exc.detail,
        },
        headers=exc.headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing request", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ExtractionError, extraction_error_handler)
    app.add_exception_handler(GrammarEngineError, grammar_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
