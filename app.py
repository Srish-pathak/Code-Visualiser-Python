import html
import os

import streamlit as st

st.set_page_config(page_title="Tech Spec Analyser", page_icon="🔍", layout="wide")

from complexity import analyze_complexity
from github_fetcher import GitHubFetchError, fetch_public_repository
from reviewer import (
    DEEPSEEK_MODEL_NAME,
    probe_deepseek_connectivity,
    provider_status,
    review_code,
    review_repo_files,
)
from utils import LANGUAGE_CONFIG, format_bug_entry, score_color, score_label

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

for key in ("review_result", "complexity_result", "repository_result", "reviewed_code", "reviewed_language"):
    st.session_state.setdefault(key, None)

PLACEHOLDERS = {
    "Python": "def calculate_total(price, quantity):\n    return price * quantity\n",
    "C++": "int add(int a, int b) {\n    return a + b;\n}\n",
    "Java": "int add(int a, int b) {\n    return a + b;\n}\n",
    "JavaScript": "function add(a, b) {\n    return a + b;\n}\n",
    "JSX": "function Greeting({ name }) {\n    return <h1>Hello, {name}</h1>;\n}\n",
    "TypeScript": "function add(a: number, b: number): number {\n    return a + b;\n}\n",
    "TSX": "function Greeting({ name }: { name: string }) {\n    return <h1>Hello, {name}</h1>;\n}\n",
    "HTML": "<main>\n    <h1>Hello</h1>\n</main>\n",
    "CSS": "main {\n    color: navy;\n}\n",
    "SCSS": "$primary: navy;\n\nmain {\n    color: $primary;\n}\n",
}
BUGGY_PYTHON = (
    "def calculate_total(price, quantity, tax=0.1):\n"
    "    total = price * quantity\n"
    "    return total + total * tax\n\n"
    "def average(values):\n"
    "    try:\n"
    "        return sum(values) / len(values)\n"
    "    except:\n"
    "        return 0\n\n"
    "print(calculate_total(5))\n"
    "print(average([]))\n"
)

AI_STATUS = {
    "completed": ("AI review completed", "#16a34a"),
    "not_run": ("AI not run", "#6b7280"),
    "missing_configuration": ("API key missing", "#d97706"),
    "invalid_api_key": ("API key invalid", "#dc2626"),
    "permission_denied": ("Access denied", "#dc2626"),
    "rate_limited": ("Rate limited", "#d97706"),
    "insufficient_balance": ("No provider balance", "#d97706"),
    "timeout": ("Provider timed out", "#d97706"),
    "network_error": ("Network error", "#d97706"),
    "invalid_response": ("Invalid AI response", "#d97706"),
    "model_not_found": ("Model not found", "#dc2626"),
    "unavailable": ("Provider unavailable", "#d97706"),
}
SEVERITY_COLOR = {"critical": "#dc2626", "high": "#ea580c", "warning": "#d97706",
                  "medium": "#d97706", "low": "#2563eb", "info": "#2563eb"}

st.markdown(
    """
<style>
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.hero {padding: 1.3rem 1.6rem; border-radius: 16px; margin-bottom: 1.2rem; color: #fff;
       background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);}
.hero h1 {margin: 0; font-size: 1.9rem; padding: 0; color: #fff;}
.hero p {margin: .25rem 0 0; opacity: .92;}
.pill {display: inline-block; padding: 2px 11px; border-radius: 999px; font-size: .78rem;
       font-weight: 600; color: #fff; margin-right: 6px;}
.card {border: 1px solid rgba(128,128,128,.28); border-left: 5px solid var(--c, #6b7280);
       border-radius: 10px; padding: .65rem 1rem; margin-bottom: .6rem;
       background: var(--secondary-background-color);}
.card .meta {font-size: .8rem; opacity: .75; margin-bottom: .2rem;}
.statrow {display: flex; gap: .8rem; flex-wrap: wrap; margin: .4rem 0 1rem;}
.stat {flex: 1; min-width: 130px; padding: .7rem 1rem; border-radius: 12px;
       background: var(--secondary-background-color); border: 1px solid rgba(128,128,128,.22);}
.stat .v {font-size: 1.6rem; font-weight: 700; line-height: 1.2;}
.stat .l {font-size: .78rem; opacity: .75;}
.section-title {font-size: 1.15rem; font-weight: 700; margin: 1.2rem 0 .3rem;}
button[data-baseweb="tab"] {font-weight: 600;}
</style>
""",
    unsafe_allow_html=True,
)


