# VerifyAI | AI & Coding Agent Verification Harness

VerifyAI is a verification harness for testing, auditing, and evaluating responses from AI assistants and coding agents (Cursor, Devin, Claude, GPT, and others). It runs responses through a configurable battery of quality and safety checks, and includes a multi-model evaluation suite for benchmarking LLMs side-by-side.

---

## What VerifyAI Can Do

### 🔍 Verification Checks (8 engines)

| Check | What it does |
|---|---|
| **Code Syntax** | Compiles Python blocks via AST, validates JSON, flags lazy placeholders and `// TODO` markers |
| **Safety & PII** | Detects jailbreak patterns, leaked emails, phone numbers, credit cards, and SSNs |
| **Citation Verifier** | Extracts URLs from Perplexity/Gemini outputs and HEAD-checks each link for liveness |
| **JSON Compliance** | Validates structured outputs against RFC 8259 parser logic |
| **Semantic Similarity** | Cosine similarity via sentence embeddings (`all-MiniLM-L6-v2`) vs a reference output; threshold 0.70 |
| **Fluency & Grammar** | Grammar issue count via LanguageTool; passes at ≤ 3 issues |
| **Sentiment Match** | String-comparison sentiment alignment vs expected output; falls back to local LLM |
| **Summarization Quality** | Cosine similarity of summary vs reference; threshold 0.60 |

Every check returns a **status** (`passed` / `warning` / `failed`) and a **numeric score** (0.0–1.0) for quantitative comparison across models.

The pipeline's `overall_status` follows a three-tier priority: `failed > warning > passed` — a response with unresolved warnings will no longer silently return as `"passed"`.

### 📊 Multi-Model Benchmark Suite
- **Model Endpoint Registry** — configure Local Ollama, OpenAI, Anthropic, Gemini, or any OpenAI-compatible interface (vLLM, LM Studio, etc.)
- **Test Case Repository** — create and manage benchmark prompts with optional reference outputs
- **Comparison Matrix** — run selected test cases against multiple models and inspect results per cell

### 📥 Bulk Processing
- **CSV/Excel Uploader** — drag-and-drop spreadsheets containing prompts and responses for batch evaluation
- **Batch JSON API** — `POST /api/verify/batch` for programmatic automation

### 📤 Export & Reporting
- **`GET /api/history/export/csv`** — downloads the full verification history as a flat CSV with per-check status and score columns
- **`GET /api/history/export/json`** — downloads full history as a structured JSON file
- Both exports are also accessible via the "Export CSV" / "Export JSON" buttons in the Logs & History tab

---

## Project Architecture

```text
VerifyAI/
├── app/
│   ├── main.py                      # FastAPI entry point, all API routes
│   ├── static/
│   │   └── index.html               # Single-page dashboard UI
│   ├── evaluations/                 # Verification engines
│   │   ├── check_code.py            # Syntax parser & completeness audit
│   │   ├── check_safety.py          # PII shield & jailbreak detector
│   │   ├── check_grounding.py       # URL extraction & liveness checks
│   │   ├── check_structure.py       # JSON/schema compliance
│   │   ├── check_consistency.py     # Semantic cosine similarity
│   │   ├── check_fluency.py         # Grammar & linguistic flow
│   │   ├── check_sentiment.py       # Sentiment alignment
│   │   └── check_summarization.py   # Summarization quality
│   ├── models/
│   │   └── ollama_chat.py           # Local Ollama wrapper
│   └── utils/
│       ├── database.py              # SQLite schema, seeds, CRUD, key encryption
│       ├── file_parser.py           # CSV and Excel parsing
│       ├── llm_execution.py         # Async HTTP clients for LLM providers
│       ├── get_cosine_similarity_score.py  # Singleton-cached sentence embeddings
│       └── get_fluency_score.py     # Singleton-cached LanguageTool instance
├── tests/
│   ├── test_main.py
│   ├── test_verification.py
│   ├── test_batch_and_evaluation.py
│   ├── test_get_cosine_similarity_score.py  # Cosine similarity unit tests
│   └── test_semantic_check.py               # /api/verify integration tests
├── requirements.txt
└── pyproject.toml
```

---

## Setup & Running

### 1. Create a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` will pull in `torch` (~120 MB). The SentenceTransformer model and LanguageTool JVM are each loaded once on first use and cached for the lifetime of the server process.

### 3. Set environment variables

```bash
# Required for persistent API key encryption (recommended)
export VERIFYAI_SECRET_KEY="<fernet-key>"   # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Required only if evaluating cloud models via the Model Evaluation suite
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

If `VERIFYAI_SECRET_KEY` is not set, a temporary key is generated at startup and printed to the console. API keys saved during that session will not be recoverable after a restart.

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

- Dashboard: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

On first run, `verifyai.db` is created automatically and seeded with four default test cases and five model endpoint configurations.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/verify` | Run verification pipeline on a single prompt/response pair |
| `POST` | `/api/verify/batch` | Verify an array of items in one request |
| `POST` | `/api/verify/upload` | Upload a CSV or Excel file for batch verification |
| `GET` | `/api/history` | Retrieve all past verification runs |
| `DELETE` | `/api/history` | Clear verification history |
| `GET` | `/api/history/export/csv` | Download history as CSV |
| `GET` | `/api/history/export/json` | Download history as JSON |
| `GET` | `/api/stats` | Aggregate pass rates and platform stats |
| `GET` | `/api/test_cases` | List test cases |
| `POST` | `/api/test_cases` | Create a test case |
| `DELETE` | `/api/test_cases/{id}` | Delete a test case |
| `GET` | `/api/models` | List configured model endpoints |
| `POST` | `/api/models` | Create or update a model endpoint |
| `DELETE` | `/api/models/{id}` | Delete a model endpoint |
| `POST` | `/api/models/test` | Send a test ping to a model endpoint |
| `POST` | `/api/evaluations/run` | Run the multi-model evaluation suite |

### `POST /api/verify` — request body

```json
{
  "source": "ChatGPT",
  "prompt": "Write a Python factorial function.",
  "message": "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)",
  "expected_output": "def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n-1)",
  "checks": ["code_check", "safety_check", "semantic_check", "fluency_check"]
}
```

`checks` is optional — omit it to run all 8 checks. Valid values: `code_check`, `safety_check`, `grounding_check`, `structure_check`, `semantic_check`, `fluency_check`, `sentiment_check`, `summarization_check`.

### Response shape

```json
{
  "id": "uuid",
  "timestamp": "2025-01-01T00:00:00",
  "source": "ChatGPT",
  "status": "passed",
  "summary": { "passed": 3, "failed": 0, "warning": 1 },
  "results": {
    "semantic_check": {
      "status": "passed",
      "message": "Semantic similarity score is 0.872 (threshold: 0.700).",
      "details": { "score": 0.872 },
      "score": 0.872
    }
  }
}
```

---

## Running Tests

```bash
PYTHONPATH=. pytest tests/ -v
```

The test suite covers evaluation routines, PII detection, AST code parsing, CSV/Excel parsing, cosine similarity correctness properties, and `/api/verify` integration paths.

---

## Security Notes

- API keys entered through the Model Endpoint UI are encrypted at rest using [Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption before being written to `verifyai.db`.
- Set `VERIFYAI_SECRET_KEY` to a stable Fernet key in production. Without it, a new key is generated each restart and previously saved keys become unreadable.
- The SQLite database (`verifyai.db`) is local only and not exposed by any endpoint.
