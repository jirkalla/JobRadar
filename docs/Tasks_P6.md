# Tasks — Phase 6: Manual Job Entry
# JobRadar | Milestone: P6 — Manual Job Entry
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Follow the Task Closing Ritual (AI_INSTRUCTIONS.md section 10) after every task
# - Do NOT implement anything outside this file

---

## Context — what P6 builds on

P5 delivered the complete Web UI:
  ui/main_ui.py            FastAPI application — all routes
  ui/templates/            All Jinja2 templates
  GET /jobs                Job list with status + score filters
  GET /jobs/{id}           Job detail — score, JD, documents, action buttons
  POST /jobs/{id}/generate AI generation flow (CL + CV) with confirm/discard
  POST /jobs/{id}/status   Outcome entry form
  POST /documents/{id}/rate Letter rating

P5 does NOT provide a way to add a job that did not come from an EML digest.
All jobs currently enter via: python main.py process (EML pipeline only).

P6 adds:
  GET  /jobs/new              Render the manual job entry form
  POST /jobs/new              Accept form, insert job, redirect to job detail
  ui/templates/job_new.html   New job entry form template
  Navigation button in /jobs  Link to /jobs/new

P6 does NOT:
  - Add AI scoring on insert — jobs enter with score=0, status="new"
  - Add URL fetching or JD auto-extraction
  - Change any existing route, template, or db.py function
  - Change the database schema

---

## Stack Constraints

Same as P5:
  Framework:    FastAPI + Jinja2
  CSS:          Bootstrap 5.3.8 — served from ui/static/
  All DB access via src/db.py — never raw sqlite3 in ui/main_ui.py
  TemplateResponse signature: templates.TemplateResponse(request, "name.html", context)
  No new pip packages

CRITICAL — Route ordering:
  GET /jobs/new MUST be registered BEFORE GET /jobs/{job_id} in main_ui.py.
  FastAPI matches routes in declaration order. If /jobs/{job_id} comes first,
  the literal string "new" will be treated as a job ID → 404.
  Verify route order before finishing P6.1.

---

## Progress

- [x] Task P6.1 — Backend: GET /jobs/new + POST /jobs/new routes
- [x] Task P6.2 — Frontend: job_new.html template + navigation button in jobs.html
- [ ] Task P6.3 — Completion check + commit

---

## Completion Checklist

### Agent verifies
- [ ] python -m py_compile ui/main_ui.py — no errors
- [ ] GET /jobs/new returns 200 (form renders)
- [ ] POST /jobs/new with valid data → redirects to /jobs/{id}
- [ ] POST /jobs/new with missing company → returns form with inline error
- [ ] POST /jobs/new with missing role_title → returns form with inline error
- [ ] POST /jobs/new with missing jd_text → returns form with inline error
- [ ] New job has score=0, status="new", source logged as "manual" in activity_log

### Jiri verifies in browser
- [ ] /jobs/new form renders correctly — all fields visible, labels clear
- [ ] All dropdowns populated (remote_type, language)
- [ ] Submitting valid form → redirected to job detail page
- [ ] Job detail shows correct company, role, JD text, score=0
- [ ] Dashboard activity log shows new entry with manual source (italic row)
- [ ] /jobs list includes the new job
- [ ] Full generate flow works for the manually added job (approve → generate → confirm)

---

## db.py functions available for P6

Read src/db.py before starting — verify signatures in source.

  insert_job(data: dict, source: str = "system", date_str: str | None = None) → str
    Required keys in data: company, role_title
    Optional: location, remote_type, url, language, jd_text, score, score_reason,
              status, source_eml, tech_stack, salary, strong_matches, concerns, notes
    Returns: job_id string (e.g. "mobile-de-data-platform-engineer-20260421")
    Side-effect: logs "scored" action to activity_log

No new db.py functions are needed for P6.

---

## Task P6.1 — Backend: GET /jobs/new + POST /jobs/new

**Status:** [ ]
**Files modified:** ui/main_ui.py

### Placement rule

Read ui/main_ui.py first. Find the GET /jobs/{job_id} route.
Add BOTH new routes immediately BEFORE GET /jobs/{job_id}.
Do NOT rearrange any other routes.

### GET /jobs/new

```python
@app.get("/jobs/new")
async def new_job_form(request: Request):
    return templates.TemplateResponse(request, "job_new.html", {"error": None, "form": {}})
```

### POST /jobs/new

Fields to read from form (all via `await request.form()`):
  company      — required
  role_title   — required
  jd_text      — required
  location     — optional, default ""
  url          — optional, default ""
  remote_type  — optional, default "unclear"
  language     — optional, default "en"
  salary       — optional, default ""

