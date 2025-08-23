# FastAPI Application

This project is a FastAPI application structured for easy development and testing. Below are the details regarding the project setup, usage, and testing.

## Project Structure

```
fastapi-app/
├── app/                     # Main application source code
│   ├── main.py             # Entry point for the FastAPI application
│   ├── api/                # API related code
│   │   └── routes.py       # API routes
│   ├── models/             # Data models
│   │   └── __init__.py     # Initialization for models
│   ├── schemas/            # Pydantic schemas
│   │   └── __init__.py     # Initialization for schemas
│   └── dependencies/       # Dependency injection
│       └── __init__.py     # Initialization for dependencies
├── tests/                  # Test files
│   ├── api/                # API tests
│   │   └── test_users_api.py  # Tests for user-related API endpoints
│   ├── ui/                 # UI tests
│   │   ├── page_objects/    # Page Object Model classes for UI testing
│   │   └── test_login.py    # Tests for login functionality
│   └── data/               # Test data management
│       ├── global_data.yml  # Global test data
│       ├── static_data.yml   # Static test data
│       └── dynamic_data.yml  # Dynamic test data
├── tests/conftest.py       # Pytest fixtures and configurations
├── requirements.txt         # Project dependencies
└── pyproject.toml          # Project metadata and dependencies
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fastapi-app
   ```

2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

## Usage Guidelines

- The main application can be accessed at `http://localhost:8000`.
- API documentation is available at `http://localhost:8000/docs`.

## Testing

To run the tests, use the following command:
```
pytest
```

This will execute all tests in the `tests/` directory.