from __future__ import annotations

import logging
import re
from types import SimpleNamespace

import numpy as np
import pytest

from app.services.content_analysis.model_manager import ModelManager
from app.services.content_analysis.topics import (
    MAX_KEYPHRASES,
    MAX_TOPICS,
    KeyphraseResult,
    TopicResult,
    extract_keyphrases,
    extract_topics,
)


def test_extract_keyphrases() -> None:
    manager = ModelManager()

    text = (
        "Artificial intelligence helps businesses analyze website content. "
        "Machine learning models can identify important concepts, topics, "
        "and semantic relationships in large collections of text."
    )

    results = extract_keyphrases(text, manager)

    assert results
    assert len(results) <= MAX_KEYPHRASES

    for result in results:
        assert result.phrase.strip()
        assert 0.0 <= result.score <= 1.0


def test_extract_keyphrases_empty_text() -> None:
    manager = ModelManager()

    assert extract_keyphrases("", manager) == []


def test_extract_topics() -> None:
    keyphrases = [
        KeyphraseResult("artificial intelligence", 0.91),
        KeyphraseResult("machine learning", 0.88),
        KeyphraseResult("website content", 0.80),
    ]

    topics = extract_topics(keyphrases)

    assert len(topics) == 3
    assert topics[0].topic == "artificial intelligence"


def test_extract_topics_removes_duplicates() -> None:
    keyphrases = [
        KeyphraseResult("Artificial Intelligence", 0.91),
        KeyphraseResult("artificial intelligence", 0.85),
        KeyphraseResult("machine learning", 0.80),
    ]

    topics = extract_topics(keyphrases)

    assert len(topics) == 2


def test_topics_are_bounded() -> None:
    keyphrases = [
        KeyphraseResult(f"topic {index}", 0.5)
        for index in range(MAX_KEYPHRASES)
    ]

    topics = extract_topics(keyphrases)

    assert len(topics) <= MAX_TOPICS

def test_extract_topics_removes_redundant_phrases() -> None:
    keyphrases = [
        KeyphraseResult("artificial intelligence", 0.91),
        KeyphraseResult("artificial intelligence systems", 0.89),
        KeyphraseResult("machine learning", 0.85),
        KeyphraseResult("machine learning models", 0.82),
    ]

    topics = extract_topics(keyphrases)

    topic_names = [topic.topic.casefold() for topic in topics]

    assert "artificial intelligence" in topic_names
    assert "machine learning" in topic_names
    assert len(topics) < len(keyphrases)


def test_extract_topics_ignores_empty_phrases() -> None:
    keyphrases = [
        KeyphraseResult("", 0.95),
        KeyphraseResult("   ", 0.90),
        KeyphraseResult("machine learning", 0.85),
    ]

    topics = extract_topics(keyphrases)

    assert len(topics) == 1
    assert topics[0].topic == "machine learning"

def test_quality_keyphrase_preserves_technical_phrases() -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    manager = ModelManager()
    source = (
        "Artificial intelligence is transforming healthcare. "
        "Hospitals are adopting AI-powered systems to improve patient care. "
        "Machine learning algorithms help analyze medical images. "
        "Natural language processing analyzes clinical documents."
    )

    phrases = [
        "artificial intelligence",
        "machine learning algorithms",
        "natural language processing",
        "medical images",
        "patient care",
        "ai powered systems",
    ]

    for phrase in phrases:
        assert _is_quality_keyphrase(phrase, manager, source), phrase


def test_quality_keyphrase_rejects_obvious_fragments() -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    manager = ModelManager()
    source = (
        "Artificial intelligence is transforming healthcare. "
        "Hospitals are adopting AI-powered systems."
    )

    phrases = [
        "intelligence transforming healthcare",
        "transforming healthcare hospitals",
        "hospitals adopting ai",
    ]

    for phrase in phrases:
        assert not _is_quality_keyphrase(phrase, manager, source), phrase


def test_extract_keyphrases_excludes_obvious_fragments() -> None:
    from app.services.content_analysis.topics import extract_keyphrases

    manager = ModelManager()

    text = (
        "Artificial intelligence is transforming healthcare. "
        "Hospitals are adopting AI-powered systems to improve patient care. "
        "Machine learning algorithms help healthcare professionals detect "
        "patterns in medical images. "
        "Natural language processing helps analyze clinical documents. "
        "Healthcare organizations must address data privacy and reliability."
    )

    results = extract_keyphrases(text, manager)
    phrases = {result.phrase.casefold() for result in results}

    assert "machine learning algorithms" in phrases
    assert "artificial intelligence" in phrases
    assert "natural language processing" in phrases
    assert "medical images" in phrases

    assert "algorithms help healthcare" not in phrases
    assert "healthcare professionals detect" not in phrases
    assert "language processing helps" not in phrases


# ---------------------------------------------------------------------------
# Keyphrase validator: POS handling, sentence boundaries, occurrences
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def validator_manager() -> ModelManager:
    return ModelManager()