Validation: if company, role_title, or jd_text is empty after .strip():
  Re-render job_new.html with:
    {"error": "Company, Role Title, and Job Description are required.", "form": form_dict}
  form_dict re-populates fields so the user does not lose their input.

On success, build data dict:
  {
      "company":        company,
      "role_title":     role_title,
      "location":       location or None,
      "remote_type":    remote_type,
      "url":            url or None,
      "language":       language,
      "jd_text":        jd_text,
      "salary":         salary or None,
      "score":          0,
      "score_reason":   "(not scored — added manually)",
      "status":         "new",
      "source_eml":     None,
      "tech_stack":     "[]",
      "strong_matches": "[]",
      "concerns":       "[]",
      "notes":          "",
  }

Call:     job_id = insert_job(data, source="manual")
Redirect: RedirectResponse(url=f"/jobs/{job_id}", status_code=303)

Imports: verify insert_job is already imported from src.db at the top of main_ui.py.
If missing: add to the existing src.db import line only. Do NOT add a new import block.

### Verification

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

```python
python -c "
from ui.main_ui import app
paths = [r.path for r in app.routes if hasattr(r, 'path')]
new_idx = paths.index('/jobs/new')
detail_idx = paths.index('/jobs/{job_id}')
assert new_idx < detail_idx, f'Route order wrong: /jobs/new at {new_idx}, /jobs/{{job_id}} at {detail_idx}'
print(f'Route order OK: /jobs/new at index {new_idx}, /jobs/{{job_id}} at index {detail_idx}')
"
```
Expected: prints route order confirmation.

Wait for Task Closing Ritual confirmation before starting Task P6.2.

---

## Task P6.2 — Frontend: job_new.html + navigation button

**Status:** [ ]
**Files created:**  ui/templates/job_new.html
**Files modified:** ui/templates/jobs.html

### job_new.html

Extend base.html. Use a Bootstrap card with max-width ~720px centered.
Style mirrors status_form.html — keep it simple.

Title block: "New Job — JobRadar"
Card title: "Add Job Manually"

Form: action="/jobs/new" method="post"

Fields (in order):
  1. Company *          — text input, name="company"
  2. Role Title *       — text input, name="role_title"
  3. Location           — text input, name="location", placeholder="e.g. Berlin"
  4. URL                — url input,  name="url",      placeholder="https://..."
  5. Remote Type        — select,     name="remote_type"
                          Options (value=label): remote=Remote, hybrid=Hybrid,
                          onsite=On-site, unclear=Unclear
                          Default selected: unclear
  6. Language           — select,     name="language"
                          Options: en=English, de=Deutsch
                          Default selected: en
  7. Salary             — text input, name="salary", placeholder="e.g. 80,000–95,000 EUR"
  8. Job Description *  — textarea,   name="jd_text",  rows=12
                          placeholder="Paste the full job description here"

Required fields: marked with * in label.

Error display: if error is not None — Bootstrap alert-danger div above the form.

Re-population on error: set value="{{ form.company|default('') }}" on each text input.
For textarea: {{ form.jd_text|default('') }}. For selects: use selected attribute conditionally.

Submit: <button type="submit" class="btn btn-primary">Add Job</button>
Cancel: <a href="/jobs" class="ms-3">← Back to Jobs</a>  (same line as submit, outside the form is fine)

### Navigation button in jobs.html

Find the filter bar row at the top of jobs.html.
Add a "New Job" button aligned to the right of the filter bar:

  <a href="/jobs/new" class="btn btn-success btn-sm">
    <i class="bi bi-plus-circle"></i> New Job
  </a>

Do not restructure the filter bar layout — only add the button.

### Verification

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

Wait for Task Closing Ritual confirmation before starting Task P6.3.

---

## Task P6.3 — Completion check + commit

**Status:** [ ]

### Agent runs

```
python -m py_compile ui/main_ui.py
```
Expected: silence.

```python
python -c "
from ui.main_ui import app
paths = [r.path for r in app.routes if hasattr(r, 'path')]
new_idx = paths.index('/jobs/new')
detail_idx = paths.index('/jobs/{job_id}')
assert new_idx < detail_idx
print(f'Route order OK: /jobs/new at {new_idx}, /jobs/{{job_id}} at {detail_idx}')
"
```
Expected: prints confirmation.

### Commit

Stage:   ui/main_ui.py, ui/templates/job_new.html, ui/templates/jobs.html
Message: feat(p6): add manual job entry via /jobs/new

Do NOT push. Do NOT merge to main.
Report: "P6 complete. All tasks done. Ready to push when you approve."
