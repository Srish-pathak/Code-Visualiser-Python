"""
AI Code Reviewer  (Gemini API + Python + Streamlit)

Features
  * Syntax error detection (Python AST)
  * Static analysis: bare except, mutable defaults, eval/exec, unused imports,
    long functions, too many arguments, missing docstrings, == None ...
  * Cyclomatic complexity + Maintainability Index (radon, with AST fallback)
  * Code quality score (0-100)
  * AI review via Gemini (bugs, code smells, best practices, improved code)
  * Multi-language AI review, download the final report

Run:
    pip install -r requirements.txt
    export GEMINI_API_KEY="your-key"      # (Windows: set GEMINI_API_KEY=your-key)
    streamlit run app.py
"""

import ast
import os
from datetime import datetime

import streamlit as st

try:
    from radon.complexity import cc_rank, cc_visit
    from radon.metrics import mi_rank, mi_visit

    HAS_RADON = True
except ImportError:  # app radon ke bina bhi chalega
    HAS_RADON = False

LANGUAGES = ["Python", "JavaScript", "TypeScript", "Java", "C", "C++", "C#", "Go", "PHP", "Rust", "SQL"]
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_PENALTY = {"high": 12, "medium": 5, "low": 2}
SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}

SAMPLE_CODE = '''import os, sys

def process(items, cache=[]):
    try:
        for i in items:
            if i == None:
                continue
            if i > 10:
                if i % 2 == 0:
                    cache.append(eval(str(i)))
                else:
                    cache.append(i)
    except:
        pass
    return cache

class Calc:
    def add(self, a, b):
        return a + b
'''


# ------------------------------------------------------------ analysis ----
def check_syntax(code: str):
    """Return None if OK, else dict with line/message."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return {"line": exc.lineno or 0, "message": f"{exc.msg}"}


def _unused_imports(tree: ast.AST):
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported[(a.asname or a.name).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != "*":
                    imported[a.asname or a.name] = node.lineno
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return [(name, line) for name, line in imported.items() if name not in used]


def static_analysis(code: str, max_func_lines=50, max_args=5):
    """AST based static checks -> list of issue dicts."""
    tree = ast.parse(code)
    issues = []

    def add(sev, line, msg):
        issues.append({"severity": sev, "line": line, "message": msg})

    for name, line in _unused_imports(tree):
        add("low", line, f"Unused import `{name}`")

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                add("high", node.lineno, "Bare `except:` hides every error (even KeyboardInterrupt). Catch specific exceptions.")
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                add("medium", node.lineno, "Exception is silently swallowed with `pass`. Log or handle it.")

        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                add("high", node.lineno, f"`{node.func.id}()` is a security risk. Avoid it (use ast.literal_eval / proper parsing).")

        elif isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comp, ast.Constant) and comp.value is None:
                    add("low", node.lineno, "Compare with None using `is` / `is not`, not `==` / `!=`.")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.args.defaults + [d for d in node.args.kw_defaults if d]:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    add("high", node.lineno, f"Mutable default argument in `{node.name}()` is shared between calls. Use `None` and create inside.")
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > max_func_lines:
                add("medium", node.lineno, f"`{node.name}()` is {length} lines long (limit {max_func_lines}). Split it up.")
            n_args = len(node.args.args) + len(node.args.kwonlyargs)
            if n_args > max_args:
                add("medium", node.lineno, f"`{node.name}()` takes {n_args} arguments (limit {max_args}). Group them in an object.")
            if not ast.get_docstring(node):
                add("low", node.lineno, f"Function `{node.name}()` has no docstring.")

        elif isinstance(node, ast.ClassDef) and not ast.get_docstring(node):
            add("low", node.lineno, f"Class `{node.name}` has no docstring.")

    issues.sort(key=lambda i: (SEVERITY_ORDER[i["severity"]], i["line"]))
    return issues


def _rank(score: float) -> str:
    for limit, letter in ((5, "A"), (10, "B"), (20, "C"), (30, "D"), (40, "E")):
        if score <= limit:
            return letter
    return "F"


def _fallback_complexity(code: str):
    """radon na ho to simple McCabe approximation."""
    tree = ast.parse(code)
    branches = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.IfExp,
                ast.comprehension, ast.AsyncFor)
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            score = 1 + sum(isinstance(n, branches) for n in ast.walk(node))
            score += sum(len(n.values) - 1 for n in ast.walk(node) if isinstance(n, ast.BoolOp))
            rows.append({"name": node.name, "line": node.lineno, "complexity": score, "rank": _rank(score)})
    return rows


def complexity_report(code: str):
    """Return (rows, maintainability_index)."""
    if HAS_RADON:
        rows = [{"name": b.name, "line": b.lineno, "complexity": b.complexity, "rank": cc_rank(b.complexity)}
                for b in cc_visit(code)]
        try:
            mi = float(mi_visit(code, multi=True))
        except Exception:
            mi = 0.0
    else:
        rows = _fallback_complexity(code)
        mi = None
    rows.sort(key=lambda r: -r["complexity"])
    return rows, mi


def quality_score(issues, rows, mi):
    """0-100 score from issues, complexity and maintainability."""
    score = 100
    score -= sum(SEVERITY_PENALTY[i["severity"]] for i in issues)
    score -= sum(min(10, (r["complexity"] - 10)) for r in rows if r["complexity"] > 10)
    if mi is not None and mi < 65:
        score -= int((65 - mi) / 3)
    return max(0, min(100, score))


def grade(score: int):
    if score >= 90:
        return "A", "Excellent"
    if score >= 75:
        return "B", "Good"
    if score >= 60:
        return "C", "Needs work"
    if score >= 40:
        return "D", "Poor"
    return "F", "Critical"


# ------------------------------------------------------------- AI review ---
def build_prompt(code, language, focus, static_summary):
    return f"""You are a senior software engineer doing a code review.