def test_quality_keyphrase_allows_participial_modifiers(
    validator_manager: ModelManager,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    source = (
        "The team tracks running costs. "
        "Trained models need data. "
        "Fine-tuned language models improve results. "
        "Companies use data-driven decisions."
    )

    for phrase in (
        "running costs",
        "trained models",
        "fine tuned language",
        "data driven decisions",
    ):
        assert _is_quality_keyphrase(
            phrase, validator_manager, source
        ), phrase


def test_quality_keyphrase_rejects_predicate_verb_fragments(
    validator_manager: ModelManager,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    source = (
        "AI is transforming healthcare. "
        "Algorithms help healthcare professionals detect patterns. "
        "We aim to improve patient care."
    )

    for phrase in (
        "transforming healthcare",
        "healthcare professionals detect",
        "improve patient care",
        "algorithms help healthcare",
    ):
        assert not _is_quality_keyphrase(
            phrase, validator_manager, source
        ), phrase


def test_quality_keyphrase_does_not_cross_sentence_boundary(
    validator_manager: ModelManager,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    source = "Models improve accuracy. Healthcare data matters."

    # "accuracy. Healthcare" would match if punctuation were skipped.
    assert not _is_quality_keyphrase(
        "improve accuracy healthcare", validator_manager, source
    )
    assert not _is_quality_keyphrase(
        "accuracy healthcare data", validator_manager, source
    )


def test_quality_keyphrase_does_not_cross_comma(
    validator_manager: ModelManager,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    source = "Consider the images, machine learning is new."

    assert not _is_quality_keyphrase(
        "images machine learning", validator_manager, source
    )


@pytest.mark.parametrize(
    "separator",
    ["\n", "\n\n", " \n", "\n  ", "\r\n"],
)
def test_quality_keyphrase_does_not_cross_line_break(
    validator_manager: ModelManager,
    separator: str,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    # spaCy emits each line break as its own whitespace token. Without
    # newline handling the words below would match as one noun phrase.
    source = f"Clinical data{separator}Machine learning"

    assert not _is_quality_keyphrase(
        "data machine learning", validator_manager, source
    )

    # The same words on one line still match, so the check above is
    # failing because of the line break and nothing else.
    assert _is_quality_keyphrase(
        "data machine learning",
        validator_manager,
        "Clinical data Machine learning",
    )


def test_quality_keyphrase_considers_all_occurrences(
    validator_manager: ModelManager,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    # First occurrence is a predicate ("is transforming healthcare");
    # the second is a valid modifier + noun.
    source = (
        "AI is transforming healthcare. "
        "Transforming healthcare requires careful planning."
    )

    assert _is_quality_keyphrase(
        "transforming healthcare", validator_manager, source
    )

    only_predicate = "AI is transforming healthcare."

    assert not _is_quality_keyphrase(
        "transforming healthcare", validator_manager, only_predicate
    )


def test_quality_keyphrase_handles_plural_noun_tagged_as_verb(
    validator_manager: ModelManager,
) -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    # en_core_web_sm tags "algorithms" as VBZ when "help" follows it.
    source = "Machine learning algorithms help analyze medical images."

    assert _is_quality_keyphrase(
        "machine learning algorithms", validator_manager, source
    )

    # A genuine verb followed by a base-form verb is still rejected.
    verb_source = "Natural language processing helps analyze clinical documents."

    assert not _is_quality_keyphrase(
        "language processing helps", validator_manager, verb_source
    )


# ---------------------------------------------------------------------------
# Plural-noun misread: deterministic unit tests on source-context evidence
# ---------------------------------------------------------------------------


def _word(word: str, pos: str, tag: str):
    from app.services.content_analysis.topics import _SourceWord

    return _SourceWord(
        word=word, pos=pos, tag=tag, segment=0, hyphen_joined=False
    )


def test_plural_noun_misread_accepted_when_followed_by_finite_verb() -> None:
    from app.services.content_analysis.topics import _occurrence_is_valid

    window = [
        _word("machine", "NOUN", "NN"),
        _word("learning", "NOUN", "NN"),
        _word("algorithms", "VERB", "VBZ"),  # misread plural noun
    ]
    following = _word("help", "VERB", "VBP")

    assert _occurrence_is_valid(
        window,
        None,
        ["machine", "learning", "algorithms"],
        following=following,
    )


def test_genuine_verb_rejected_when_followed_by_infinitive() -> None:
    from app.services.content_analysis.topics import _occurrence_is_valid

    window = [
        _word("language", "NOUN", "NN"),
        _word("processing", "NOUN", "NN"),
        _word("helps", "VERB", "VBZ"),
    ]

    for following in (_word("analyze", "VERB", "VB"), None):
        assert not _occurrence_is_valid(
            window,
            None,
            ["language", "processing", "helps"],
            following=following,
        )


def test_non_plural_verb_never_treated_as_noun() -> None:
    from app.services.content_analysis.topics import _occurrence_is_valid

    window = [
        _word("healthcare", "NOUN", "NN"),
        _word("professionals", "NOUN", "NNS"),
        _word("detect", "VERB", "VBP"),
    ]

    assert not _occurrence_is_valid(
        window,
        None,
        ["healthcare", "professionals", "detect"],
        following=_word("patterns", "NOUN", "NNS"),
    )


def test_two_word_window_with_verb_tail_follows_same_rule() -> None:
    from app.services.content_analysis.topics import _occurrence_is_valid

    window = [_word("processing", "NOUN", "NN"), _word("helps", "VERB", "VBZ")]

    assert not _occurrence_is_valid(
        window, None, ["processing", "helps"], following=None
    )


# ---------------------------------------------------------------------------
# Stage 1B: keyphrase limit and score handling
#
# KeyBERT and the Stage 1A validator are stubbed so these tests are
# deterministic and isolate limit/score logic from model behaviour.
# ---------------------------------------------------------------------------


class _FakeKeyBERT:
    results: list = []

    def __init__(self, model=None) -> None:
        pass

    def extract_keywords(self, text, **kwargs):
        return list(type(self).results)


def _run_extract(monkeypatch, results):
    import types

    from app.services.content_analysis import topics as topics_module

    _FakeKeyBERT.results = results
    monkeypatch.setattr(topics_module, "KeyBERT", _FakeKeyBERT)
    monkeypatch.setattr(
        topics_module, "_is_quality_keyphrase", lambda *args, **kwargs: True
    )
    manager = types.SimpleNamespace(embeddings=None, nlp=None)

    return topics_module.extract_keyphrases("some source text", manager)


def test_keyphrase_limit_is_enforced(monkeypatch) -> None:
    results = [
        (f"topic{index} words", 0.9 - index * 0.01)
        for index in range(MAX_KEYPHRASES * 3)
    ]

    output = _run_extract(monkeypatch, results)

    assert len(output) == MAX_KEYPHRASES
    # Existing ranking is preserved: the first N candidates are kept.
    assert [r.phrase for r in output] == [p for p, _ in results[:MAX_KEYPHRASES]]


def test_keyphrase_limit_exact_boundary(monkeypatch) -> None:
    results = [(f"topic{i} words", 0.5) for i in range(MAX_KEYPHRASES)]

    assert len(_run_extract(monkeypatch, results)) == MAX_KEYPHRASES


def test_fewer_candidates_than_limit(monkeypatch) -> None:
    results = [(f"topic{i} words", 0.5) for i in range(5)]

    assert len(_run_extract(monkeypatch, results)) == 5


def test_negative_scores_are_never_returned(monkeypatch) -> None:
    results = [
        ("alpha beta", 0.8),
        ("gamma delta", -0.2),
        ("epsilon zeta", -0.0001),
        ("eta theta", 0.3),
    ]

    output = _run_extract(monkeypatch, results)

    assert [r.phrase for r in output] == ["alpha beta", "eta theta"]
    assert all(0.0 <= r.score <= 1.0 for r in output)


def test_negative_scores_do_not_consume_limit_slots(monkeypatch) -> None:
    results = [(f"neg{i} word", -0.1) for i in range(10)] + [
        (f"pos{i} word", 0.5) for i in range(MAX_KEYPHRASES * 2)
    ]

    output = _run_extract(monkeypatch, results)

    assert len(output) == MAX_KEYPHRASES
    assert all(r.phrase.startswith("pos") for r in output)


def test_all_negative_scores_return_empty(monkeypatch) -> None:
    assert _run_extract(monkeypatch, [("alpha beta", -0.5)]) == []


def test_zero_and_positive_scores_are_preserved(monkeypatch) -> None:
    import math

    results = [
        ("alpha beta", 0.91234),
        ("gamma delta", 0.0),
        ("epsilon zeta", -0.0),
    ]

    output = _run_extract(monkeypatch, results)
    scores = {r.phrase: r.score for r in output}

    assert scores["alpha beta"] == 0.9123
    assert scores["gamma delta"] == 0.0
    assert scores["epsilon zeta"] == 0.0
    assert math.copysign(1.0, scores["epsilon zeta"]) == 1.0


def test_score_overshoot_is_clamped_to_one(monkeypatch) -> None:
    output = _run_extract(
        monkeypatch,
        [
            ("alpha beta", 1.0000001),
            ("invalid phrase", 1.00005),
        ],
    )

    assert len(output) == 1
    assert output[0].phrase == "alpha beta"
    assert output[0].score == 1.0


def test_score_boundaries_in_extraction(monkeypatch) -> None:
    results = [
        ("exact one", 1.0),
        ("tiny overshoot", 1.0000001),
        ("too high", 1.5),
        ("just too high", 1.001),
        ("exact zero", 0.0),
    ]

    output = _run_extract(monkeypatch, results)

    assert [(r.phrase, r.score) for r in output] == [
        ("exact one", 1.0),
        ("tiny overshoot", 1.0),
        ("exact zero", 0.0),
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, 0.0),
        (-0.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
        (1.0000001, 1.0),
        (1.00005, None),
        (1.001, None),
        (1.5, None),
        (-1e-9, None),
        (-0.5, None),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
        ("abc", None),
        (None, None),
    ],
)
def test_sanitize_score_boundaries(value, expected) -> None:
    import math

    from app.services.content_analysis.topics import _sanitize_score

    result = _sanitize_score(value)

    assert result == expected
    if result == 0.0:
        assert math.copysign(1.0, result) == 1.0


def test_valid_candidates_reject_substantially_invalid_scores() -> None:
    from app.services.content_analysis.topics import _valid_candidates

    candidates = _valid_candidates(
        [
            KeyphraseResult("alpha beta", 1.5),
            KeyphraseResult("gamma delta", 1.0000001),
            KeyphraseResult("epsilon zeta", 0.4),
        ]
    )

    assert [(c.phrase, c.score) for c in candidates] == [
        ("gamma delta", 1.0),
        ("epsilon zeta", 0.4),
    ]


def test_returned_scores_satisfy_response_schema(monkeypatch) -> None:
    from app.schemas.content_analysis import KeyConceptItem, TopicItem

    results = [
        ("alpha beta", 0.9),
        ("gamma delta", -0.4),
        ("epsilon zeta", 1.0000001),
        ("eta theta", 1.5),
        ("iota kappa", 0.0),
        ("lambda mu", float("nan")),
    ]

    output = _run_extract(monkeypatch, results)

    assert output
    for item in output:
        # Raises pydantic.ValidationError if the score violates ge/le.
        KeyConceptItem(phrase=item.phrase, score=item.score)
        TopicItem(phrase=item.phrase, score=item.score)


def test_non_finite_scores_are_skipped(monkeypatch) -> None:
    results = [
        ("alpha beta", float("nan")),
        ("gamma delta", float("inf")),
        ("epsilon zeta", float("-inf")),
        ("eta theta", 0.4),
    ]

    output = _run_extract(monkeypatch, results)

    assert [r.phrase for r in output] == ["eta theta"]


def test_ranking_order_preserved_after_score_handling(monkeypatch) -> None:
    results = [
        ("alpha beta", 0.9),
        ("gamma delta", 0.3),
        ("epsilon zeta", -0.2),
        ("eta theta", 0.5),
        ("iota kappa", 0.0),
    ]

    output = _run_extract(monkeypatch, results)

    # KeyBERT/MMR order is kept as-is; only invalid entries are removed.
    assert [r.phrase for r in output] == [
        "alpha beta",
        "gamma delta",
        "eta theta",
        "iota kappa",
    ]


def test_topic_candidates_reject_negative_scores() -> None:
    from app.services.content_analysis.topics import _valid_candidates

    candidates = _valid_candidates(
        [
            KeyphraseResult("alpha beta", 0.7),
            KeyphraseResult("gamma delta", -0.3),
            KeyphraseResult("epsilon zeta", 0.0),
        ]
    )

    assert [c.phrase for c in candidates] == ["alpha beta", "epsilon zeta"]


def test_stage_1a_validation_still_applies_with_score_handling(
    monkeypatch, validator_manager: ModelManager
) -> None:
    from app.services.content_analysis import topics as topics_module

    source = (
        "Artificial intelligence is transforming healthcare. "
        "Machine learning algorithms help healthcare professionals detect "
        "patterns in medical images. "
        "Natural language processing helps analyze clinical documents."
    )
    _FakeKeyBERT.results = [
        ("artificial intelligence", 0.9),
        ("algorithms help healthcare", 0.8),
        ("language processing helps", 0.7),
        ("machine learning algorithms", 0.6),
        ("medical images", -0.1),
    ]
    monkeypatch.setattr(topics_module, "KeyBERT", _FakeKeyBERT)

    class _Manager:
        embeddings = None
        nlp = staticmethod(validator_manager.nlp)

    output = topics_module.extract_keyphrases(source, _Manager())

    assert [r.phrase for r in output] == [
        "artificial intelligence",
        "machine learning algorithms",
    ]

# ---------------------------------------------------------------------------
# Stage 1C-1: the source document is parsed at most once per extraction
#
# A fake spaCy callable counts parses and builds minimal doc objects, so
# these tests are deterministic and need no downloaded models.
# ---------------------------------------------------------------------------

_LEXICON = {
    "improve": ("VERB", "VBP"),
    "improves": ("VERB", "VBZ"),
    "helps": ("VERB", "VBZ"),
    ".": ("PUNCT", "."),
    ",": ("PUNCT", ","),
}


class _FakeToken:
    def __init__(self, text: str, idx: int) -> None:
        self.text = text
        self.idx = idx
        self.is_space = False
        self.pos_, self.tag_ = _LEXICON.get(text.casefold(), ("NOUN", "NN"))


class _FakeDoc:
    def __init__(self, text: str) -> None:
        self.text = text
        self._tokens = [
            _FakeToken(match.group(), match.start())
            for match in re.finditer(r"\w+|[^\w\s]", text)
        ]

    def __iter__(self):
        return iter(self._tokens)


class _CountingNlp:
    """Callable standing in for a spaCy pipeline; records every parse."""

    def __init__(self) -> None:
        self.parsed: list[str] = []

    def __call__(self, text: str) -> _FakeDoc:
        self.parsed.append(text)
        return _FakeDoc(text)


_PARSE_SOURCE = (
    "Machine learning models improve data quality. "
    "Careful data quality checks help teams."
)


def _manager_with(nlp) -> SimpleNamespace:
    return SimpleNamespace(embeddings=None, nlp=nlp)


def test_source_document_is_parsed_once_for_many_candidates(
    monkeypatch,
) -> None:
    from app.services.content_analysis import topics as topics_module

    nlp = _CountingNlp()
    candidates = [
        ("machine learning", 0.95),
        ("learning models", 0.90),
        ("models improve data", 0.85),  # interior verb: rejected
        ("data quality", 0.80),
        ("not in source", 0.75),
    ] + [(f"absent{i} phrase", 0.5) for i in range(30)]
    _FakeKeyBERT.results = candidates
    monkeypatch.setattr(topics_module, "KeyBERT", _FakeKeyBERT)

    output = topics_module.extract_keyphrases(
        _PARSE_SOURCE, _manager_with(nlp)
    )

    assert nlp.parsed == [_PARSE_SOURCE]
    assert [r.phrase for r in output] == [
        "machine learning",
        "learning models",
        "data quality",
    ]


def test_no_parse_when_no_candidate_needs_validation(monkeypatch) -> None:
    from app.services.content_analysis import topics as topics_module

    nlp = _CountingNlp()
    monkeypatch.setattr(topics_module, "KeyBERT", _FakeKeyBERT)

    _FakeKeyBERT.results = []
    assert topics_module.extract_keyphrases(
        _PARSE_SOURCE, _manager_with(nlp)
    ) == []

    # Single words, bad scores, non-strings and duplicates never reach the
    # validator's parse step.
    _FakeKeyBERT.results = [
        ("machine", 0.9),
        ("alpha beta", -0.5),
        ("gamma delta", float("nan")),
        (None, 0.8),
        ("data", 0.7),
        ("   ", 0.6),
    ]
    assert topics_module.extract_keyphrases(
        _PARSE_SOURCE, _manager_with(nlp)
    ) == []

    assert nlp.parsed == []


def test_each_extraction_call_parses_independently(monkeypatch) -> None:
    from app.services.content_analysis import topics as topics_module

    nlp = _CountingNlp()
    monkeypatch.setattr(topics_module, "KeyBERT", _FakeKeyBERT)
    _FakeKeyBERT.results = [("machine learning", 0.9), ("data quality", 0.8)]

    topics_module.extract_keyphrases(_PARSE_SOURCE, _manager_with(nlp))
    topics_module.extract_keyphrases(_PARSE_SOURCE, _manager_with(nlp))

    # No document state is kept between calls.
    assert nlp.parsed == [_PARSE_SOURCE, _PARSE_SOURCE]


def test_direct_validator_calls_still_work_without_shared_analysis() -> None:
    from app.services.content_analysis.topics import _is_quality_keyphrase

    nlp = _CountingNlp()
    manager = _manager_with(nlp)

    assert _is_quality_keyphrase("machine learning", manager, _PARSE_SOURCE)
    assert _is_quality_keyphrase("data quality", manager, _PARSE_SOURCE)
    assert not _is_quality_keyphrase(
        "models improve data", manager, _PARSE_SOURCE
    )

    # Existing direct-call behaviour: one parse per call.
    assert nlp.parsed == [_PARSE_SOURCE] * 3

    # Without source text the phrase alone is parsed, as before.
    nlp.parsed.clear()
    assert _is_quality_keyphrase("machine learning", manager)
    assert nlp.parsed == ["machine learning"]

    # Pre-checks still return before any parse.
    nlp.parsed.clear()
    assert not _is_quality_keyphrase("machine", manager, _PARSE_SOURCE)
    assert not _is_quality_keyphrase("", manager, _PARSE_SOURCE)
    assert not _is_quality_keyphrase("a b c d", manager, _PARSE_SOURCE)
    assert nlp.parsed == []


def test_shared_source_analysis_gives_identical_results_with_one_parse() -> None:
    from app.services.content_analysis.topics import (
        _is_quality_keyphrase,
        _SourceAnalysis,
    )

    phrases = [
        "machine learning",
        "learning models",
        "models improve data",
        "improve data quality",
        "data quality",
        "data quality checks",
        "teams help",
        "quality checks help",
        "absent phrase",
    ]

    separate_nlp = _CountingNlp()
    separate = [
        _is_quality_keyphrase(p, _manager_with(separate_nlp), _PARSE_SOURCE)
        for p in phrases
    ]

    shared_nlp = _CountingNlp()
    manager = _manager_with(shared_nlp)
    analysis = _SourceAnalysis(_PARSE_SOURCE, manager)
    assert shared_nlp.parsed == []  # lazy: nothing parsed on construction

    shared = [
        _is_quality_keyphrase(
            p, manager, _PARSE_SOURCE, source_analysis=analysis
        )
        for p in phrases
    ]

    assert shared == separate
    assert any(shared) and not all(shared)
    assert len(separate_nlp.parsed) == sum(
        1 for p in phrases if 2 <= len(p.split()) <= 3
    )
    assert shared_nlp.parsed == [_PARSE_SOURCE]
    assert analysis.words is analysis.words


# ---------------------------------------------------------------------------
# Stage 1C-2: topic embedding validation and normalisation
# ---------------------------------------------------------------------------


def _normalized(raw, rows):
    from app.services.content_analysis.topics import (
        _normalized_topic_embeddings,
    )

    return _normalized_topic_embeddings(raw, rows)


def test_valid_embeddings_are_normalised_to_unit_float32() -> None:
    result = _normalized([[3.0, 4.0], [0.0, 2.0], [-1.0, 1.0]], 3)

    assert result.dtype == np.float32
    assert result.shape == (3, 2)
    np.testing.assert_allclose(
        result,
        [[0.6, 0.8], [0.0, 1.0], [-0.70710678, 0.70710678]],
        atol=1e-6,
    )
    np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1.0, atol=1e-6)


def test_normalisation_matches_plain_float32_for_ordinary_vectors() -> None:
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(12, 384)).astype(np.float32)

    expected = raw / np.linalg.norm(raw, axis=1)[:, np.newaxis]

    np.testing.assert_allclose(_normalized(raw, 12), expected, atol=1e-6)


def test_float32_norm_overflow_is_handled_without_invalid_vectors() -> None:
    raw = np.array([[3e38, 3e38], [1.0, 0.0]], dtype=np.float32)

    # Premise: the naive float32 norm of the first row overflows.
    with np.errstate(over="ignore"):
        assert not np.isfinite(np.linalg.norm(raw, axis=1)[0])

    result = _normalized(raw, 2)

    assert np.isfinite(result).all()
    np.testing.assert_allclose(result[0], [0.70710678, 0.70710678], atol=1e-6)
    np.testing.assert_allclose(result[1], [1.0, 0.0], atol=1e-6)


def test_tiny_float32_vectors_are_not_mistaken_for_zero_vectors() -> None:
    raw = np.full((1, 2), 1e-30, dtype=np.float32)

    # Premise: the float32 sum of squares underflows to zero.
    with np.errstate(under="ignore"):
        assert float(np.linalg.norm(raw, axis=1)[0]) == 0.0

    np.testing.assert_allclose(
        _normalized(raw, 1), [[0.70710678, 0.70710678]], atol=1e-6
    )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([[1.0, 0.0], [0.0, 0.0]], "zero-length"),
        ([[0.0, 0.0]], "zero-length"),
        ([[1.0, float("nan")], [0.0, 1.0]], "non-finite"),
        ([[1.0, float("inf")], [0.0, 1.0]], "non-finite"),
        ([[1.0, float("-inf")], [0.0, 1.0]], "non-finite"),
    ],
)
def test_unusable_vectors_are_rejected(raw, message) -> None:
    with pytest.raises(ValueError, match=message):
        _normalized(raw, len(raw))


@pytest.mark.parametrize(
    "raw",
    [
        [1.0, 0.0],  # 1-D
        [[[1.0, 0.0]], [[0.0, 1.0]]],  # 3-D
        None,  # 0-D after conversion
        [[], []],  # zero width
        [[1.0, 0.0]],  # too few rows
        [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],  # too many rows
        [],  # no rows
    ],
)
def test_invalid_shapes_and_row_counts_are_rejected(raw) -> None:
    with pytest.raises(ValueError, match="invalid shape"):
        _normalized(raw, 2)


def test_ragged_embeddings_are_rejected() -> None:
    with pytest.raises(ValueError):
        _normalized([[1.0, 0.0], [1.0]], 2)


def test_non_finite_norm_is_rejected_even_if_elements_are_finite(
    monkeypatch,
) -> None:
    from app.services.content_analysis import topics as topics_module

    real_norm = np.linalg.norm

    def fake_norm(values, *args, **kwargs):
        result = real_norm(values, *args, **kwargs)
        result[0] = np.inf
        return result

    monkeypatch.setattr(topics_module.np.linalg, "norm", fake_norm)

    with pytest.raises(ValueError, match="non-finite vector norm"):
        _normalized([[1.0, 0.0], [0.0, 1.0]], 2)


# ---------------------------------------------------------------------------
# Stage 1C-3: extract_topics with controlled embeddings and fallback
# ---------------------------------------------------------------------------


class _EmbeddingCalls:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], object]] = []


