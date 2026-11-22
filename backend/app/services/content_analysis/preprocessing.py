from __future__ import annotations

import re
import unicodedata

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Hard production limits.
# These are intentionally constants and are not environment-configurable.
# ---------------------------------------------------------------------------

MAX_REQUEST_CHARACTERS = 200_000
MAX_ANALYSIS_CHARACTERS = 50_000
MAX_ANALYZED_SENTENCES = 400
MAX_SEMANTIC_CHUNKS = 20

# Extra room for spaCy's internal processing.
SPACY_MAX_LENGTH_MARGIN = 1_000


# ---------------------------------------------------------------------------
# Internal cleanup patterns
# ---------------------------------------------------------------------------

_HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTIPLE_NEWLINES_RE = re.compile(r"\n{3,}")

# A sentence boundary must follow terminal punctuation and any closing
# quotation marks or brackets, followed by whitespace or the end of a line.
_SENTENCE_END_RE = re.compile(
    r"""[.!?]["'”’)\]]*(?=\s|$)"""
)

_WORD_RE = re.compile(r"[A-Za-z]+(?:\.[A-Za-z]+)*$")

# Common abbreviations that should not end a sentence by themselves.
_ABBREVIATIONS = frozenset(
    {
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "sr",
        "jr",
        "st",
        "vs",
        "etc",
        "e.g",
        "i.e",
        "u.s",
        "u.k",
        "no",
        "fig",
        "approx",
        "dept",
        "inc",
        "ltd",
        "corp",
        "co",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "sept",
        "oct",
        "nov",
        "dec",
    }
)

# Remove these explicitly, but preserve zero-width joiners and non-joiners,
# which can be meaningful in emoji and some writing systems.
_DISALLOWED_FORMAT_CHARACTERS = frozenset(
    {
        "\u200b",  # Zero-width space
        "\ufeff",  # Byte-order mark / zero-width no-break space
        "\u2060",  # Word joiner
    }
)


@dataclass(frozen=True)
class PreprocessedText:
    """Normalized and bounded text prepared for Feature 5 analysis."""

    received_characters: int
    original_characters: int
    analyzed_characters: int
    text: str
    sentences: tuple[str, ...]
    truncated: bool
    truncation_reason: str | None


def normalize_text(text: str) -> str:
    """
    Normalize Unicode and remove unsafe control characters.

    NFC normalization makes canonically equivalent Unicode sequences
    consistent. Newlines are normalized to LF. Tabs and newlines are
    preserved, as are Unicode joiners that may carry semantic meaning.

    This function does not impose the request-size limit. That limit is
    enforced by preprocess_text() before normalization.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    cleaned: list[str] = []

    for character in normalized:
        if character in _DISALLOWED_FORMAT_CHARACTERS:
            continue

        if character in {"\n", "\t"}:
            cleaned.append(character)
            continue

        category = unicodedata.category(character)

        # Cc: control characters.
        # Cs: surrogate code points, including lone surrogates.
        if category in {"Cc", "Cs"}:
            continue

        cleaned.append(character)

    return "".join(cleaned)


def _clean_text(text: str) -> str:
    """
    Normalize horizontal whitespace while preserving line and paragraph
    boundaries. Runs of three or more newlines become two newlines.
    """
    lines = [
        _HORIZONTAL_WHITESPACE_RE.sub(" ", line).strip()
        for line in text.split("\n")
    ]

    cleaned = "\n".join(lines)
    cleaned = _MULTIPLE_NEWLINES_RE.sub("\n\n", cleaned)

    return cleaned.strip()


def _is_abbreviation_boundary(
    line: str,
    match: re.Match[str],
) -> bool:
    """
    Identify common abbreviations that should not split a sentence.

    This is a lightweight heuristic, not a full linguistic sentence parser.
    """
    if not match.group().startswith("."):
        return False

    prefix = line[: match.start()].rstrip()
    token_match = _WORD_RE.search(prefix)

    if token_match is None:
        return False

    token = token_match.group().casefold()

    if token in _ABBREVIATIONS:
        return True

    # Avoid splitting common single-letter initials, such as "A. Smith".
    if len(token) == 1 and token.isalpha():
        return True

    return False


def _sentence_spans(
    text: str,
) -> list[tuple[int, int, str]]:
    """
    Return sentence-like spans as (start, end, sentence).

    Each non-empty line is processed independently so headings, list items,
    and line boundaries remain available to structural analysis.

    Offsets refer to the original supplied text. This lets truncation retain
    the original text prefix instead of rebuilding it from sentence strings.
    """
    spans: list[tuple[int, int, str]] = []
    offset = 0

    for raw_line in text.splitlines(keepends=True):
        line = raw_line.removesuffix("\n")

        if line.strip():
            cursor = 0

            for match in _SENTENCE_END_RE.finditer(line):
                if _is_abbreviation_boundary(line, match):
                    continue

                segment_start = cursor

                while (
                    segment_start < match.start()
                    and line[segment_start].isspace()
                ):
                    segment_start += 1

                sentence = line[segment_start : match.end()].strip()

                if sentence:
                    spans.append(
                        (
                            offset + segment_start,
                            offset + match.end(),
                            sentence,
                        )
                    )

                cursor = match.end()

            tail_start = cursor

            while (
                tail_start < len(line)
                and line[tail_start].isspace()
            ):
                tail_start += 1

            tail = line[tail_start:].strip()

            if tail:
                tail_end = len(line.rstrip())

                spans.append(
                    (
                        offset + tail_start,
                        offset + tail_end,
                        tail,
                    )
                )

        offset += len(raw_line)

    return spans


def _is_sentence_terminated(sentence: str) -> bool:
    """Return whether a segment ends in terminal punctuation."""
    return bool(
        re.search(
            r"""[.!?]["'”’)\]]*$""",
            sentence.rstrip(),
        )
    )