Language: {language}
Focus areas: {", ".join(focus)}

Automated static-analysis findings (Python only, may be empty):
{static_summary or "n/a"}

Review the code below. Respond in Markdown with exactly these sections:
## Summary
(2-3 lines overall verdict)
## Bugs & Logic Issues
(bullet list with line numbers, or "None found")
## Code Smells & Best Practices
(bullet list)
## Security & Performance
(bullet list)
## Improved Code
(one complete improved version in a fenced code block)
## Score
(a single line: `Score: X/10`)

Be specific, concise, and beginner friendly.

```{language.lower()}
{code}
```"""


def ai_review(code, language, focus, static_summary, api_key, model):
    from google import genai  # lazy import: app bina SDK ke bhi khul jaye

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=build_prompt(code, language, focus, static_summary),
    )
    return response.text or "(Empty response from model)"


def get_default_key():
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            key = ""
    return key


def make_report(code, language, score, issues, rows, mi, ai_text):
    g, label = grade(score)
    lines = [f"# Code Review Report", f"_Generated {datetime.now():%Y-%m-%d %H:%M}_", "",
             f"**Language:** {language}", f"**Quality score:** {score}/100 ({g} - {label})"]
    if mi is not None:
        lines.append(f"**Maintainability Index:** {mi:.1f}")
    lines += ["", "## Static analysis issues"]
    lines += [f"- [{i['severity'].upper()}] line {i['line']}: {i['message']}" for i in issues] or ["- None"]
    lines += ["", "## Complexity"]
    lines += [f"- `{r['name']}` (line {r['line']}): {r['complexity']} ({r['rank']})" for r in rows] or ["- n/a"]
    if ai_text:
        lines += ["", "# AI Review", ai_text]
    lines += ["", "## Reviewed code", f"```{language.lower()}", code, "```"]
    return "\n".join(lines)


# ------------------------------------------------------------------- UI ----
def main():
    st.set_page_config(page_title="AI Code Reviewer", page_icon="🧐", layout="wide")
    st.title("🧐 AI Code Reviewer")
    st.caption("Static analysis + complexity metrics + Gemini AI review")

    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("Gemini API key", value=get_default_key(), type="password",
                                help="Free key: https://aistudio.google.com/apikey")
        model = st.text_input("Gemini model", value="gemini-2.5-flash")
        language = st.selectbox("Language", LANGUAGES)
        focus = st.multiselect("Review focus",
                               ["Bugs", "Readability", "Performance", "Security", "Best practices", "Testing"],
                               default=["Bugs", "Readability", "Security", "Best practices"])
        use_ai = st.toggle("Run AI review", value=True)
        if not HAS_RADON:
            st.warning("`radon` not installed - using simplified complexity. `pip install radon`")

    uploaded = st.file_uploader("Upload a file (optional)", type=["py", "js", "ts", "java", "c", "cpp", "cs", "go", "php", "rs", "sql", "txt"])
    default = uploaded.read().decode("utf-8", errors="ignore") if uploaded else SAMPLE_CODE
    code = st.text_area("Paste your code", value=default, height=320, key=f"code_{uploaded.name if uploaded else 'x'}")

    if not st.button("🔍 Review my code", type="primary"):
        return
    if not code.strip():
        st.error("Please paste some code first.")
        return

    issues, rows, mi, syntax_err = [], [], None, None
    if language == "Python":
        syntax_err = check_syntax(code)
        if syntax_err:
            st.error(f"❌ Syntax error on line {syntax_err['line']}: {syntax_err['message']}")
        else:
            issues = static_analysis(code)
            rows, mi = complexity_report(code)

    score = quality_score(issues, rows, mi) if language == "Python" and not syntax_err else (0 if syntax_err else None)

    if score is not None:
        g, label = grade(score)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Quality score", f"{score}/100", f"{g} - {label}", delta_color="off")
        c2.metric("Issues found", len(issues))
        c3.metric("Max complexity", max((r["complexity"] for r in rows), default=0))
        c4.metric("Maintainability", f"{mi:.1f}" if mi is not None else "n/a")
        st.progress(score / 100)

    ai_text = ""
    tab_issues, tab_cx, tab_ai = st.tabs(["⚠️ Static issues", "📈 Complexity", "🤖 AI review"])

    with tab_issues:
        if language != "Python":
            st.info("Static analysis is available for Python. The AI review works for all languages.")
        elif syntax_err:
            st.warning("Fix the syntax error to see static analysis.")
        elif not issues:
            st.success("No issues found. Nice work! 🎉")
        else:
            for i in issues:
                st.markdown(f"{SEVERITY_ICON[i['severity']]} **Line {i['line']}** - {i['message']}")

    with tab_cx:
        if rows:
            st.dataframe(rows, hide_index=True)
            st.bar_chart({r["name"]: r["complexity"] for r in rows})
            st.caption("Rank: A (1-5) simple, B (6-10), C (11-20), D (21-30), E/F very complex.")
        else:
            st.info("No functions/classes to measure (or not Python).")

    with tab_ai:
        if not use_ai:
            st.info("AI review is turned off in the sidebar.")
        elif not api_key:
            st.warning("Add your Gemini API key in the sidebar to get the AI review.")
        else:
            summary = "\n".join(f"- line {i['line']}: {i['message']}" for i in issues)
            try:
                with st.spinner("Gemini is reviewing your code..."):
                    ai_text = ai_review(code, language, focus or ["Best practices"], summary, api_key, model)
                st.markdown(ai_text)
            except ImportError:
                st.error("Install the SDK:  `pip install google-genai`")
            except Exception as exc:
                st.error(f"AI review failed: {exc}")

    report = make_report(code, language, score if score is not None else 0, issues, rows, mi, ai_text)
    st.download_button("⬇️ Download report (.md)", report, file_name="code_review_report.md", mime="text/markdown")


if __name__ == "__main__":
    main()
