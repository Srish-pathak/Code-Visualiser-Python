import os
from collections.abc import Callable
from typing import Any

import streamlit as st
from google import genai
from streamlit.errors import StreamlitSecretNotFoundError

try:
    from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
except ImportError:
    APIConnectionError = APIStatusError = APITimeoutError = OpenAI = None

from complexity import analyze_complexity
from static_analysis import analyze_static
from syntax_checker import check_syntax
from utils import safe_json_parse

MODEL_NAME = "gemini-2.5-flash"
DEEPSEEK_MODEL_NAME = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

SYSTEM_PROMPT = """
You are a senior software engineer performing a code review.

You ALWAYS respond with ONLY ONE VALID JSON OBJECT.

Never return markdown.

Never return ```json

Never explain anything outside JSON.

Schema:

{
  "summary":"",
  "bugs":[
    {
      "line":"",
      "severity":"",
      "description":""
    }
  ],
  "improvements":[
    {
      "title":"",
      "detail":""
    }
  ],
  "complexity_notes":"",
  "improved_code":"",
  "overall_score":8
}

Rules

- Return JSON only.
- improved_code should contain COMPLETE runnable code.
- Don't invent bugs.
- Keep suggestions educational.
"""
def get_client() -> genai.Client:
    """Create a Gemini client using environment or Streamlit credentials."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except (KeyError, StreamlitSecretNotFoundError):
            api_key = None

    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not found. Set it as an environment variable "
            "or in Streamlit secrets."
        )

    return genai.Client(api_key=api_key)


def get_deepseek_client() -> Any:
    """Create an OpenAI-compatible client configured for DeepSeek."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY not found. Set it as an environment variable."
        )
    if OpenAI is None:
        raise ImportError("The openai package is required for DeepSeek reviews.")

    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def _selected_ai_provider() -> str:
    """Select an explicitly configured provider, defaulting to the available key."""
    configured = os.getenv("AI_PROVIDER", "").strip().lower()
    if configured in {"deepseek", "gemini"}:
        return configured
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "gemini"


def _provider_error_message(exc: Exception, provider: str) -> tuple[str, str]:
    """Return a safe provider name, status, and message without exposing credentials."""
    text = "{} {}".format(type(exc).__name__, exc)
    lowered = text.lower()
    provider_name = "DeepSeek" if provider == "deepseek" else "Gemini"
    status_code = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    status = str(status_code or code or "")

    if (
        "429" in text
        or status == "429"
        or "resource_exhausted" in lowered
        or "rate limit" in lowered
        or "quota" in lowered
    ):
        return (
            "{} rate limit or quota reached. Static analysis is still available.".format(provider_name),
            "rate_limited",
        )
    invalid_response = (
        ("empty" in lowered and "response" in lowered)
        or "incomplete response" in lowered
        or "could not parse model response" in lowered
    )
    if invalid_response:
        return (
            "{} returned an invalid or incomplete response. Static analysis is still available.".format(provider_name),
            "invalid_response",
        )
    if "invalid api key" in lowered:
        return (
            "The configured {} API key is invalid. Static analysis is still available.".format(provider_name),
            "invalid_api_key",
        )
    if (
        "401" in text
        or "403" in text
        or status in {"401", "403", "PERMISSION_DENIED"}
        or "permission_denied" in lowered
        or "authentication" in lowered
        or "incorrect api key" in lowered
    ):
        return (
            "{} access was denied. Check the API key and account permissions.".format(provider_name),
            "permission_denied",
        )
    if (
        ("api key" in lowered or "api_key" in lowered)
        and "not found" in lowered
    ):
        return (
            "{} API key is not configured. Static analysis is still available.".format(provider_name),
            "invalid_api_key",
        )
    is_timeout = (
        APITimeoutError is not None and isinstance(exc, APITimeoutError)
    ) or isinstance(exc, TimeoutError)
    if "timeout" in lowered or "timed out" in lowered or is_timeout:
        return (
            "{} timed out while generating the review. Static analysis is still available.".format(provider_name),
            "timeout",
        )
    is_connection_error = (
        APIConnectionError is not None
        and isinstance(exc, APIConnectionError)
    )
    if isinstance(exc, ConnectionError) or is_connection_error:
        return (
            "Could not connect to {}. Static analysis is still available.".format(provider_name),
            "network_error",
        )
    return (
        "{} review is currently unavailable. Static analysis is still available.".format(provider_name),
        "unavailable",
    )


def _call_ai(code: str, language: str, provider: str) -> str:
    """Call the selected AI provider and return its response text."""
    prompt = build_user_prompt(code, language)
    if provider == "deepseek":
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError, TypeError):
            raise ValueError("DeepSeek returned an empty or incomplete response.")

    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )
    return getattr(response, "text", None) or ""


def build_user_prompt(code: str, language: str) -> str:
    """Build the code-review prompt sent to Gemini."""
    return f"""
Review this {language} code.

Code:

```{language.lower()}
{code}
```

Return your review strictly as the JSON schema described in your instructions."""


