import streamlit as st
from reviewer import review_code, review_repo_files
from complexity import analyze_complexity
from github_fetcher import GitHubFetchError, fetch_public_repository
from utils import (
    LANGUAGE_CONFIG,
    score_color,
    score_label,
    format_bug_entry,
    format_improvement_entry,
)

DEFAULT_SESSION_STATE = {
    "review_result": None,
    "complexity_result": None,
    "repository_result": None,
}

for key, default_value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

st.set_page_config(page_title="Tech Spec Analyser", page_icon="🔍", layout="wide")

st.title("🔍 Tech Spec Analyser")
st.caption("AI-Powered Repository and Code Analysis Platform")

with st.sidebar:
    st.header("⚙️ Settings")
    language = st.selectbox("Language", list(LANGUAGE_CONFIG.keys()))
    st.markdown("---")
    st.markdown(
        "**How it works**\n\n"
        "1. Paste or write your code\n"
        "2. Click **Review My Code**\n"
        "3. Get bugs, suggestions, complexity & a score"
    )
    st.markdown("---")
    st.caption("Requires `GEMINI_API_KEY` set as an environment variable or Streamlit secret.")

st.subheader("Your Code")

placeholder_code = {
    "Python": "def add(a, b):\n    return a+b\n",
    "C++": "int add(int a, int b) {\n    return a+b;\n}\n",
    "Java": "int add(int a, int b) {\n    return a+b;\n}\n",
    "JavaScript": "function add(a, b) {\n    return a + b;\n}\n",
    "JSX": "function Greeting({ name }) {\n    return <h1>Hello, {name}</h1>;\n}\n",
    "TypeScript": "function add(a: number, b: number): number {\n    return a + b;\n}\n",
    "TSX": "function Greeting({ name }: { name: string }) {\n    return <h1>Hello, {name}</h1>;\n}\n",
    "HTML": "<main>\n    <h1>Hello</h1>\n</main>\n",
    "CSS": "main {\n    color: navy;\n}\n",
    "SCSS": "$primary: navy;\n\nmain {\n    color: $primary;\n}\n",
}[language]

if HAS_ACE:
    code_input = st_ace(
        value=placeholder_code,
        language=LANGUAGE_CONFIG[language]["ace_mode"],
        theme="tomorrow_night",
        font_size=14,
        height=300,
        key="code_editor",
    )
else:
    code_input = st.text_area("Paste code here", value=placeholder_code, height=300)

