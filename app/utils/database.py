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

engine = sqlalchemy.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata.create_all(engine)

database = Database(DATABASE_URL)

async def init_db():
    if not database.is_connected:
        await database.connect()

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
