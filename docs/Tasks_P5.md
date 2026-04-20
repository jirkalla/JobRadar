# Tasks — Phase 5: Web UI
# JobRadar | Milestone: P5 — Web UI
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Follow the Task Closing Ritual (AI_INSTRUCTIONS.md section 10) after every task
# - Do NOT implement anything outside this file
# - Do NOT add new business logic — UI wraps what already exists

---

## Context — what P5 builds on

P4 delivered a complete CLI pipeline:
  main.py commands:  fetch, process, review, generate, status, report
  src/db.py:         full schema, all read/write functions
  src/generator.py:  CV + cover letter generation, Markdown output
  src/pdf_writer.py: Markdown → PDF via reportlab
  src/scorer.py:     AI scoring, location validation
  src/report.py:     agency PDF + CSV export

P5 adds:
  ui/main_ui.py            FastAPI application — routing only, no business logic
  ui/templates/            Jinja2 HTML templates (Bootstrap 5.3.8)
  ui/static/               Bootstrap 5.3.8 CSS + JS — downloaded, not CDN
  requirements.txt         add: fastapi, uvicorn, jinja2, python-multipart

P5 does NOT:
  - Add new business logic anywhere
  - Change any existing src/ module (except targeted additions to db.py where noted)
  - Change the database schema
  - Change any CLI command behaviour
  - Expose fetch/process in browser — those remain CLI commands
    (python main.py fetch --date YYYYMMDD && python main.py process --file filename.eml)

---

## Stack Constraints

  Framework:    FastAPI + Jinja2
  CSS:          Bootstrap 5.3.8 — served from ui/static/, NOT from CDN
  JS:           Bootstrap 5.3.8 bundle — same static dir
  Icons:        Bootstrap Icons 1.13.1 — CDN link in base.html <head>
  Dynamic:      htmx optional (add only if a specific task calls for it)
  No React, no Vue, no other frontend framework
  No business logic in ui/main_ui.py or any template
  All data access via src/db.py functions — never raw sqlite3 in ui/
  TemplateResponse signature (Starlette 1.0.0): templates.TemplateResponse(request, "name.html", context)
    NOT the old form: TemplateResponse("name.html", {"request": request})

---

## Progress

- [x] Task P5.0 — Bootstrap: deps, db.py additions, scaffold ui/, startup cleanup
- [x] Task P5.1 — Dashboard: GET / — stats panel + recent activity
- [x] Task P5.2 — Job list: GET /jobs — filterable table
- [x] Task P5.3 — Job detail: GET /jobs/{id} — full JD, score, documents
- [x] Task P5.4 — Status update: POST /jobs/{id}/status — outcome entry form
- [x] Task P5.5a — Generate (research): read generator.py, pdf_writer.py, report findings
- [x] Task P5.5b — Generate (implement): four-POST temp-file flow
- [x] Task P5.6 — Rate document: POST /documents/{id}/rate — letter rating
- [x] Task P5.7 — History: GET /history — full activity log with filters
- [x] Task P5.8 — Report: GET /report + POST /report/export — date range + download
- [x] Task P5.9 — Profile: GET /profile + POST /profile — view and edit profile.yaml
- [x] Task P5.10 — Completion check + merge to main

---

## Completion Checklist

### Agent verifies (run these, show output)
- [ ] python -m py_compile ui/main_ui.py — no errors
- [ ] python -m py_compile src/db.py — no errors
- [ ] uvicorn ui.main_ui:app --reload --port 8471 starts without error on port 8471
- [ ] GET / returns 200
- [ ] GET /jobs returns 200
- [ ] GET /jobs/{real_job_id} returns 200
- [ ] GET /history returns 200
- [ ] GET /report returns 200
- [ ] GET /profile returns 200
- [ ] POST /jobs/{id}/status with valid outcome saves exactly one row to outcomes table
- [ ] POST /jobs/{id}/status approve writes exactly one row to activity_log (not two)
- [ ] POST /documents/{id}/rate with rating=4 sets use_as_example=1 in DB
- [ ] POST /profile updates profile.yaml — skills section still present after save
- [ ] output/.tmp/ is empty on server startup (startup sweep confirmed)

### You verify in browser (Jiri checks these)
- [ ] Dashboard: stat cards show real counts, activity table populated
- [ ] Job list: status filter works, score colour coding visible
- [ ] Job detail: all five sections render, action buttons correct per status
- [ ] Job detail: strong_matches / concerns / tech_stack display as lists not raw JSON
- [ ] Outcome form: all five reply_type options present, submission works
- [ ] Generate: preview shown before save, [Revise] regenerates with notes, [Discard] removes temp files cleanly
- [ ] History: manual source rows visually distinct from system rows
- [ ] Report: PDF and CSV download, files open without error
- [ ] Profile: all listed fields editable, success message shown after save
- [ ] Works on Chrome/Edge on Windows (local, port 8471)

