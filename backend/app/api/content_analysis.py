from __future__ import annotations
import logging

from dataclasses import asdict
from threading import BoundedSemaphore

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings

from app.schemas.content_analysis import (
    ContentAnalysisRequest,
    ContentAnalysisResponse,
)

from app.services.ai.provider import (
    AIProviderError,
    AIProviderConfigurationError,
    AIProviderUnavailableError,
    AIProviderQuotaExceededError,
    AIProviderPaidPlanRequiredError,
    AIProviderRequestError,
)

from app.services.content_analysis.service import (
    get_content_analysis_service,
)

logger = logging.getLogger(__name__)




router = APIRouter()

_settings = get_settings()

_analysis_semaphore = BoundedSemaphore(
    value=_settings.content_analysis_max_concurrency
)


@router.post(
    "/content-analysis",
    response_model=ContentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["content-analysis"],
    summary="Analyze website content using AI-powered NLP",
)
def analyze_content(
    request: ContentAnalysisRequest,
) -> ContentAnalysisResponse:
    """
    Analyze supplied website content using AI-powered analysis
    and deterministic Python-based quality and structure analysis.
    """

    acquired = _analysis_semaphore.acquire(
        timeout=_settings.content_analysis_busy_timeout_seconds
    )

    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Content analysis is currently busy. "
                "Please retry your request shortly."
            ),
            headers={"Retry-After": "5"},
        )

    try:
        result = get_content_analysis_service().analyze(
            main_text=request.main_text,
            title=request.title,
            description=request.description,
        )

        return ContentAnalysisResponse.model_validate(
            asdict(result)
        )

    except AIProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI content analysis is not configured correctly. "
                "Please contact the service administrator."
            ),
        ) from exc

    except AIProviderQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The available AI provider quota has been exhausted. "
                "Please try again later."
            ),
        ) from exc

    except AIProviderPaidPlanRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The backup AI provider requires paid usage. "
                "Paid usage is disabled."
            ),
        ) from exc

    except AIProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI content analysis is temporarily unavailable. "
                "Please try again later."
            ),
        ) from exc

    except AIProviderRequestError as exc:
        logger.error(
            "AI provider request failure. Error: %s | Underlying cause: %s",
            exc,
            exc.__cause__,
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI provider could not process the analysis request."
            ),
        ) from exc

    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI content analysis could not be completed.",
        ) from exc

    finally:
        _analysis_semaphore.release()