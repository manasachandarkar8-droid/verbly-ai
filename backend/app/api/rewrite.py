from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.rewrite import RewriteRequest, RewriteResponse

from app.services.rewrite.admission import (
    RewriteAdmissionError,
    RewriteAdmissionUnavailableError,
    RewriteCapacityExceededError,
)

from app.services.rewrite.circuit_breaker import (
    RewriteCircuitError,
    RewriteCircuitOpenError,
    RewriteCircuitUnavailableError,
)

from app.services.rewrite.cloudflare_client import (
    RewriteCloudflareAuthenticationError,
    RewriteCloudflareConfigurationError,
    RewriteCloudflareError,
    RewriteCloudflarePaidPlanRequiredError,
    RewriteCloudflareQuotaExceededError,
    RewriteCloudflareRequestError,
)

from app.services.rewrite.factory import get_rewrite_service

from app.services.rewrite.groq_client import (
    RewriteGroqAuthenticationError,
    RewriteGroqConfigurationError,
    RewriteGroqError,
    RewriteGroqRequestError,
)

from app.services.rewrite.provider import (
    RewriteDeadlineExceededError,
    RewriteProviderError,
    RewriteProviderResponseError,
    RewriteProvidersUnavailableError,
)

from app.services.rewrite.redis_client import (
    RewriteRedisConfigurationError,
    RewriteRedisError,
    RewriteRedisUnavailableError,
)


router = APIRouter()


@router.post(
    "/rewrite",
    response_model=RewriteResponse,
    status_code=status.HTTP_200_OK,
)
def rewrite(request: RewriteRequest) -> RewriteResponse:
    """Rewrite content using the configured Feature 6 AI providers."""

    try:
        service = get_rewrite_service()

        rewritten_text = service.rewrite(
    		main_text=request.main_text,
    		tone=request.tone,
    		custom_instruction=request.custom_instruction,
	)

        return RewriteResponse(
            rewritten_text=rewritten_text,
        )

    except RewriteCapacityExceededError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rewrite capacity is currently full. Please try again shortly.",
        )

    except (
        RewriteAdmissionUnavailableError,
        RewriteCircuitUnavailableError,
        RewriteRedisConfigurationError,
        RewriteRedisUnavailableError,
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rewrite infrastructure is temporarily unavailable.",
        )

    except RewriteDeadlineExceededError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The rewrite request exceeded its execution deadline.",
        )

    except RewriteProvidersUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The rewrite providers are temporarily unavailable.",
        )

    except RewriteCircuitOpenError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The rewrite provider is temporarily recovering.",
        )

    except (
        RewriteGroqConfigurationError,
        RewriteGroqAuthenticationError,
        RewriteCloudflareConfigurationError,
        RewriteCloudflareAuthenticationError,
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rewrite provider configuration is unavailable.",
        )

    except (
        RewriteCloudflareQuotaExceededError,
        RewriteCloudflarePaidPlanRequiredError,
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The free backup provider quota is unavailable. Paid usage is disabled.",
        )

    except (
        RewriteGroqRequestError,
        RewriteCloudflareRequestError,
        RewriteProviderResponseError,
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A rewrite provider returned an invalid response.",
        )

    except (
        RewriteAdmissionError,
        RewriteCircuitError,
        RewriteRedisError,
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rewrite infrastructure is temporarily unavailable.",
        )

    except (
        RewriteGroqError,
        RewriteCloudflareError,
        RewriteProviderError,
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The rewrite operation could not be completed.",
        )