---

## db.py functions available for P5

These functions exist after P5.0 completes (P5.0 adds the ones marked NEW).
Read src/db.py before every task that touches the DB layer — verify signatures in source.

  get_jobs(status=None, min_score=None)          → list[dict]
    Check actual signature — may support SQL-level filtering already
  get_job(job_id)                                → dict | None
  get_activity_log(job_id=None,
                   action=None, limit=100)        → list[dict]
    NOTE: action filter added in P5.0 — NEW
  get_documents(job_id)                          → list[dict]
    NOTE: added in P5.0 — NEW
  get_document(doc_id)                           → dict | None
    NOTE: added in P5.0 — NEW
  get_outcomes(job_id)                           → list[dict]
  get_weekly_summary()                           → dict | None
  rate_document(doc_id, rating)                  → None
  record_outcome(job_id, reply_type,
                 reply_date=None, notes=None)    → None
  update_job_status(job_id, status,
                    notes=None, applied_at=None) → None
    NOTE: read the implementation — it may already call log_action() internally
  log_action(job_id, action, detail=None)        → None

If any other needed function is missing from db.py, add it there — never
query SQLite directly from ui/main_ui.py.
Any db.py addition must be committed separately before the route that uses it.
  Commit format: feat(db): add {function_name} for P5 {route}

---

## Template conventions

Base template:    ui/templates/base.html
  — Bootstrap 5.3.8 navbar + Bootstrap Icons 1.13.1: Dashboard / Jobs / History / Report / Profile
  — {% block title %}JobRadar{% endblock %}
  — {% block content %}{% endblock %}

All other templates extend base.html.
Template file naming: {page}.html (e.g. jobs.html, job_detail.html)
Flash messages: pass via query param ?msg=... rendered in base.html — keep it simple.
No login, no auth — this is a local personal tool.

---

## YAML decision — make before starting P5.0

profile.yaml will be saved via yaml.dump() in P5.9. yaml.dump() strips all
# comments from the file. Before P5.0 starts, decide:

Option A (recommended): Accept comment-stripping. Remove all comments from
  config/profile.yaml manually now, so nothing is lost unexpectedly later.
  No new packages required.

Option B: Preserve comments. Add ruamel.yaml to requirements.txt in P5.0.
  Use ruamel.yaml for the P5.9 save operation instead of yaml.dump().
  Requires: pip install ruamel.yaml (approve this before P5.0).

The agent will not make this decision. Jiri decides before P5.0 starts.
Record the decision here: Option A — comments stripped manually before P5.0 starts.
  Action: open config/profile.yaml, delete all lines starting with #, save.
  Commit: chore: remove yaml comments before P5.9 profile save

---

## Task P5.0 — Bootstrap: deps, db.py additions, scaffold ui/, startup cleanup

**Status:** [ ]
**Files modified:**
  requirements.txt
  src/db.py                (add three missing read functions)
  .gitignore               (add output/.tmp/)
**Files created:**
  ui/__init__.py
  ui/main_ui.py
  ui/templates/base.html
  ui/templates/index.html
  ui/static/bootstrap.min.css
  ui/static/bootstrap.bundle.min.js

### Step A — YAML decision

Before writing any code, confirm with Jiri which YAML option was chosen (see above).
If Option B: add ruamel.yaml to requirements.txt now.

### Step B — Update requirements.txt

Check current requirements.txt — do not duplicate. Add:
  fastapi
  uvicorn[standard]
  jinja2
  python-multipart
  (ruamel.yaml — only if Option B chosen)

Run: pip install -r requirements.txt
Expected: no errors.

### Step C — Add missing db.py functions (commit separately)

Read src/db.py in full first. Then add any of the following that are missing.
Add all three in a single edit. Only add what is genuinely absent.

```python
def get_activity_log(
    job_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return activity log rows, most recent first.
    Optionally filter by job_id and/or action type.
    """
    query = "SELECT * FROM activity_log WHERE 1=1"
    params: list = []
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if action:
        query += " AND action = ?"
        params.append(action)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_documents(job_id: str) -> list[dict]:
    """Return all documents for a job, ordered by created_at DESC."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(doc_id: int) -> dict | None:
    """Return a single document row by id, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None
```

Verify backward compatibility: existing callers of get_activity_log() use keyword
args — adding action=None is backward-compatible. Verify no existing caller will break.

After adding:
```
python -m py_compile src/db.py
```
Expected: silence.

Verify all three are importable:
```
python -c "
from src.db import get_activity_log, get_documents, get_document
print('All three imported OK')
"
```

Commit: feat(db): add get_activity_log action filter, get_documents, get_document for P5

### Step D — Add output/.tmp/ to .gitignore

Add this line to .gitignore:
  output/.tmp/

### Step E — Download Bootstrap 5.3.8 and add Bootstrap Icons 1.13.1