def review_code(code: str, language: str) -> dict[str, Any]:
    """Run syntax, static, and Gemini review analysis for one code sample."""
    if not code or not code.strip():
        return {
            "bugs": [],
            "improvements": [],
            "complexity_notes": "N/A",
            "overall_score": 0,
            "improved_code": "",
            "summary": "No code was provided to review.",
            "error": True,
            "analysis_status": {"static": "failed", "ai": "not_run"},
        }

    syntax_result = check_syntax(code, language)
    if not syntax_result.get("valid", True):
        syntax_bugs = syntax_result.get("bugs", [])
        if isinstance(syntax_bugs, dict):
            syntax_bugs = [syntax_bugs]
        return {
            "summary": "Syntax error detected.",
            "bugs": syntax_bugs,
            "improvements": [],
            "complexity_notes": "Fix syntax errors before reviewing.",
            "improved_code": "",
            "overall_score": 1,
            "static_analysis": {"syntax": syntax_result, "findings": syntax_bugs},
            "complexity_notes": "Fix syntax errors before reviewing.",
            "analysis_status": {"static": "completed_with_errors", "ai": "not_run"},
        }

    static_bugs = analyze_static(code, language)
    complexity = analyze_complexity(code, language) if language == "Python" else None

    provider = _selected_ai_provider()
    provider_name = "DeepSeek" if provider == "deepseek" else "Gemini"

    # Provider failures are kept separate from static analysis so deterministic
    # findings remain available even when the AI service is unavailable.
    try:
        response_text = _call_ai(code, language, provider)
        if not response_text:
            raise ValueError("{} returned an empty or incomplete response.".format(provider_name))
        ai_result = safe_json_parse(response_text)
        if ai_result.get("error"):
            raise ValueError(ai_result["summary"])
        result = ai_result
    except Exception as exc:
        message, ai_status = _provider_error_message(exc, provider)
        return {
            "bugs": static_bugs,
            "improvements": [],
            "complexity_notes": "N/A",
            "overall_score": 0,
            "improved_code": "",
            "summary": "AI Review Unavailable — {}".format(message),
            "error": True,
            "static_analysis": {"syntax": syntax_result, "findings": static_bugs},
            "complexity": complexity,
            "analysis_status": {"static": "completed", "ai": ai_status},
        }

    result["bugs"] = static_bugs + result.get("bugs", [])
    result["static_analysis"] = {"syntax": syntax_result, "findings": static_bugs}
    result["complexity"] = complexity
    result["analysis_status"] = {"static": "completed", "ai": "completed"}
    return result


def review_repo_files(
    files: list[dict[str, Any]],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Review fetched files individually, reusing ``review_code`` for each.

    ``files`` is a sequence of dictionaries with path, language, and content.
    The optional callback receives (completed, total, current_path).
    """
    total = len(files)
    results = []
    score_values = []
    critical_count = 0
    warning_count = 0
    improvement_count = 0
    failed_count = 0
    ai_failed_count = 0

    for index, file_info in enumerate(files, start=1):
        path = file_info.get("path", "<unknown>")
        language = file_info.get("language", "")
        code = file_info.get("content", "")
        try:
            review = review_code(code, language)
            if not isinstance(review, dict):
                raise TypeError("The reviewer returned an invalid result.")
        except Exception as exc:
            review = {
                "summary": "Review failed: {}".format(exc),
                "bugs": [],
                "improvements": [],
                "complexity_notes": "Not available because the file review failed.",
                "overall_score": 0,
                "improved_code": "",
                "error": True,
                "analysis_status": {"static": "failed", "ai": "not_run"},
            }

        bugs = review.get("bugs", [])
        if isinstance(bugs, dict):
            bugs = [bugs]
        if not isinstance(bugs, list):
            bugs = []
        review["bugs"] = bugs

        complexity = None
        if language == "Python":
            try:
                complexity = analyze_complexity(code, language)
            except Exception as exc:
                complexity = {"error": "Complexity analysis failed: {}".format(exc)}

        for bug in bugs:
            severity = str(bug.get("severity", "info")).lower() if isinstance(bug, dict) else "info"
            if severity == "critical":
                critical_count += 1
            elif severity == "warning":
                warning_count += 1
        improvements = review.get("improvements", [])
        if isinstance(improvements, list):
            improvement_count += len(improvements)

        is_error = bool(review.get("error"))
        if is_error:
            ai_status = review.get("analysis_status", {}).get("ai")
            if ai_status not in {None, "not_run"}:
                ai_failed_count += 1
            else:
                failed_count += 1
        else:
            try:
                score_values.append(float(review.get("overall_score", 0)))
            except (TypeError, ValueError):
                pass

        results.append({
            "path": path,
            "language": language,
            "content": code,
            "review": review,
            "complexity": complexity,
        })
        if progress_callback:
            progress_callback(index, total, path)

    return {
        "files_reviewed": len(results),
        "critical_bugs": critical_count,
        "warnings": warning_count,
        "improvement_count": improvement_count,
        "failed_files": failed_count,
        "ai_failed_files": ai_failed_count,
        "overall_score": round(sum(score_values) / len(score_values), 1) if score_values else None,
        "file_results": results,
    }
