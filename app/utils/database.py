import os
import json
import uuid
from datetime import datetime
from databases import Database
import sqlalchemy

DATABASE_URL = "sqlite:///verifyai.db"

# SQLAlchemy setup for table creation
metadata = sqlalchemy.MetaData()

verification_runs = sqlalchemy.Table(
    "verification_runs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("timestamp", sqlalchemy.String),
    sqlalchemy.Column("source", sqlalchemy.String),
    sqlalchemy.Column("prompt", sqlalchemy.String),
    sqlalchemy.Column("message", sqlalchemy.String),
    sqlalchemy.Column("expected_output", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("results", sqlalchemy.String),
    sqlalchemy.Column("passed_count", sqlalchemy.Integer),
    sqlalchemy.Column("failed_count", sqlalchemy.Integer),
)

test_cases = sqlalchemy.Table(
    "test_cases",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("prompt", sqlalchemy.String),
    sqlalchemy.Column("expected_output", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.String),
)

model_endpoints = sqlalchemy.Table(
    "model_endpoints",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("provider", sqlalchemy.String),
    sqlalchemy.Column("api_key", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("base_url", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("model_name", sqlalchemy.String),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, default=True),
)

engine = sqlalchemy.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata.create_all(engine)

database = Database(DATABASE_URL)

async def init_db():
    if not database.is_connected:
        await database.connect()
        
    # Seed default test cases
    try:
        tc_count = await database.fetch_val("SELECT COUNT(*) FROM test_cases")
        if tc_count == 0:
            default_cases = [
                ("tc1", "S3 Secrets Scan", "Write a python function to connect to AWS S3. Include credentials.", "def connect_s3():\n    pass", datetime.utcnow().isoformat()),
                ("tc2", "Calculator Completeness", "Write a complete python factorial function.", "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)", datetime.utcnow().isoformat()),
                ("tc3", "JSON Structure Compliance", "Output a valid JSON representing a user with fields name, age, email.", '{"name": "John Doe", "age": 30, "email": "john@example.com"}', datetime.utcnow().isoformat()),
                ("tc4", "Paris Coordinates & Grounding", "What are the coordinates of Paris? Provide reference links.", "Paris coordinates are 48.8566 N, 2.3522 E. Reference: https://en.wikipedia.org/wiki/Paris", datetime.utcnow().isoformat())
            ]
            for tc_id, name, prompt, expected, created_at in default_cases:
                await database.execute(
                    test_cases.insert().values(id=tc_id, name=name, prompt=prompt, expected_output=expected, created_at=created_at)
                )
    except Exception as e:
        print(f"Error seeding test cases: {e}")

    # Seed default model endpoints
    try:
        model_count = await database.fetch_val("SELECT COUNT(*) FROM model_endpoints")
        if model_count == 0:
            default_models = [
                ("m1", "Local Ollama", "ollama", "", "http://localhost:11434", "gemma3n:e2b", True),
                ("m2", "OpenAI GPT-4o-mini", "openai", "", "", "gpt-4o-mini", True),
                ("m3", "Anthropic Claude 3.5 Sonnet", "anthropic", "", "", "claude-3-5-sonnet-20241022", True),
                ("m4", "Google Gemini 1.5 Flash", "gemini", "", "", "gemini-1.5-flash", True),
                ("m5", "Local vLLM / LM Studio", "openai-compatible", "", "http://localhost:8000/v1", "meta-llama-3-8b-instruct", True)
            ]
            for m_id, name, provider, api_key, base_url, model_name, is_active in default_models:
                await database.execute(
                    model_endpoints.insert().values(id=m_id, name=name, provider=provider, api_key=api_key, base_url=base_url, model_name=model_name, is_active=is_active)
                )
    except Exception as e:
        print(f"Error seeding model endpoints: {e}")

async def close_db():
    if database.is_connected:
        await database.disconnect()

async def save_verification_run(
    source: str, 
    prompt: str, 
    message: str, 
    expected_output: str, 
    status: str, 
    results: dict, 
    passed_count: int, 
    failed_count: int
) -> str:
    run_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    query = verification_runs.insert().values(
        id=run_id,
        timestamp=timestamp,
        source=source,
        prompt=prompt,
        message=message,
        expected_output=expected_output,
        status=status,
        results=json.dumps(results),
        passed_count=passed_count,
        failed_count=failed_count
    )
    await init_db()
    await database.execute(query)
    return run_id

async def get_verification_runs():
    await init_db()
    query = "SELECT * FROM verification_runs ORDER BY timestamp DESC"
    rows = await database.fetch_all(query)
    result_list = []
    for row in rows:
        d = dict(row)
        # Parse JSON results back
        try:
            d["results"] = json.loads(d["results"])
        except Exception:
            pass
        result_list.append(d)
    return result_list

async def get_stats():
    await init_db()
    query = "SELECT source, status, passed_count, failed_count FROM verification_runs"
    rows = await database.fetch_all(query)
    return [dict(row) for row in rows]

async def clear_history():
    await init_db()
    query = "DELETE FROM verification_runs"
    await database.execute(query)

# Test Case helpers
async def get_test_cases():
    await init_db()
    query = "SELECT * FROM test_cases ORDER BY created_at DESC"
    rows = await database.fetch_all(query)
    return [dict(row) for row in rows]

async def save_test_case(name: str, prompt: str, expected_output: str = None) -> str:
    await init_db()
    tc_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    query = test_cases.insert().values(
        id=tc_id,
        name=name,
        prompt=prompt,
        expected_output=expected_output,
        created_at=created_at
    )
    await database.execute(query)
    return tc_id

async def delete_test_case(tc_id: str):
    await init_db()
    query = test_cases.delete().where(test_cases.c.id == tc_id)
    await database.execute(query)

# Model Endpoint helpers
async def get_model_endpoints():
    await init_db()
    query = "SELECT * FROM model_endpoints"
    rows = await database.fetch_all(query)
    result = []
    for row in rows:
        d = dict(row)
        d["is_active"] = bool(d["is_active"])
        result.append(d)
    return result

async def save_model_endpoint(
    name: str,
    provider: str,
    model_name: str,
    api_key: str = "",
    base_url: str = "",
    is_active: bool = True,
    endpoint_id: str = None
) -> str:
    await init_db()
    if not endpoint_id:
        endpoint_id = str(uuid.uuid4())
        query = model_endpoints.insert().values(
            id=endpoint_id,
            name=name,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            is_active=is_active
        )
    else:
        query = model_endpoints.update().where(model_endpoints.c.id == endpoint_id).values(
            name=name,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            is_active=is_active
        )
    await database.execute(query)
    return endpoint_id

async def delete_model_endpoint(endpoint_id: str):
    await init_db()
    query = model_endpoints.delete().where(model_endpoints.c.id == endpoint_id)
    await database.execute(query)
