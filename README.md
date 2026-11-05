# TechSpecAnalyser (CodeLens AI)
### A Static-Analysis-Grounded AI System for Automated Code Review and Documentation Generation

<p align="center">

**Intelligent Code Analysis | Automated Review | Code Quality | AI-Assisted Development**

</p>

---

## 1. Overview

**TechSpecAnalyser (CodeLens AI)** is an AI-assisted code analysis and review system designed to improve software quality through a combination of static code analysis and Large Language Model (LLM)-based reasoning.

The system analyses source code, identifies potential bugs and code quality issues, suggests improvements, evaluates complexity, and generates improved code with explanations.

Unlike systems that rely exclusively on AI-generated feedback, TechSpecAnalyser integrates deterministic static analysis techniques with AI-powered analysis to provide more structured and context-aware code reviews.

The platform also supports GitHub repository integration, allowing developers to analyse source files directly from public repositories.

## 2. Problem Statement

Traditional code review is often a manual, time-consuming process that requires developers to inspect source code, identify bugs, evaluate complexity, and suggest improvements.

Existing AI-based code review approaches may produce inconsistent or unverified suggestions when used without static analysis.

TechSpecAnalyser addresses these challenges by combining programmatic code analysis with AI-assisted review to provide a structured approach to understanding and improving source code quality.

## 3. Objectives

- Automate preliminary source code review.
- Detect potential programming errors and code quality issues.
- Integrate static analysis with AI-powered reasoning.
- Analyse code complexity and maintainability.
- Generate optimized and improved code suggestions.
- Support GitHub repository-based code analysis.
- Provide understandable explanations of detected issues.
- Improve developer productivity and code comprehension.

## 4. Key Features

| Feature | Description |
|---|---|
| AI Code Review | AI-assisted analysis of submitted source code |
| Static Analysis | Python AST-based structural analysis |
| Bug Detection | Identification of potential errors and suspicious patterns |
| Code Improvements | Suggestions for improving readability and maintainability |
| Complexity Analysis | Complexity insights using static analysis tools |
| Code Scoring | Structured code quality evaluation |
| Improved Code | AI-generated revised code suggestions |
| GitHub Integration | Fetch and analyse supported source files from public repositories |
| Review History | Access to previous review results, where supported |
| Interactive Dashboard | Structured presentation of analysis results |

## 5. System Architecture

The system follows a modular analysis workflow.

```text
          User
           |
           v
    Web Application
           |
           v
      Code Input
           |
     +-----+------+
     |            |
     v            v
 Static Analysis  GitHub Fetcher
     |            |
     v            v
 AST Analysis   Source Files
     |            |
     +-----+------+
           |
           v
    AI Review Engine
           |
           v
   Structured Analysis
           |
     +-----+----------------+
     |          |           |
     v          v           v
   Issues   Improvements  Complexity
     |          |           |
     +----------+-----------+
                |
                v
         Review Results
                |
                v
       Interactive Dashboard
```

*Note: This diagram represents the high-level workflow. It does not imply that every analysis stage is an independent AI agent.*

## 6. Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Frontend / Application Interface | Streamlit |
| AI Integration | Google Gemini API |
| Static Analysis | Python AST |
| Complexity Analysis | Radon |
| Repository Integration | GitHub API / repository fetching |
| Testing | Pytest |
| Version Control | Git and GitHub |
| Deployment | Streamlit-compatible hosting environment |

## 7. Working Methodology

### Step 1: Code Input
Users submit source code directly or provide a supported public GitHub repository URL.

### Step 2: Source Code Processing
The application validates the input and processes supported source files.

### Step 3: Static Analysis
The Python AST module examines the syntactic structure of Python source code. Additional static checks and complexity analysis help identify potential issues.

### Step 4: AI-Powered Review
The Gemini API processes the code and generates structured review information, including:
- Summary
- Potential bugs
- Suggested improvements
- Complexity observations
- Improved code
- Overall review score

### Step 5: Result Generation
The analysis results are presented through an interactive dashboard for easier understanding and comparison.

## 8. Project Structure

The repository contains the following major components (illustrative structure; verify against the current branch):

```text
Code-Visualiser-Python/
│
├── app.py
│   └── Main Streamlit application
│
├── reviewer.py
│   └── AI-powered code review engine
│
├── github_fetcher.py
│   └── GitHub repository fetching and processing
│
├── test_github_fetcher.py
│   └── GitHub fetcher tests
│
├── requirements.txt
│   └── Project dependencies
│
├── .gitignore
│   └── Ignored files and directories
│
└── README.md
    └── Project documentation
```

## 9. Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- A Google Gemini API key
- Internet connection

### Step 1: Clone the repository

```bash
git clone https://github.com/Srish-pathak/Code-Visualiser-Python.git

cd Code-Visualiser-Python
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**
```bash
venv\Scripts\activate
```

**Linux / macOS**
```bash
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create a `.env` file or configure the environment variable in your deployment environment.

```env
GEMINI_API_KEY=your_gemini_api_key
```

Never commit API keys or other sensitive credentials to GitHub.

### Step 5: Run the application

```bash
streamlit run app.py
```

Open the local URL displayed in your terminal.

## 10. Testing

Run the project tests using:

```bash
pytest -v
```

Additional validation:

```bash
python -m compileall .
```

Testing should cover:
- Valid and invalid code inputs.
- Syntax errors.
- Supported and unsupported file extensions.
- Invalid GitHub repository URLs.
- Missing or inaccessible repository files.
- API failures and malformed AI responses.
- Complexity analysis and review output consistency.

## 11. Security Considerations

- API credentials must be stored in environment variables.
- Repository fetching should validate user-provided URLs.
- File size and file count limits should be enforced.
- Unsupported files and binary files should be excluded.
- AI-generated suggestions should be reviewed before implementation.
- Untrusted source code should not be executed automatically.

## 12. Limitations

- AI-generated suggestions may not always be correct.
- Static analysis cannot detect every logical or runtime error.
- Analysis quality depends on source code quality and available context.
- Repository access may be limited by GitHub permissions and API restrictions.
- Supported languages and file extensions depend on the implemented analyzers.

## 13. Future Scope

Potential future enhancements include:

1. Multi-language static analysis support.
2. Advanced multi-agent code review architecture.
3. Automated security vulnerability detection.
4. Integration with GitHub Pull Requests.
5. Test case generation and execution in a secure sandbox.
6. Automated technical documentation generation.
7. Code similarity and duplication detection.
8. Advanced maintainability metrics.
9. Historical code quality tracking.
10. RFC and technical specification linting.

## 14. Expected Impact

TechSpecAnalyser aims to make code review more systematic, accessible, and understandable by combining conventional static analysis techniques with AI-assisted reasoning.

It can serve as a development support tool for students, individual developers, and software engineering teams.

## 15. Author

**Srishti Pathak**

Integrated B.Tech & M.Tech in Computer Science and Engineering  
Specialization: Artificial Intelligence and Data Science  
Central University of Jharkhand

**GitHub:** https://github.com/Srish-pathak

**Project Repository:** https://github.com/Srish-pathak/Code-Visualiser-Python

---

## 16. License

This project is currently maintained as an academic engineering project. A formal open-source license should be added to the repository before external redistribution.

---

<p align="center">

**TechSpecAnalyser (CodeLens AI)**

*Making Code Review More Intelligent, Structured, and Explainable.*

</p>
