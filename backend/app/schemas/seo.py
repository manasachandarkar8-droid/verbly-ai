from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from app.services.seo.constants import DEFAULT_MAX_KEYWORDS, HARD_MAX_KEYWORDS


class SEORequest(BaseModel):
    url: HttpUrl = Field(..., description="The webpage URL to fetch and analyze for SEO.")
    max_keywords: int = Field(
        default=DEFAULT_MAX_KEYWORDS,
        ge=1,
        le=HARD_MAX_KEYWORDS,
        description="Maximum number of top keywords to return.",
    )


class TitleResult(BaseModel):
    value: str | None
    present: bool
    length: int
    length_status: str
    duplicate_tags_found: bool
    issues: list[str]


class MetaDescriptionResult(BaseModel):
    value: str | None
    present: bool
    length: int
    length_status: str
    duplicate_tags_found: bool
    issues: list[str]


class HeadingsResult(BaseModel):
    total: int
    counts_by_level: dict[str, int]
    h1_count: int
    has_multiple_h1: bool
    hierarchy_gaps_found: bool
    headings: list[dict[str, object]]
    issues: list[str]


class KeywordResult(BaseModel):
    keyword: str
    count: int
    density: float


class KeywordRelationshipResult(BaseModel):
    keyword: str
    in_title: bool
    in_meta_description: bool
    in_content: bool


class UrlAnalysisResult(BaseModel):
    url: str
    is_https: bool
    length: int
    length_status: str
    has_query_parameters: bool
    query_parameter_count: int
    tracking_parameters_found: list[str]
    has_fragment: bool
    path_segment_count: int
    issues: list[str]


class ImagesResult(BaseModel):
    total: int
    with_alt_text: int
    without_alt_text: int
    empty_alt_count: int
    alt_text_coverage_percent: float
    issues: list[str]


class LinksResult(BaseModel):
    total: int
    internal: int
    external: int
    without_usable_href: int
    issues: list[str]


class CanonicalResult(BaseModel):
    value: str | None
    present: bool
    duplicate_tags_found: bool
    matches_page_url: bool | None
    issues: list[str]


class RobotsResult(BaseModel):
    directives: list[str]
    present: bool
    indexing_allowed: bool | None
    following_allowed: bool | None
    issues: list[str]


class OpenGraphResult(BaseModel):
    title: str | None
    description: str | None
    type: str | None
    url: str | None
    image: str | None
    present_tags: list[str]
    missing_tags: list[str]
    duplicate_tags_found: list[str]
    issues: list[str]


class SEOResponse(BaseModel):
    """
    Deterministic SEO analysis result.

    NOTE: there is intentionally no single aggregate "SEO score" here.
    Each section reports its own explicit, rule-based issues; `issues` is
    the flattened union of all of them for convenience. A weighted overall
    content score is a separate, later feature (Feature 7) and is out of
    scope for this response.
    """

    requested_url: str
    final_url: str
    title: TitleResult
    meta_description: MetaDescriptionResult
    headings: HeadingsResult
    keywords: list[KeywordResult]
    keyword_relationships: list[KeywordRelationshipResult]
    url_analysis: UrlAnalysisResult
    images: ImagesResult
    links: LinksResult
    canonical: CanonicalResult
    robots: RobotsResult
    open_graph: OpenGraphResult
    issues: list[str]