def pill(text: str, color: str) -> str:
    return '<span class="pill" style="background:{}">{}</span>'.format(color, html.escape(text))


def stat(value, label: str, color: str | None = None) -> str:
    style = ' style="color:{}"'.format(color) if color else ""
    return '<div class="stat"><div class="v"{}>{}</div><div class="l">{}</div></div>'.format(
        style, html.escape(str(value)), html.escape(label)
    )


def stat_row(*stats: str) -> None:
    st.markdown('<div class="statrow">{}</div>'.format("".join(stats)), unsafe_allow_html=True)


def bug_card(bug: dict, path: str | None = None) -> None:
    severity = str(bug.get("severity", "info")).lower()
    color = SEVERITY_COLOR.get(severity, "#6b7280")
    text = bug.get("description") or bug.get("explanation") or bug.get("title") or "No description provided."
    where = "{} · ".format(html.escape(path)) if path else ""
    st.markdown(
        '<div class="card" style="--c:{}"><div class="meta">{}Line {} · {}</div>{}</div>'.format(
            color, where, html.escape(str(bug.get("line", "N/A"))),
            pill(severity.title(), color), html.escape(str(text)),
        ),
        unsafe_allow_html=True,
    )


def improvement_card(item: dict, path: str | None = None) -> None:
    title = html.escape(str(item.get("title", "Suggestion")))
    detail = html.escape(str(item.get("detail") or item.get("explanation") or ""))
    where = '<div class="meta">{}</div>'.format(html.escape(path)) if path else ""
    st.markdown(
        '<div class="card" style="--c:#7c3aed">{}<b>💡 {}</b><br>{}</div>'.format(where, title, detail),
        unsafe_allow_html=True,
    )


def count_severities(bugs: list) -> tuple[int, int]:
    severe = other = 0
    for bug in bugs:
        if isinstance(bug, dict):
            if str(bug.get("severity", "")).lower() in {"critical", "high"}:
                severe += 1
            else:
                other += 1
    return severe, other


def build_report(result: dict, complexity: dict | None, language: str, code: str) -> str:
    lines = ["# Tech Spec Analyser report", "", "Language: {}".format(language), ""]
    status = result.get("analysis_status", {})
    lines += ["Static analysis: {}".format(status.get("static")), "AI status: {}".format(status.get("ai")), ""]
    if status.get("ai") == "completed":
        lines += ["## Summary", result.get("summary", ""), "", "Score: {}/10".format(result.get("overall_score")), ""]
    lines.append("## Bugs")
    lines += [format_bug_entry(b) for b in result.get("bugs", []) if isinstance(b, dict)] or ["None reported."]
    lines += ["", "## Improvements"]
    for item in result.get("improvements", []):
        if isinstance(item, dict):
            lines.append("- **{}**: {}".format(item.get("title", "Suggestion"), item.get("detail", "")))
    if complexity and complexity.get("supported") is not False and not complexity.get("error"):
        lines += ["", "## Complexity", "Average: {} (rating {})".format(complexity["average_complexity"], complexity["rating"]),
                  "Maintainability index: {}".format(complexity.get("maintainability_index"))]
    lines += ["", "## Source", "```" + language.lower(), code, "```"]
    return "\n".join(lines)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    language = st.selectbox("Language", list(LANGUAGE_CONFIG.keys()))
    ai_provider = st.radio("AI provider", ["DeepSeek", "Gemini"], horizontal=True)
    enable_fallback = st.checkbox(
        "Fall back to Gemini if DeepSeek fails", value=False, disabled=ai_provider != "DeepSeek"
    )
    example = "Default sample"
    if language == "Python":
        example = st.selectbox("Start from", ["Default sample", "Sample with bugs"])

    keys = provider_status()
    st.markdown("**Provider status**")
    st.markdown(
        pill("DeepSeek " + ("ready" if keys["deepseek"] else "no key"), "#16a34a" if keys["deepseek"] else "#9ca3af")
        + pill("Gemini " + ("ready" if keys["gemini"] else "no key"), "#16a34a" if keys["gemini"] else "#9ca3af"),
        unsafe_allow_html=True,
    )
    st.caption("DeepSeek model: `{}`".format(DEEPSEEK_MODEL_NAME))
    if ai_provider == "DeepSeek" and st.button("Test DeepSeek connection", width="stretch"):
        with st.spinner("Contacting DeepSeek..."):
            probe = probe_deepseek_connectivity()
        if probe["connected"]:
            st.success("Connected (model {}).".format(probe["model"]))
        else:
            st.error(probe["error"])
    st.divider()
    st.caption("Keys are read from environment variables or `.streamlit/secrets.toml`. They are never shown or logged.")