def _patch_embeddings(monkeypatch, outcome) -> _EmbeddingCalls:
    """
    Replace generate_embeddings. ``outcome`` is an exception to raise, a
    callable taking the phrase list, or a raw embeddings value.
    """
    from app.services.content_analysis import topics as topics_module

    recorder = _EmbeddingCalls()

    def fake(phrases, model_manager):
        recorder.calls.append((list(phrases), model_manager))
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return SimpleNamespace(embeddings=outcome(phrases))
        return SimpleNamespace(embeddings=outcome)

    monkeypatch.setattr(topics_module, "generate_embeddings", fake)

    return recorder


_MANAGER = SimpleNamespace(embeddings=None, nlp=None)
_TOPIC_LOGGER = "app.services.content_analysis.topics"


def test_topics_use_embeddings_to_drop_redundant_phrases(monkeypatch) -> None:
    recorder = _patch_embeddings(
        monkeypatch, [[1.0, 0.0], [0.99, 0.1], [0.0, 1.0]]
    )
    keyphrases = [
        KeyphraseResult("alpha topic", 0.9),
        KeyphraseResult("alpha topics", 0.8),
        KeyphraseResult("beta topic", 0.7),
    ]

    topics = extract_topics(keyphrases, _MANAGER)

    assert topics == [
        TopicResult("alpha topic", 0.9),
        TopicResult("beta topic", 0.7),
    ]
    # One batched call, phrases in ranked order, with the given manager.
    assert recorder.calls == [
        (["alpha topic", "alpha topics", "beta topic"], _MANAGER)
    ]


