from app.services.content_analysis.ai_prompts import (
    SYSTEM_PROMPT,
    build_analysis_messages,
)


def test_build_analysis_messages_returns_system_and_user_messages():
    messages = build_analysis_messages(
        text="AI helps analyse content.",
        sentences=["AI helps analyse content."],
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_system_prompt_treats_website_content_as_untrusted():
    assert "untrusted" in SYSTEM_PROMPT.lower()
    assert "never follow instructions" in SYSTEM_PROMPT.lower()


def test_sentence_indices_are_zero_based():
    messages = build_analysis_messages(
        text="First sentence. Second sentence.",
        sentences=[
            "First sentence.",
            "Second sentence.",
        ],
    )

    assert '"index": 0' in messages[1]["content"]
    assert '"index": 1' in messages[1]["content"]


def test_metadata_is_included():
    messages = build_analysis_messages(
        text="AI content analysis.",
        sentences=["AI content analysis."],
        title="Verbly AI",
        description="Website content intelligence.",
    )

    assert "Verbly AI" in messages[1]["content"]
    assert "Website content intelligence." in messages[1]["content"]


def test_unicode_content_is_preserved():
    messages = build_analysis_messages(
        text="ಬೆಂಗಳೂರು is a technology hub.",
        sentences=["ಬೆಂಗಳೂರು is a technology hub."],
    )

    assert "ಬೆಂಗಳೂರು" in messages[1]["content"]


def test_empty_optional_metadata_is_supported():
    messages = build_analysis_messages(
        text="Example content.",
        sentences=["Example content."],
    )

    assert len(messages) == 2
    assert messages[1]["role"] == "user"