# ---------------- Hero ----------------
st.markdown(
    '<div class="hero"><h1>🔍 Tech Spec Analyser</h1>'
    "<p>Syntax checks, static analysis and complexity metrics — plus optional AI review from DeepSeek or Gemini.</p></div>",
    unsafe_allow_html=True,
)

# ---------------- Manual review ----------------
st.markdown('<div class="section-title">Your code</div>', unsafe_allow_html=True)
starter = BUGGY_PYTHON if example == "Sample with bugs" else PLACEHOLDERS[language]
if HAS_ACE:
    code_input = st_ace(
        value=starter,
        language=LANGUAGE_CONFIG[language]["ace_mode"],
        theme="tomorrow_night",
        font_size=14,
        height=300,
        key="code_editor_{}_{}".format(language, example),
    )
else:
    code_input = st.text_area("Paste code here", value=starter, height=300, key="text_{}_{}".format(language, example))

col_run, col_clear, _ = st.columns([1.2, 1, 6])
run_clicked = col_run.button("▶ Review code", type="primary", width="stretch")
if col_clear.button("Clear", width="stretch"):
    for k in ("review_result", "complexity_result", "reviewed_code", "reviewed_language"):
        st.session_state[k] = None
    st.rerun()

if run_clicked:
    if not code_input or not code_input.strip():
        st.warning("Paste or write some code first.")
    else:
        os.environ["AUTO_AI_FALLBACK"] = "true" if enable_fallback else "false"
        with st.spinner("Reviewing your code..."):
            st.session_state.review_result = review_code(code_input, language, "<input>", ai_provider.lower())
            st.session_state.reviewed_code = code_input
            st.session_state.reviewed_language = language
            st.session_state.complexity_result = analyze_complexity(code_input, language)

result = st.session_state.review_result
complexity = st.session_state.complexity_result
shown_language = st.session_state.reviewed_language or language

