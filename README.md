# VerifyAI | AI & Coding Agent Verification Harness

VerifyAI is a verification harness designed to test, audit, and evaluate responses from major AI assistants and coding agents (such as Cursor, Devin, Claude, and GPT). It provides real-time verification filters alongside a multi-model evaluation suite that lets you benchmark different LLMs on your custom test prompts.

---

## What VerifyAI Can Do

### 🔍 Real-Time Compliance Filters
VerifyAI runs incoming agent responses through a suite of safety and quality checks:
*   **Code Syntax Validation:** Compiles Python code blocks to detect syntax issues and validates structural JSON configurations.
*   **Completeness & Integrity Check:** Searches for lazy placeholders, ellipses (`...`), or unresolved comments (like `// TODO`).
*   **Jailbreak & PII Shield:** Flags potential jailbreak instructions in prompt streams and prevents leakage of phone numbers, credit cards, SSNs, or email addresses.
*   **Semantic Consistency:** Computes cosine similarity of response text against a reference using sentence embeddings.
*   **Citation & URL Verifier:** Tests citations to confirm external URLs are live and reachable.

### 📊 Multi-Model Benchmark Suite
Evaluate different models side-by-side:
*   **Model Endpoint Registry:** Configure endpoints for Local Ollama, OpenAI, Anthropic, Gemini, or custom OpenAI-compatible interfaces (vLLM, LM Studio, etc.).
*   **Test Case Repository:** Create and organize benchmark prompts with optional target responses.
*   **Comparison Matrix:** Run selected test cases against multiple models to generate a grid reporting compliance status for each run.

### 📥 Bulk Processing
*   **CSV/Excel Uploader:** Drag and drop spreadsheets containing test prompts and responses to evaluate them in bulk.
*   **Batch JSON API:** Send arrays of evaluation items to `/api/verify/batch` to automate tests programmatically.

---

## Project Architecture

Here is the directory structure:

```text
VerifyAI/
├── app/                             # Main FastAPI Application
│   ├── main.py                      # FastAPI entry point & API routes
│   ├── static/                      # Web UI Files
│   │   └── index.html               # Frontend dashboard & evaluation console
│   ├── evaluations/                 # Verification Engines
│   │   ├── check_code.py            # Syntax parser & completeness audit
│   │   ├── check_safety.py          # PII shield & jailbreak detector
│   │   ├── check_grounding.py       # Extract & check URLs
│   │   ├── check_structure.py       # JSON/schema structure checking
│   │   ├── check_consistency.py     # Semantic cosine similarity checks
│   │   └── check_fluency.py         # Grammar & linguistic flow checking
│   ├── models/                      # Legacy model wrappers
│   │   └── ollama_chat.py           
│   └── utils/                       # Core utilities
│       ├── database.py              # SQLite schema, seeds & CRUD helpers
│       ├── file_parser.py           # CSV and Excel parsing (openpyxl)
│       └── llm_execution.py         # Async HTTP client for LLM APIs
├── tests/                           # Verification test suites
│   ├── test_main.py                 
│   ├── test_verification.py         
│   └── test_batch_and_evaluation.py # Tests for upload, batch APIs & CRUD
├── requirements.txt                 # Dependencies
└── pyproject.toml                   
```

*Key Files:*
*   [main.py](file:///Users/lalit.kumar/Documents/Projects/DataMyner_Utils/more/VerifyAI/app/main.py) - Endpoint routing for verification and evaluations.
*   [database.py](file:///Users/lalit.kumar/Documents/Projects/DataMyner_Utils/more/VerifyAI/app/utils/database.py) - Seeding logic and SQLite schema configurations.
*   [file_parser.py](file:///Users/lalit.kumar/Documents/Projects/DataMyner_Utils/more/VerifyAI/app/utils/file_parser.py) - Column mapping and parsing of spreadsheet uploads.
*   [llm_execution.py](file:///Users/lalit.kumar/Documents/Projects/DataMyner_Utils/more/VerifyAI/app/utils/llm_execution.py) - Async clients routing queries to LLM providers.
*   [index.html](file:///Users/lalit.kumar/Documents/Projects/DataMyner_Utils/more/VerifyAI/app/static/index.html) - Client-side UI dashboard.

---

## Setup & Running Guide

### 1. Setup Virtual Environment
Create and activate your environment, then install requirements:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Keys (Optional)
If you evaluate cloud providers, set environment variables. The API client automatically reads them if they are omitted in the UI config fields:
```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GEMINI_API_KEY="your-gemini-key"
```

### 3. Run the App
Start the Uvicorn web server:
```bash
uvicorn app.main:app --reload
```
*   **Web Dashboard:** [http://localhost:8000/](http://localhost:8000/)
*   **Interactive OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

*Note: On your first run, the SQLite database is automatically created (`verifyai.db`) and seeded with default test cases and model endpoints.*

---

## Running Verification Tests

To verify that the harness and all parsing/evaluation APIs function correctly, run the full test suite using `pytest`:
```bash
PYTHONPATH=. pytest
```
This runs all 18 automated tests validating evaluation routines, PII shields, AST code parsing, and CSV/Excel parsing.