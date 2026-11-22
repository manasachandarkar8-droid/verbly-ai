"""Feature 3 orchestration: fetch -> parse -> deterministic SEO analysis."""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from app.services.extraction.fetcher import fetch_html
from app.services.seo.analysis import (
    CanonicalAnalysis,
    HeadingsAnalysis,
    ImagesAnalysis,
    KeywordRelationship,
    LinksAnalysis,
    MetaDescriptionAnalysis,
    OpenGraphAnalysis,
    RobotsAnalysis,
    TitleAnalysis,
    UrlAnalysis,
    analyze_canonical,
    analyze_headings,
    analyze_images,
    analyze_keyword_relationships,
    analyze_links,
    analyze_meta_description,
    analyze_open_graph,
    analyze_robots,
    analyze_title,
    analyze_url,
)
from app.services.seo.constants import DEFAULT_MAX_KEYWORDS, HARD_MAX_KEYWORDS
from app.services.seo.html_parser import parse_seo_html
from app.services.seo.keywords import KeywordStat, extract_keywords


@dataclass(frozen=True)
class SEOAnalysisResult:
    requested_url: str
    final_url: str
    title: TitleAnalysis
    meta_description: MetaDescriptionAnalysis
    headings: HeadingsAnalysis
    keywords: list[KeywordStat]
    keyword_relationships: list[KeywordRelationship]
    url_analysis: UrlAnalysis
    images: ImagesAnalysis
    links: LinksAnalysis
    canonical: CanonicalAnalysis
    robots: RobotsAnalysis
    open_graph: OpenGraphAnalysis
    issues: list[str] = field(default_factory=list)


def _collect_issues(*analyses: object) -> list[str]:
    """Flatten each section's own `.issues` list into one deterministic,
    ordered list. Deliberately not scored or weighted -- see module note
    on scoring in the schema layer."""
    collected: list[str] = []
    for analysis in analyses:
        collected.extend(getattr(analysis, "issues", []))
    return collected


def analyze_seo(
    url: str,
    *,
    max_keywords: int = DEFAULT_MAX_KEYWORDS,
    _transport: httpx.BaseTransport | None = None,
) -> SEOAnalysisResult:
    """
    Fetch ``url`` (reusing Feature 1's hardened ``fetch_html``) and run
    deterministic SEO analysis against the raw HTML.

    ``_transport`` is the same internal test seam already used by
    ``fetch_html`` itself (see ``app.services.extraction.fetcher``);
    production code should never pass it.

    Any exception raised by ``fetch_html`` (SSRF blocked, timeout, too
    large, unsupported content type, etc.) propagates unchanged -- these
    are ``ExtractionError`` subclasses already handled by the existing
    centralized exception handler, so no SEO-specific exception type is
    needed here.
    """
    max_keywords = max(1, min(max_keywords, HARD_MAX_KEYWORDS))

    fetch_result = fetch_html(url, _transport=_transport)
    parsed = parse_seo_html(fetch_result.html)

    title_analysis = analyze_title(parsed.titles)
    meta_description_analysis = analyze_meta_description(parsed.meta_descriptions)
    headings_analysis = analyze_headings(parsed.headings)
    url_analysis = analyze_url(fetch_result.final_url)
    images_analysis = analyze_images(parsed.images)
    links_analysis = analyze_links(parsed.links, page_url=fetch_result.final_url)
    canonical_analysis = analyze_canonical(parsed.canonical_hrefs, page_url=fetch_result.final_url)
    robots_analysis = analyze_robots(parsed.meta_robots)
    open_graph_analysis = analyze_open_graph(parsed.og_tags)

    keywords = extract_keywords(parsed.body_text, max_keywords=max_keywords)
    keyword_relationships = analyze_keyword_relationships(
        keywords,
        title=title_analysis.value,
        meta_description=meta_description_analysis.value,
        body_text=parsed.body_text,
    )

    issues = _collect_issues(
        title_analysis,
        meta_description_analysis,
        headings_analysis,
        url_analysis,
        images_analysis,
        links_analysis,
        canonical_analysis,
        robots_analysis,
        open_graph_analysis,
    )

    return SEOAnalysisResult(
        requested_url=url,
        final_url=fetch_result.final_url,
        title=title_analysis,
        meta_description=meta_description_analysis,
        headings=headings_analysis,
        keywords=keywords,
        keyword_relationships=keyword_relationships,
        url_analysis=url_analysis,
        images=images_analysis,
        links=links_analysis,
        canonical=canonical_analysis,
        robots=robots_analysis,
        open_graph=open_graph_analysis,
        issues=issues,
    )
