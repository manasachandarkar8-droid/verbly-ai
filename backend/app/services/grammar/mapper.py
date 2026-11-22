from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.grammar.constants import ISSUE_TYPE_SEVERITY, MAX_REPLACEMENTS_PER_FINDING

@dataclass(frozen=True)
class GrammarFinding:
    message: str
    short_message: str | None
    category: str | None
    rule_id: str | None
    issue_type: str | None
    severity: str | None
    offset: int
    length: int
    context: str | None
    replacements: list[str]


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def map_match(match: Any) -> GrammarFinding | None:
    if not isinstance(match, dict):
        return None
    message = _text(match.get("message"))
    offset = match.get("offset")
    length = match.get("length")
    if message is None or not isinstance(offset, int) or isinstance(offset, bool) or not isinstance(length, int) or isinstance(length, bool):
        return None
    if offset < 0 or length < 0:
        return None

    rule = match.get("rule") if isinstance(match.get("rule"), dict) else {}
    category = rule.get("category") if isinstance(rule.get("category"), dict) else {}
    issue_type = _text(rule.get("issueType"))
    replacements: list[str] = []
    raw_replacements = match.get("replacements", [])
    if isinstance(raw_replacements, list):
        for item in raw_replacements:
            if isinstance(item, dict):
                value = _text(item.get("value"))
                if value is not None:
                    replacements.append(value)
                    if len(replacements) >= MAX_REPLACEMENTS_PER_FINDING:
                        break
    context = match.get("context")
    context_text = context.get("text") if isinstance(context, dict) and isinstance(context.get("text"), str) else None
    return GrammarFinding(
        message=message,
        short_message=_text(match.get("shortMessage")),
        category=_text(category.get("name")),
        rule_id=_text(rule.get("id")),
        issue_type=issue_type,
        severity=ISSUE_TYPE_SEVERITY.get(issue_type) if issue_type else None,
        offset=offset,
        length=length,
        context=context_text,
        replacements=replacements,
    )


def map_matches(matches: list[Any]) -> list[GrammarFinding]:
    return [finding for match in matches if (finding := map_match(match)) is not None]
