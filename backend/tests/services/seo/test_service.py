import httpx
import pytest

from app.services.seo.service import analyze_seo

SAMPLE_HTML = """
<html>
<head>
  <title>Great Python Tutorial For Beginners</title>
  <meta name="description" content="Learn Python programming from scratch with this comprehensive beginner-friendly guide.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://example.com/tutorial">
  <meta property="og:title" content="Great Python Tutorial">
  <meta property="og:description" content="Learn Python programming.">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://example.com/tutorial">
  <meta property="og:image" content="https://example.com/img.png">
</head>
<body>
  <h1>Python Tutorial</h1>
  <h2>Getting Started</h2>
  <p>Python is a popular programming language. Python is easy to learn.
     This tutorial covers python basics for beginners.</p>
  <img src="a.png" alt="Python logo">
  <img src="b.png">
  <a href="/next-lesson">Next lesson</a>
  <a href="https://external-blog.com/post">External reference</a>
</body>
</html>
"""


def _transport_returning(html: str, *, status_code: int = 200, content_type: str = "text/html") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            content=html.encode("utf-8"),
            headers={"content-type": content_type},
        )

    return httpx.MockTransport(handler)


def test_analyze_seo_full_pipeline():
    result = analyze_seo(
        "https://example.com/tutorial",
        _transport=_transport_returning(SAMPLE_HTML),
    )

    assert result.title.value == "Great Python Tutorial For Beginners"
    assert result.meta_description.present is True
    assert result.headings.h1_count == 1
    assert result.canonical.value == "https://example.com/tutorial"
    assert result.robots.indexing_allowed is True
    assert result.open_graph.title == "Great Python Tutorial"
    assert result.images.total == 2
    assert result.images.with_alt_text == 1
    assert result.links.internal == 1
    assert result.links.external == 1
    keywords = {k.keyword for k in result.keywords}
    assert "python" in keywords


def test_analyze_seo_deterministic_across_calls():
    first = analyze_seo("https://example.com/tutorial", _transport=_transport_returning(SAMPLE_HTML))
    second = analyze_seo("https://example.com/tutorial", _transport=_transport_returning(SAMPLE_HTML))
    assert first == second


def test_analyze_seo_minimal_html():
    result = analyze_seo("https://example.com/", _transport=_transport_returning("<html></html>"))
    assert result.title.present is False
    assert result.meta_description.present is False
    assert result.headings.total == 0
    assert result.keywords == []


def test_analyze_seo_empty_html():
    result = analyze_seo("https://example.com/", _transport=_transport_returning(""))
    assert result.title.present is False
    assert result.keywords == []


def test_analyze_seo_respects_max_keywords():
    words = [
        "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
        "hotel", "india", "juliet",
    ]
    html = "<body>" + " ".join(f"<p>{w} {w}</p>" for w in words) + "</body>"
    result = analyze_seo("https://example.com/", max_keywords=3, _transport=_transport_returning(html))
    assert len(result.keywords) == 3


def test_analyze_seo_clamps_max_keywords_to_hard_max():
    result = analyze_seo(
        "https://example.com/tutorial",
        max_keywords=10_000,
        _transport=_transport_returning(SAMPLE_HTML),
    )
    from app.services.seo.constants import HARD_MAX_KEYWORDS

    assert len(result.keywords) <= HARD_MAX_KEYWORDS


def test_analyze_seo_uses_final_url_after_redirect():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(301, headers={"location": "https://example.com/final"})
        return httpx.Response(200, content=SAMPLE_HTML.encode(), headers={"content-type": "text/html"})

    result = analyze_seo("https://example.com/start", _transport=httpx.MockTransport(handler))
    assert result.final_url == "https://example.com/final"
    assert result.requested_url == "https://example.com/start"


def test_analyze_seo_propagates_fetch_errors_unchanged():
    from app.services.extraction.exceptions import UnsupportedContentTypeError

    transport = _transport_returning(SAMPLE_HTML, content_type="application/json")
    with pytest.raises(UnsupportedContentTypeError):
        analyze_seo("https://example.com/", _transport=transport)


def test_analyze_seo_issues_list_flattened_from_sections():
    result = analyze_seo("https://example.com/", _transport=_transport_returning("<html></html>"))
    # Missing title, missing description, no H1, no canonical, no robots,
    # missing OG tags should all surface in the flattened issues list.
    assert any("title" in issue.lower() for issue in result.issues)
    assert any("h1" in issue.lower() for issue in result.issues)