Use urllib.request (stdlib). Save locally:
  ui/static/bootstrap.min.css
    https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css
  ui/static/bootstrap.bundle.min.js
    https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js

If download fails: use CDN URLs in base.html as temporary fallback and flag clearly.

Bootstrap Icons — load from CDN in base.html <head> (icon webfonts make local
download complex; CDN is appropriate for this local-only tool):
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css">

### Step F — Scaffold ui/

Create ui/__init__.py (empty).

Create ui/main_ui.py with:
- FastAPI app, static mount, Jinja2 templates
- Startup lifespan handler that sweeps output/.tmp/ on server start
- One route GET /

```python
"""FastAPI application for JobRadar Web UI — routing only, no business logic."""

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    return templates.TemplateResponse(request, "index.html")
```

Create ui/templates/base.html:
- Bootstrap 5.3.8 CSS + JS (local static)
- Bootstrap Icons 1.13.1 (CDN link in <head>)
- Navbar: JobRadar | Dashboard | Jobs | History | Report | Profile
- ?msg= flash: if request.query_params.get('msg'), show as a Bootstrap alert
- {% block title %} and {% block content %} blocks

Create ui/templates/index.html:
- {% extends "base.html" %}
- Placeholder: "Dashboard coming soon."

### Step G — Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

```
python -m uvicorn ui.main_ui:app --reload
```
Expected: starts on port 8471 with no import errors.
Confirm in startup log that the lifespan handler ran (no error on startup).
Open http://localhost:8471 in your browser. Confirm page loads with Bootstrap navbar.
Paste a brief description of what you see. Stop server.

Acceptance Criteria:
- pip install completes without error
- db.py: all three functions present and importable
- Server starts without error
- Startup sweep runs without error (output/.tmp/ exists and is empty after start)
- GET / renders base template with navbar and Bootstrap styling
- output/.tmp/ in .gitignore
- No business logic in main_ui.py

Commit after confirmation: feat(p5): scaffold FastAPI app, Bootstrap 5.3.8, base template

---

## Task P5.1 — Dashboard: GET /

**Status:** [x]
**Files modified:**
  ui/main_ui.py
  ui/templates/index.html

### Data to fetch (all via db.py — no raw sqlite3 in main_ui.py)

  get_jobs()                  → all jobs
  get_activity_log(limit=10)  → 10 most recent entries
  get_weekly_summary()        → dict or None

Before using get_jobs(): read its signature in db.py. If it supports SQL-level
filtering (status=, min_score=), use those parameters where applicable rather
than filtering in Python.

Simple aggregations in the route are acceptable:
  total_jobs = len(jobs)
  by_status  = {s: count} — built with a dict comprehension

No business logic, no AI calls, no file I/O in main_ui.py.

### Layout

Four Bootstrap stat cards in a row:
  Total jobs | Approved | Applied | Closed

Recent activity table (10 rows):
  Timestamp | Job | Action | Detail | Source

Weekly summary panel (hidden when get_weekly_summary() returns None):
  Response rate % | Avg score of responded jobs | Most common outcome

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server. Open http://localhost:8471 in your browser.
Confirm: stat cards show real counts, activity table populated, no exception.
Paste a brief description of what you see. Stop server.

Acceptance Criteria:
- Stat cards show real counts from DB
- Activity table shows up to 10 most recent rows
- Summary panel hidden when None, visible when data present
- No exception with empty DB

Commit after confirmation: feat(p5): implement dashboard with stats and activity feed

---

## Task P5.2 — Job list: GET /jobs

**Status:** [x] Complete
**Files modified:**
  ui/main_ui.py
  ui/templates/jobs.html

### Route behaviour

GET /jobs?status=&min_score=

Before implementing: read get_jobs() in db.py.
  If it supports status= and min_score= at SQL level → pass params directly.
  If not → call get_jobs() and filter in Python.
Either way: sort result by score DESC.

### Layout

Filter bar (GET form, params in URL):
  Status dropdown: All / new / reviewed / approved / applied /
                   responded / interview / closed / rejected
  Min score number input (0–10)
  Apply button

Job table:
  Score (green ≥7 | yellow 5–6 | red ≤4) | Company | Role |
  Location | Status | Date | [View]

[View] → GET /jobs/{id}

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server. Open /jobs in browser. Confirm table with jobs, colour-coded scores.
Apply a status filter — confirm only matching rows shown.
Paste a brief description. Stop server.

Acceptance Criteria:
- All jobs shown by default, sorted score DESC
- Status and min_score filters work
- Score colour coding visible
- [View] links go to /jobs/{id}

Commit after confirmation: feat(p5): implement job list page with filters

---

## Task P5.3 — Job detail: GET /jobs/{id}

**Status:** [x] Complete
**Files modified:**
  ui/main_ui.py
  ui/templates/job_detail.html

