# VerifyAI FastAPI Application

This project is a FastAPI application for evaluating GenAI outputs with a simple web UI and API endpoints.

## Project Structure

```
VerifyAI/
├── app/                         # Main application source code
│   ├── main.py                  # FastAPI entry point
│   ├── static/                  # Static files (frontend)
│   │   └── index.html           # Main UI page
│   ├── evaluations/             # Evaluation logic
│   │   └── check_sentiment.py   # Sentiment evaluation
│   ├── models/                  # Model wrappers/utilities
│   │   └── ollama_chat.py       # Example: Ollama chat model
│   └── utils/                   # Utility functions
│       └── get_cosine_similarity_score.py
├── tests/                       # Test files
│   ├── api/                     # API tests
│   │   └── test_users_api.py
│   ├── ui/                      # UI tests
│   │   ├── page_objects/
│   │   └── test_login.py
│   ├── data/                    # Test data
│   │   ├── global_data.yml
│   │   ├── static_data.yml
│   │   └── dynamic_data.yml
│   └── conftest.py              # Pytest fixtures/config
├── requirements.txt             # Project dependencies
└── pyproject.toml               # Project metadata (optional)
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd VerifyAI
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Usage

- Access the web UI at: [http://localhost:8000/](http://localhost:8000/)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

## Testing

To run all tests:
```bash
pytest
```

This will execute all tests in the `tests/` directory.

---

**Note:**  
- The UI is served from `app/static/index.html`.
- Update `requirements.txt` if you add new dependencies.