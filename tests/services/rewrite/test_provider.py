from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.rewrite.admission import (
    RewriteAdmissionUnavailableError,
)

from app.services.rewrite.circuit_breaker import (
    RewriteCircuitOpenError,
)

from app.services.rewrite.cloudflare_client import (
    RewriteCloudflareAuthenticationError,
    RewriteCloudflareQuotaExceededError,
    RewriteCloudflareTimeoutError,
)

from app.services.rewrite.groq_client import (
    RewriteGroqAuthenticationError,
    RewriteGroqConnectionError,
    RewriteGroqRateLimitError,
    RewriteGroqTimeoutError,
)

from app.services.rewrite.provider import (
    RewriteDeadlineExceededError,
    RewriteProvider,
    RewriteProviderResponseError,
    RewriteProvidersUnavailableError,
)

from app.services.rewrite.cloudflare_client import (
    RewriteCloudflarePaidPlanRequiredError,
)

from app.services.rewrite.groq_client import (
    RewriteGroqRequestError,
)


@pytest.fixture
def dependencies():
    lease = SimpleNamespace(token="test-lease")

    groq = Mock()
    cloudflare = Mock()
    admission = Mock()
    circuits = Mock()

    admission.acquire.return_value = lease

    circuits.allow_request.side_effect = lambda provider: (
        SimpleNamespace(
            provider=provider,
            is_probe=False,
        )
    )

    provider = RewriteProvider(
        groq_client=groq,
        cloudflare_client=cloudflare,
        admission_controller=admission,
        circuit_breaker=circuits,
        deadline_seconds=75.0,
    )

    return SimpleNamespace(
        provider=provider,
        groq=groq,
        cloudflare=cloudflare,
        admission=admission,
        circuits=circuits,
        lease=lease,
    )


@pytest.fixture
def messages():
    return [
        {
            "role": "system",
            "content": "Rewrite the content clearly.",
        },
        {
            "role": "user",
            "content": "This is the original content.",
        },
    ]


# --------------------------------------------------
# Primary provider
# --------------------------------------------------