col_run, col_clear = st.columns([1, 5])
with col_run:
    run_clicked = st.button("Review Code", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear results"):
        st.session_state.review_result = None
        st.session_state.complexity_result = None
        st.rerun()

if run_clicked:
    if not code_input or not code_input.strip():
        st.warning("Please paste some code first.")
    else:
        with st.spinner("AI is reviewing your code..."):
            st.session_state.review_result = review_code(code_input, language)
            if LANGUAGE_CONFIG[language]["supports_radon"]:
                st.session_state.complexity_result = analyze_complexity(code_input, language)
            else:
                st.session_state.complexity_result = None


# ---------- Manual review results ----------
result = st.session_state.get("review_result")
complexity = st.session_state.get("complexity_result")

if result:
    if result.get("error"):
        st.error(result.get("summary", "Something went wrong during review."))
    else:
        st.markdown("---")
        st.subheader("Review Results")

        if result.get("summary"):
            st.info(result["summary"])

        tab_bugs, tab_improve, tab_complexity, tab_score, tab_diff = st.tabs(
            ["🐛 Bugs", "💡 Improvements", "⚙️ Complexity", "📊 Score", "🔀 Before/After"]
        )

        with tab_bugs:
            bugs = result.get("bugs", [])
            if not bugs:
                st.success("No bugs found. Nice and clean! ✅")
            else:
                for bug in bugs:
                    with st.expander("Line {} — {}".format(bug.get("line", "N/A"), bug.get("severity", "info").title())):
                        st.markdown(format_bug_entry(bug))

        with tab_improve:
            improvements = result.get("improvements", [])
            if not improvements:
                st.info("No specific improvements suggested.")
            else:
                for item in improvements:
                    st.markdown(format_improvement_entry(item))
                    st.markdown("")

        with tab_complexity:
            if complexity:
                c1, c2, c3 = st.columns(3)
                c1.metric("Method", complexity["method"].title())
                c2.metric("Avg. Complexity", complexity["average_complexity"])
                c3.metric("Rating", complexity["rating"])

                if complexity.get("maintainability_index") is not None:
                    st.metric("Maintainability Index", complexity["maintainability_index"])

                if complexity.get("details"):
                    st.markdown("**Breakdown**")
                    st.table(complexity["details"])

                if complexity.get("error"):
                    st.warning(complexity["error"])

            st.caption(result.get("complexity_notes", ""))

        with tab_score:
            score = result.get("overall_score", 0)
            color = score_color(score)
            label = score_label(score)

            st.markdown("### Overall Code Health: **{}/10** — {}".format(score, label))
            st.progress(min(max(score / 10, 0), 1.0))

            if color == "green":
                st.success("This code is in great shape!")
            elif color == "orange":
                st.warning("Decent, but there's room to improve.")
            else:
                st.error("This code needs significant work.")

        with tab_diff:
            improved = result.get("improved_code", "")
            if improved:
                left, right = st.columns(2)
                with left:
                    st.markdown("**Original**")
                    st.code(code_input, language=language.lower())
                with right:
                    st.markdown("**AI-Improved**")
                    st.code(improved, language=language.lower())
            else:
                st.info("No improved version was returned.")
else:
    st.markdown("---")
    st.caption("Paste your code above and click **Review My Code** to get started.")


# ---------- GitHub repository review ----------
st.markdown("---")
st.subheader("🐙 Tech Spec Analyser – GitHub Repository Analysis")
st.caption(
    "Analyse supported source files from a public GitHub repository. "
    "Files are sent to an AI provider for analysis; do not submit code you are not permitted to share."
)
repository_url = st.text_input(
    "Public GitHub repository URL",
    placeholder="https://github.com/owner/repository",
    key="repository_url",
)
if st.button("Analyze Repository", type="primary", key="analyze_repository"):
    if not repository_url.strip():
        st.warning("Enter a public GitHub repository URL first.")
    else:
        try:
            with st.spinner("Fetching repository metadata and source files from GitHub..."):
                repository_data = fetch_public_repository(repository_url)
            if not repository_data["files"]:
                st.session_state.repository_result = None
                st.warning("No supported, readable source files were found in this repository.")
            else:
                progress_bar = st.progress(0.0, text="Preparing file reviews...")
                status_text = st.empty()

                def update_review_progress(completed, total, current_path):
                    progress_bar.progress(completed / total, text="Reviewing {}/{} files".format(completed, total))
                    status_text.caption("Currently reviewing: {}".format(current_path))

                with st.spinner("TechSpecAnalyser is reviewing your code..."):
                    review_data = review_repo_files(repository_data["files"], update_review_progress)
                progress_bar.empty()
                status_text.empty()
                st.session_state.repository_result = {
                    "repository": repository_data,
                    "review": review_data,
                }
        except GitHubFetchError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("Repository review could not be completed: {}".format(exc))

repo_result = st.session_state.get("repository_result")
if repo_result:
    repository_data = repo_result["repository"]
    review_data = repo_result["review"]
    st.markdown("---")
    st.markdown("### [{}]({}) — `{}`".format(
        repository_data["full_name"], repository_data["html_url"], repository_data["branch"]
    ))
    if repository_data.get("description"):
        st.write(repository_data["description"])

    dashboard = st.columns(5)
    dashboard[0].metric("Source files detected", repository_data["source_files_detected"])
    dashboard[1].metric("Files reviewed", review_data["files_reviewed"])
    dashboard[2].metric("Critical bugs", review_data["critical_bugs"])
    dashboard[3].metric("Warnings", review_data["warnings"])
    dashboard[4].metric(
        "Repository quality",
        "{}/10".format(review_data["overall_score"]) if review_data["overall_score"] is not None else "N/A",
    )

    if repository_data.get("files_limited"):
        st.info("Review is capped at 30 files. Narrow the repository or review a smaller project for complete coverage.")
    if repository_data.get("tree_truncated"):
        st.warning("GitHub returned a truncated file tree; the detected file count may be incomplete.")
    if review_data.get("failed_files"):
        st.warning("{} file(s) could not be reviewed; other file results are available below.".format(review_data["failed_files"]))
    if repository_data.get("fetch_errors"):
        with st.expander("Files skipped during download ({})".format(len(repository_data["fetch_errors"]))):
            for item in repository_data["fetch_errors"]:
                st.write("**{}** — {}".format(item["path"], item["error"]))

    if review_data["overall_score"] is not None:
        score = review_data["overall_score"]
        color = score_color(score)
        if color == "green":
            st.success("Average quality score: {}/10 — {}".format(score, score_label(score)))
        elif color == "orange":
            st.warning("Average quality score: {}/10 — {}".format(score, score_label(score)))
        else:
            st.error("Average quality score: {}/10 — {}".format(score, score_label(score)))

    st.markdown("#### Repository findings")
    all_bugs = []
    all_improvements = []
    for file_result in review_data["file_results"]:
        for bug in file_result["review"].get("bugs", []):
            if isinstance(bug, dict):
                all_bugs.append((file_result["path"], bug))
        for improvement in file_result["review"].get("improvements", []):
            if isinstance(improvement, dict):
                all_improvements.append((file_result["path"], improvement))

    findings_tab, improvements_tab, files_tab = st.tabs(["🐛 Bugs & security", "💡 Improvements", "📁 File-wise analysis"])
    with findings_tab:
        if not all_bugs:
            st.success("No bugs were reported in the reviewed files.")
        else:
            for path, bug in all_bugs:
                with st.expander("{} — Line {} — {}".format(
                    path, bug.get("line", "N/A"), str(bug.get("severity", "info")).title()
                )):
                    st.markdown(format_bug_entry(bug))
                    description = str(bug.get("description", "")).lower()
                    if any(term in description for term in ("security", "injection", "credential", "authentication", "authorization", "permission", "xss", "secret")):
                        st.caption("Potential security-related finding (based on the review description).")
    with improvements_tab:
        if not all_improvements:
            st.info("No improvement suggestions were returned.")
        else:
            for path, improvement in all_improvements:
                st.markdown("**{}**".format(path))
                st.markdown(format_improvement_entry(improvement))
                st.markdown("")

    with files_tab:
        file_results = review_data["file_results"]
        selected_path = st.selectbox("Select a reviewed file", [item["path"] for item in file_results])
        selected = next(item for item in file_results if item["path"] == selected_path)
        st.caption("Language: {}".format(selected["language"]))
        st.markdown("**Source code**")
        st.code(selected["content"], language=selected["language"].lower())

        per_file_review = selected["review"]
        st.markdown("**Review summary**")
        st.write(per_file_review.get("summary") or "No summary returned.")
        st.markdown("**Bugs and potential security findings**")
        if per_file_review.get("bugs"):
            for bug in per_file_review["bugs"]:
                if isinstance(bug, dict):
                    st.markdown(format_bug_entry(bug))
        else:
            st.write("No bugs reported.")
        st.markdown("**Improvements and AI suggestions**")
        if per_file_review.get("improvements"):
            for suggestion in per_file_review["improvements"]:
                if isinstance(suggestion, dict):
                    st.markdown(format_improvement_entry(suggestion))
        else:
            st.write("No improvement suggestions returned.")
        st.markdown("**Complexity analysis**")
        file_complexity = selected.get("complexity")
        if selected["language"] != "Python":
            st.info("Complexity analysis is not available for this language in repository review.")
        elif not file_complexity:
            st.info("Complexity analysis was not available.")
        else:
            if file_complexity.get("error"):
                st.warning(file_complexity["error"])
            else:
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Method", file_complexity.get("method", "N/A").title())
                cc2.metric("Average complexity", file_complexity.get("average_complexity", "N/A"))
                cc3.metric("Rating", file_complexity.get("rating", "N/A"))
                if file_complexity.get("maintainability_index") is not None:
                    st.metric("Maintainability index", file_complexity["maintainability_index"])
                if file_complexity.get("details"):
                    st.table(file_complexity["details"])
        improved_code = per_file_review.get("improved_code", "")
        if improved_code:
            with st.expander("AI-generated improved version"):
                st.code(improved_code, language=selected["language"].lower())
