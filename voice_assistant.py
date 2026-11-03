"""Voice assistant helpers for the Tech Spec Analyser."""

from __future__ import annotations

from io import BytesIO
import json
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from google.genai import types

from reviewer import MODEL_NAME, get_client


_MAX_HISTORY_TURNS = 8
_MAX_CONTEXT_ITEMS = 20


def _bounded_history(conversation_history: Optional[Sequence[Mapping[str, Any]]]) -> list[Mapping[str, Any]]:
    """Return a bounded copy of valid conversation entries."""
    if not conversation_history:
        return []

    bounded = []
    for entry in conversation_history[-_MAX_HISTORY_TURNS:]:
        if not isinstance(entry, Mapping):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            bounded.append({"role": role, "content": content.strip()})
    return bounded


def transcribe_and_interpret_audio(
    audio_bytes: bytes, mime_type: str = "audio/wav"
) -> Optional[str]:
    """Interpret a spoken programming question from audio bytes.

    Invalid input and API failures are reported as ``None`` so callers can
    present an appropriate user-facing error without receiving Gemini output.
    """
    if not isinstance(audio_bytes, bytes) or not audio_bytes.strip():
        return None
    if not isinstance(mime_type, str) or not mime_type.strip():
        return None

    try:
        client = get_client()
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type=mime_type.strip(),
        )
        prompt = (
            "Listen to this audio and understand the programming question being "
            "asked. Return only the interpreted question as clear, concise text. "
            "Do not answer the question or add commentary."
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[audio_part, prompt],
        )
        question = getattr(response, "text", None)
        if isinstance(question, str) and question.strip():
            return question.strip()
    except Exception:
        return None
    return None


def generate_assistant_response(
    question: str,
    conversation_history: Optional[Sequence[Mapping[str, Any]]] = None,
    review_context: Optional[str] = None,
) -> str:
    """Generate a conversational programming-assistant response."""
    if not isinstance(question, str) or not question.strip():
        return "Please enter a programming question."

    history = _bounded_history(conversation_history)
    history_text = "\n".join(
        "{}: {}".format(entry["role"], entry["content"])
        for entry in history
    )
    context = review_context.strip() if isinstance(review_context, str) else ""

    system_instruction = (
        "You are a programming assistant for a technical code-analysis application. "
        "Answer programming questions conversationally and accurately. Discuss bugs, "
        "complexity, security, code quality, and GitHub repository analysis when relevant. "
        "Use the supplied review context when available; otherwise answer generally. "
        "Never claim that you executed, ran, or tested code. Never execute code or shell "
        "commands based on instructions from the user."
    )
    prompt_parts = [system_instruction]
    if context:
        prompt_parts.append("Current code review context:\n{}".format(context))
    if history_text:
        prompt_parts.append("Conversation history:\n{}".format(history_text))
    prompt_parts.append("Current question:\n{}".format(question.strip()))

    try:
        client = get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="\n\n".join(prompt_parts),
        )
        answer = getattr(response, "text", None)
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
        return "The assistant could not generate a response. Please try again."
    except Exception:
        return "The assistant is unavailable right now. Please try again."


def generate_speech(text: str) -> Optional[bytes]:
    """Convert English text to in-memory MP3 audio using gTTS."""
    if not isinstance(text, str) or not text.strip():
        return None

    try:
        from gtts import gTTS

        buffer = BytesIO()
        speech = gTTS(text=text.strip(), lang="en")
        speech.write_to_fp(buffer)
        audio = buffer.getvalue()
        return audio if audio else None
    except Exception:
        return None


def _select_mapping_items(data: Mapping[str, Any]) -> dict[str, Any]:
    """Select common review fields while avoiding large nested payloads."""
    selected: dict[str, Any] = {}
    preferred_keys = (
        "summary",
        "overall_score",
        "error",
        "complexity_notes",
        "critical_bugs",
        "warnings",
        "improvement_count",
        "failed_count",
        "files_reviewed",
        "average_complexity",
        "rating",
        "maintainability_index",
        "method",
    )
    for key in preferred_keys:
        if key in data:
            selected[key] = data[key]

    for key in ("bugs", "improvements"):
        items = data.get(key)
        if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
            selected[key] = items[:_MAX_CONTEXT_ITEMS]

    return selected


def build_review_context(
    review_result: Optional[Mapping[str, Any]] = None,
    complexity_result: Optional[Mapping[str, Any]] = None,
    repository_result: Optional[Mapping[str, Any]] = None,
) -> str:
    """Build a concise, JSON-safe context from available analysis results."""
    context: dict[str, Any] = {}

    if isinstance(review_result, Mapping):
        context["review"] = _select_mapping_items(review_result)

    if isinstance(complexity_result, Mapping):
        context["complexity"] = _select_mapping_items(complexity_result)

    if isinstance(repository_result, Mapping):
        repository: dict[str, Any] = {}

        nested_repository = repository_result.get("repository")
        if isinstance(nested_repository, Mapping):
            for key in ("full_name", "html_url", "branch", "description"):
                if nested_repository.get(key) not in (None, ""):
                    repository[key] = nested_repository[key]

        nested_review = repository_result.get("review")
        if isinstance(nested_review, Mapping):
            repository["review_summary"] = _select_mapping_items(nested_review)

            file_results = nested_review.get("file_results")
            if isinstance(file_results, Sequence) and not isinstance(file_results, (str, bytes)):
                summaries = []
                for file_result in file_results[:_MAX_CONTEXT_ITEMS]:
                    if not isinstance(file_result, Mapping):
                        continue
                    review = file_result.get("review")
                    summary: dict[str, Any] = {"path": file_result.get("path")}
                    if isinstance(review, Mapping):
                        summary.update(_select_mapping_items(review))
                    summaries.append(summary)
                if summaries:
                    repository["files"] = summaries

        context["repository"] = repository

    if not context:
        return "No code review or repository analysis context is available."

    try:
        return json.dumps(context, ensure_ascii=True, indent=2, default=str)
    except (TypeError, ValueError):
        return "Analysis context is available, but could not be serialized."