if result:
    status = result.get("analysis_status", {})
    ai_status = status.get("ai", "unknown")
    ai_label, ai_color = AI_STATUS.get(ai_status, (ai_status, "#6b7280"))
    static_ok = status.get("static") == "completed"

    st.markdown('<div class="section-title">Results</div>', unsafe_allow_html=True)
    chips = pill("Static: " + status.get("static", "unknown").replace("_", " "), "#16a34a" if static_ok else "#d97706")
    chips += pill(ai_label, ai_color)
    if result.get("provider_used"):
        chips += pill(result["provider_used"], "#4f46e5")
    st.markdown(chips, unsafe_allow_html=True)

    bugs = [b for b in result.get("bugs", []) if isinstance(b, dict)]
    severe, other = count_severities(bugs)
    has_cx = bool(complexity) and complexity.get("supported") is not False and not complexity.get("error")
    score = result.get("overall_score", 0)
    stat_row(
        stat(severe, "Critical / high", "#dc2626" if severe else None),
        stat(other, "Other findings"),
        stat("{}/10".format(round(score, 1)) if ai_status == "completed" else "—", "AI score",
             {"green": "#16a34a", "orange": "#d97706", "red": "#dc2626"}[score_color(score)] if ai_status == "completed" else None),
        stat(complexity["rating"] if has_cx else "—", "Complexity rating"),
        stat(complexity["maintainability_index"] if has_cx and complexity.get("maintainability_index") is not None else "—",
             "Maintainability"),
    )

    if ai_status == "completed" and result.get("summary"):
        st.info(result["summary"])
    elif ai_status not in {"completed", "not_run"}:
        st.caption(result.get("summary", ""))
    elif result.get("summary"):
        st.info(result["summary"])

    t_bugs, t_imp, t_cx, t_score, t_diff = st.tabs(
        ["🐛 Bugs", "💡 Improvements", "⚙️ Complexity", "📊 Score", "🔀 Before / after"]
    )
    with t_bugs:
        if not bugs:
            st.success("No bugs found by static analysis or the AI review. ✅" if ai_status == "completed"
                       else "No static bugs found. AI findings are unavailable.")
        for bug in bugs:
            bug_card(bug)
    with t_imp:
        items = [i for i in result.get("improvements", []) if isinstance(i, dict)]
        if not items:
            st.info("No AI suggestions available." if ai_status != "completed" else "No specific improvements suggested.")
        for item in items:
            improvement_card(item)
    with t_cx:
        if complexity and complexity.get("supported") is False:
            st.info(complexity["error"])
        elif complexity and complexity.get("error"):
            st.warning(complexity["error"])
        elif complexity:
            a, b, c = st.columns(3)
            a.metric("Method", complexity["method"].title())
            b.metric("Average complexity", complexity["average_complexity"])
            c.metric("Rating", complexity["rating"])
            if complexity.get("details"):
                st.dataframe(complexity["details"], width="stretch", hide_index=True)
        if ai_status == "completed" and result.get("complexity_notes"):
            st.caption(result["complexity_notes"])
    with t_score:
        if ai_status != "completed":
            st.info("The AI score only appears when the AI review completes. Nothing is estimated.")
        else:
            st.markdown("### {}/10 — {}".format(round(score, 1), score_label(score)))
            st.progress(min(max(score / 10, 0), 1.0))
            {"green": st.success, "orange": st.warning, "red": st.error}[score_color(score)](
                {"green": "This code is in great shape.", "orange": "Decent, but there's room to improve.",
                 "red": "This code needs significant work."}[score_color(score)]
            )
    with t_diff:
        improved = result.get("improved_code", "")
        if improved:
            left, right = st.columns(2)
            left.markdown("**Original**")
            left.code(st.session_state.reviewed_code or "", language=shown_language.lower())
            right.markdown("**AI-improved**")
            right.code(improved, language=shown_language.lower())
        else:
            st.info("No improved version was returned.")

    st.download_button(
        "⬇ Download report (Markdown)",
        build_report(result, complexity, shown_language, st.session_state.reviewed_code or ""),
        file_name="techspec_report.md",
        mime="text/markdown",
    )
else:
    st.caption("Write or paste code above and click **Review code**. Static analysis works without any API key.")

# ---------------- GitHub repository review ----------------
st.divider()
st.markdown('<div class="section-title">🐙 GitHub repository analysis</div>', unsafe_allow_html=True)
st.caption("Reviews supported source files from a public repository (up to 30 files). Files are sent to the selected "
           "AI provider, so only analyse code you're allowed to share.")
url_col, btn_col = st.columns([5, 1])
repository_url = url_col.text_input("Repository URL", placeholder="https://github.com/owner/repository",
                                    label_visibility="collapsed")
analyze_clicked = btn_col.button("Analyze", type="primary", width="stretch")

if analyze_clicked:
    if not repository_url.strip():
        st.warning("Enter a public GitHub repository URL first.")
    else:
        try:
            with st.spinner("Fetching repository from GitHub..."):
                repo = fetch_public_repository(repository_url)
            if not repo["files"]:
                st.session_state.repository_result = None
                st.warning("No supported, readable source files were found in this repository.")
            else:
                os.environ["AUTO_AI_FALLBACK"] = "true" if enable_fallback else "false"
                bar = st.progress(0.0, text="Preparing file reviews...")

                def on_progress(done, total, path):
                    bar.progress(done / total, text="Reviewed {}/{}: {}".format(done, total, path))

                review = review_repo_files(repo["files"], on_progress, ai_provider.lower())
                bar.empty()
                st.session_state.repository_result = {"repository": repo, "review": review}
        except GitHubFetchError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("Repository review could not be completed: {}".format(exc))

