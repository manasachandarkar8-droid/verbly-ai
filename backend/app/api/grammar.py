from __future__ import annotations

from fastapi import APIRouter

from app.schemas.grammar import GrammarFindingResult, GrammarRequest, GrammarResponse
from app.services.grammar.service import analyze_grammar

router = APIRouter()

@router.post("/grammar", response_model=GrammarResponse)
async def grammar(request: GrammarRequest) -> GrammarResponse:
    result = await analyze_grammar(request.text)
    findings = [GrammarFindingResult(**finding.__dict__) for finding in result.findings]
    return GrammarResponse(
        text_length=result.text_length,
        finding_count=len(findings),
        findings=findings,
        issues=[finding.message for finding in findings],
    )