def test_topics_below_redundancy_threshold_are_all_kept(monkeypatch) -> None:
    # cosine(first, second) is about 0.5, far below the 0.85 threshold.
    _patch_embeddings(monkeypatch, [[1.0, 0.0], [0.5, 0.8660254]])
    keyphrases = [KeyphraseResult("one", 0.9), KeyphraseResult("two", 0.8)]

    assert [t.topic for t in extract_topics(keyphrases, _MANAGER)] == [
        "one",
        "two",
    ]


def test_topic_cap_is_enforced_with_distinct_embeddings(monkeypatch) -> None:
    _patch_embeddings(monkeypatch, np.eye(MAX_KEYPHRASES))
    keyphrases = [
        KeyphraseResult(f"topic{index} word", 0.9 - index * 0.01)
        for index in range(MAX_KEYPHRASES)
    ]

    topics = extract_topics(keyphrases, _MANAGER)

    assert len(topics) == MAX_TOPICS
    assert [t.topic for t in topics] == [
        k.phrase for k in keyphrases[:MAX_TOPICS]
    ]


def test_huge_but_finite_embeddings_still_filter_redundancy(
    monkeypatch, caplog
) -> None:
    caplog.set_level(logging.WARNING, logger=_TOPIC_LOGGER)
    huge = np.array(
        [[3e38, 3e38], [2.9e38, 2.9e38], [0.0, 1.0]], dtype=np.float32
    )
    _patch_embeddings(monkeypatch, huge)
    keyphrases = [
        KeyphraseResult("alpha topic", 0.9),
        KeyphraseResult("alpha topics", 0.8),
        KeyphraseResult("beta topic", 0.7),
    ]

    topics = extract_topics(keyphrases, _MANAGER)

    # Semantic filtering worked (no fallback, no warning) and the two
    # parallel vectors were recognised as redundant.
    assert [t.topic for t in topics] == ["alpha topic", "beta topic"]
    assert caplog.records == []