### Route behaviour

GET /jobs/{id}
  get_job(id) → 404 if None
  get_documents(id), get_outcomes(id), get_activity_log(job_id=id)

JSON field parsing — REQUIRED in route before passing to template:
  strong_matches, concerns, and tech_stack are JSON strings in the DB.
  Without parsing, the template renders raw strings like ["Python", "FastAPI"].

  ```python
  import json
  job = dict(job)  # make mutable copy
  job['strong_matches'] = json.loads(job.get('strong_matches') or '[]')
  job['concerns']       = json.loads(job.get('concerns') or '[]')
  job['tech_stack']     = json.loads(job.get('tech_stack') or '[]')
  ```

### Layout

Header: Company — Role | Score badge | Status badge | Location

Five sections (Bootstrap tabs or accordion):
  1. Overview: score_reason, strong_matches (list), concerns (list),
               salary, tech_stack (list), notes
  2. Job Description: jd_text in scrollable <pre> (max-height, overflow-y: auto)
  3. Documents: table — doc_type, path, version, rating.
               Rating form inline (completed in P5.6 — stub acceptable here)
  4. Outcomes: list of recorded outcomes
  5. Activity: activity_log rows for this job only

Action buttons (conditional — show only when valid):
  [Approve]         if status == 'reviewed'
  [Generate]        if status == 'approved'
  [Record Outcome]  if status in ('applied', 'responded', 'interview')

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server.
Open /jobs/{a real job id} — confirm all five sections render, lists display
correctly (not raw JSON strings). Open /jobs/nonexistent — confirm clean 404.
Paste a brief description of both pages. Stop server.

Acceptance Criteria:
- All five sections render without exception
- JSON fields display as lists, not raw strings
- Correct action buttons per status
- 404 for unknown job id
- jd_text in scrollable block

Commit after confirmation: feat(p5): implement job detail page

---

## Task P5.4 — Status update: POST /jobs/{id}/status

**Status:** [x] Complete
**Files modified:**
  ui/main_ui.py
  ui/templates/status_form.html

### Two cases on POST /jobs/{id}/status

Case A — Quick update (approve / reject):
  action = 'approve' → update_job_status(id, 'approved')
  action = 'reject'  → update_job_status(id, 'rejected')

  IMPORTANT: Read update_job_status() in db.py before implementing.
  If it already calls log_action() internally — do NOT add a second log_action()
  call in the route. Calling both creates duplicate activity_log rows.
  If it does NOT log internally — add log_action() in the route.
  Document which case applies in your task summary.

  Redirect to GET /jobs/{id}.

Case B — Outcome entry:
  GET /jobs/{id}/status → render status_form.html
  Fields: reply_type (select) | reply_date (date, optional) | notes (textarea, optional)
  POST with action='outcome' → call record_outcome(id, reply_type, reply_date, notes)
  Redirect to GET /jobs/{id}?msg=Outcome+recorded

Validate reply_type — return 400 if not in:
  {'no_reply', 'rejection', 'positive', 'interview', 'offer'}

No outcome logic in main_ui.py — call db.py functions only.

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server.

Test A: Open a reviewed job in browser. Click [Approve]. Confirm redirect,
status shows 'approved'. Check activity_log has exactly one new row (not two):
```
python -c "
import sqlite3
c = sqlite3.connect('data/tracker.db')
rows = c.execute(
    'SELECT * FROM activity_log ORDER BY ts DESC LIMIT 3'
).fetchall()
for r in rows: print(r)
"
```
Expected: one row for this action, not two identical rows.

Test B: Open an applied job in browser. Click [Record Outcome].
Confirm form renders with all five reply_type options. Submit no_reply.
Confirm redirect.
```
python -c "
import sqlite3
c = sqlite3.connect('data/tracker.db')
c.row_factory = sqlite3.Row
print(dict(c.execute(
    'SELECT job_id, reply_type FROM outcomes ORDER BY created_at DESC LIMIT 1'
).fetchone()))
"
```
Expected: correct job_id, reply_type='no_reply'.

Paste browser descriptions + both query results. Stop server.
Wait for my confirmation.

Acceptance Criteria:
- Approve/reject updates status and redirects
- Approve/reject writes exactly ONE activity_log row (not two)
- Outcome form has all five reply_type options
- Submitting outcome saves to DB and redirects
- Invalid reply_type returns 400

Commit after confirmation: feat(p5): implement status update and outcome entry

---

## Task P5.5a — Generate (research): read source files, report findings

**Status:** [ ]
**Files:** none — research only, no code changes

This is a read-only session. No code is written. The output is a report for Jiri.

### What to read

Read these files in full:
  src/generator.py
  src/pdf_writer.py
  main.py  — find and read cmd_generate specifically

### What to report

After reading, provide Jiri with:

1. generator.py public functions — name, full signature, return type, what it does
2. pdf_writer.py public functions — name, full signature, return type, what it does
3. What cmd_generate does step by step — in plain language
4. What the generation pipeline returns:
   - File paths? Content strings? Both? What exactly?
5. Which db.py functions cmd_generate calls to save document records
   - Do those functions exist in db.py? If not, name them.
6. Output directory structure that cmd_generate uses — exact path pattern
7. Any state (profile, config) that must be passed into generator.py functions
8. Risks or complications you see for the web implementation

### Output format

Provide a structured summary under these headings:
  ## generator.py functions
  ## pdf_writer.py functions
  ## cmd_generate flow
  ## Return values and file paths
  ## DB functions needed
  ## Output path pattern
  ## State required
  ## Risks

Do not write any code. Do not propose an implementation.
Wait for Jiri's confirmation and any follow-up questions before P5.5b starts.

No commit for this task.

---

## Task P5.5b — Generate (implement): four-POST temp-file flow

**Status:** [ ]
**Files modified:**
  ui/main_ui.py
  ui/templates/generate_result.html
  src/db.py  (if any document-saving function is missing)

This task implements based on the findings from P5.5a.
Do not start without Jiri's explicit confirmation after P5.5a.

### Design — four-POST temp-file flow (mandatory)

The "no auto-save" rule from the CLI applies in the UI.
Implementation uses four routes:

POST /jobs/{id}/generate  — generate to temp, show preview
  1. get_job(id) → 404 if not found, 400 if status != 'approved'
  2. Call generator.py + pdf_writer.py (exact calls confirmed in P5.5a)
  3. Write to output/.tmp/{job_id}/ (same filenames as permanent path)
     If output/.tmp/{job_id}/ already exists — delete it first (previous abandoned run)
  4. Render generate_result.html:
       Cover letter: full body text in a scrollable block
       CV: filename + brief summary of what changed
       Notes textarea: optional, placeholder "Feedback for regeneration…"
       [Save]    → POST /jobs/{id}/generate/confirm
       [Revise]  → POST /jobs/{id}/generate/revise
       [Discard] → POST /jobs/{id}/generate/discard

POST /jobs/{id}/generate/confirm  — move to permanent, save records
  0. Guard: if output/.tmp/{job_id}/ does not exist →
       redirect to GET /jobs/{id}?msg=Already+saved
       (protects against double-submit and browser back+resubmit)
  1. Determine permanent path: output/{YYYYMMDD}_{company-slug}_{role-slug}/
     If that directory already exists (same-day re-generation):
       append _v2, _v3, etc. until a free path is found
  2. Move all files from output/.tmp/{job_id}/ to the permanent path
  3. Save document records to DB (functions confirmed in P5.5a)
  4. Call update_job_status(id, 'applied')
     Check whether update_job_status logs internally (same rule as P5.4)
  4b. log_action(id, 'generated', detail=str(permanent_path))
      NOTE: Pass the permanent output path as detail (NOT the temp path).
      Discarded generations must NOT log — only call after files are moved.
      One 'generated' row in activity_log = one saved output.
      Revisions that are discarded leave no trace, keeping the log clean.
  5. Delete output/.tmp/{job_id}/
  6. Redirect to GET /jobs/{id}?msg=Documents+saved

POST /jobs/{id}/generate/discard  — delete temp, no DB record
  1. Delete output/.tmp/{job_id}/ and all contents (ignore if already gone)
  2. Redirect to GET /jobs/{id}?msg=Generation+discarded

POST /jobs/{id}/generate/revise  — regenerate with notes, replace temp
  1. Read 'notes' field from form (optional, empty string if blank).
  2. jd_with_notes = job['jd_text'] + f"\n\nRegeneration notes: {notes}"
  3. Re-run generator.py + pdf_writer.py with jd_with_notes (same calls as /generate).
  4. Delete output/.tmp/{job_id}/, recreate with new files.
  5. Re-render generate_result.html with updated preview.
  No DB writes. No status change.

### Pre-implementation check

Before writing any code:
  - Confirm output/.tmp/ is gitignored (check .gitignore)
  - Confirm the startup sweep in main_ui.py lifespan handler is in place
  - If any db.py function for saving document records is missing:
    add it to db.py first, commit separately as feat(db): ...

NOTE — hot-reload race condition:
Do not save any editor files while the preview page is open during testing.
uvicorn --reload re-runs the lifespan handler on every file save, which deletes
output/.tmp/ — this erases temp files mid-test and causes a 500 on [Save].

### Verify

```
python -m py_compile ui/main_ui.py
python -m py_compile src/db.py
```
Expected: silence for both.

NOTE: This task makes a live AI API call. Confirm API key is set before running.

Start server.

