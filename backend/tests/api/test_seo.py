import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.seo import router as seo_router
from app.core.exceptions import register_exception_handlers

SAMPLE_HTML = """
<html><head><title>A Reasonably Sized Page Title Here</title>
<meta name="description" content="A meta description long enough to satisfy the configured minimum length threshold for SEO."></head>
<body><h1>Heading</h1><p>Some page content about testing and quality.</p></body></html>
"""


@pytest.fixture()
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(seo_router)
    register_exception_handlers(application)
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _mock_fetch_html(monkeypatch, html: str, *, final_url: str | None = None, status_code: int = 200):
    from app.services.extraction.fetcher import FetchResult

    def fake_fetch_html(url: str, *, _transport=None):
        return FetchResult(
            url=url,
            final_url=final_url or url,
            status_code=status_code,
            content_type="text/html",
            html=html,
        )

    monkeypatch.setattr("app.services.seo.service.fetch_html", fake_fetch_html)


def test_seo_endpoint_success(client: TestClient, monkeypatch):
    _mock_fetch_html(monkeypatch, SAMPLE_HTML)

    response = client.post("/seo", json={"url": "https://example.com/page"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"]["present"] is True
    assert body["requested_url"] == "https://example.com/page"
    assert "keywords" in body
    assert "issues" in body


def test_seo_endpoint_invalid_url_returns_422(client: TestClient):
    response = client.post("/seo", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_seo_endpoint_missing_url_field_returns_422(client: TestClient):
    response = client.post("/seo", json={})
    assert response.status_code == 422


def test_seo_endpoint_max_keywords_validation(client: TestClient, monkeypatch):
    _mock_fetch_html(monkeypatch, SAMPLE_HTML)
    response = client.post("/seo", json={"url": "https://example.com/page", "max_keywords": 0})
    assert response.status_code == 422


def test_seo_endpoint_propagates_extraction_errors_as_json(client: TestClient, monkeypatch):
    from app.services.extraction.exceptions import FetchTimeoutError

    def fake_fetch_html(url: str, *, _transport=None):
        raise FetchTimeoutError("timed out")

    monkeypatch.setattr("app.services.seo.service.fetch_html", fake_fetch_html)

    response = client.post("/seo", json={"url": "https://example.com/page"})
    assert response.status_code == 504
    assert response.json()["error"] == "FetchTimeoutError"


def test_seo_endpoint_response_matches_schema_shape(client: TestClient, monkeypatch):
    _mock_fetch_html(monkeypatch, SAMPLE_HTML)
    response = client.post("/seo", json={"url": "https://example.com/page"})
    body = response.json()
    for key in (
        "requested_url",
        "final_url",
        "title",
        "meta_description",
        "headings",
        "keywords",
        "keyword_relationships",
        "url_analysis",
        "images",
        "links",
        "canonical",
        "robots",
        "open_graph",
        "issues",
    ):
        assert key in body


def test_seo_endpoint_default_max_keywords_applied(client: TestClient, monkeypatch):
    words = [f"keyword{chr(ord('a') + i)}" for i in range(20)]
    html = "<body>" + " ".join(f"<p>{w}</p>" for w in words) + "</body>"
    _mock_fetch_html(monkeypatch, html)
    response = client.post("/seo", json={"url": "https://example.com/page"})
    from app.services.seo.constants import DEFAULT_MAX_KEYWORDS

    assert len(response.json()["keywords"]) == DEFAULT_MAX_KEYWORDS
