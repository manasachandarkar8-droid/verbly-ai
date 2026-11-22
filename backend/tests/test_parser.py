from __future__ import annotations

import pytest

from app.services.extraction.exceptions import InsufficientContentError
from app.services.extraction.parser import parse_html

_ARTICLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>A Long Article About Testing</title>
  <meta name="author" content="Jane Doe">
  <meta name="description" content="An article about software testing practices.">
</head>
<body>
  <nav>Home | About | Contact</nav>
  <article>
    <h1>A Long Article About Testing</h1>
    <p>Software testing is a critical part of building reliable systems.
    It helps catch regressions before they reach production and gives
    engineers confidence when making changes to a codebase.</p>
    <p>Good tests are deterministic, fast, and isolated from external
    systems such as the network or the filesystem where possible, which
    makes them trustworthy and repeatable across environments.</p>
  </article>
  <footer>Copyright 2026</footer>
</body>
</html>
"""

_THIN_HTML = "<html><body><p>hi</p></body></html>"


def test_parses_main_content_and_metadata():
    parsed = parse_html(_ARTICLE_HTML, url="https://example.com/article")
    assert "critical part of building reliable systems" in parsed.main_text
    assert parsed.word_count > 20
    assert parsed.character_count > 0
    assert parsed.title


def test_insufficient_content_raises():
    with pytest.raises(InsufficientContentError):
        parse_html(_THIN_HTML, url="https://example.com/empty")


def test_empty_html_raises():
    with pytest.raises(InsufficientContentError):
        parse_html("", url="https://example.com/empty")
