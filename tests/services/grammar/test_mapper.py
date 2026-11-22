from __future__ import annotations

from app.services.grammar.mapper import GrammarFinding, map_match, map_matches


def _match(**overrides):
    base = {
        "message": "Possible spelling mistake found.",
        "shortMessage": "Spelling mistake",
        "offset": 5,
        "length": 4,
        "replacements": [{"value": "teh"}],
        "context": {"text": "This teh sentence.", "offset": 5, "length": 4},
        "rule": {
            "id": "MORFOLOGIK_RULE_EN_US",
            "issueType": "misspelling",
            "category": {"id": "TYPOS", "name": "Possible Typo"},
        },
    }
    base.update(overrides)
    return base


def test_map_match_normal_finding():
    finding = map_match(_match())

    assert isinstance(finding, GrammarFinding)
    assert finding.message == "Possible spelling mistake found."
    assert finding.short_message == "Spelling mistake"
    assert finding.category == "Possible Typo"
    assert finding.rule_id == "MORFOLOGIK_RULE_EN_US"
    assert finding.issue_type == "misspelling"
    assert finding.severity == "error"
    assert finding.offset == 5
    assert finding.length == 4
    assert finding.context == "This teh sentence."
    assert finding.replacements == ["teh"]


def test_map_matches_multiple_findings_preserve_order():
    matches = [
        _match(message="First issue.", offset=0, length=3),
        _match(message="Second issue.", offset=10, length=2),
    ]

    findings = map_matches(matches)

    assert [f.message for f in findings] == ["First issue.", "Second issue."]


def test_map_match_replacements_are_capped():
    match = _match(replacements=[{"value": f"opt{i}"} for i in range(10)])

    finding = map_match(match)

    assert len(finding.replacements) == 5
    assert finding.replacements == ["opt0", "opt1", "opt2", "opt3", "opt4"]


def test_map_match_replacements_skip_malformed_entries():
    match = _match(replacements=[{"value": "good"}, {"no_value": True}, "not-a-dict", {"value": ""}])

    finding = map_match(match)

    assert finding.replacements == ["good"]


def test_map_match_optional_fields_missing():
    match = {
        "message": "Some issue.",
        "offset": 0,
        "length": 1,
    }

    finding = map_match(match)

    assert finding.message == "Some issue."
    assert finding.short_message is None
    assert finding.category is None
    assert finding.rule_id is None
    assert finding.issue_type is None
    assert finding.severity is None
    assert finding.context is None
    assert finding.replacements == []


def test_map_match_unknown_issue_type_has_no_invented_severity():
    match = _match(rule={"id": "SOME_RULE", "issueType": "totally_unrecognized_type"})

    finding = map_match(match)

    assert finding.issue_type == "totally_unrecognized_type"
    assert finding.severity is None


def test_map_match_missing_message_returns_none():
    match = _match()
    del match["message"]

    assert map_match(match) is None


def test_map_match_blank_message_returns_none():
    match = _match(message="   ")

    assert map_match(match) is None


def test_map_match_missing_offset_or_length_returns_none():
    match_no_offset = _match()
    del match_no_offset["offset"]
    assert map_match(match_no_offset) is None

    match_no_length = _match()
    del match_no_length["length"]
    assert map_match(match_no_length) is None


def test_map_match_negative_offset_or_length_returns_none():
    assert map_match(_match(offset=-1)) is None
    assert map_match(_match(length=-1)) is None


def test_map_match_non_integer_offset_returns_none():
    assert map_match(_match(offset="5")) is None
    assert map_match(_match(offset=5.5)) is None


def test_map_match_malformed_match_is_not_a_dict_returns_none():
    assert map_match("not-a-dict") is None
    assert map_match(None) is None
    assert map_match(["a", "list"]) is None


def test_map_match_malformed_rule_is_ignored_gracefully():
    match = _match(rule="not-a-dict")

    finding = map_match(match)

    assert finding is not None
    assert finding.rule_id is None
    assert finding.issue_type is None
    assert finding.category is None
    assert finding.severity is None


def test_map_match_malformed_category_is_ignored_gracefully():
    match = _match(rule={"id": "R1", "issueType": "grammar", "category": "not-a-dict"})

    finding = map_match(match)

    assert finding is not None
    assert finding.category is None
    assert finding.severity == "warning"


def test_map_matches_drops_individually_malformed_matches():
    matches = [
        _match(message="Good one.", offset=0, length=1),
        {"message": "", "offset": 1, "length": 1},  # blank message -> dropped
        "not-a-dict",  # dropped
        _match(message="Another good one.", offset=5, length=1),
    ]

    findings = map_matches(matches)

    assert [f.message for f in findings] == ["Good one.", "Another good one."]


def test_map_match_unicode_text_is_preserved():
    match = _match(
        message="Café should have an accent — vérifiez l'orthographe.",
        context={"text": "Café ☕ 日本語 text", "offset": 0, "length": 4},
        replacements=[{"value": "Café"}],
    )

    finding = map_match(match)

    assert finding.message == "Café should have an accent — vérifiez l'orthographe."
    assert finding.context == "Café ☕ 日本語 text"
    assert finding.replacements == ["Café"]

