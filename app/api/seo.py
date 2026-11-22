from __future__ import annotations

from fastapi import APIRouter

from app.schemas.seo import (
    CanonicalResult,
    HeadingsResult,
    ImagesResult,
    KeywordRelationshipResult,
    KeywordResult,
    LinksResult,
    MetaDescriptionResult,
    OpenGraphResult,
    RobotsResult,
    SEORequest,
    SEOResponse,
    TitleResult,
    UrlAnalysisResult,
)
from app.services.seo.service import analyze_seo

router = APIRouter()


@router.post("/seo", response_model=SEOResponse)
def create_seo_analysis(payload: SEORequest) -> SEOResponse:
    # Any ExtractionError subclass raised by fetch_html (called inside
    # analyze_seo) is caught by the same centralized handler registered in
    # app.core.exceptions (see register_exception_handlers in app.main) that
    # already handles Feature 1's errors -- no SEO-specific exception type
    # or handler registration is needed.
    result = analyze_seo(str(payload.url), max_keywords=payload.max_keywords)

    return SEOResponse(
        requested_url=result.requested_url,
        final_url=result.final_url,
        title=TitleResult(**result.title.__dict__),
        meta_description=MetaDescriptionResult(**result.meta_description.__dict__),
        headings=HeadingsResult(**result.headings.__dict__),
        keywords=[KeywordResult(**k.__dict__) for k in result.keywords],
        keyword_relationships=[
            KeywordRelationshipResult(**r.__dict__) for r in result.keyword_relationships
        ],
        url_analysis=UrlAnalysisResult(**result.url_analysis.__dict__),
        images=ImagesResult(**result.images.__dict__),
        links=LinksResult(**result.links.__dict__),
        canonical=CanonicalResult(**result.canonical.__dict__),
        robots=RobotsResult(**result.robots.__dict__),
        open_graph=OpenGraphResult(**result.open_graph.__dict__),
        issues=result.issues,
    )
