from __future__ import annotations

import pytest

from app.services.readability.text_stats import (
    count_sentences,
    count_syllables,
    count_words,
    extract_words,
    normalize_whitespace,
    split_sentences,
    total_syllables,
)


# --- normalize_whitespace ------------------------------------------------


def test_normalize_whitespace_collapses_runs():
    assert normalize_whitespace("Hello    world\n\nfoo\tbar") == "Hello world foo bar"


def test_normalize_whitespace_strips_ends():
    assert normalize_whitespace("   padded text   ") == "padded text"


def test_normalize_whitespace_empty_string():
    assert normalize_whitespace("") == ""


def test_normalize_whitespace_whitespace_only():
    assert normalize_whitespace("   \n\t  ") == ""


def test_normalize_whitespace_none_safe():
    assert normalize_whitespace(None) == ""  # type: ignore[arg-type]


# --- word extraction -------------------------------------------------------


def test_extract_words_basic():
    assert extract_words("The quick brown fox.") == ["The", "quick", "brown", "fox"]


def test_extract_words_handles_apostrophes_as_single_word():
    assert extract_words("It's Claude's turn.") == ["It's", "Claude's", "turn"]


def test_extract_words_empty_text():
    assert extract_words("") == []


def test_extract_words_punctuation_only():
    assert extract_words("... !! ??") == []


def test_count_words_matches_extract_words_length():
    text = "One two three four five."
    assert count_words(text) == len(extract_words(text))
    assert count_words(text) == 5


# --- sentence splitting -----------------------------------------------------


def test_split_sentences_empty_text():
    assert split_sentences("") == []


def test_split_sentences_whitespace_only():
    assert split_sentences("   \n\t ") == []


def test_split_sentences_one_word_no_terminal_punctuation():
    assert split_sentences("Hello") == ["Hello"]


def test_split_sentences_single_sentence():
    assert split_sentences("This is one sentence.") == ["This is one sentence."]


def test_split_sentences_multiple_sentences():
    text = "Hello world. This is great! Are you sure? Yes."
    assert split_sentences(text) == [
        "Hello world.",
        "This is great!",
        "Are you sure?",
        "Yes.",
    ]


def test_split_sentences_does_not_split_on_common_abbreviations():
    text = "Mr. Smith went home. He was tired."
    assert split_sentences(text) == [
        "Mr. Smith went home.",
        "He was tired.",
    ]


def test_split_sentences_handles_multiple_abbreviations():
    text = "Dr. Jones met Mrs. Lee at noon. They discussed the report."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[0] == "Dr. Jones met Mrs. Lee at noon."
    assert sentences[1] == "They discussed the report."


def test_split_sentences_title_abbreviations_never_end_a_sentence():
    # Exact example from the review request.
    text = "Dr. Smith met Mr. Jones. They discussed the report."
    assert split_sentences(text) == [
        "Dr. Smith met Mr. Jones.",
        "They discussed the report.",
    ]


def test_split_sentences_contextual_abbreviation_can_end_a_sentence():
    # Exact example from the review request: "etc." here really is the
    # end of the first sentence, since the next fragment starts with a
    # capitalized new sentence ("The students...").
    text = "Prof. Adams explained the theory, etc. The students took notes."
    assert split_sentences(text) == [
        "Prof. Adams explained the theory, etc.",
        "The students took notes.",
    ]


@pytest.mark.parametrize(
    "abbreviation",
    ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Sr.", "Jr.", "St.", "vs."],
)
def test_split_sentences_title_style_abbreviations_do_not_split(abbreviation):
    text = f"{abbreviation} Alpha visited the museum yesterday. It went well."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[0].startswith(abbreviation)
    assert sentences[1] == "It went well."


def test_split_sentences_etc_mid_sentence_does_not_split():
    text = "We packed shirts, socks, etc. and left for the trip."
    assert split_sentences(text) == [
        "We packed shirts, socks, etc. and left for the trip."
    ]