def _truncate_at_sentence_boundary(
    text: str,
    maximum_characters: int,
) -> tuple[str, bool]:
    """
    Bound text by characters, preferring a complete sentence boundary.

    If no complete sentence boundary exists within the limit, prefer a
    whitespace boundary to avoid cutting through a word. A hard character
    cut is used only when no suitable whitespace boundary exists.
    """
    if maximum_characters < 1:
        raise ValueError("maximum_characters must be positive")

    if len(text) <= maximum_characters:
        return text, False

    candidate = text[:maximum_characters]
    spans = _sentence_spans(candidate)

    for _, end, sentence in reversed(spans):
        # The boundary must be followed by whitespace in the original text.
        # This prevents a character-limit cut from masquerading as a
        # genuine sentence boundary.
        if (
            end < len(text)
            and text[end].isspace()
            and _is_sentence_terminated(sentence)
        ):
            return text[:end].rstrip(), True

    # No suitable sentence boundary was found. Avoid cutting a word when
    # possible. The limit remains a strict upper bound.
    whitespace_positions = [
        candidate.rfind(" "),
        candidate.rfind("\n"),
        candidate.rfind("\t"),
    ]

    boundary = max(whitespace_positions)

    if boundary > 0:
        return candidate[:boundary].rstrip(), True

    return candidate, True


def _limit_sentences(
    text: str,
    sentences: list[tuple[int, int, str]],
    maximum_sentences: int,
) -> tuple[str, list[tuple[int, int, str]], bool]:
    """
    Limit the number of sentence-like segments without reconstructing text.

    Returns the retained text, retained spans, and whether content was
    discarded because of the sentence limit.
    """
    if maximum_sentences < 1:
        raise ValueError("maximum_sentences must be positive")

    if len(sentences) <= maximum_sentences:
        return text, sentences, False

    end = sentences[maximum_sentences - 1][1]
    bounded_text = text[:end].rstrip()

    retained_sentences = sentences[:maximum_sentences]

    return bounded_text, retained_sentences, True


def _build_semantic_chunks(
    sentences: list[str],
    maximum_chunks: int,
) -> tuple[tuple[str, ...], bool]:
    """
    Group sentences into at most maximum_chunks.

    The Boolean indicates whether aggregation into fewer chunks occurred.
    Aggregation does not discard sentences and is not content truncation.
    """
    if maximum_chunks < 1:
        raise ValueError("maximum_chunks must be positive")

    usable_sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence and sentence.strip()
    ]

    if not usable_sentences:
        return (), False

    if len(usable_sentences) <= maximum_chunks:
        return tuple(usable_sentences), False

    chunk_count = maximum_chunks
    base_size, remainder = divmod(
        len(usable_sentences),
        chunk_count,
    )

    chunks: list[str] = []
    index = 0

    for chunk_index in range(chunk_count):
        size = base_size + (1 if chunk_index < remainder else 0)

        chunk = " ".join(
            usable_sentences[index : index + size]
        ).strip()

        if chunk:
            chunks.append(chunk)

        index += size

    return tuple(chunks), True


def preprocess_text(text: str) -> PreprocessedText:
    """
    Normalize and safely bound user-provided content.

    Character semantics:

    - received_characters:
        Length of the raw input.
    - original_characters:
        Length after Unicode normalization and text cleanup, before
        analysis truncation.
    - analyzed_characters:
        Exact length of the final text passed to analysis.
    - truncated:
        True only when characters or sentence-like segments were discarded.
    - truncation_reason:
        "characters", "sentences", or None.

    Semantic chunk aggregation is handled separately and does not mark the
    original content as truncated.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    received_characters = len(text)

    if received_characters > MAX_REQUEST_CHARACTERS:
        raise ValueError(
            "Input exceeds the maximum request size of "
            f"{MAX_REQUEST_CHARACTERS} characters."
        )

    normalized = normalize_text(text)
    cleaned = _clean_text(normalized)

    original_characters = len(cleaned)

    if not cleaned:
        return PreprocessedText(
            received_characters=received_characters,
            original_characters=0,
            analyzed_characters=0,
            text="",
            sentences=(),
            truncated=False,
            truncation_reason=None,
        )

    bounded_text, character_truncated = (
        _truncate_at_sentence_boundary(
            cleaned,
            MAX_ANALYSIS_CHARACTERS,
        )
    )

    sentence_spans = _sentence_spans(bounded_text)

    bounded_text, sentence_spans, sentence_truncated = (
        _limit_sentences(
            bounded_text,
            sentence_spans,
            MAX_ANALYZED_SENTENCES,
        )
    )

    sentences = tuple(
        sentence
        for _, _, sentence in sentence_spans
    )

    analyzed_characters = len(bounded_text)

    if character_truncated:
        truncation_reason = "characters"
    elif sentence_truncated:
        truncation_reason = "sentences"
    else:
        truncation_reason = None

    return PreprocessedText(
        received_characters=received_characters,
        original_characters=original_characters,
        analyzed_characters=analyzed_characters,
        text=bounded_text,
        sentences=sentences,
        truncated=character_truncated or sentence_truncated,
        truncation_reason=truncation_reason,
    )


def build_semantic_chunks(
    sentences: tuple[str, ...],
) -> tuple[tuple[str, ...], bool]:
    """
    Build bounded semantic chunks for embedding-based analysis.

    The Boolean reports whether sentences were aggregated into fewer chunks.
    It does not mean that original sentences were discarded.
    """
    return _build_semantic_chunks(
        list(sentences),
        MAX_SEMANTIC_CHUNKS,
    )