repo_result = st.session_state.repository_result
if repo_result:
    repo, review = repo_result["repository"], repo_result["review"]
    st.markdown("#### [{}]({}) · `{}`".format(repo["full_name"], repo["html_url"], repo["branch"]))
    if repo.get("description"):
        st.caption(repo["description"])
    quality = review["overall_score"]
    stat_row(
        stat(repo["source_files_detected"], "Source files detected"),
        stat(review["files_reviewed"], "Files reviewed"),
        stat(review["critical_bugs"], "Critical bugs", "#dc2626" if review["critical_bugs"] else None),
        stat(review["warnings"], "Warnings"),
        stat("{}/10".format(quality) if quality is not None else "N/A", "Repository quality",
             {"green": "#16a34a", "orange": "#d97706", "red": "#dc2626"}[score_color(quality)] if quality is not None else None),
    )
    if repo.get("files_limited"):
        st.info("Review is capped at 30 files; {} more were skipped.".format(repo["file_limit_skipped"]))
    if repo.get("tree_truncated"):
        st.warning("GitHub returned a truncated file tree, so the detected count may be incomplete.")
    if review.get("failed_files"):
        st.warning("{} file(s) could not be reviewed.".format(review["failed_files"]))
    if review.get("ai_failed_files"):
        st.caption("AI review was unavailable for {} file(s); static analysis still ran.".format(review["ai_failed_files"]))
    if repo.get("fetch_errors"):
        with st.expander("Files skipped during download ({})".format(len(repo["fetch_errors"]))):
            for item in repo["fetch_errors"]:
                st.write("**{}** — {}".format(item["path"], item["error"]))

    all_bugs, all_imps = [], []
    for fr in review["file_results"]:
        all_bugs += [(fr["path"], b) for b in fr["review"].get("bugs", []) if isinstance(b, dict)]
        all_imps += [(fr["path"], i) for i in fr["review"].get("improvements", []) if isinstance(i, dict)]

    t1, t2, t3 = st.tabs(["🐛 Bugs and security", "💡 Improvements", "📁 File-wise analysis"])
    with t1:
        if not all_bugs:
            st.info("No bugs were reported in the reviewed files.")
        for path, bug in all_bugs:
            bug_card(bug, path)
    with t2:
        if not all_imps:
            st.info("No improvement suggestions were returned.")
        for path, item in all_imps:
            improvement_card(item, path)
    with t3:
        results = review["file_results"]
        chosen = st.selectbox("Reviewed file", [r["path"] for r in results])
        sel = next(r for r in results if r["path"] == chosen)
        rv = sel["review"]
        st.caption("Language: {}".format(sel["language"]))
        with st.expander("Source code", expanded=False):
            st.code(sel["content"], language=sel["language"].lower())
        st.markdown("**Summary**")
        st.write(rv.get("summary") or "No summary returned.")
        st.markdown("**Bugs**")
        for bug in rv.get("bugs", []):
            if isinstance(bug, dict):
                bug_card(bug)
        if not rv.get("bugs"):
            st.write("No bugs reported.")
        st.markdown("**Improvements**")
        for item in rv.get("improvements", []):
            if isinstance(item, dict):
                improvement_card(item)
        if not rv.get("improvements"):
            st.write("No improvement suggestions returned.")
        st.markdown("**Complexity**")
        fc = sel.get("complexity")
        if sel["language"] != "Python":
            st.info("Complexity analysis is only available for Python.")
        elif not fc or fc.get("error"):
            st.warning((fc or {}).get("error", "Complexity analysis was not available."))
        else:
            a, b, c = st.columns(3)
            a.metric("Method", fc["method"].title())
            b.metric("Average complexity", fc["average_complexity"])
            c.metric("Rating", fc["rating"])
            if fc.get("details"):
                st.dataframe(fc["details"], width="stretch", hide_index=True)
        if rv.get("improved_code"):
            with st.expander("AI-generated improved version"):
                st.code(rv["improved_code"], language=sel["language"].lower())