def test_model_manager_defaults_to_shared_manager(monkeypatch) -> None:
    from app.services.content_analysis import model_manager as mm

    sentinel = object()
    monkeypatch.setattr(mm, "get_model_manager", lambda: sentinel)
    recorder = _patch_embeddings(monkeypatch, [[1.0, 0.0]])

    extract_topics([KeyphraseResult("only topic", 0.9)])

    assert recorder.calls[0][1] is sentinel


_FALLBACK_KEYPHRASES = [
    KeyphraseResult("Alpha Topic", 0.95),
    KeyphraseResult("alpha topic", 0.94),  # duplicate by casefold
    KeyphraseResult("bad negative", -0.2),
    KeyphraseResult("beta topic", 0.90),
    KeyphraseResult("overshoot topic", 1.0000001),
    KeyphraseResult("gamma topic", 0.80),
]


def _expected_fallback(keyphrases) -> list[TopicResult]:
    from app.services.content_analysis.topics import _valid_candidates

    return [
        TopicResult(c.phrase, c.score) for c in _valid_candidates(keyphrases)
    ][:MAX_TOPICS]


@pytest.mark.parametrize(
    ("label", "outcome", "error_name"),
    [
        ("raises", RuntimeError("encoder exploded"), "RuntimeError"),
        ("none", None, "ValueError"),
        ("empty", [], "ValueError"),
        ("one_dimensional", [1.0, 0.0, 0.0, 0.0], "ValueError"),
        ("three_dimensional", np.ones((4, 2, 2)), "ValueError"),
        ("zero_width", np.ones((4, 0)), "ValueError"),
        ("too_few_rows", np.eye(4)[:3], "ValueError"),
        ("too_many_rows", np.ones((6, 4)), "ValueError"),
        ("ragged", [[1.0, 0.0], [1.0], [0.5, 0.5], [0.1, 0.9]], "ValueError"),
        (
            "nan",
            np.array([[1.0, 0], [0, 1], [np.nan, 1], [1, 1]]),
            "ValueError",
        ),
        (
            "inf",
            np.array([[1.0, 0], [0, 1], [np.inf, 1], [1, 1]]),
            "ValueError",
        ),
        (
            "negative_inf",
            np.array([[1.0, 0], [0, 1], [-np.inf, 1], [1, 1]]),
            "ValueError",
        ),
        (
            "zero_vector",
            np.array([[1.0, 0], [0, 1], [0, 0], [1, 1]]),
            "ValueError",
        ),
    ],
)
def test_embedding_failures_fall_back_to_ranked_candidates(
    monkeypatch, caplog, label, outcome, error_name
) -> None:
    caplog.set_level(logging.WARNING, logger=_TOPIC_LOGGER)
    _patch_embeddings(monkeypatch, outcome)

    topics = extract_topics(_FALLBACK_KEYPHRASES, _MANAGER)

    expected = _expected_fallback(_FALLBACK_KEYPHRASES)
    assert [t.topic for t in topics] == [
        "Alpha Topic",
        "beta topic",
        "overshoot topic",
        "gamma topic",
    ], label
    assert topics == expected, label
    assert topics[2].score == 1.0

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, label
    message = warnings[0].getMessage()
    assert "Semantic topic filtering failed" in message
    assert "4 candidate(s)" in message
    assert error_name in message
    assert warnings[0].exc_info is None


