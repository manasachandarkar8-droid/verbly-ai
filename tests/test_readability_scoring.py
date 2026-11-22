from __future__ import annotations

import pytest

from app.services.readability.scoring import (
    flesch_kincaid_grade,
    flesch_reading_ease,
    interpret_reading_ease,
)


def test_flesch_reading_ease_known_example():
    # words/sentence = 20, syllables/word = 1.5
    # 206.835 - 1.015*20 - 84.6*1.5 = 206.835 - 20.3 - 126.9 = 59.635
    score = flesch_reading_ease(20.0, 1.5)
    assert score == pytest.approx(59.635, abs=1e-6)


def test_flesch_kincaid_grade_known_example():
    # 0.39*20 + 11.8*1.5 - 15.59 = 7.8 + 17.7 - 15.59 = 9.91
    grade = flesch_kincaid_grade(20.0, 1.5)
    assert grade == pytest.approx(9.91, abs=1e-6)


def test_flesch_reading_ease_zero_inputs():
    # Formula must not raise even at degenerate inputs; only division
    # by zero upstream (0 sentences/words) is a real hazard, and that's
    # guarded before these functions are ever called.
    assert flesch_reading_ease(0.0, 0.0) == pytest.approx(206.835)


@pytest.mark.parametrize(
    "score,expected",
    [
        (100.0, "Very Easy"),
        (95.0, "Very Easy"),
        (85.0, "Easy"),
        (75.0, "Fairly Easy"),
        (65.0, "Standard"),
        (55.0, "Fairly Difficult"),
        (35.0, "Difficult"),
        (10.0, "Very Difficult"),
        (-20.0, "Very Difficult"),
        (150.0, "Very Easy"),
    ],
)
def test_interpret_reading_ease_bands(score, expected):
    assert interpret_reading_ease(score) == expected


def test_interpret_reading_ease_boundary_values():
    assert interpret_reading_ease(90.0) == "Very Easy"
    assert interpret_reading_ease(89.99) == "Easy"
    assert interpret_reading_ease(30.0) == "Difficult"
    assert interpret_reading_ease(29.99) == "Very Difficult"
