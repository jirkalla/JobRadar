"""FastAPI application for JobRadar Web UI — routing only, no business logic."""

import asyncio
import json
import shutil
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from src import generator
from src.ai_client import get_client
from src.db import (
    get_activity_log,
    get_activity_report,
    get_document,
    get_documents,
    get_job,
    get_jobs,
    get_outcomes,
    get_weekly_summary,
    log_action,
    rate_document,
    record_outcome,
    save_document,
    update_job_status,
)
from src.report import generate_report
from src.generator import _slugify
from src.pdf_writer import cover_letter_md_to_pdf, cv_md_to_pdf

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


_VALID_REPLY_TYPES = {'no_reply', 'rejection', 'positive', 'interview', 'offer'}


@app.get("/jobs/{job_id}/status", response_class=HTMLResponse)
async def status_form(request: Request, job_id: str) -> Response:
    """Render the outcome entry form."""
    job = get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request, "404.html", {"job_id": job_id}, status_code=404
        )
    return templates.TemplateResponse(request, "status_form.html", {"job": job})


@app.post("/jobs/{job_id}/status")
async def status_update(
    request: Request,
    job_id: str,
    action: str = Form(...),
    reply_type: str | None = Form(default=None),
    reply_date: str | None = Form(default=None),
    notes: str | None = Form(default=None),
) -> Response:
    """Handle approve/reject (Case A) and outcome entry (Case B)."""
    job = get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request, "404.html", {"job_id": job_id}, status_code=404
        )

    if action == "approve":
        # update_job_status() writes to activity_log internally — no second call
        update_job_status(job_id, "approved")
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    if action == "reject":
        update_job_status(job_id, "rejected")
        return RedirectResponse(f"/jobs/{job_id}", status_code=303)

    if action == "outcome":
        if not reply_type or reply_type not in _VALID_REPLY_TYPES:
            return templates.TemplateResponse(
                request,
                "status_form.html",
                {"job": job, "error": f"Invalid reply type: {reply_type!r}"},
                status_code=400,
            )
        record_outcome(
            job_id,
            reply_type,
            reply_date or None,
            notes or None,
        )
        return RedirectResponse(
            f"/jobs/{job_id}?msg=Outcome+recorded", status_code=303
        )

    # Unknown action
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


# ---------------------------------------------------------------------------
# Generation helper
# ---------------------------------------------------------------------------

async def _run_generation(job: dict, jd_text: str, tmp_dir: Path) -> dict:
    """Run the full generation pipeline (blocking calls via asyncio.to_thread).

    Writes files to tmp_dir. Returns a dict with keys:
      cl_text    — plain text body of the cover letter
      cv_changes — dict from generate_cv_changes(), or None if unavailable
      cl_md_path, cl_body_path, cl_pdf_path — Path objects
      cv_md_path, cv_pdf_path               — Path objects or None
    """
    profile = yaml.safe_load(Path("config/profile.yaml").read_text(encoding="utf-8"))
    client = get_client(profile)

    date_str     = datetime.now(timezone.utc).strftime("%Y%m%d")
    company_slug = _slugify(job["company"])
    language     = job.get("language") or "en"

    # Cover letter — up to 3 attempts on banned-phrase ValueError
    cl_text: str | None = None
    last_err: str = ""
    for _ in range(3):
        try:
            cl_text = await asyncio.to_thread(
                generator.generate_cover_letter, client, profile, jd_text, language
            )
            break
        except ValueError as exc:
            last_err = str(exc)

    if cl_text is None:
        raise ValueError(f"Could not produce a clean cover letter after 3 attempts. Last error: {last_err}")

    # Write cover letter markdown files
    cl_md_path   = tmp_dir / f"cl_{date_str}_{company_slug}.md"
    cl_body_path = tmp_dir / f"cl_{date_str}_{company_slug}_body.md"
    cl_pdf_path  = tmp_dir / f"cl_{date_str}_{company_slug}.pdf"

    await asyncio.to_thread(
        generator.write_cover_letter_md,
        cl_text, cl_md_path, cl_body_path,
        profile, job["company"], date_str, language,
    )
    await asyncio.to_thread(cover_letter_md_to_pdf, cl_md_path, cl_pdf_path)

    # CV changes — skip silently on any error
    cv_changes = None
    try:
        cv_changes = await asyncio.to_thread(
            generator.generate_cv_changes, client, profile, jd_text
        )
    except (FileNotFoundError, ValueError):
        pass

    cv_md_path  = None
    cv_pdf_path = None
    if cv_changes is not None:
        cv_base = Path("examples/cv_base.md")
        if cv_base.exists():
            cv_md_path  = tmp_dir / f"cv_{date_str}_{company_slug}.md"
            cv_pdf_path = tmp_dir / f"cv_{date_str}_{company_slug}.pdf"
            await asyncio.to_thread(generator.apply_cv_changes, cv_base, cv_changes, cv_md_path)
            await asyncio.to_thread(cv_md_to_pdf, cv_md_path, cv_pdf_path)

    return {
        "cl_text":      cl_text,
        "cv_changes":   cv_changes,
        "cl_md_path":   cl_md_path,
        "cl_body_path": cl_body_path,
        "cl_pdf_path":  cl_pdf_path,
        "cv_md_path":   cv_md_path,
        "cv_pdf_path":  cv_pdf_path,
        "date_str":     date_str,
    }