def test_split_sentences_eg_mid_sentence_does_not_split():
    text = "Bring warm clothes, e.g. a coat, before the trip."
    assert split_sentences(text) == [
        "Bring warm clothes, e.g. a coat, before the trip."
    ]


def test_split_sentences_ie_inside_parentheses_does_not_split():
    text = "Note the exception (i.e. the edge case) here."
    assert split_sentences(text) == [
        "Note the exception (i.e. the edge case) here."
    ]


def test_split_sentences_eg_followed_by_new_sentence_does_split():
    text = "Bring supplies, e.g. Tools are essential for this job."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[1] == "Tools are essential for this job."


def test_split_sentences_abbreviation_at_end_of_text_does_not_crash():
    text = "I packed shirts, socks, etc."
    assert split_sentences(text) == ["I packed shirts, socks, etc."]


def test_split_sentences_multiple_title_abbreviations_in_one_sentence():
    text = "Mrs. Lee and Ms. Patel arrived. Sr. Garcia was late."
    assert split_sentences(text) == [
        "Mrs. Lee and Ms. Patel arrived.",
        "Sr. Garcia was late.",
    ]


def test_split_sentences_unusual_punctuation_does_not_crash():
    text = "Wait... what?! Really?!?! Ok."
    sentences = split_sentences(text)
    assert isinstance(sentences, list)
    assert len(sentences) >= 1


def test_count_sentences_empty_text_is_zero():
    assert count_sentences("") == 0


def test_count_sentences_no_terminal_punctuation_is_at_least_one():
    assert count_sentences("no punctuation here") == 1


def test_count_sentences_multiple():
    assert count_sentences("One. Two. Three.") == 3


# --- syllable counting -----------------------------------------------------


def test_count_syllables_never_zero_for_nonempty_word():
    for word in ["a", "I", "the", "strengths", "rhythm"]:
        assert count_syllables(word) >= 1


def test_count_syllables_empty_string_is_zero():
    assert count_syllables("") == 0


def test_count_syllables_simple_one_syllable_words():
    assert count_syllables("cat") == 1
    assert count_syllables("dog") == 1
    assert count_syllables("run") == 1


def test_count_syllables_handles_silent_trailing_e():
    assert count_syllables("code") == 1
    assert count_syllables("large") == 1
    assert count_syllables("hope") == 1


def test_count_syllables_handles_le_ending():
    assert count_syllables("table") == 2
    assert count_syllables("little") == 2
    assert count_syllables("syllable") == 3


def test_count_syllables_handles_common_verb_endings():
    # "-ed" preceded by a non t/d consonant is silent.
    assert count_syllables("walked") == 1
    assert count_syllables("jumped") == 1
    # "-ed" preceded by t/d adds its own syllable.
    assert count_syllables("needed") == 2
    assert count_syllables("wanted") == 2


def test_count_syllables_multisyllable_word():
    assert count_syllables("beautiful") == 3


def test_count_syllables_is_case_insensitive():
    assert count_syllables("BEAUTIFUL") == count_syllables("beautiful")


def test_count_syllables_ignores_surrounding_punctuation():
    assert count_syllables("hello,") == count_syllables("hello")
    assert count_syllables('"quoted"') == count_syllables("quoted")


def test_count_syllables_word_with_no_vowels_still_returns_one():
    # "psst" has no a/e/i/o/u/y at all; the heuristic must still return
    # a positive count rather than 0.
    assert count_syllables("psst") == 1


def test_count_syllables_is_deterministic_across_repeated_calls():
    word = "wonderful"
    results = {count_syllables(word) for _ in range(20)}
    assert len(results) == 1


def test_total_syllables_sums_across_words():
    words = ["cat", "table", "beautiful"]  # 1 + 2 + 3
    assert total_syllables(words) == 6


def test_total_syllables_empty_list():
    assert total_syllables([]) == 0
