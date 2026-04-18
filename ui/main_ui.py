"""FastAPI application for JobRadar Web UI — routing only, no business logic."""

import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from src.db import (
    get_activity_log,
    get_documents,
    get_job,
    get_jobs,
    get_outcomes,
    get_weekly_summary,
)

BASE_DIR = Path(__file__).parent
TMP_DIR  = Path("output/.tmp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Clean up stale temp files from any previous session on startup."""
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="JobRadar", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the dashboard page."""
    jobs = get_jobs()
    by_status: dict[str, int] = {}
    for j in jobs:
        s = j.get("status", "")
        by_status[s] = by_status.get(s, 0) + 1
    stats = {
        "total":    len(jobs),
        "approved": by_status.get("approved", 0),
        "applied":  by_status.get("applied", 0),
        "closed":   by_status.get("closed", 0),
    }
    activity = get_activity_log(limit=10)
    summary  = get_weekly_summary()
    return templates.TemplateResponse(request, "index.html", {
        "stats":    stats,
        "activity": activity,
        "summary":  summary,
    })


@app.get("/jobs", response_class=HTMLResponse)
async def job_list(
    request: Request,
    status: str | None = Query(default=None),
    min_score: int = Query(default=0),
) -> HTMLResponse:
    """Render the job list page with optional filtering."""
    jobs = get_jobs(status=status or None, min_score=min_score)
    return templates.TemplateResponse(request, "jobs.html", {
        "jobs":      jobs,
        "status":    status or "",
        "min_score": min_score,
    })


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: str) -> Response:
    """Render the job detail page."""
    job = get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request, "404.html", {"job_id": job_id}, status_code=404
        )
    # Parse JSON fields stored as strings in the DB
    job["strong_matches"] = json.loads(job.get("strong_matches") or "[]")
    job["concerns"]       = json.loads(job.get("concerns") or "[]")
    job["tech_stack"]     = json.loads(job.get("tech_stack") or "[]")

    documents = get_documents(job_id)
    outcomes  = get_outcomes(job_id)
    activity  = get_activity_log(job_id=job_id)
    return templates.TemplateResponse(request, "job_detail.html", {
        "job":       job,
        "documents": documents,
        "outcomes":  outcomes,
        "activity":  activity,
    })