# ---------------------------------------------------------------------------
# Generation routes
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/generate")
async def generate_start(request: Request, job_id: str) -> Response:
    """Generate cover letter and CV changes, write to tmp, render preview."""
    job = get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request, "404.html", {"job_id": job_id}, status_code=404
        )
    if job["status"] != "approved":
        return templates.TemplateResponse(
            request, "job_detail.html",
            {
                "job":       job,
                "documents": get_documents(job_id),
                "outcomes":  get_outcomes(job_id),
                "activity":  get_activity_log(job_id=job_id),
                "error":     f"Cannot generate: job status is '{job['status']}' (must be 'approved').",
            },
            status_code=400,
        )

    jd_text = job.get("jd_text") or ""
    if not jd_text:
        return RedirectResponse(f"/jobs/{job_id}?msg=No+job+description+stored", status_code=303)

    # Parse JSON fields before any branching so every code path renders correctly
    job["strong_matches"] = json.loads(job.get("strong_matches") or "[]")
    job["concerns"]       = json.loads(job.get("concerns") or "[]")
    job["tech_stack"]     = json.loads(job.get("tech_stack") or "[]")

    tmp_job_dir = TMP_DIR / job_id
    if tmp_job_dir.exists():
        shutil.rmtree(tmp_job_dir)
    tmp_job_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = await _run_generation(job, jd_text, tmp_job_dir)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        shutil.rmtree(tmp_job_dir, ignore_errors=True)
        err_msg = str(exc).replace('+', '%2B').replace(' ', '+')
        return RedirectResponse(f"/jobs/{job_id}?msg=Generation+failed:+{err_msg}", status_code=303)

    return templates.TemplateResponse(request, "generate_result.html", {
        "job":        job,
        "cl_text":    result["cl_text"],
        "cv_changes": result["cv_changes"],
        "cv_md_name": result["cv_md_path"].name if result["cv_md_path"] else None,
        "today":      datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })


@app.post("/jobs/{job_id}/generate/confirm")
async def generate_confirm(request: Request, job_id: str) -> Response:
    """Move tmp files to permanent path, save DB records, mark applied."""
    form = await request.form()
    tmp_job_dir = TMP_DIR / job_id
    if not tmp_job_dir.exists():
        return RedirectResponse(f"/jobs/{job_id}?msg=Already+saved", status_code=303)

    job = get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request, "404.html", {"job_id": job_id}, status_code=404
        )

    # Find files in tmp
    tmp_files = list(tmp_job_dir.iterdir())

    # Determine date_str — from form override, then filename, then today
    date_str = (form.get("applied_date") or "").replace("-", "")
    if not (date_str.isdigit() and len(date_str) == 8):
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        for f in tmp_files:
            if f.name.startswith("cl_") and f.suffix == ".md" and "_body" not in f.name:
                parts = f.stem.split("_")
                if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 8:
                    date_str = parts[1]
                    break

    company_slug = _slugify(job["company"])
    role_slug    = _slugify(job.get("role_title") or "")
    perm_dir     = Path("output") / date_str / company_slug / role_slug

    # Auto-version if the directory already exists
    if perm_dir.exists():
        for n in range(2, 10):
            candidate = Path("output") / date_str / company_slug / f"{role_slug}_v{n}"
            if not candidate.exists():
                perm_dir = candidate
                break

    perm_dir.mkdir(parents=True, exist_ok=True)

    # Move all files
    for f in tmp_files:
        shutil.move(str(f), str(perm_dir / f.name))

    # Save document records
    for f in sorted(perm_dir.iterdir()):
        if f.name.endswith("_body.md"):
            save_document(job_id, "cover_letter", str(f))
        elif f.name.startswith("cv_") and f.suffix == ".md":
            save_document(job_id, "cv", str(f))

    # Log generation action BEFORE status update
    log_action(job_id, "generated", detail=str(perm_dir))

    # update_job_status() writes to activity_log internally — no second log_action
    update_job_status(job_id, "applied", applied_at=date_str)

    # Clean up tmp
    shutil.rmtree(tmp_job_dir, ignore_errors=True)

    return RedirectResponse(f"/jobs/{job_id}?msg=Documents+saved#docs", status_code=303)


@app.post("/jobs/{job_id}/generate/discard")
async def generate_discard(job_id: str) -> Response:
    """Delete tmp files without saving anything."""
    tmp_job_dir = TMP_DIR / job_id
    shutil.rmtree(tmp_job_dir, ignore_errors=True)
    return RedirectResponse(f"/jobs/{job_id}?msg=Generation+discarded", status_code=303)


@app.post("/jobs/{job_id}/generate/revise")
async def generate_revise(
    request: Request,
    job_id: str,
    notes: str = Form(default=""),
) -> Response:
    """Re-run generation with optional feedback appended to jd_text. No DB writes."""
    job = get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request, "404.html", {"job_id": job_id}, status_code=404
        )

    jd_text = job.get("jd_text") or ""
    if notes.strip():
        jd_text = jd_text + f"\n\nRegeneration notes: {notes.strip()}"

    # Parse JSON fields before any branching so every code path renders correctly
    job["strong_matches"] = json.loads(job.get("strong_matches") or "[]")
    job["concerns"]       = json.loads(job.get("concerns") or "[]")
    job["tech_stack"]     = json.loads(job.get("tech_stack") or "[]")

    tmp_job_dir = TMP_DIR / job_id
    if tmp_job_dir.exists():
        shutil.rmtree(tmp_job_dir)
    tmp_job_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = await _run_generation(job, jd_text, tmp_job_dir)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        shutil.rmtree(tmp_job_dir, ignore_errors=True)
        err_msg = str(exc).replace('+', '%2B').replace(' ', '+')
        return RedirectResponse(f"/jobs/{job_id}?msg=Revision+failed:+{err_msg}", status_code=303)

    return templates.TemplateResponse(request, "generate_result.html", {
        "job":        job,
        "cl_text":    result["cl_text"],
        "cv_changes": result["cv_changes"],
        "cv_md_name": result["cv_md_path"].name if result["cv_md_path"] else None,
        "today":      datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })


# ---------------------------------------------------------------------------
# Document rating
# ---------------------------------------------------------------------------

@app.post("/documents/{doc_id}/rate")
async def document_rate(
    request: Request,
    doc_id: int,
    rating: int = Form(...),
) -> Response:
    """Rate a document 1–5. rating >= 4 marks it as a style example."""
    if rating < 1 or rating > 5:
        return HTMLResponse("Invalid rating: must be between 1 and 5.", status_code=400)
    doc = get_document(doc_id)
    if doc is None:
        return HTMLResponse("Document not found.", status_code=404)
    rate_document(doc_id, rating)
    return RedirectResponse(f"/jobs/{doc['job_id']}", status_code=303)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@app.get("/report", response_class=HTMLResponse)