def test_missing_embeddings_attribute_falls_back(
    monkeypatch, caplog
) -> None:
    from app.services.content_analysis import topics as topics_module

    caplog.set_level(logging.WARNING, logger=_TOPIC_LOGGER)
    monkeypatch.setattr(
        topics_module, "generate_embeddings", lambda *a, **k: object()
    )

    topics = extract_topics(_FALLBACK_KEYPHRASES, _MANAGER)

    assert topics == _expected_fallback(_FALLBACK_KEYPHRASES)
    assert "AttributeError" in caplog.records[0].getMessage()


def test_model_load_failure_inside_embeddings_falls_back(
    monkeypatch, caplog
) -> None:
    from app.services.content_analysis.model_manager import ModelLoadError

    caplog.set_level(logging.WARNING, logger=_TOPIC_LOGGER)
    _patch_embeddings(monkeypatch, ModelLoadError("models unavailable"))

    topics = extract_topics(_FALLBACK_KEYPHRASES, _MANAGER)

    assert topics == _expected_fallback(_FALLBACK_KEYPHRASES)
    assert "ModelLoadError" in caplog.records[0].getMessage()


def test_fallback_respects_topic_limit_and_ranking(monkeypatch) -> None:
    _patch_embeddings(monkeypatch, RuntimeError("down"))
    keyphrases = [
        KeyphraseResult(f"topic{index} word", 0.9 - index * 0.01)
        for index in range(MAX_KEYPHRASES + 5)
    ]

    topics = extract_topics(keyphrases, _MANAGER)

    assert len(topics) == MAX_TOPICS
    assert topics == [
        TopicResult(k.phrase, k.score) for k in keyphrases[:MAX_TOPICS]
    ]


