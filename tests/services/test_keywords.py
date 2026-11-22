from app.services.seo.keywords import extract_keywords, tokenize


def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("Hello, World! It's great.") == ["hello", "world", "it's", "great"]


def test_tokenize_empty_string():
    assert tokenize("") == []
    assert tokenize(None) == []  # type: ignore[arg-type]


def test_extract_keywords_empty_content():
    assert extract_keywords("", max_keywords=10) == []


def test_extract_keywords_short_content_below_min_length_filtered():
    # "a", "an", "is" are all short/stopwords -> nothing meaningful left
    result = extract_keywords("a an is to of", max_keywords=10)
    assert result == []


def test_extract_keywords_filters_stopwords():
    text = "the cat sat on the mat and the cat slept"
    result = extract_keywords(text, max_keywords=10)
    keywords = {k.keyword for k in result}
    assert "the" not in keywords
    assert "and" not in keywords
    assert "on" not in keywords
    assert "cat" in keywords


def test_extract_keywords_frequency_and_density():
    text = "python python python code code testing"
    result = extract_keywords(text, max_keywords=10)
    by_keyword = {k.keyword: k for k in result}
    assert by_keyword["python"].count == 3
    assert by_keyword["code"].count == 2
    assert by_keyword["testing"].count == 1
    total_meaningful = 6
    assert by_keyword["python"].density == round(3 / total_meaningful * 100, 2)


def test_extract_keywords_deterministic_ordering_ties_broken_alphabetically():
    text = "zebra zebra apple apple mango mango"
    result = extract_keywords(text, max_keywords=10)
    # all tied at count=2 -> alphabetical
    assert [k.keyword for k in result] == ["apple", "mango", "zebra"]


def test_extract_keywords_respects_max_keywords():
    words = [
        "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
        "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
        "oscar", "papa", "quebec", "romeo", "sierra", "tango",
    ]
    text = " ".join(f"{word} {word}" for word in words)
    result = extract_keywords(text, max_keywords=5)
    assert len(result) == 5


def test_extract_keywords_deterministic_repeated_calls():
    text = "search engine optimization search engine content strategy"
    first = extract_keywords(text, max_keywords=10)
    second = extract_keywords(text, max_keywords=10)
    assert first == second


def test_extract_keywords_ignores_html_markup_characters():
    # Simulates already-stripped body text containing stray angle brackets;
    # the tokenizer should not treat them as part of words.
    text = "keyword <b>bold keyword</b> normal-text"
    result = extract_keywords(text, max_keywords=10)
    keywords = {k.keyword for k in result}
    assert "keyword" in keywords
    assert "bold" in keywords
    assert "normal" in keywords and "text" in keywords