Test generate + save:
Open an approved job in browser. Click [Generate].
Confirm: preview page loads with CV filename and cover letter preview text.
Click [Save]. Confirm redirect to job detail.
```
python -c "
from pathlib import Path
files = [f for f in sorted(Path('output').rglob('*'))
         if '.tmp' not in str(f) and f.is_file()]
for f in files: print(f)
"
```
Expected: CV and cover letter under output/{date_slug}/, nothing under .tmp/.

Test same-day re-generation (version suffix):
  Cannot reuse the same job — status becomes 'applied' after first [Save].
  Manual collision setup:
    1. Create a directory by hand: mkdir output\{YYYYMMDD}_{company-slug}_{role-slug}\
       (use any name matching the date_company_role pattern for today's date).
    2. Open a DIFFERENT approved job → Click [Generate] → Click [Save].
    3. Confirm the new output directory ends in _v2.

Test discard:
Click [Generate] on a different approved job. Click [Discard].
Confirm output/.tmp/ is empty.

Test revise:
Open an approved job. Click [Generate]. On preview page, enter some feedback in
the Notes textarea. Click [Revise]. Confirm preview reloads with updated content.
Click [Save]. Confirm files saved to permanent path.

Paste browser descriptions + file listings for all four tests.
Stop server. Wait for my confirmation.

Acceptance Criteria:
- Preview shown before any permanent save
- [Save] moves files, saves DB records, updates status to 'applied'
- [Revise] regenerates with notes appended, re-renders preview, no DB write
- [Discard] deletes temp files, no DB record written
- Same-day re-generation uses _v2 suffix, not overwrite
- output/.tmp/ empty after every user action
- No auto-save without user action

Commit after confirmation: feat(p5): implement document generation with temp-file preview flow

---

## Task P5.6 — Rate document: POST /documents/{id}/rate

**Status:** [x]
**Files modified:**
  ui/main_ui.py
  ui/templates/job_detail.html  (add rating form to Documents section)

Note: get_document() was added to db.py in P5.0 — do not re-add it.
Verify it is present before starting: python -c "from src.db import get_document; print('OK')"

### Route behaviour

POST /documents/{id}/rate
  Form field: rating (int)
  Validate 1 ≤ rating ≤ 5 — return 400 if not.
  Call rate_document(doc_id, rating).
  Call get_document(doc_id) to retrieve job_id for redirect.
  Redirect to GET /jobs/{job_id}.

Add an inline rating form to the Documents section of job_detail.html.
A number input (1–5) with a [Rate] submit button per document row is sufficient.

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server. Open a job detail with at least one document in browser.
Submit rating 4 via the form. Confirm redirect to job detail.
Stop server.
```
python -c "
import sqlite3
c = sqlite3.connect('data/tracker.db')
c.row_factory = sqlite3.Row
print(dict(c.execute(
    'SELECT id, rating, use_as_example FROM documents ORDER BY created_at DESC LIMIT 1'
).fetchone()))
"
```
Expected: rating=4, use_as_example=1.

Paste browser description + DB result. Wait for my confirmation.

Acceptance Criteria:
- Rating form present in Documents section of job detail
- rate_document() called correctly
- Rating >= 4 sets use_as_example=1
- Redirect back to job detail
- Invalid rating (0, 6, non-integer) returns 400

Commit after confirmation: feat(p5): implement document rating route

---

## Task P5.7 — History: GET /history

**Status:** [x]
**Files modified:**
  ui/main_ui.py
  ui/templates/history.html

Note: get_activity_log() with action filter was added in P5.0.
Verify: python -c "from src.db import get_activity_log; import inspect; print(inspect.signature(get_activity_log))"
Expected signature includes action parameter.

### Route behaviour

GET /history?job_id=&action=&limit=50
  Call get_activity_log(job_id=..., action=..., limit=...).
  Clamp limit: default 50, max 200.

### Layout

Filter bar (GET form): Job ID text input | Action dropdown | Limit selector | Apply
Table: Timestamp | Job ID (link → /jobs/{id}) | Action | Detail | Source
source='manual' rows: italic style or small badge.
"Showing N rows" count above the table.

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server. Open /history in browser. Confirm rows render.
Apply action filter — confirm only matching rows shown.
Paste a brief description. Stop server.

Acceptance Criteria:
- All activity_log rows rendered by default
- job_id and action filters work
- Job ID links correct
- source='manual' visually distinct
- No exception with empty log

Commit after confirmation: feat(p5): implement history page with activity log

---

## Task P5.8 — Report: GET /report + POST /report/export

**Status:** [ ]
**Files modified:**
  ui/main_ui.py
  ui/templates/report.html

### Route behaviour

Read src/report.py in full before implementing. Do not change report.py's logic.

GET /report
  Default date range: today minus 30 days to today.
  Compute in route:
  ```python
  from datetime import date, timedelta
  # YYYYMMDD — required by get_activity_report()
  date_from_fmt = (date.today() - timedelta(days=30)).strftime('%Y%m%d')
  date_to_fmt   = date.today().strftime('%Y%m%d')
  preview_rows  = get_activity_report(date_from_fmt, date_to_fmt)
  # %Y-%m-%d — for <input type="date"> pre-fill only
  date_from_form = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
  date_to_form   = date.today().strftime('%Y-%m-%d')
  ```
  Render report.html with form pre-filled (date_from_form, date_to_form) and preview_rows.
  Do NOT pass date_from_fmt/date_to_fmt to the template as form values.

POST /report/export
  Form fields: date_from (YYYY-MM-DD from browser date input), date_to (YYYY-MM-DD),
               format ('pdf' | 'csv')

  DATE FORMAT CONVERSION — REQUIRED:
  generate_report() expects dates as YYYYMMDD (no dashes).
  Browser <input type="date"> submits YYYY-MM-DD (with dashes).
  Convert before calling generate_report():
  ```python
  date_from_fmt = date_from.replace('-', '')  # "2026-01-17" → "20260117"
  date_to_fmt   = date_to.replace('-', '')
  pdf_path, csv_path, count = generate_report(date_from_fmt, date_to_fmt)
  ```
  Skipping this conversion causes a ValueError in strptime at runtime.

  If count == 0: re-render form with message "No activity found in this date range."
  Do not trigger a download on count == 0.

  Serve file with FileResponse:
  ```python
  from fastapi.responses import FileResponse
  from pathlib import Path

  if format == 'pdf':
      return FileResponse(pdf_path, media_type='application/pdf',
                          filename=Path(pdf_path).name)
  return FileResponse(csv_path, media_type='text/csv',
                      filename=Path(csv_path).name)
  ```
  Files remain in output/reports/ after download — intentional.

  If generate_report() signature differs from (date_from, date_to) → report to Jiri
  before implementing. Do not change report.py's internal logic.

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server. Open /report in browser. Confirm form and preview table render.
Set a date range with known activity.
Select PDF → confirm browser downloads a file. Open it — confirm it contains data.
Select CSV → confirm browser downloads a file. Open it — confirm it has rows.
Paste descriptions of both downloads. Stop server.

Acceptance Criteria:
- Form renders with default 30-day range
- Preview table shows rows in selected range
- PDF and CSV download correctly with real data
- Date conversion applied — no strptime ValueError
- Empty range shows message, no download triggered
- Files remain in output/reports/

Commit after confirmation: feat(p5): implement agency report export page

---

## Task P5.9 — Profile: GET /profile + POST /profile

**Status:** [ ]
**Files modified:**
  ui/main_ui.py
  ui/templates/profile.html

### Editable fields

Read config/profile.yaml to confirm key names before implementing.

Render as form inputs:
  preferences.min_score_to_show    (number input)
  restrictions.hybrid_cities       (comma-separated text —
                                    join list→str on GET, split str→list on POST)
  personal.name                    (text input)
  personal.email                   (text input)
  ai.provider                      (select: gemini / claude / openai)
  ai.model                         (text input)

Do NOT expose: API keys, skills lists, prompt files.

### Save behaviour — surgical update (CRITICAL)

Load → update only the listed fields → write back.
Never overwrite the full structure.

```python
import yaml
from pathlib import Path

profile_path = Path('config/profile.yaml')
profile = yaml.safe_load(profile_path.read_text(encoding='utf-8'))

profile['preferences']['min_score_to_show'] = int(form_data['min_score_to_show'])
profile['restrictions']['hybrid_cities'] = [
    c.strip() for c in form_data['hybrid_cities'].split(',') if c.strip()
]
profile['personal']['name']  = form_data['name']
profile['personal']['email'] = form_data['email']
profile['ai']['provider']    = form_data['provider']
profile['ai']['model']       = form_data['model']

# yaml.dump() strips comments — see YAML decision in P5.0
profile_path.write_text(yaml.dump(profile, allow_unicode=True), encoding='utf-8')
```

If Option B (ruamel.yaml) was chosen in P5.0: use ruamel.yaml round-trip loader/dumper
instead. The surgical update logic is the same — only the load/dump calls change.

After save: redirect to GET /profile?msg=Profile+saved.

### Verify

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Start server. Open /profile in browser. Confirm all listed fields show current values.
Change min_score_to_show. Click Save. Confirm success message in browser.
Stop server.
```
python -c "
import yaml
p = yaml.safe_load(open('config/profile.yaml'))
print('min_score_to_show:', p['preferences']['min_score_to_show'])
print('skills present:', bool(p.get('skills')))
print('ai.provider:', p['ai']['provider'])
"
```
Expected: updated value, skills still present, ai.provider unchanged.
Change min_score_to_show back to original. Confirm.

Paste browser description + script output. Wait for my confirmation.

Acceptance Criteria:
- All listed fields editable and pre-filled with current values
- Save updates only the listed fields
- All other profile.yaml sections preserved (skills, etc.)
- Success message shown after save
- No API keys visible in UI

Commit after confirmation: feat(p5): implement profile view and edit page

---

## Task P5.10 — Completion check + merge to main

**Status:** [ ]
**Files:** docs/MILESTONES.md (status update only)

### Part 1 — Agent-verifiable checks

Run each. Show exact output. Report PASS or FAIL. Stop and wait for "ok to merge".

```
python -m py_compile ui/main_ui.py
python -m py_compile src/db.py
```

```
python -m uvicorn ui.main_ui:app --reload
# confirm clean start + lifespan startup message — then Ctrl+C
```

HTTP status checks (run with server running in a second terminal):
```
python -c "
import urllib.request
for path in ['/', '/jobs', '/history', '/report', '/profile']:
    r = urllib.request.urlopen(f'http://localhost:8471{path}')
    print(f'GET {path}: {r.status}')
"
```
Expected: all 200.

Activity log duplicate check:
```
python -c "
import sqlite3
c = sqlite3.connect('data/tracker.db')
rows = c.execute(
    'SELECT ts, job_id, action FROM activity_log ORDER BY ts DESC LIMIT 50'
).fetchall()
rows = [r for r in rows if r[2] in ('approved', 'rejected')][:10]
for r in rows: print(r)
"
```
Expected: no duplicate (ts, job_id, action) pairs from P5.4 approve/reject.

DB integrity checks:
```
python -c "
import sqlite3
c = sqlite3.connect('data/tracker.db')
c.row_factory = sqlite3.Row
doc = c.execute(
    'SELECT id, rating, use_as_example FROM documents WHERE rating >= 4 LIMIT 1'
).fetchone()
print('Rated doc:', dict(doc) if doc else 'None found')
outcomes = c.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0]
print('Outcome count:', outcomes)
"
```

Profile integrity check:
```
python -c "
import yaml
p = yaml.safe_load(open('config/profile.yaml'))
print('skills present:', bool(p.get('skills')))
print('min_score_to_show:', p['preferences']['min_score_to_show'])
"
```

Temp dir check:
```
python -c "
from pathlib import Path
tmp = Path('output/.tmp')
stale = list(tmp.iterdir()) if tmp.exists() else []
print('Stale temp dirs:', stale)
"
```
Expected: empty list.

Stop here. Show all outputs. Wait for my "ok to merge".

### Part 2 — Only after explicit "ok to merge" from Jiri

1. Update docs/MILESTONES.md: P5 status → "Done"
2. Commit: docs(p5): mark P5 complete in MILESTONES.md
3. Run:
   git checkout main
   git merge feature/p5-web-ui --no-ff -m "feat(p5): merge Phase 5 web UI"
4. git branch --show-current   (expected: main)
5. git log --oneline -8
6. Show both outputs. Wait for final confirmation.

Constraints:
- NEVER merge without Jiri's explicit "ok to merge"
- NEVER push without asking

---

## Notes for Claude Code

### Hard rules for P5

- No business logic in ui/main_ui.py or any template
- All DB access via src/db.py functions — never raw sqlite3 in ui/
- No AI calls anywhere in ui/ — generation goes through generator.py → ai_client.py only
- All file paths via pathlib.Path
- Bootstrap 5.3.8 from local static/ — never CDN in production templates
  (Bootstrap Icons 1.13.1 is CDN only — icon webfonts are not downloaded locally)
- profile.yaml: update only the listed fields, never overwrite the full structure
- output/.tmp/ is gitignored and always empty after any user action completes

### Route summary

  GET  /                             Dashboard
  GET  /jobs                         Job list (filters: status, min_score)
  GET  /jobs/{id}                    Job detail
  GET  /jobs/{id}/status             Outcome entry form
  POST /jobs/{id}/status             Outcome or quick status update (approve/reject)
  POST /jobs/{id}/generate           Generate to temp → preview page
  POST /jobs/{id}/generate/confirm   Move temp to permanent, save DB records
  POST /jobs/{id}/generate/discard   Delete temp files, no DB record
  POST /jobs/{id}/generate/revise    Regenerate with feedback, replace temp
  POST /documents/{id}/rate          Rate a document
  GET  /history                      Activity log with filters
  GET  /report                       Report form + preview
  POST /report/export                Download PDF or CSV via FileResponse
  GET  /profile                      View profile
  POST /profile                      Surgical update of profile.yaml

### Temp file directory

output/.tmp/{job_id}/   — in-progress generation (P5.5b only)
  Created:   POST /jobs/{id}/generate
  Deleted:   POST /jobs/{id}/generate/confirm  (after moving to permanent)
             POST /jobs/{id}/generate/discard   (immediate)
             Server startup lifespan handler    (sweeps any stale dirs)
  Gitignored: yes (P5.0)
  Rule: always empty after any user action or server restart