def test_groq_success_does_not_call_cloudflare(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.return_value = "Rewritten by Groq."

    result = dependencies.provider.rewrite(messages=messages)

    assert result == "Rewritten by Groq."
    dependencies.groq.rewrite.assert_called_once()
    dependencies.cloudflare.rewrite.assert_not_called()

    dependencies.circuits.record_success.assert_called_once()
    dependencies.circuits.record_failure.assert_not_called()


# --------------------------------------------------
# Groq to Cloudflare fallback
# --------------------------------------------------

@pytest.mark.parametrize(
    "error",
    [
        RewriteGroqTimeoutError("timeout"),
        RewriteGroqConnectionError("connection"),
        RewriteGroqRateLimitError("rate limit"),
    ],
)
def test_groq_transient_failure_triggers_cloudflare(
    dependencies,
    messages,
    error,
):
    dependencies.groq.rewrite.side_effect = error
    dependencies.cloudflare.rewrite.return_value = (
        "Rewritten by Cloudflare."
    )

    result = dependencies.provider.rewrite(messages=messages)

    assert result == "Rewritten by Cloudflare."

    dependencies.groq.rewrite.assert_called_once()
    dependencies.cloudflare.rewrite.assert_called_once()

    assert dependencies.circuits.record_failure.call_count == 1
    assert dependencies.circuits.record_success.call_count == 1


def test_groq_authentication_failure_does_not_trigger_fallback(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = (
        RewriteGroqAuthenticationError("authentication failed")
    )

    with pytest.raises(RewriteGroqAuthenticationError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.cloudflare.rewrite.assert_not_called()
    dependencies.circuits.record_failure.assert_not_called()


def test_open_groq_circuit_uses_cloudflare(
    dependencies,
    messages,
):
    def allow_request(provider):
        if provider == "groq":
            raise RewriteCircuitOpenError("groq", 1000)

        return SimpleNamespace(
            provider=provider,
            is_probe=False,
        )

    dependencies.circuits.allow_request.side_effect = allow_request

    dependencies.cloudflare.rewrite.return_value = (
        "Cloudflare backup response."
    )

    result = dependencies.provider.rewrite(messages=messages)

    assert result == "Cloudflare backup response."

    dependencies.groq.rewrite.assert_not_called()
    dependencies.cloudflare.rewrite.assert_called_once()


# --------------------------------------------------
# Backup provider
# --------------------------------------------------

def test_cloudflare_quota_exhaustion_stops_processing(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    dependencies.cloudflare.rewrite.side_effect = (
        RewriteCloudflareQuotaExceededError(
            "Daily free quota exhausted."
        )
    )

    with pytest.raises(RewriteCloudflareQuotaExceededError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.cloudflare.rewrite.assert_called_once()


def test_cloudflare_authentication_failure_stops_processing(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    dependencies.cloudflare.rewrite.side_effect = (
        RewriteCloudflareAuthenticationError(
            "Cloudflare authentication failed."
        )
    )

    with pytest.raises(RewriteCloudflareAuthenticationError):
        dependencies.provider.rewrite(messages=messages)


def test_cloudflare_failure_returns_controlled_error(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    dependencies.cloudflare.rewrite.side_effect = (
        RewriteCloudflareTimeoutError("Cloudflare timeout")
    )

    with pytest.raises(RewriteProvidersUnavailableError):
        dependencies.provider.rewrite(messages=messages)


def test_open_cloudflare_circuit_returns_controlled_error(
    dependencies,
    messages,
):
    def allow_request(provider):
        if provider == "cloudflare":
            raise RewriteCircuitOpenError("cloudflare", 1000)

        return SimpleNamespace(
            provider=provider,
            is_probe=False,
        )

    dependencies.circuits.allow_request.side_effect = allow_request

    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    with pytest.raises(RewriteProvidersUnavailableError):
        dependencies.provider.rewrite(messages=messages)


# --------------------------------------------------
# Admission control
# --------------------------------------------------

def test_admission_lease_released_after_success(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.return_value = "Successful rewrite."

    dependencies.provider.rewrite(messages=messages)

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )


def test_admission_lease_released_after_failure(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = (
        RewriteGroqAuthenticationError("Invalid credentials")
    )

    with pytest.raises(RewriteGroqAuthenticationError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )


def test_admission_failure_prevents_provider_calls(
    dependencies,
    messages,
):
    dependencies.admission.acquire.side_effect = (
        RewriteAdmissionUnavailableError("Redis unavailable")
    )

    with pytest.raises(RewriteAdmissionUnavailableError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.groq.rewrite.assert_not_called()
    dependencies.cloudflare.rewrite.assert_not_called()


# --------------------------------------------------
# Input validation
# --------------------------------------------------

def test_empty_messages_are_rejected(dependencies):
    with pytest.raises(ValueError):
        dependencies.provider.rewrite(messages=[])

    dependencies.admission.acquire.assert_not_called()


def test_invalid_message_role_is_rejected(
    dependencies,
):
    with pytest.raises(ValueError):
        dependencies.provider.rewrite(
            messages=[
                {
                    "role": "invalid",
                    "content": "Test content.",
                }
            ]
        )

    dependencies.admission.acquire.assert_not_called()

@pytest.mark.parametrize(
    "invalid_role",
    [
        [],
        {},
        123,
        None,
    ],
)
def test_non_string_message_role_is_rejected(
    dependencies,
    invalid_role,
):
    with pytest.raises(ValueError):
        dependencies.provider.rewrite(
            messages=[
                {
                    "role": invalid_role,
                    "content": "Test content.",
                }
            ]
        )

    dependencies.admission.acquire.assert_not_called()
    dependencies.groq.rewrite.assert_not_called()
    dependencies.cloudflare.rewrite.assert_not_called()

def test_deadline_must_be_positive():
    with pytest.raises(ValueError):
        RewriteProvider(
            groq_client=Mock(),
            cloudflare_client=Mock(),
            admission_controller=Mock(),
            circuit_breaker=Mock(),
            deadline_seconds=0,
        )

def test_groq_invalid_request_does_not_trigger_fallback(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = RewriteGroqRequestError(
        "Invalid request"
    )

    with pytest.raises(RewriteGroqRequestError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.cloudflare.rewrite.assert_not_called()


def test_cloudflare_paid_plan_error_stops_processing(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    dependencies.cloudflare.rewrite.side_effect = (
        RewriteCloudflarePaidPlanRequiredError(
            "Paid plan required"
        )
    )

    with pytest.raises(RewriteCloudflarePaidPlanRequiredError):
        dependencies.provider.rewrite(messages=messages)


def test_deadline_exceeded_prevents_provider_request(
    dependencies,
    messages,
    monkeypatch,
):
    import app.services.rewrite.provider as provider_module

    timestamps = iter([100.0, 100.5])

    monkeypatch.setattr(
        provider_module.time,
        "monotonic",
        lambda: next(timestamps),
    )

    dependencies.provider._deadline_seconds = 0.25

    with pytest.raises(RewriteDeadlineExceededError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.groq.rewrite.assert_not_called()
    dependencies.cloudflare.rewrite.assert_not_called()

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )        


def test_deadline_exceeded_after_provider_response(
    dependencies,
    messages,
    monkeypatch,
):
    import app.services.rewrite.provider as provider_module

    timestamps = iter([
    100.0,  # Overall deadline starts.
    100.0,  # Immediately after admission acquisition.
    100.0,  # Before circuit permission.
    100.0,  # Before provider request.
    100.3,  # Provider response arrives after deadline.
    ])

    monkeypatch.setattr(
        provider_module.time,
        "monotonic",
        lambda: next(timestamps),
    )

    dependencies.provider._deadline_seconds = 0.25
    dependencies.groq.rewrite.return_value = "Valid rewritten content."

    with pytest.raises(RewriteDeadlineExceededError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.groq.rewrite.assert_called_once()
    dependencies.cloudflare.rewrite.assert_not_called()

    dependencies.circuits.record_success.assert_not_called()

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )    

def test_invalid_groq_response_triggers_cloudflare_fallback(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.return_value = ""

    dependencies.cloudflare.rewrite.return_value = (
        "Rewritten successfully by Cloudflare."
    )

    result = dependencies.provider.rewrite(messages=messages)

    assert result == "Rewritten successfully by Cloudflare."

    dependencies.groq.rewrite.assert_called_once()
    dependencies.cloudflare.rewrite.assert_called_once()

    assert dependencies.circuits.record_failure.call_count == 1
    assert dependencies.circuits.record_success.call_count == 1

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )


def test_invalid_cloudflare_response_returns_controlled_error(
    dependencies,
    messages,
):
    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    dependencies.cloudflare.rewrite.return_value = ""

    with pytest.raises(RewriteProvidersUnavailableError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.groq.rewrite.assert_called_once()
    dependencies.cloudflare.rewrite.assert_called_once()

    assert dependencies.circuits.record_failure.call_count == 2
    dependencies.circuits.record_success.assert_not_called()

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )    

# --------------------------------------------------
# Half-open circuit breaker integration
# --------------------------------------------------

def test_successful_half_open_groq_probe_closes_circuit(
    dependencies,
    messages,
):
    groq_probe = SimpleNamespace(
        provider="groq",
        generation=1,
        probe_token="groq-probe-token",
        is_probe=True,
    )

    dependencies.circuits.allow_request.side_effect = None
    dependencies.circuits.allow_request.return_value = groq_probe
    dependencies.groq.rewrite.return_value = "Successful rewrite."

    result = dependencies.provider.rewrite(messages=messages)

    assert result == "Successful rewrite."

    dependencies.circuits.record_success.assert_called_once_with(
        groq_probe
    )

    dependencies.circuits.record_failure.assert_not_called()
    dependencies.circuits.abandon_probe.assert_not_called()

    dependencies.cloudflare.rewrite.assert_not_called()


def test_transient_half_open_groq_failure_triggers_cloudflare(
    dependencies,
    messages,
):
    groq_probe = SimpleNamespace(
        provider="groq",
        generation=1,
        probe_token="groq-probe-token",
        is_probe=True,
    )

    cloudflare_permit = SimpleNamespace(
        provider="cloudflare",
        generation=0,
        is_probe=False,
    )

    def allow_request(provider):
        if provider == "groq":
            return groq_probe
        return cloudflare_permit

    dependencies.circuits.allow_request.side_effect = allow_request

    dependencies.groq.rewrite.side_effect = RewriteGroqTimeoutError(
        "Groq timeout"
    )

    dependencies.cloudflare.rewrite.return_value = (
        "Successful Cloudflare rewrite."
    )

    result = dependencies.provider.rewrite(messages=messages)

    assert result == "Successful Cloudflare rewrite."

    dependencies.circuits.record_failure.assert_called_once_with(
        groq_probe
    )

    dependencies.circuits.record_success.assert_called_once_with(
        cloudflare_permit
    )

    dependencies.circuits.abandon_probe.assert_not_called()


def test_authentication_failure_abandons_half_open_groq_probe(
    dependencies,
    messages,
):
    groq_probe = SimpleNamespace(
        provider="groq",
        generation=1,
        probe_token="groq-probe-token",
        is_probe=True,
    )

    dependencies.circuits.allow_request.side_effect = None
    dependencies.circuits.allow_request.return_value = groq_probe

    dependencies.groq.rewrite.side_effect = (
        RewriteGroqAuthenticationError(
            "Authentication failed."
        )
    )

    with pytest.raises(RewriteGroqAuthenticationError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.circuits.abandon_probe.assert_called_once_with(
        groq_probe
    )

    dependencies.circuits.record_failure.assert_not_called()
    dependencies.circuits.record_success.assert_not_called()

    dependencies.cloudflare.rewrite.assert_not_called()


def test_deadline_exceeded_abandons_half_open_groq_probe(
    dependencies,
    messages,
    monkeypatch,
):
    import app.services.rewrite.provider as provider_module

    groq_probe = SimpleNamespace(
        provider="groq",
        generation=1,
        probe_token="groq-probe-token",
        is_probe=True,
    )

    dependencies.circuits.allow_request.side_effect = None
    dependencies.circuits.allow_request.return_value = groq_probe

    timestamps = iter([
        100.0,  # Overall deadline starts.
        100.0,  # Immediately after admission acquisition.
        100.0,  # Before circuit permission.
        100.0,  # Before provider request.
        100.3,  # Provider response arrives after deadline.
    ])

    monkeypatch.setattr(
        provider_module.time,
        "monotonic",
        lambda: next(timestamps),
    )

    dependencies.provider._deadline_seconds = 0.25

    dependencies.groq.rewrite.return_value = (
        "Late provider response."
    )

    with pytest.raises(RewriteDeadlineExceededError):
        dependencies.provider.rewrite(messages=messages)

    dependencies.groq.rewrite.assert_called_once()
    dependencies.cloudflare.rewrite.assert_not_called()

    dependencies.circuits.abandon_probe.assert_called_once_with(
        groq_probe
    )

    dependencies.circuits.record_failure.assert_not_called()
    dependencies.circuits.record_success.assert_not_called()

    dependencies.admission.release.assert_called_once_with(
        dependencies.lease
    )
