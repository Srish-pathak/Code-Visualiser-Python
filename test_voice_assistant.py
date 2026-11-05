import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import voice_assistant


def test_empty_audio_returns_none():
    assert voice_assistant.transcribe_and_interpret_audio(b"") is None


def test_valid_audio_calls_gemini_with_audio_part():
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="How do I sort this list?")

    with (
        patch("voice_assistant.get_client", return_value=client),
        patch("voice_assistant.types.Part.from_bytes", return_value="audio-part") as from_bytes,
    ):
        result = voice_assistant.transcribe_and_interpret_audio(b"audio-data", "audio/wav")

    assert result == "How do I sort this list?"
    from_bytes.assert_called_once_with(data=b"audio-data", mime_type="audio/wav")
    call = client.models.generate_content.call_args.kwargs
    assert call["model"] == voice_assistant.MODEL_NAME
    assert call["contents"][0] == "audio-part"


def test_gemini_transcription_error_is_handled_safely():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("Gemini unavailable")

    with patch("voice_assistant.get_client", return_value=client):
        result = voice_assistant.transcribe_and_interpret_audio(b"audio-data")

    assert result is None


def test_empty_programming_question_returns_helpful_message():
    result = voice_assistant.generate_assistant_response("   ")

    assert "programming question" in result.lower()


def test_assistant_response_uses_conversation_history():
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="Use a stack.")

    history = [
        {"role": "user", "content": "Explain balanced parentheses."},
        {"role": "assistant", "content": "A stack tracks opening brackets."},
    ]
    with patch("voice_assistant.get_client", return_value=client):
        result = voice_assistant.generate_assistant_response(
            "What data structure should I use?",
            conversation_history=history,
        )

    assert result == "Use a stack."
    prompt = client.models.generate_content.call_args.kwargs["contents"]
    assert "Conversation history:" in prompt
    assert "Explain balanced parentheses." in prompt
    assert "A stack tracks opening brackets." in prompt


def test_assistant_response_receives_review_context():
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="Fix the SQL query.")
    review_context = '{"review": {"summary": "Potential SQL injection"}}'

    with patch("voice_assistant.get_client", return_value=client):
        result = voice_assistant.generate_assistant_response(
            "How serious is this bug?",
            review_context=review_context,
        )

    assert result == "Fix the SQL query."
    prompt = client.models.generate_content.call_args.kwargs["contents"]
    assert "Current code review context:" in prompt
    assert review_context in prompt


def test_gemini_assistant_error_is_handled_safely():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("Gemini unavailable")

    with patch("voice_assistant.get_client", return_value=client):
        result = voice_assistant.generate_assistant_response("Explain decorators.")

    assert "unavailable" in result.lower()


def test_empty_speech_text_returns_none():
    assert voice_assistant.generate_speech("") is None


def test_gtts_failure_returns_none():
    gtts_module = ModuleType("gtts")

    def failing_gtts(*args, **kwargs):
        raise RuntimeError("network unavailable")

    gtts_module.gTTS = failing_gtts
    with patch.dict(sys.modules, {"gtts": gtts_module}):
        result = voice_assistant.generate_speech("Hello")

    assert result is None


def test_build_review_context_handles_missing_results():
    assert "No code review" in voice_assistant.build_review_context()
    assert "No code review" in voice_assistant.build_review_context(
        review_result="not-a-mapping"
    )


def test_build_review_context_includes_manual_review_and_complexity():
    context = voice_assistant.build_review_context(
        review_result={
            "summary": "Found two issues",
            "overall_score": 6,
            "bugs": [{"line": 10, "description": "Possible null dereference"}],
        },
        complexity_result={
            "average_complexity": 12.5,
            "rating": "B",
            "maintainability_index": 71.2,
        },
    )
    parsed = json.loads(context)

    assert parsed["review"]["summary"] == "Found two issues"
    assert parsed["review"]["bugs"][0]["line"] == 10
    assert parsed["complexity"]["average_complexity"] == 12.5
    assert parsed["complexity"]["rating"] == "B"


def test_repository_context_includes_only_bounded_file_summaries():
    file_results = [
        {
            "path": "file-{}.py".format(index),
            "review": {
                "summary": "Summary {}".format(index),
                "bugs": [{"line": index, "description": "Bug {}".format(index)}],
            },
        }
        for index in range(30)
    ]
    repository_result = {
        "repository": {
            "full_name": "owner/repository",
            "html_url": "https://github.com/owner/repository",
            "branch": "main",
            "description": "Example repository",
        },
        "review": {
            "files_reviewed": 30,
            "file_results": file_results,
        },
    }

    parsed = json.loads(
        voice_assistant.build_review_context(repository_result=repository_result)
    )
    files = parsed["repository"]["files"]

    assert len(files) == voice_assistant._MAX_CONTEXT_ITEMS
    assert files[0]["path"] == "file-0.py"
    assert files[-1]["path"] == "file-19.py"
    assert all("content" not in item for item in files)
