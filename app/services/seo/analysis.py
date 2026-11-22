"""
Pure, deterministic SEO judgment functions.

``html_parser.py`` collects raw facts; ``keywords.py`` extracts keyword
statistics; this module turns those facts into typed analysis results with
explicit, documented thresholds (see ``constants.py``). No network or I/O
happens here, which is what makes these functions trivial to test
exhaustively and to reason about.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlsplit

from app.services.seo.constants import (
    KNOWN_TRACKING_PARAMS,
    META_DESCRIPTION_MAX_LENGTH,
    META_DESCRIPTION_MIN_LENGTH,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
    URL_RECOMMENDED_MAX_LENGTH,
)
from app.services.seo.html_parser import HeadingTag, ImageTag, LinkTag
from app.services.seo.keywords import KeywordStat

# --- Title -------------------------------------------------------------


@dataclass(frozen=True)
class TitleAnalysis:
    value: str | None
    present: bool
    length: int
    length_status: str  # "too_short" | "good" | "too_long" | "missing"
    duplicate_tags_found: bool
    issues: list[str] = field(default_factory=list)


def analyze_title(titles: list[str]) -> TitleAnalysis:
    non_empty_titles = [t for t in titles if t.strip()]
    duplicate = len(titles) > 1

    if not non_empty_titles:
        issues = ["Missing <title> tag or title is empty."]
        if titles and not non_empty_titles:
            issues.append("A <title> tag is present but contains no meaningful text.")
        if duplicate:
            issues.append(f"Found {len(titles)} <title> tags; there should be exactly one.")
        return TitleAnalysis(
            value=None,
            present=False,
            length=0,
            length_status="missing",
            duplicate_tags_found=duplicate,
            issues=issues,
        )

    value = non_empty_titles[0]
    length = len(value)
    issues: list[str] = []

    if length < TITLE_MIN_LENGTH:
        status = "too_short"
        issues.append(
            f"Title is {length} characters; recommended minimum is "
            f"{TITLE_MIN_LENGTH} to make good use of SERP space."
        )
    elif length > TITLE_MAX_LENGTH:
        status = "too_long"
        issues.append(
            f"Title is {length} characters; recommended maximum is "
            f"{TITLE_MAX_LENGTH} before search engines commonly truncate it."
        )
    else:
        status = "good"

    if duplicate:
        issues.append(f"Found {len(titles)} <title> tags; there should be exactly one.")

    return TitleAnalysis(
        value=value,
        present=True,
        length=length,
        length_status=status,
        duplicate_tags_found=duplicate,
        issues=issues,
    )


# --- Meta description --------------------------------------------------


@dataclass(frozen=True)
class MetaDescriptionAnalysis:
    value: str | None
    present: bool
    length: int
    length_status: str  # "too_short" | "good" | "too_long" | "missing"
    duplicate_tags_found: bool
    issues: list[str] = field(default_factory=list)


def analyze_meta_description(descriptions: list[str]) -> MetaDescriptionAnalysis:
    non_empty = [d for d in descriptions if d.strip()]
    duplicate = len(descriptions) > 1

    if not non_empty:
        issues = ["Missing <meta name=\"description\"> tag or its content is empty."]
        if duplicate:
            issues.append(
                f"Found {len(descriptions)} meta description tags; there should be exactly one."
            )
        return MetaDescriptionAnalysis(
            value=None,
            present=False,
            length=0,
            length_status="missing",
            duplicate_tags_found=duplicate,
            issues=issues,
        )

    value = non_empty[0]
    length = len(value)
    issues = []

    if length < META_DESCRIPTION_MIN_LENGTH:
        status = "too_short"
        issues.append(
            f"Meta description is {length} characters; recommended minimum is "
            f"{META_DESCRIPTION_MIN_LENGTH} to give a fuller SERP snippet."
        )
    elif length > META_DESCRIPTION_MAX_LENGTH:
        status = "too_long"
        issues.append(
            f"Meta description is {length} characters; recommended maximum is "
            f"{META_DESCRIPTION_MAX_LENGTH} before search engines commonly truncate it."
        )
    else:
        status = "good"

    if duplicate:
        issues.append(
            f"Found {len(descriptions)} meta description tags; there should be exactly one."
        )

    return MetaDescriptionAnalysis(
        value=value,
        present=True,
        length=length,
        length_status=status,
        duplicate_tags_found=duplicate,
        issues=issues,
    )


# --- Headings ------------------------------------------------------------


@dataclass(frozen=True)
class HeadingsAnalysis:
    total: int
    counts_by_level: dict[str, int]  # "h1".."h6" -> count
    h1_count: int
    has_multiple_h1: bool
    hierarchy_gaps_found: bool
    headings: list[dict[str, object]]  # [{"level": int, "text": str}, ...]
    issues: list[str] = field(default_factory=list)


def analyze_headings(headings: list[HeadingTag]) -> HeadingsAnalysis:
    counts_by_level = {f"h{i}": 0 for i in range(1, 7)}
    for h in headings:
        counts_by_level[f"h{h.level}"] += 1

    h1_count = counts_by_level["h1"]
    issues: list[str] = []

    if h1_count == 0:
        issues.append("No <h1> found. Each page should generally have exactly one H1.")
    elif h1_count > 1:
        issues.append(f"Found {h1_count} <h1> tags; a single H1 per page is generally recommended.")

    # Detect an actual *skip*: a heading level appearing more than one
    # step deeper than the deepest level seen so far in document order
    # (e.g. H2 straight to H4 with no H3 in between). Levels *decreasing*
    # (H3 back to H2) or repeating are normal document structure, not a
    # skip, so they are not flagged.
    hierarchy_gaps_found = False
    deepest_seen = 0
    for h in headings:
        if deepest_seen and h.level > deepest_seen + 1:
            hierarchy_gaps_found = True
        deepest_seen = max(deepest_seen, h.level)

    if hierarchy_gaps_found:
        issues.append(
            "Heading levels skip at least one level (e.g. H2 directly to H4), "
            "which can make the document outline harder to follow."
        )

    return HeadingsAnalysis(
        total=len(headings),
        counts_by_level=counts_by_level,
        h1_count=h1_count,
        has_multiple_h1=h1_count > 1,
        hierarchy_gaps_found=hierarchy_gaps_found,
        headings=[{"level": h.level, "text": h.text} for h in headings],
        issues=issues,
    )


# --- URL -------------------------------------------------------------------


@dataclass(frozen=True)
class UrlAnalysis:
    url: str
    is_https: bool
    length: int
    length_status: str  # "good" | "long"
    has_query_parameters: bool
    query_parameter_count: int
    tracking_parameters_found: list[str]
    has_fragment: bool
    path_segment_count: int
    issues: list[str] = field(default_factory=list)


def analyze_url(url: str) -> UrlAnalysis:
    parts = urlsplit(url)
    is_https = parts.scheme.lower() == "https"
    length = len(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    tracking_found = sorted(
        {key for key, _ in query_pairs if key.lower() in KNOWN_TRACKING_PARAMS}
    )
    path_segments = [seg for seg in parts.path.split("/") if seg]

    issues: list[str] = []
    if not is_https:
        issues.append("URL does not use HTTPS.")

    length_status = "good"
    if length > URL_RECOMMENDED_MAX_LENGTH:
        length_status = "long"
        issues.append(
            f"URL is {length} characters; recommended maximum is "
            f"{URL_RECOMMENDED_MAX_LENGTH} for readability and SERP display."
        )

    # Query parameters are only flagged when they are recognizable tracking
    # parameters -- a query string by itself (e.g. ?id=42 addressing
    # distinct content) is not treated as an SEO problem.
    if tracking_found:
        issues.append(
            "URL contains known tracking parameter(s): "
            + ", ".join(tracking_found)
            + ". Consider whether the canonical tag should exclude these."
        )

    return UrlAnalysis(
        url=url,
        is_https=is_https,
        length=length,
        length_status=length_status,
        has_query_parameters=bool(query_pairs),
        query_parameter_count=len(query_pairs),
        tracking_parameters_found=tracking_found,
        has_fragment=bool(parts.fragment),
        path_segment_count=len(path_segments),
        issues=issues,
    )


# --- Images ------------------------------------------------------------


@dataclass(frozen=True)
class ImagesAnalysis:
    total: int
    with_alt_text: int
    without_alt_text: int
    empty_alt_count: int  # alt="" specifically (valid for decorative images)
    alt_text_coverage_percent: float
    issues: list[str] = field(default_factory=list)


def analyze_images(images: list[ImageTag]) -> ImagesAnalysis:
    total = len(images)
    if total == 0:
        return ImagesAnalysis(
            total=0,
            with_alt_text=0,
            without_alt_text=0,
            empty_alt_count=0,
            alt_text_coverage_percent=0.0,
            issues=[],
        )

    with_meaningful_alt = sum(1 for img in images if img.alt_present and img.alt_value.strip())
    empty_alt = sum(1 for img in images if img.alt_present and not img.alt_value.strip())
    without_alt_attr = sum(1 for img in images if not img.alt_present)

    coverage = round((with_meaningful_alt / total) * 100, 2)

    issues: list[str] = []
    if without_alt_attr:
        issues.append(
            f"{without_alt_attr} of {total} image(s) have no `alt` attribute at all."
        )

    return ImagesAnalysis(
        total=total,
        with_alt_text=with_meaningful_alt,
        without_alt_text=without_alt_attr + empty_alt,
        empty_alt_count=empty_alt,
        alt_text_coverage_percent=coverage,
        issues=issues,
    )


# --- Links ---------------------------------------------------------------


@dataclass(frozen=True)
class LinksAnalysis:
    total: int
    internal: int
    external: int
    without_usable_href: int
    issues: list[str] = field(default_factory=list)


_USELESS_HREF_PREFIXES = ("javascript:",)


def analyze_links(links: list[LinkTag], *, page_url: str) -> LinksAnalysis:
    page_host = urlsplit(page_url).hostname or ""

    internal = 0
    external = 0
    unusable = 0

    for link in links:
        href = link.href.strip()
        lowered = href.lower()

        if not href or href == "#" or lowered.startswith(_USELESS_HREF_PREFIXES):
            unusable += 1
            continue

        if lowered.startswith("mailto:") or lowered.startswith("tel:"):
            unusable += 1
            continue

        link_host = urlsplit(href).hostname
        if link_host is None:
            # Relative link (e.g. "/about", "about.html", "#section") ->
            # resolves against the same host.
            internal += 1
        elif link_host.lower() == page_host.lower():
            internal += 1
        else:
            external += 1

    issues: list[str] = []
    if unusable:
        issues.append(f"{unusable} link(s) have no usable destination (empty, `#`, or javascript:).")

    return LinksAnalysis(
        total=len(links),
        internal=internal,
        external=external,
        without_usable_href=unusable,
        issues=issues,
    )


# --- Canonical -----------------------------------------------------------


@dataclass(frozen=True)
class CanonicalAnalysis:
    value: str | None
    present: bool
    duplicate_tags_found: bool
    matches_page_url: bool | None  # None when not determinable (e.g. absent)
    issues: list[str] = field(default_factory=list)


def analyze_canonical(canonical_hrefs: list[str], *, page_url: str) -> CanonicalAnalysis:
    duplicate = len(canonical_hrefs) > 1

    if not canonical_hrefs:
        return CanonicalAnalysis(
            value=None,
            present=False,
            duplicate_tags_found=False,
            matches_page_url=None,
            issues=["No <link rel=\"canonical\"> tag found."],
        )

    value = canonical_hrefs[0]
    issues: list[str] = []
    if duplicate:
        issues.append(
            f"Found {len(canonical_hrefs)} canonical tags; there should be exactly one."
        )

    matches = value.rstrip("/") == page_url.rstrip("/")
    if not matches:
        # Informational, not necessarily an error -- pointing canonical at
        # a different URL is a deliberate and valid pattern (e.g. paginated
        # or parameterized pages canonicalizing to a primary version).
        issues.append(
            "Canonical URL differs from the fetched URL. Confirm this is intentional."
        )

    return CanonicalAnalysis(
        value=value,
        present=True,
        duplicate_tags_found=duplicate,
        matches_page_url=matches,
        issues=issues,
    )


# --- Robots ----------------------------------------------------------------


@dataclass(frozen=True)
class RobotsAnalysis:
    directives: list[str]
    present: bool
    indexing_allowed: bool | None  # None when not determinable
    following_allowed: bool | None
    issues: list[str] = field(default_factory=list)


def analyze_robots(meta_robots_values: list[str]) -> RobotsAnalysis:
    if not meta_robots_values:
        return RobotsAnalysis(
            directives=[],
            present=False,
            indexing_allowed=None,
            following_allowed=None,
            issues=[
                "No <meta name=\"robots\"> tag found; indexing behavior is determined "
                "by defaults (typically index, follow) or robots.txt, which this "
                "analysis does not check."
            ],
        )

    # If multiple robots tags exist, browsers/crawlers combine directives;
    # we conservatively union all of them rather than silently picking one.
    all_directives: list[str] = []
    for raw in meta_robots_values:
        all_directives.extend(part.strip().lower() for part in raw.split(",") if part.strip())

    indexing_allowed = "noindex" not in all_directives
    following_allowed = "nofollow" not in all_directives

    issues: list[str] = []
    if not indexing_allowed:
        issues.append("`noindex` directive present: this page is instructed not to be indexed.")
    if not following_allowed:
        issues.append("`nofollow` directive present: links on this page are instructed not to be followed.")

    return RobotsAnalysis(
        directives=sorted(set(all_directives)),
        present=True,
        indexing_allowed=indexing_allowed,
        following_allowed=following_allowed,
        issues=issues,
    )


# --- Open Graph --------------------------------------------------------


@dataclass(frozen=True)
class OpenGraphAnalysis:
    title: str | None
    description: str | None
    type: str | None
    url: str | None
    image: str | None
    present_tags: list[str]
    missing_tags: list[str]
    duplicate_tags_found: list[str]
    issues: list[str] = field(default_factory=list)


_TRACKED_OG_PROPERTIES = ("og:title", "og:description", "og:type", "og:url", "og:image")


def analyze_open_graph(og_tags: dict[str, list[str]]) -> OpenGraphAnalysis:
    present_tags = [prop for prop in _TRACKED_OG_PROPERTIES if og_tags.get(prop)]
    missing_tags = [prop for prop in _TRACKED_OG_PROPERTIES if prop not in present_tags]
    duplicates = [prop for prop in _TRACKED_OG_PROPERTIES if len(og_tags.get(prop, [])) > 1]

    def first_value(prop: str) -> str | None:
        values = og_tags.get(prop)
        return values[0] if values else None

    issues: list[str] = []
    if missing_tags:
        issues.append(
            "Missing Open Graph tag(s): " + ", ".join(missing_tags) + "."
        )
    if duplicates:
        issues.append(
            "Duplicate Open Graph tag(s) found: " + ", ".join(duplicates) + "."
        )

    return OpenGraphAnalysis(
        title=first_value("og:title"),
        description=first_value("og:description"),
        type=first_value("og:type"),
        url=first_value("og:url"),
        image=first_value("og:image"),
        present_tags=present_tags,
        missing_tags=missing_tags,
        duplicate_tags_found=duplicates,
        issues=issues,
    )


# --- Keyword relationships -----------------------------------------------


@dataclass(frozen=True)
class KeywordRelationship:
    keyword: str
    in_title: bool
    in_meta_description: bool
    in_content: bool


def analyze_keyword_relationships(
    keywords: list[KeywordStat],
    *,
    title: str | None,
    meta_description: str | None,
    body_text: str,
) -> list[KeywordRelationship]:
    """
    For each extracted keyword, deterministically report whether it also
    appears (case-insensitively, substring match) in the title, meta
    description, and body content. Presence/absence only -- this
    deliberately does not combine into any single "SEO score".
    """
    title_lower = (title or "").lower()
    description_lower = (meta_description or "").lower()
    body_lower = (body_text or "").lower()

    return [
        KeywordRelationship(
            keyword=stat.keyword,
            in_title=stat.keyword in title_lower,
            in_meta_description=stat.keyword in description_lower,
            in_content=stat.keyword in body_lower,
        )
        for stat in keywords
    ]
