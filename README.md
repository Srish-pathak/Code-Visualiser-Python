# Tech Spec Analyser

A space-themed Streamlit app that reviews source code with **deterministic static analysis** (syntax, AST, Radon, security patterns) and an optional **DeepSeek** AI review, for pasted code or public GitHub repositories.

Static and AI results are kept separate: if DeepSeek is unavailable, the offline findings are still shown.

## Quick start (3 steps)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 and:

1. Click **Review My Code**. The sample code works immediately, with no key, using offline analysis.
2. For the AI review, get a key from the DeepSeek platform and **paste it into the sidebar** (kept in your session only), then click **Test DeepSeek connection**.
3. Click **Review My Code** again to see the full report with score, improvements and before/after code.

Prefer not to paste the key? Either set an environment variable or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:

```bash
export DEEPSEEK_API_KEY="sk-..."          # macOS/Linux
$env:DEEPSEEK_API_KEY="sk-..."            # Windows PowerShell
```

## What you get

| Section | Contents |
| --- | --- |
| Overview | AI summary and top issues |
| Issues | Syntax, AST, security-pattern and AI findings with severity and line |
| Improvements | Actionable suggestions |
| Complexity | Radon cyclomatic complexity and maintainability (Python) |
| Score | AI health score out of 10 |
| Before / After | Original vs AI-improved code |
| History | Previous reviews in the session, reopenable |
| Export | Markdown and JSON reports |

**GitHub Orbit** tab: paste a public repository URL (for example `https://github.com/owner/repo`) to review up to 30 supported files, with per-file isolation so one failure never stops the rest.

## How it works

1. Input: pasted code, an uploaded file, or a public GitHub repository.
2. Local checks: empty input and Python syntax errors.
3. Static analysis: AST call-argument checks plus offline pattern checks (`local_checks.py`).
4. Complexity: Radon (Python).
5. AI review: structured JSON-only prompt to DeepSeek (`deepseek-chat`, OpenAI-compatible client, bounded retries).
6. Normalise and validate the response into one schema.
7. Display static, AI and provider status separately.

Review schema:

```json
{"summary": "", "bugs": [], "improvements": [], "complexity_notes": "", "improved_code": "", "overall_score": 8}
```

## Configuration

| Setting | Purpose |
| --- | --- |
| Sidebar key box | Session-only DeepSeek key (easiest for testing) |
| `DEEPSEEK_API_KEY` | Environment variable or Streamlit secret |
| `DEEPSEEK_MODEL` | Optional model override (default `deepseek-chat`) |

Provider errors are reported clearly: missing key, invalid key, insufficient balance, rate limit, timeout, network error, or malformed response.

## Project structure

```text
app.py              Streamlit UI
theme.py            Space theme CSS and components
reviewer.py         DeepSeek integration and review orchestration
local_checks.py     Offline security and quality checks
static_analysis.py  AST call-signature checks
syntax_checker.py   Python syntax validation
complexity.py       Radon complexity metrics
github_fetcher.py   Public repository fetching
report.py           Markdown/JSON report builders
utils.py            JSON parsing and presentation helpers
test_*.py           Tests (all provider calls are mocked)
```

## Testing

```bash
pytest -q
```

Tests use mocked clients and never spend API credit. A live DeepSeek check is done with the sidebar **Test DeepSeek connection** button.

## Limitations

- AI output can be incomplete or wrong; offline findings are the grounded baseline.
- Radon and AST checks are Python-only; other languages get pattern checks and AI review.
- GitHub requests are unauthenticated (rate-limited) and capped at 30 files per repository.
- Source is sent to DeepSeek when a key is configured; don't submit code you may not share.

## Project information

Engineering Project-I, Central University of Jharkhand. Presented by Srishti Pathak; faculty guide Dr. Prashant Prashun.
