from __future__ import annotations

from dataclasses import dataclass
import httpx

from app.services.grammar.analysis import process_findings
from app.services.grammar.client import check_text
from app.services.grammar.mapper import GrammarFinding, map_matches

@dataclass(frozen=True)
class GrammarAnalysisResult:
    text_length: int
    findings: list[GrammarFinding]


async def analyze_grammar(
    text: str,
    _transport: httpx.AsyncBaseTransport | None = None,
) -> GrammarAnalysisResult:
    result = await check_text(text, _transport=_transport)
    findings = process_findings(map_matches(result.matches))
    return GrammarAnalysisResult(text_length=len(text), findings=findings)
