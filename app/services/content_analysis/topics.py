from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import re

import numpy as np
from keybert import KeyBERT

from app.services.content_analysis.embeddings import generate_embeddings
from app.services.content_analysis.model_manager import ModelManager


logger = logging.getLogger(__name__)

MAX_KEYPHRASES = 20
MAX_TOPICS = 10
TOPIC_REDUNDANCY_THRESHOLD = 0.85

# Largest amount by which a cosine-similarity score may exceed 1.0 and still
# be treated as float32 rounding noise. It matches the 4-decimal precision
# of reported scores. Anything larger is a genuinely invalid score.
SCORE_OVERSHOOT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class KeyphraseResult:
    phrase: str
    score: float


@dataclass(frozen=True)
class TopicResult:
    topic: str
    score: float


def _normalize_phrase(phrase: str) -> str:
    """Normalize whitespace and case for duplicate detection."""
    return " ".join(phrase.split()).casefold()


def _sanitize_score(value: object) -> float | None:
    """
    Return a schema-safe score in [0.0, 1.0], or None if unusable.

    The response schema (TopicItem / KeyConceptItem) requires
    ``0.0 <= score <= 1.0``. KeyBERT scores are cosine similarities in
    [-1, 1]:

    * Negative values point away from the document and carry no relevance
      evidence, so they are rejected rather than reported.
    * NaN, infinity and non-numeric values are rejected.
    * Values in (1.0, 1.0 + SCORE_OVERSHOOT_TOLERANCE] are float rounding
      noise on a perfect match and are clamped to 1.0.
    * Larger values cannot come from a cosine similarity, so they signal a
      real defect upstream and are rejected, not hidden by clamping.
    * Scores already in [0, 1] are returned unchanged; -0.0 becomes 0.0.
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(score) or score < 0.0:
        return None

    if score > 1.0 + SCORE_OVERSHOOT_TOLERANCE:
        return None

    return min(score, 1.0) + 0.0


def _valid_candidates(
    keyphrases: list[KeyphraseResult],
) -> list[KeyphraseResult]:
    """Remove empty phrases and exact duplicates while preserving ranking."""
    seen: set[str] = set()
    candidates: list[KeyphraseResult] = []

    for keyphrase in keyphrases:
        if not isinstance(keyphrase.phrase, str):
            continue

        normalized = _normalize_phrase(keyphrase.phrase)

        if not normalized or normalized in seen:
            continue

        safe_score = _sanitize_score(keyphrase.score)

        if safe_score is None:
            continue

        seen.add(normalized)

        if safe_score != keyphrase.score:
            keyphrase = KeyphraseResult(
                phrase=keyphrase.phrase,
                score=safe_score,
            )

        candidates.append(keyphrase)

        if len(candidates) >= MAX_KEYPHRASES:
            break

    return candidates



_VERB_POS = {"VERB", "AUX"}
_NOUN_POS = {"NOUN", "PROPN"}
_TECHNICAL_COMPOUNDS = {
    ("ai", "powered"), ("ai", "based"), ("ai", "driven"),
    ("ai", "assisted"), ("ml", "based"), ("ml", "driven"),
    ("nlp", "based"),
}


@dataclass(frozen=True)
class _SourceWord:
    word: str
    pos: str
    tag: str
    segment: int
    hyphen_joined: bool


def _lexical_tokens(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", value.casefold())


def _is_intra_word_hyphen(tokens: list, index: int) -> bool:
    """True for a hyphen with a word character touching it on both sides."""
    token = tokens[index]
    if token.text not in {"-", "\u2010"} or index == 0:
        return False
    if index + 1 >= len(tokens):
        return False

    previous, following = tokens[index - 1], tokens[index + 1]
    word = r"[^\W_]"

    return (
        previous.idx + len(previous.text) == token.idx
        and following.idx == token.idx + len(token.text)
        and re.search(word, previous.text) is not None
        and re.search(word, following.text) is not None
    )


def _source_words(doc) -> list[_SourceWord]:
    """
    Flatten a spaCy doc into lexical words tagged with a segment number.

    The segment increments at every punctuation token and every line break,
    so words in different segments can never be matched as one phrase.
    Intra-word hyphens (AI-powered) do not start a new segment.

    Boundaries are derived from character offsets and token text rather
    than from spaCy's whitespace-token behaviour.
    """
    text = doc.text
    tokens = list(doc)
    words: list[_SourceWord] = []
    segment = 0
    previous_end = 0
    hyphen_pending = False

    for index, token in enumerate(tokens):
        gap = text[previous_end:token.idx]
        previous_end = token.idx + len(token.text)

        if "\n" in gap or "\r" in gap:
            segment += 1
            hyphen_pending = False

        if token.is_space:
            if "\n" in token.text or "\r" in token.text:
                segment += 1
                hyphen_pending = False
            continue

        parts = _lexical_tokens(token.text)

        if not parts:
            if _is_intra_word_hyphen(tokens, index):
                hyphen_pending = True
            else:
                segment += 1
                hyphen_pending = False
            continue

        for position, part in enumerate(parts):
            words.append(
                _SourceWord(
                    word=part,
                    pos=token.pos_,
                    tag=token.tag_,
                    segment=segment,
                    hyphen_joined=hyphen_pending or position > 0,
                )
            )
        hyphen_pending = False

    return words


_FINITE_VERB_TAGS = {"VBZ", "VBP", "VBD", "MD"}


def _is_plural_noun_misread(
    window: list[_SourceWord],
    following: _SourceWord | None,
) -> bool:
    """
    Decide whether a verb-tagged final word is really a plural noun.

    en_core_web_sm sometimes tags a plural noun as a present-tense verb
    when a real verb follows it ("algorithms" in "Machine learning
    algorithms help analyze ..."). The evidence comes from the original
    source context, not from re-tagging the phrase in isolation:

    * the word is tagged VBZ/VBP and looks plural (ends in "s");
    * a noun precedes it inside the phrase; and
    * the next word in the same segment is itself a finite verb.

    Two finite verbs cannot be adjacent in one clause, so the earlier
    one must be the noun. A genuine verb such as "helps" in "Natural
    language processing helps analyze ..." is followed by an infinitive
    (VB), a noun, or nothing, so it is never reclassified.
    """
    last = window[-1]

    return (
        last.tag in {"VBZ", "VBP"}
        and last.word.endswith("s")
        and any(word.pos in _NOUN_POS for word in window[:-1])
        and following is not None
        and following.pos in _VERB_POS
        and following.tag in _FINITE_VERB_TAGS
    )


def _occurrence_is_valid(
    window: list[_SourceWord],
    previous: _SourceWord | None,
    phrase_tokens: list[str],
    model_manager: ModelManager | None = None,
    following: _SourceWord | None = None,
) -> bool:
    """
    Validate one occurrence of a phrase using source-context POS data.

    ``previous`` and ``following`` are the neighbouring words in the same
    segment (or None). ``model_manager`` is kept for interface
    compatibility; no additional spaCy processing is performed here.
    """
    if tuple(phrase_tokens[:2]) in _TECHNICAL_COMPOUNDS:
        return window[-1].pos in _NOUN_POS

    first, last = window[0], window[-1]

    # A leading verb is acceptable only as a participial modifier,
    # such as "running costs", not as a progressive predicate.
    if first.pos in _VERB_POS:
        is_modifier = (
            first.tag in {"VBG", "VBN"}
            and window[1].pos in _NOUN_POS
            and (previous is None or previous.pos != "AUX")
        )
        if not is_modifier:
            return False

    # Reject clauses containing an interior verb, except for the
    # second component of a hyphenated compound.
    for word in window[1:-1]:
        if word.pos in _VERB_POS and not word.hyphen_joined:
            return False

    # A phrase may not end on a verb unless source context shows that
    # the verb tag is a misread plural noun.
    if last.pos in _VERB_POS:
        return _is_plural_noun_misread(window, following)

    return any(word.pos in _NOUN_POS for word in window)


class _SourceAnalysis:
    """
    Lazily parsed view of one source document for one extraction call.

    The document is parsed with spaCy at most once, on first use of
    ``words``, and the flattened words are reused for every later
    candidate. Nothing is parsed if no candidate reaches validation. An
    instance belongs to a single ``extract_keyphrases`` call and is never
    stored at module level or shared between requests.
    """

    __slots__ = ("_text", "_model_manager", "_words")

    def __init__(self, text: str, model_manager: ModelManager) -> None:
        self._text = text
        self._model_manager = model_manager
        self._words: list[_SourceWord] | None = None

    @property
    def words(self) -> list[_SourceWord]:
        if self._words is None:
            self._words = _source_words(self._model_manager.nlp(self._text))

        return self._words


def _is_quality_keyphrase(
    phrase: str,
    model_manager: ModelManager,
    source_text: str | None = None,
    *,
    source_analysis: _SourceAnalysis | None = None,
) -> bool:
    """
    Validate source-grounded keyphrases and reject obvious fragments.

    ``source_analysis`` is optional. When supplied, its already-parsed
    words are used instead of parsing ``source_text`` again; direct calls
    without it behave exactly as before.
    """
    if not isinstance(phrase, str) or not phrase.strip():
        return False

    phrase_tokens = _lexical_tokens(phrase)
    if not 2 <= len(phrase_tokens) <= 3:
        return False

    if source_analysis is not None:
        words = source_analysis.words
    else:
        text_to_analyze = source_text if source_text is not None else phrase
        words = _source_words(model_manager.nlp(text_to_analyze))

    size = len(phrase_tokens)

    # Every occurrence is considered; one valid occurrence is enough.
    for start in range(len(words) - size + 1):
        window = words[start:start + size]

        if [w.word for w in window] != phrase_tokens:
            continue

        # Never match across punctuation, sentence or line boundaries.
        if window[0].segment != window[-1].segment:
            continue

        previous = None
        if start > 0 and words[start - 1].segment == window[0].segment:
            previous = words[start - 1]

        following = None
        end = start + size
        if end < len(words) and words[end].segment == window[-1].segment:
            following = words[end]

        if _occurrence_is_valid(
            window,
            previous,
            phrase_tokens,
            model_manager,
            following=following,
        ):
            return True

    return False


def extract_keyphrases(
    text: str,
    model_manager: ModelManager,
) -> list[KeyphraseResult]:
    """
    Extract relevant keyphrases using KeyBERT and the shared models.
    """
    if not text.strip():
        return []

    keybert_model = KeyBERT(model=model_manager.embeddings)

    results = keybert_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 3),
        stop_words="english",
        use_mmr=True,
        diversity=0.5,
        top_n=MAX_KEYPHRASES * 5,
    )

    candidates: list[KeyphraseResult] = []
    seen: set[str] = set()

    # Parsed lazily and at most once for this call (see _SourceAnalysis).
    source_analysis = _SourceAnalysis(text, model_manager)

    for phrase, score in results:
        if not isinstance(phrase, str):
            continue

        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            continue

        safe_score = _sanitize_score(numeric_score)

        if safe_score is None:
            continue

        normalized = _normalize_phrase(phrase)

        if not normalized or normalized in seen:
            continue

        if not _is_quality_keyphrase(
            phrase,
            model_manager,
            text,
            source_analysis=source_analysis,
        ):
            continue

        seen.add(normalized)

        candidates.append(
            KeyphraseResult(
                phrase=phrase,
                score=round(safe_score, 4),
            )
        )

        if len(candidates) >= MAX_KEYPHRASES:
            break

        

    return candidates


def _normalized_topic_embeddings(
    raw_embeddings: object,
    expected_rows: int,
) -> np.ndarray:
    """
    Validate topic embeddings and return unit-length float32 row vectors.

    Raises ``ValueError`` for anything unusable: a wrong shape or row
    count, an empty width, non-finite elements, zero-length vectors, or a
    norm that is not finite and positive.

    Norms are accumulated in float64. Every finite float32 value squares
    safely in float64, so a row of large but finite float32 values (whose
    float32 norm would overflow to infinity) is normalised correctly, and
    a row of tiny float32 values is not mistaken for a zero vector.
    Nothing is suppressed: the checks below reject any result that still
    is not a finite, positive norm.
    """
    embeddings = np.asarray(raw_embeddings, dtype=np.float32)

    if (
        embeddings.ndim != 2
        or embeddings.shape[0] != expected_rows
        or embeddings.shape[1] == 0
        or not np.isfinite(embeddings).all()
    ):
        raise ValueError(
            "Topic embeddings have an invalid shape or contain "
            "non-finite values."
        )

    wide = embeddings.astype(np.float64)
    norms = np.linalg.norm(wide, axis=1)

    if not np.isfinite(norms).all():
        raise ValueError("Topic embeddings have a non-finite vector norm.")

    if np.any(norms <= 0):
        raise ValueError("Topic embeddings contain zero-length vectors.")

    normalized = (wide / norms[:, np.newaxis]).astype(np.float32)

    if not np.isfinite(normalized).all():
        raise ValueError("Normalized topic embeddings are not finite.")

    return normalized


def extract_topics(
    keyphrases: list[KeyphraseResult],
    model_manager: ModelManager | None = None,
) -> list[TopicResult]:
    """
    Select ranked, non-redundant topics using the shared MiniLM embeddings.

    If semantic filtering fails, retain the safely deduplicated candidates
    and log the failure rather than pretending semantic filtering succeeded.
    """
    candidates = _valid_candidates(keyphrases)

    if not candidates:
        return []

    if model_manager is None:
        from app.services.content_analysis.model_manager import (
            get_model_manager,
        )

        model_manager = get_model_manager()

    try:
        embedding_result = generate_embeddings(
            [candidate.phrase for candidate in candidates],
            model_manager,
        )

        embeddings = _normalized_topic_embeddings(
            embedding_result.embeddings,
            len(candidates),
        )

    except Exception as exc:
        logger.warning(
            "Semantic topic filtering failed for %d candidate(s) (%s); "
            "returning deduplicated keyphrases without semantic filtering.",
            len(candidates),
            type(exc).__name__,
        )
        return [
            TopicResult(topic=item.phrase, score=item.score)
            for item in candidates[:MAX_TOPICS]
        ]

    selected_indices: list[int] = []

    for index, candidate_embedding in enumerate(embeddings):
        is_redundant = any(
            float(np.dot(candidate_embedding, embeddings[selected_index]))
            >= TOPIC_REDUNDANCY_THRESHOLD
            for selected_index in selected_indices
        )

        if is_redundant:
            continue

        selected_indices.append(index)

        if len(selected_indices) >= MAX_TOPICS:
            break

    return [
        TopicResult(
            topic=candidates[index].phrase,
            score=candidates[index].score,
        )
        for index in selected_indices
    ]