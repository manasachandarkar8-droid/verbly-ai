from __future__ import annotations

from app.services.grammar.mapper import GrammarFinding

_SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2, None: 3}


def process_findings(findings: list[GrammarFinding]) -> list[GrammarFinding]:
    unique: dict[tuple[int, int, str, str | None], GrammarFinding] = {}
    for finding in findings:
        key = (finding.offset, finding.length, finding.message, finding.rule_id)
        unique.setdefault(key, finding)

    by_span: dict[tuple[int, int], GrammarFinding] = {}
    for finding in unique.values():
        span = (finding.offset, finding.length)
        current = by_span.get(span)
        if current is None or _SEVERITY_RANK[finding.severity] < _SEVERITY_RANK[current.severity]:
            by_span[span] = finding

    return sorted(
        by_span.values(),
        key=lambda item: (item.offset, item.length, item.rule_id or item.message),
    )
