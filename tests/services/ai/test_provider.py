import pytest

from unittest.mock import MagicMock

from app.services.ai.provider import (
    AIProvider,
    AIProviderConfigurationError,
    AIProviderUnavailableError,
    AIProviderQuotaExceededError,
    AIProviderPaidPlanRequiredError,
    AIProviderRequestError,
)

from app.services.ai.groq_client import (
    GroqConfigurationError,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqConnectionError,
    GroqServerError,
    GroqRequestError,
    GroqResponseError,
)

from app.services.ai.cloudflare_client import (
    CloudflareConfigurationError,
    CloudflareAuthenticationError,
    CloudflarePaidPlanRequiredError,
    CloudflareQuotaExceededError,
    CloudflareRateLimitError,
    CloudflareTimeoutError,
    CloudflareConnectionError,
    CloudflareServerError,
    CloudflareRequestError,
    CloudflareResponseError,
)
from time import monotonic

from app.services.ai.provider import AIProviderDeadlineExceededError

@pytest.fixture
def valid_response():
    return {
        "summary_sentence_indices": [0],
        "topics": [
            {"phrase": "artificial intelligence", "score": 0.95}
        ],
        "key_concepts": [
            {"phrase": "machine learning", "score": 0.91}
        ],
        "entities": [
            {"text": "Bangalore", "label": "GPE"}
        ],
        "intent_scores": [
            {"label": "informational", "score": 0.85},
            {"label": "commercial", "score": 0.05},
            {"label": "transactional", "score": 0.05},
            {"label": "navigational", "score": 0.05},
        ],
        "semantic_metrics": {
            "semantic_coherence": 0.85,
            "semantic_redundancy": 0.15,
            "concept_diversity": 0.75,
        },
    }

@pytest.fixture
def messages():
    return [
        {"role": "user", "content": "Analyze this article."}
    ]


@pytest.fixture
def schema():
    return {
        "type": "object",
        "properties": {},
    }


@pytest.fixture
def clients(valid_response):
    groq = MagicMock()
    cloudflare = MagicMock()

    groq.create_structured_completion.return_value = valid_response
    cloudflare.create_structured_completion.return_value = valid_response

    return groq, cloudflare


def make_provider(clients):
    groq, cloudflare = clients

    return AIProvider(
        groq_client_factory=lambda: groq,
        cloudflare_client_factory=lambda: cloudflare,
    )


def analyze(provider, messages, schema):
    return provider.analyze(
        messages=messages,
        schema_name="content_analysis",
        json_schema=schema,
    )