def test_invalid_candidates_never_trigger_embedding_generation(
    monkeypatch,
) -> None:
    recorder = _patch_embeddings(monkeypatch, [[1.0, 0.0]])

    keyphrases = [
        KeyphraseResult("", 0.9),
        KeyphraseResult("   ", 0.8),
        KeyphraseResult(None, 0.7),  # type: ignore[arg-type]
        KeyphraseResult("negative score", -0.1),
        KeyphraseResult("nan score", float("nan")),
        KeyphraseResult("too high", 1.5),
    ]

    assert extract_topics(keyphrases, _MANAGER) == []
    assert extract_topics([], _MANAGER) == []
    assert recorder.calls == []


def test_only_valid_deduplicated_candidates_are_embedded(monkeypatch) -> None:
    recorder = _patch_embeddings(
        monkeypatch, lambda phrases: np.eye(len(phrases))
    )
    keyphrases = [
        KeyphraseResult("", 0.95),
        KeyphraseResult("Alpha Topic", 0.9),
        KeyphraseResult("alpha  topic", 0.85),  # duplicate after whitespace
        KeyphraseResult("negative", -0.3),
        KeyphraseResult("beta topic", 0.8),
    ]

    topics = extract_topics(keyphrases, _MANAGER)

    assert recorder.calls == [(["Alpha Topic", "beta topic"], _MANAGER)]
    assert [t.topic for t in topics] == ["Alpha Topic", "beta topic"]