from __future__ import annotations

LANGUAGETOOL_LANGUAGE = "en-US"
LANGUAGETOOL_CHECK_PATH = "/v2/check"
MAX_REPLACEMENTS_PER_FINDING = 5

ISSUE_TYPE_SEVERITY: dict[str, str] = {
    "misspelling": "error",
    "typographical": "error",
    "grammar": "warning",
    "punctuation": "warning",
    "casing": "warning",
    "confused_words": "warning",
    "duplication": "warning",
    "style": "info",
    "register": "info",
    "redundancy": "info",
    "inconsistency": "info",
    "whitespace": "info",
    "semantics": "info",
    "non-conformance": "info",
}