def test_groq_success_does_not_initialize_cloudflare(
    clients, messages, schema
):
    groq, cloudflare = clients

    cloudflare_factory = MagicMock(return_value=cloudflare)

    provider = AIProvider(
        groq_client_factory=lambda: groq,
        cloudflare_client_factory=cloudflare_factory,
    )

    result = analyze(provider, messages, schema)

    assert result.summary_sentence_indices == [0]
    groq.create_structured_completion.assert_called_once()
    cloudflare_factory.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        GroqRateLimitError("Rate limit"),
        GroqTimeoutError("Timeout"),
        GroqConnectionError("Connection failed"),
        GroqServerError("Server error"),
        GroqResponseError("Invalid response"),
    ],
)
def test_eligible_groq_failures_trigger_cloudflare(
    clients, messages, schema, error
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = error

    provider = make_provider(clients)

    result = analyze(provider, messages, schema)

    assert result.summary_sentence_indices == [0]
    groq.create_structured_completion.assert_called_once()
    cloudflare.create_structured_completion.assert_called_once()


@pytest.mark.parametrize(
    "error",
    [
        GroqConfigurationError("Missing configuration"),
        GroqAuthenticationError("Invalid credentials"),
        GroqRequestError("Invalid request"),
    ],
)
def test_non_retriable_groq_failures_do_not_trigger_cloudflare(
    clients, messages, schema, error
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = error

    provider = make_provider(clients)

    with pytest.raises(
        (
            AIProviderConfigurationError,
            AIProviderRequestError,
        )
    ):
        analyze(provider, messages, schema)

    cloudflare.create_structured_completion.assert_not_called()


def test_invalid_groq_schema_response_triggers_cloudflare(
    clients, valid_response, messages, schema
):
    groq, cloudflare = clients

    invalid_response = valid_response.copy()
    invalid_response["unexpected_field"] = "invalid"

    groq.create_structured_completion.return_value = invalid_response

    provider = make_provider(clients)

    result = analyze(provider, messages, schema)

    assert result.summary_sentence_indices == [0]
    cloudflare.create_structured_completion.assert_called_once()


@pytest.mark.parametrize(
    "error, expected_exception",
    [
        (
            CloudflarePaidPlanRequiredError("Paid plan required"),
            AIProviderPaidPlanRequiredError,
        ),
        (
            CloudflareQuotaExceededError("Free quota exhausted"),
            AIProviderQuotaExceededError,
        ),
        (
            CloudflareConfigurationError("Missing configuration"),
            AIProviderConfigurationError,
        ),
        (
            CloudflareAuthenticationError("Invalid credentials"),
            AIProviderConfigurationError,
        ),
        (
            CloudflareRequestError("Invalid request"),
            AIProviderRequestError,
        ),
    ],
)
def test_cloudflare_failures_are_mapped_correctly(
    clients, messages, schema, error, expected_exception
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = (
        GroqRateLimitError("Primary rate limit")
    )

    cloudflare.create_structured_completion.side_effect = error

    provider = make_provider(clients)

    with pytest.raises(expected_exception):
        analyze(provider, messages, schema)

    groq.create_structured_completion.assert_called_once()
    cloudflare.create_structured_completion.assert_called_once()        


@pytest.mark.parametrize(
    "error",
    [
        CloudflareRateLimitError("Rate limit"),
        CloudflareTimeoutError("Timeout"),
        CloudflareConnectionError("Connection failed"),
        CloudflareServerError("Server error"),
        CloudflareResponseError("Invalid response"),
    ],
)
def test_cloudflare_transient_failures_return_unavailable(
    clients, messages, schema, error
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = (
        GroqRateLimitError("Primary rate limit")
    )

    cloudflare.create_structured_completion.side_effect = error

    provider = make_provider(clients)

    with pytest.raises(AIProviderUnavailableError):
        analyze(provider, messages, schema)


def test_invalid_cloudflare_response_is_rejected(
    clients, valid_response, messages, schema
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = (
        GroqRateLimitError("Primary rate limit")
    )

    invalid_response = valid_response.copy()
    invalid_response["unexpected_field"] = "invalid"

    cloudflare.create_structured_completion.return_value = (
        invalid_response
    )

    provider = make_provider(clients)

    with pytest.raises(AIProviderUnavailableError):
        analyze(provider, messages, schema)


def test_provider_reuses_initialized_clients(
    clients, messages, schema
):
    groq, cloudflare = clients

    provider = make_provider(clients)

    analyze(provider, messages, schema)
    analyze(provider, messages, schema)

    assert groq.create_structured_completion.call_count == 2
    assert cloudflare.create_structured_completion.call_count == 0


from time import monotonic

from app.services.ai.provider import AIProviderDeadlineExceededError


def test_groq_receives_remaining_deadline(
    clients, messages, schema
):
    groq, cloudflare = clients

    provider = make_provider(clients)
    deadline = monotonic() + 10

    analyze_result = provider.analyze(
        messages=messages,
        schema_name="content_analysis",
        json_schema=schema,
        deadline=deadline,
    )

    assert analyze_result is not None

    kwargs = groq.create_structured_completion.call_args.kwargs

    assert 0 < kwargs["timeout_seconds"] <= 10
    cloudflare.create_structured_completion.assert_not_called()


def test_cloudflare_receives_remaining_deadline(
    clients, messages, schema
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = (
        GroqRateLimitError("Rate limit")
    )

    provider = make_provider(clients)
    deadline = monotonic() + 10

    result = provider.analyze(
        messages=messages,
        schema_name="content_analysis",
        json_schema=schema,
        deadline=deadline,
    )

    assert result is not None

    kwargs = cloudflare.create_structured_completion.call_args.kwargs

    assert 0 < kwargs["timeout_seconds"] <= 10


def test_expired_deadline_prevents_cloudflare_fallback(
    clients, messages, schema
):
    groq, cloudflare = clients

    groq.create_structured_completion.side_effect = (
        GroqRateLimitError("Rate limit")
    )

    provider = make_provider(clients)
    expired_deadline = monotonic() - 1

    with pytest.raises(AIProviderDeadlineExceededError):
        provider.analyze(
            messages=messages,
            schema_name="content_analysis",
            json_schema=schema,
            deadline=expired_deadline,
        )

    groq.create_structured_completion.assert_not_called()
    cloudflare.create_structured_completion.assert_not_called()


def test_late_provider_response_is_rejected(
    clients, messages, schema, valid_response
):
    groq, cloudflare = clients

    provider = make_provider(clients)

    deadline = monotonic() + 0.05

    def delayed_response(**kwargs):
        import time
        time.sleep(0.1)
        return valid_response

    groq.create_structured_completion.side_effect = delayed_response

    with pytest.raises(AIProviderDeadlineExceededError):
        provider.analyze(
            messages=messages,
            schema_name="content_analysis",
            json_schema=schema,
            deadline=deadline,
        )

    cloudflare.create_structured_completion.assert_not_called()
