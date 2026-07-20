import csv
import io
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.utils import database

router = APIRouter()


@router.get("/history")
async def get_history():
    return await database.get_verification_runs()


@router.delete("/history")
async def delete_history():
    await database.clear_history()
    return {"status": "success", "message": "Verification history cleared."}


@router.get("/history/export/json")
async def export_history_json():
    """Download full verification history as a JSON file."""
    runs = await database.get_verification_runs()
    content = json.dumps(runs, indent=2, default=str)
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=verifyai_history.json"},
    )


@router.get("/history/export/csv")
async def export_history_csv():
    """Download history as CSV with per-check status and score columns."""
    runs = await database.get_verification_runs()
    output = io.StringIO()

    all_check_keys: set = set()
    for run in runs:
        all_check_keys.update(run.get("results", {}).keys())
    check_keys = sorted(all_check_keys)

    fieldnames = (
        ["id", "timestamp", "source", "status", "passed_count", "failed_count",
         "prompt", "message", "expected_output"]
        + [f"{k}_status" for k in check_keys]
        + [f"{k}_score" for k in check_keys]
    )

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for run in runs:
        row: dict = {
            "id": run.get("id"),
            "timestamp": run.get("timestamp"),
            "source": run.get("source"),
            "status": run.get("status"),
            "passed_count": run.get("passed_count"),
            "failed_count": run.get("failed_count"),
            "prompt": run.get("prompt", "")[:500],
            "message": run.get("message", "")[:500],
            "expected_output": run.get("expected_output", "")[:300],
        }
        results = run.get("results", {})
        for k in check_keys:
            check = results.get(k, {})
            row[f"{k}_status"] = check.get("status", "")
            row[f"{k}_score"] = check.get("score", "")
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=verifyai_history.csv"},
    )


@router.get("/stats")
async def get_stats():
    runs = await database.get_stats()
    total = len(runs)
    if total == 0:
        return {"total_runs": 0, "pass_rate": 0.0, "platform_stats": {}}

    passed_runs = sum(1 for r in runs if r["status"] == "passed")

    platform_stats: dict = {}
    for r in runs:
        src = r["source"]
        bucket = platform_stats.setdefault(src, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if r["status"] == "passed":
            bucket["passed"] += 1

    return {
        "total_runs": total,
        "pass_rate": round(passed_runs / total, 3),
        "platform_stats": {
            src: {
                "total": s["total"],
                "passed": s["passed"],
                "pass_rate": round(s["passed"] / s["total"], 3),
            }
            for src, s in platform_stats.items()
        },
    }
