"""
Deterministic text-analysis primitives for Feature 2 (readability analysis).

Everything in this module is pure, dependency-free, and rule-based -- no
LLM calls, no network access, no external NLP libraries. Given the same
input string, every function here always returns the same output.

These are low-level building blocks. Orchestration (turning them into the
Flesch scores and a human-readable interpretation) lives in ``service.py``,
matching the fetcher.py / parser.py / service.py split used by Feature 1's
extraction service.
"""
from __future__ import annotations

import re

# --- Whitespace ---------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """
    Collapse any run of whitespace (spaces, tabs, newlines) into a single
    space and strip leading/trailing whitespace.

    This does not touch punctuation, so sentence-terminating characters
    are preserved for ``split_sentences``.
    """
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


# --- Words ----------------------------------------------------------------

# A "word" is a run of letters/digits, optionally with a single internal
# apostrophe (so "don't" / "it's" count as one word rather than two).
# Hyphenated compounds (e.g. "well-known") are counted as two words; this
# is a documented simplification consistent with how most plain-text
# readability tools tokenize, and keeps the tokenizer simple and
# deterministic.
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")


def extract_words(text: str) -> list[str]:
    """Return the list of word tokens found in ``text``."""
    if not text:
        return []
    return _WORD_RE.findall(text)


def count_words(text: str) -> int:
    """Return the number of word tokens in ``text``."""
    return len(extract_words(text))


# --- Sentences --------------------------------------------------------

# Title/reference abbreviations that are, for practical purposes, *never*
# the actual end of a sentence -- they are almost always immediately
# followed by the proper noun or number they introduce (e.g. "Dr. Smith",
# "St. Louis", "vs. Warriors"), regardless of whether that following word
# happens to be capitalized. These always keep accumulating into the same
# sentence.
_ALWAYS_MERGE_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs",
    "rev", "gen", "col", "capt", "sgt", "lt", "cmdr", "gov", "hon",
    "assoc", "messrs", "corp", "co", "inc", "ltd", "dept", "univ",
    "no", "vol", "fig", "approx", "apt",
    "jan", "feb", "mar", "apr", "jun", "jul",
    "aug", "sep", "sept", "oct", "nov", "dec",
}

# Abbreviations that are genuinely ambiguous: they commonly appear
# mid-sentence as a parenthetical aside ("..., e.g. dogs and cats, ...")
# but can also legitimately be the last word of a real sentence, with a
# brand new sentence starting right after ("...took notes, etc. The
# students then left."). Note the retained internal period in "e.g" /
# "i.e" -- that's deliberate, since the token-extraction step below only
# strips *enclosing* punctuation, not internal periods.
_CONTEXTUAL_ABBREVIATIONS = {"etc", "e.g", "i.e"}

# Split right after a sentence-terminating run of . ! or ?, but only when
# followed by whitespace (so it does not fire on trailing punctuation at
# the very end of the string, which the loop below still picks up as a
# final fragment).
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")

# Punctuation that can enclose or trail a word without being part of it
# (parentheses, quotes, commas, terminal sentence punctuation). Stripped
# from both ends of a token before checking it against the abbreviation
# sets, so e.g. "(i.e." -> "i.e" rather than failing to match because of
# the leading "(".
_TOKEN_STRIP_CHARS = ".,!?;:()[]{}\"'\u201c\u201d\u2018\u2019"

_FIRST_LETTER_RE = re.compile(r"[A-Za-z]")


def _last_token(buffer: str) -> str:
    """Return the last whitespace-separated token of ``buffer``, with
    enclosing punctuation stripped and lowercased, for abbreviation
    matching. Internal punctuation (e.g. the periods in "e.g") is left
    intact."""
    words = buffer.split()
    if not words:
        return ""
    return words[-1].strip(_TOKEN_STRIP_CHARS).lower()


def _looks_like_new_sentence_start(fragment: str) -> bool:
    """
    Heuristic: does ``fragment`` look like it opens a new sentence?

    Judged by the case of its first letter (capitalized => new sentence).
    If ``fragment`` contains no letters at all, there is nothing to judge
    by, so it defaults to treating it as a new sentence -- swallowing a
    genuine sentence boundary silently is worse than an occasional
    over-split on unusual punctuation-only text.
    """
    match = _FIRST_LETTER_RE.search(fragment)
    if not match:
        return True
    return match.group(0).isupper()


def split_sentences(text: str) -> list[str]:
    """
    Split ``text`` into sentences using a deterministic, punctuation-based
    heuristic that guards against splitting on common abbreviations.

    Two tiers of abbreviation are handled:

    - "Always merge" abbreviations (``Dr.``, ``Mr.``, ``St.``, ``vs.``, ...)
      never end a sentence on their own; the fragment they end is always
      folded into the next one.
    - "Contextual" abbreviations (``etc.``, ``e.g.``, ``i.e.``) can go
      either way, so the next fragment's leading capitalization decides:
      a lowercase continuation ("e.g. dogs") stays in the same sentence,
      while a capitalized follow-on ("etc. The students...") is treated
      as a genuine new sentence.

    Returns an empty list for empty/whitespace-only input. Text with words
    but no terminating punctuation is returned as a single sentence, so
    callers never need to special-case "zero sentences but nonzero words".
    """
    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    fragments = _SENTENCE_BOUNDARY_RE.split(normalized)

    sentences: list[str] = []
    buffer = ""
    for index, fragment in enumerate(fragments):
        fragment = fragment.strip()
        if not fragment:
            continue
        buffer = f"{buffer} {fragment}".strip() if buffer else fragment

        token = _last_token(buffer)

        if token in _ALWAYS_MERGE_ABBREVIATIONS:
            # Almost certainly introduces a name/number that continues
            # this same sentence (e.g. "Dr." before "Smith").
            continue

        if token in _CONTEXTUAL_ABBREVIATIONS:
            next_fragment = fragments[index + 1] if index + 1 < len(fragments) else ""
            if not next_fragment or not _looks_like_new_sentence_start(next_fragment):
                # No more text, or the continuation looks lowercase /
                # mid-clause (e.g. "e.g. dogs") -- keep buffering.
                continue
            # Otherwise the next fragment looks like a fresh, capitalized
            # sentence -- fall through and close this one out.

        sentences.append(buffer)
        buffer = ""

    if buffer:
        # Trailing fragment with no terminal punctuation (or an
        # abbreviation-like ending at the very end of the text).
        sentences.append(buffer)

    return sentences


def count_sentences(text: str) -> int:
    """
    Return the number of sentences in ``text``.

    Guarantees at least 1 for any text that contains at least one word,
    so callers can safely divide by this value without a zero-check.
    """
    sentences = split_sentences(text)
    if sentences:
        return len(sentences)
    return 1 if normalize_whitespace(text) else 0


# --- Syllables -----------------------------------------------------------

_VOWELS = "aeiouy"
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")
_NON_ALPHA_RE = re.compile(r"[^a-z]")


def count_syllables(word: str) -> int:
    """
    Estimate the number of syllables in a single English word.

    This is a deterministic heuristic (vowel-group counting with
    silent-e and common suffix adjustments), not a dictionary lookup, so
    it will occasionally be wrong on irregular words -- but it never
    returns 0 for a word that contains at least one letter, is fully
    explainable, and requires no external data or model calls.
    """
    cleaned = _NON_ALPHA_RE.sub("", word.lower())
    if not cleaned:
        return 0

    vowel_groups = _VOWEL_GROUP_RE.findall(cleaned)
    count = len(vowel_groups)

    # Silent trailing "e" (e.g. "code", "large") usually doesn't carry its
    # own syllable, *unless* the word ends in "-le" (e.g. "table",
    # "little"), where the final syllable is real.
    if cleaned.endswith("e") and not cleaned.endswith("le") and count > 1:
        count -= 1

    # "-ed" endings are silent (add no syllable) when preceded by a
    # consonant sound other than "t"/"d" (e.g. "walked", "jumped" -> 1
    # fewer syllable than naive vowel-counting suggests). When preceded
    # by "t" or "d" the "-ed" *does* add its own syllable (e.g. "needed",
    # "wanted"), so it is left alone in that case.
    if (
        cleaned.endswith("ed")
        and len(cleaned) > 2
        and count > 1
        and cleaned[-3] not in _VOWELS
        and cleaned[-3] not in ("t", "d")
    ):
        count -= 1

    # Every real word has at least one syllable.
    return max(count, 1)


def total_syllables(words: list[str]) -> int:
    """Return the sum of syllable counts across ``words``."""
    return sum(count_syllables(word) for word in words)
