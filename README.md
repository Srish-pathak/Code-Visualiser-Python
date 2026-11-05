TechSpecAnalyser
CodeLens AI
AI-Assisted Static Analysis and Intelligent Code Review Platform
Python
Streamlit
Google Gemini
AST Analysis
Radon

Academic Engineering Project-I | Central University of Jharkhand









vibesec.app


1. Project Introduction
TechSpecAnalyser (CodeLens AI) is an intelligent software engineering support platform that combines static program analysis with Large Language Model-based reasoning to assist developers in understanding, reviewing and improving source code.

It is designed to reduce repetitive manual code inspection and provide structured feedback about potential defects, code quality, complexity and possible improvements.

The system combines deterministic analysis techniques with AI-generated insights rather than relying solely on generative AI.
2. Problem Definition
Software developers face several challenges during code review:
- Manual code review consumes time.
- Potential defects may remain unnoticed.
- Complex code is difficult to maintain.
- Beginners may struggle to understand code quality issues.
- AI-only code review may produce inaccurate suggestions.
- Reviewing multiple files in a repository can be tedious.
Proposed solution: An integrated platform that combines static analysis, repository processing and AI-assisted review to produce structured, explainable feedback.
3. Objectives
1. Automate preliminary source code review.
2. Detect potential programming errors and suspicious patterns.
3. Analyse code structure using static analysis.
4. Generate context-aware improvement suggestions.
5. Provide complexity insights.
6. Support analysis of public GitHub repositories.
7. Present results in a user-friendly dashboard.
8. Encourage better software engineering practices.
4. System Architecture







medium.com


The architecture consists of the following logical components:
Component	Responsibility
User Interface	Accepts source code and repository URLs
Input Processor	Validates and prepares source files
GitHub Fetcher	Retrieves supported repository files
Static Analyzer	Performs deterministic source code checks
AST Processor	Examines Python syntax structure
Complexity Analyzer	Calculates complexity metrics using Radon
AI Review Engine	Generates structured review feedback
Result Processor	Organizes analysis outputs
Dashboard	Displays review results

5. Core Technical Concepts
Static Code Analysis

Static analysis examines source code without executing the program. It helps identify structural issues and potential defects.

Abstract Syntax Tree (AST)

AST represents source code in a tree structure. It allows the analyzer to inspect programming constructs such as functions, loops, conditions and imports.

Large Language Models

Gemini is integrated to interpret source code and generate explanations, improvement suggestions and structured review results.

Cyclomatic Complexity

Cyclomatic complexity estimates the number of independent execution paths in a program. Radon is used for complexity-related analysis.
6. AI Review Pipeline







linkedin.com


1. Receive source code.
2. Validate input.
3. Perform available static checks.
4. Calculate complexity metrics.
5. Send relevant code context to the AI review engine.
6. Obtain structured review output.
7. Organize bugs, improvements and complexity observations.
8. Display results to the user.
7. GitHub Repository Integration
The GitHub integration extends the platform beyond single-file analysis.

Workflow:
- User provides a public GitHub repository URL.
- The repository fetcher identifies the repository and its default branch.
- Supported source files are collected.
- Unnecessary directories and unsupported files are excluded.
- File count and file size limits help control processing.
- Retrieved files are passed through the review workflow.
The implementation supports configured source extensions including Python, Java, C++, JavaScript, JSX, TypeScript, TSX, HTML, CSS and SCSS.
8. Review Dashboard
The planned presentation structure includes seven review sections:
Tab	Purpose
Overview	Summary of the review
Issues	Potential bugs and detected concerns
Improvements	Recommendations for better code
Complexity	Complexity observations
Score	Overall review score
Before/After Diff	Comparison of original and suggested code
History	Previous review records, if enabled

9. Technology Stack
- Python — core application logic.
- Streamlit — application interface.
- Google Gemini API — AI-powered review.
- Python AST — structural code inspection.
- Radon — complexity analysis.
- GitHub integration — repository retrieval.
- Pytest — automated testing.
- Git and GitHub — version control.
10. Quality Assurance
Testing should evaluate:
- Valid source code.
- Invalid syntax.
- Empty input.
- Unsupported file types.
- Large source files.
- Invalid repository URLs.
- Missing repository files.
- API timeout and failures.
- Malformed AI responses.
- Output consistency.
Important: Add actual test counts, test results, and screenshots before claiming measured accuracy or reliability.
11. Security and Reliability
- Store API keys in environment variables.
- Do not expose secrets in source code.
- Validate repository URLs.
- Enforce file-size and file-count restrictions.
- Avoid executing untrusted source code.
- Handle external API errors gracefully.
- Treat AI-generated code as suggestions requiring human review.
12. Limitations
- Static analysis cannot detect every runtime defect.
- AI-generated recommendations may be incorrect.
- Analysis depends on the supported language and file types.
- Large repositories require processing constraints.
- Complexity metrics do not independently measure overall code quality.
13. Future Enhancements
- Multi-language AST-based analysis.
- Security vulnerability scanning.
- Automated test generation.
- Secure sandbox-based code execution.
- Pull request review integration.
- Technical specification and RFC linting.
- Advanced multi-agent review orchestration.
- Historical quality trend analysis.
14. Academic Information
Project: TechSpecAnalyser (CodeLens AI)

Student: Srishti Pathak

Institution: Central University of Jharkhand, Ranchi

Degree: Integrated B.Tech & M.Tech in Computer Science and Engineering

Specialization: Artificial Intelligence and Data Science

Course: Engineering Project-I

Course Code: CSE05419

Project Type: Individual Engineering Project

Project Guide: Dr. Prashant Prashun, Assistant Professor (confirm before publishing)
15. Repository and Setup
Repository: Code-Visualiser-Python
git clone https://github.com/Srish-pathak/Code-Visualiser-Python.git
cd Code-Visualiser-Python

python -m venv venv


Windows:
venv\Scripts\activate


Install:
pip install -r requirements.txt


Configure:
GEMINI_API_KEY=your_gemini_api_key


Launch:
streamlit run app.py


Run tests:
pytest -v


16. Expected Contribution
The main engineering contribution is the integration of conventional static analysis with AI-assisted code review in a unified workflow.

It provides a structured way to inspect source code, understand potential issues and evaluate improvement suggestions.
17. License and Acknowledgements
This project is developed as an academic engineering project. A suitable open-source license should be added before external redistribution.

TechSpecAnalyser (CodeLens AI)

Bridging Traditional Static Analysis and AI-Assisted Software Engineering
