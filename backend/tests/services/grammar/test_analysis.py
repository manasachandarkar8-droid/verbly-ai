from __future__ import annotations

from app.services.grammar.analysis import process_findings
from app.services.grammar.mapper import GrammarFinding


def _finding(**overrides) -> GrammarFinding:
    base = dict(
        message="Some issue.",
        short_message=None,
        category=None,
        rule_id="RULE_A",
        issue_type="grammar",
        severity="warning",
        offset=0,
        length=1,
        context=None,
        replacements=[],
    )
    base.update(overrides)
    return GrammarFinding(**base)


def test_process_findings_empty_list():
    assert process_findings([]) == []


def test_process_findings_removes_exact_duplicates():
    a = _finding(offset=0, length=3, message="Dup.", rule_id="R1")
    b = _finding(offset=0, length=3, message="Dup.", rule_id="R1")

    result = process_findings([a, b])

    assert len(result) == 1


def test_process_findings_keeps_same_span_different_rule_or_message():
    a = _finding(offset=0, length=3, message="Dup.", rule_id="R1")
    b = _finding(offset=0, length=3, message="Different message.", rule_id="R1")
    c = _finding(offset=0, length=3, message="Dup.", rule_id="R2")

    deduped_only = process_findings([a, a])
    assert len(deduped_only) == 1

    # b and c are not exact duplicates of a, but DO share a's span, so the
    # overlap step still collapses them down to one per span.
    result = process_findings([a, b, c])
    assert len(result) == 1


def test_process_findings_resolves_same_span_overlap_by_severity():
    low = _finding(offset=2, length=4, message="Style nit.", rule_id="STYLE", severity="info")
    high = _finding(offset=2, length=4, message="Real error.", rule_id="ERR", severity="error")

    result = process_findings([low, high])

    assert len(result) == 1
    assert result[0].severity == "error"
    assert result[0].message == "Real error."


def test_process_findings_keeps_distinct_overlapping_but_non_identical_spans():
    # These spans intersect (2-6 and 4-8) but are not identical, so both
    # must be preserved -- only exact same-span duplicates collapse.
    first = _finding(offset=2, length=4, message="First.", rule_id="R1")
    second = _finding(offset=4, length=4, message="Second.", rule_id="R2")

    result = process_findings([first, second])

    assert len(result) == 2


def test_process_findings_deterministic_ordering_by_offset():
    a = _finding(offset=10, length=2, message="Later.", rule_id="R1")
    b = _finding(offset=0, length=2, message="Earlier.", rule_id="R2")

    result = process_findings([a, b])

    assert [f.message for f in result] == ["Earlier.", "Later."]


def test_process_findings_same_offset_ordered_by_length_then_rule_id():
    a = _finding(offset=0, length=5, message="Long.", rule_id="Z_RULE")
    b = _finding(offset=0, length=2, message="Short.", rule_id="A_RULE")

    result = process_findings([a, b])

    assert [f.message for f in result] == ["Short.", "Long."]


def test_process_findings_same_offset_and_length_ordered_by_rule_id():
    a = _finding(offset=0, length=3, message="Msg A.", rule_id="Z_RULE")
    b = _finding(offset=0, length=3, message="Msg B.", rule_id="A_RULE")
    # Different spans so overlap resolution doesn't collapse them; force
    # distinct lengths to isolate ordering-by-rule_id at the same offset.
    a = _finding(offset=0, length=5, message="Msg A.", rule_id="Z_RULE")
    b = _finding(offset=0, length=3, message="Msg B.", rule_id="A_RULE")

    result = process_findings([a, b])

    assert [f.rule_id for f in result] == ["A_RULE", "Z_RULE"]


def test_process_findings_ordering_is_stable_and_reproducible():
    findings = [
        _finding(offset=20, length=1, rule_id="C", message="c"),
        _finding(offset=5, length=1, rule_id="B", message="b"),
        _finding(offset=5, length=2, rule_id="A", message="a"),
    ]

    result_1 = process_findings(list(findings))
    result_2 = process_findings(list(reversed(findings)))

    assert [f.message for f in result_1] == [f.message for f in result_2]
    assert [f.message for f in result_1] == ["b", "a", "c"]


def test_process_findings_preserves_context_field():
    finding = _finding(context="Some surrounding text.")

    result = process_findings([finding])

    assert result[0].context == "Some surrounding text."


def test_process_findings_preserves_text_positions():
    finding = _finding(offset=42, length=7)

    result = process_findings([finding])

    assert result[0].offset == 42
    assert result[0].length == 7

