"""
Structural HTML parsing for SEO analysis, using only the Python standard
library (``html.parser``).

This is deliberately independent of Feature 1's ``parser.py`` (which uses
trafilatura and discards structural/markup information such as headings,
images, links, canonical, robots, and Open Graph tags -- exactly the data
this feature needs). No Feature 1 file is imported or modified here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# Tags whose text content must never be counted as visible page text.
_NON_CONTENT_TEXT_TAGS = {"script", "style", "noscript", "template"}


@dataclass(frozen=True)
class HeadingTag:
    level: int  # 1-6
    text: str


@dataclass(frozen=True)
class ImageTag:
    src: str | None
    alt_present: bool  # True if an `alt` attribute exists at all
    alt_value: str  # "" if alt="" or attribute absent


@dataclass(frozen=True)
class LinkTag:
    href: str


@dataclass(frozen=True)
class ParsedSEOHtml:
    """Raw structural facts extracted from one HTML document."""

    titles: list[str] = field(default_factory=list)
    meta_descriptions: list[str] = field(default_factory=list)
    meta_robots: list[str] = field(default_factory=list)
    canonical_hrefs: list[str] = field(default_factory=list)
    og_tags: dict[str, list[str]] = field(default_factory=dict)
    headings: list[HeadingTag] = field(default_factory=list)
    images: list[ImageTag] = field(default_factory=list)
    links: list[LinkTag] = field(default_factory=list)
    body_text: str = ""


class _SEOHTMLParser(HTMLParser):
    """
    Single-pass collector. Kept intentionally "dumb": it records facts
    (what tags/attributes exist) without judging them -- all SEO
    judgment/thresholds live in ``analysis.py``.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titles: list[str] = []
        self.meta_descriptions: list[str] = []
        self.meta_robots: list[str] = []
        self.canonical_hrefs: list[str] = []
        self.og_tags: dict[str, list[str]] = {}
        self.headings: list[HeadingTag] = []
        self.images: list[ImageTag] = []
        self.links: list[LinkTag] = []

        self._body_text_parts: list[str] = []
        self._suppress_text_depth = 0  # inside script/style/etc.
        self._current_title_parts: list[str] | None = None
        self._current_heading_level: int | None = None
        self._current_heading_parts: list[str] = []

    # -- helpers --------------------------------------------------------
    @staticmethod
    def _attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        # HTML attribute names are case-insensitive; normalize to lower.
        # Values are left as-is (case can matter, e.g. URLs).
        return {(name or "").lower(): (value if value is not None else "") for name, value in attrs}

    # -- HTMLParser overrides --------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        a = self._attrs_dict(attrs)

        if tag in _NON_CONTENT_TEXT_TAGS:
            self._suppress_text_depth += 1
            return

        if tag == "title":
            self._current_title_parts = []
            return

        if tag in _HEADING_TAGS:
            self._current_heading_level = int(tag[1])
            self._current_heading_parts = []
            return

        if tag == "meta":
            name = a.get("name", "").strip().lower()
            prop = a.get("property", "").strip().lower()
            content = a.get("content", "")
            if name == "description":
                self.meta_descriptions.append(content)
            elif name == "robots":
                self.meta_robots.append(content)
            elif prop.startswith("og:"):
                self.og_tags.setdefault(prop, []).append(content)
            return

        if tag == "link":
            rel_value = a.get("rel", "").strip().lower()
            rel_tokens = rel_value.split()
            if "canonical" in rel_tokens:
                href = a.get("href", "")
                if href:
                    self.canonical_hrefs.append(href)
            return

        if tag == "img":
            src = a.get("src") or None
            alt_present = "alt" in a
            self.images.append(
                ImageTag(src=src, alt_present=alt_present, alt_value=a.get("alt", ""))
            )
            return

        if tag == "a":
            href = a.get("href", "")
            if href:
                self.links.append(LinkTag(href=href))
            return

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in _NON_CONTENT_TEXT_TAGS:
            if self._suppress_text_depth > 0:
                self._suppress_text_depth -= 1
            return

        if tag == "title":
            if self._current_title_parts is not None:
                self.titles.append("".join(self._current_title_parts).strip())
            self._current_title_parts = None
            return

        if tag in _HEADING_TAGS and self._current_heading_level is not None:
            text = "".join(self._current_heading_parts).strip()
            self.headings.append(HeadingTag(level=self._current_heading_level, text=text))
            self._current_heading_level = None
            self._current_heading_parts = []
            return

    def handle_data(self, data: str) -> None:
        if self._current_title_parts is not None:
            self._current_title_parts.append(data)
            return

        if self._current_heading_level is not None:
            self._current_heading_parts.append(data)
            # Heading text is also meaningful body content for keyword
            # extraction -- fall through to record it below as well.

        if self._suppress_text_depth > 0:
            return

        self._body_text_parts.append(data)

    def get_result(self) -> ParsedSEOHtml:
        return ParsedSEOHtml(
            titles=list(self.titles),
            meta_descriptions=list(self.meta_descriptions),
            meta_robots=list(self.meta_robots),
            canonical_hrefs=list(self.canonical_hrefs),
            og_tags={k: list(v) for k, v in self.og_tags.items()},
            headings=list(self.headings),
            images=list(self.images),
            links=list(self.links),
            body_text=" ".join(part for part in self._body_text_parts if part.strip()),
        )


def parse_seo_html(html: str) -> ParsedSEOHtml:
    """
    Parse raw HTML into structural facts needed for SEO analysis.

    Malformed/incomplete HTML is handled gracefully: ``html.parser`` does
    not raise on invalid markup, and unclosed tags simply stop
    contributing to their respective collections rather than crashing.
    """
    parser = _SEOHTMLParser()
    parser.feed(html or "")
    parser.close()
    return parser.get_result()
