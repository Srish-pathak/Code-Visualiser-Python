from google import genai
from utils import safe_json_parse
from google.genai import types
from syntax_checker import check_syntax
from static_analysis import analyze_static
from complexity import analyze_complexity

MODEL_NAME = "gemini-3.8-flash"

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


import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def get_client():
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


def build_user_prompt(code, language):
    return f"""
Review this {language} code.

Code:

```{language.lower()}
{code}
```

Return your review strictly as the JSON schema described in your instructions."""


def review_code(code, language):
    if not code or not code.strip():
        return {
            "bugs": [],
            "improvements": [],
            "complexity_notes": "N/A",
            "overall_score": 0,
            "improved_code": "",
            "summary": "No code was provided to review.",
            "error": True,
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
        }

    static_bugs = analyze_static(code, language)

    # Keep client creation inside the exception boundary: missing credentials and
    # Gemini/network errors should become a normal review result, not a crash.
    try:
        client = get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=build_user_prompt(code, language),
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )
        result = safe_json_parse(response.text)
    except Exception as exc:
        return {
            "bugs": static_bugs,
            "improvements": [],
            "complexity_notes": "N/A",
            "overall_score": 0,
            "improved_code": "",
            "summary": "Gemini API Error: {}".format(exc),
            "error": True,
        }

    result["bugs"] = static_bugs + result.get("bugs", [])
    return result


def review_repo_files(files, progress_callback=None):
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
            }

        bugs = review.get("bugs", [])
        if isinstance(bugs, dict):
            bugs = [bugs]
        if not isinstance(bugs, list):
            bugs = []
        review["bugs"] = bugs

        # Complexity is only reported where the existing project has a real
        # analyzer. The heuristic fallback is intentionally not used here.
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
        "overall_score": round(sum(score_values) / len(score_values), 1) if score_values else None,
        "file_results": results,
    }