async def report_get(
    request: Request,
    date_from: str = Query(default=""),
    date_to:   str = Query(default=""),
) -> HTMLResponse:
    """Show the report form with an optional date range and a preview table."""
    # Defaults: last 30 days
    default_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    default_to   = date.today().strftime("%Y-%m-%d")
    date_from_form = date_from or default_from
    date_to_form   = date_to   or default_to
    # DB call expects YYYYMMDD
    date_from_fmt = date_from_form.replace("-", "")
    date_to_fmt   = date_to_form.replace("-", "")
    preview_rows  = get_activity_report(date_from_fmt, date_to_fmt)
    return templates.TemplateResponse(request, "report.html", {
        "preview_rows":   preview_rows,
        "date_from_form": date_from_form,
        "date_to_form":   date_to_form,
        "msg":            None,
    })


@app.post("/report/export")
async def report_export(
    request: Request,
    date_from: str = Form(...),
    date_to:   str = Form(...),
    format:    str = Form(...),
) -> Response:
    """Export PDF or CSV for the chosen date range."""
    # Browser submits YYYY-MM-DD; generate_report() expects YYYYMMDD
    date_from_fmt = date_from.replace("-", "")
    date_to_fmt   = date_to.replace("-", "")

    pdf_path, csv_path, count = generate_report(date_from_fmt, date_to_fmt)

    if count == 0:
        # Re-render form with message
        preview_rows = get_activity_report(date_from_fmt, date_to_fmt)
        return templates.TemplateResponse(
            request, "report.html",
            {
                "preview_rows":   preview_rows,
                "date_from_form": date_from,
                "date_to_form":   date_to,
                "msg":            "No activity found in this date range.",
            },
            status_code=200,
        )

    if format == "pdf":
        return FileResponse(pdf_path, media_type="application/pdf",
                            filename=Path(pdf_path).name)
    return FileResponse(csv_path, media_type="text/csv",
                        filename=Path(csv_path).name)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@app.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    job_id: str = Query(default=""),
    action: str = Query(default=""),
    limit: int = Query(default=50),
) -> HTMLResponse:
    """Display the full activity log with optional filters."""
    limit = max(1, min(limit, 200))
    rows = get_activity_log(
        job_id=job_id or None,
        action=action or None,
        limit=limit,
    )
    return templates.TemplateResponse(request, "history.html", {
        "rows":      rows,
        "job_id":    job_id,
        "action":    action,
        "limit":     limit,
    })


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

PROFILE_PATH = Path("config/profile.yaml")


@app.get("/profile", response_class=HTMLResponse)
async def profile_get(
    request: Request,
    msg: str = Query(default=""),
) -> HTMLResponse:
    """Display the editable profile fields."""
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    hybrid_cities_str = ", ".join(profile.get("restrictions", {}).get("hybrid_cities", []))
    return templates.TemplateResponse(request, "profile.html", {
        "profile":           profile,
        "hybrid_cities_str": hybrid_cities_str,
        "msg":               msg,
    })


@app.post("/profile", response_class=HTMLResponse)
async def profile_post(
    request: Request,
    name:              str = Form(...),
    email:             str = Form(...),
    min_score_to_show: str = Form(...),
    hybrid_cities:     str = Form(...),
    provider:          str = Form(...),
    model:             str = Form(...),
) -> Response:
    """Save the listed profile fields surgically — all other keys preserved."""
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))

    profile["personal"]["name"]  = name
    profile["personal"]["email"] = email
    profile["preferences"]["min_score_to_show"] = int(min_score_to_show)
    profile["restrictions"]["hybrid_cities"] = [
        c.strip() for c in hybrid_cities.split(",") if c.strip()
    ]
    profile["ai"]["provider"] = provider
    profile["ai"]["model"]    = model

    PROFILE_PATH.write_text(yaml.dump(profile, allow_unicode=True), encoding="utf-8")
    return RedirectResponse("/profile?msg=Profile+saved", status_code=303)

