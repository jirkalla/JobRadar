# P6 Session Prompts — JobRadar
# One prompt per Claude Code session. Copy the block, paste as first message.
# Wait for Task Closing Ritual confirmation before starting the next session.

==============================================================================
TASK P6.1 — Backend: GET /jobs/new + POST /jobs/new routes
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p6-manual-job-entry
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P6.md Task P6.1 — read it fully before touching any file
- ui/main_ui.py — read the ENTIRE file to understand existing routes and imports

Your job:

Step A: Verify insert_job is imported in ui/main_ui.py.
  Check the existing import line from src.db. If insert_job is missing, add it
  to the existing src.db import line only — do NOT create a new import block.

Step B: Add GET /jobs/new and POST /jobs/new routes.
  CRITICAL: both routes MUST be placed immediately BEFORE the GET /jobs/{job_id}
  route. Read Tasks_P6.md Task P6.1 for exact route implementations and the full
  data dict to pass to insert_job().

  GET /jobs/new: renders job_new.html with {"error": None, "form": {}}
  POST /jobs/new: validates required fields, builds data dict, calls
    insert_job(data, source="manual"), redirects to /jobs/{job_id} with 303.
    On validation failure: re-render form with error message and form_dict
    so the user does not lose their input.

Step C: Verify route order.
  python -m py_compile ui/main_ui.py
  Expected: silence.

  python -c "
  from ui.main_ui import app
  paths = [r.path for r in app.routes if hasattr(r, 'path')]
  new_idx = paths.index('/jobs/new')
  detail_idx = paths.index('/jobs/{job_id}')
  assert new_idx < detail_idx, f'Route order wrong: /jobs/new at {new_idx}, /jobs/{{job_id}} at {detail_idx}'
  print(f'Route order OK: /jobs/new at index {new_idx}, /jobs/{{job_id}} at index {detail_idx}')
  "
  Expected: prints route order confirmation.

Show py_compile and route order output. Wait for my confirmation.

After I confirm:
- Mark Task P6.1 [x] in docs/Tasks_P6.md
- Commit: feat(p6): add GET and POST /jobs/new routes
- Complete Task Closing Ritual (AI_INSTRUCTIONS.md section 10)
- Do not start Task P6.2


==============================================================================
TASK P6.2 — Frontend: job_new.html template + navigation button
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p6-manual-job-entry
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P6.md Task P6.2 — read it fully before touching any file
- ui/templates/status_form.html — read it for style reference (Bootstrap card pattern)
- ui/templates/jobs.html — read it to find where to insert the New Job button

Your job:

Step A: Create ui/templates/job_new.html.
  Extend base.html. Bootstrap card, max-width ~720px, centered.
  Fields in order: Company*, Role Title*, Location, URL, Remote Type (select),
  Language (select), Salary, Job Description* (textarea rows=12).
  Required fields marked with * in label.
  Error display: Bootstrap alert-danger above the form if error is not None.
  Re-population: all inputs pre-filled from {{ form.field|default('') }} on error.
  Submit: "Add Job" (btn-primary). Cancel link: "← Back to Jobs" (/jobs).
  See Tasks_P6.md Task P6.2 for full field spec including select options.

Step B: Add New Job button to ui/templates/jobs.html.
  Find the filter bar at the top of the jobs list page.
  Add this button aligned to the right of the filter bar:
    <a href="/jobs/new" class="btn btn-success btn-sm">
      <i class="bi bi-plus-circle"></i> New Job
    </a>
  Do not restructure the filter bar — only add the button.

Step C: Verify.
  python -m py_compile ui/main_ui.py
  Expected: silence.

  Then start the server and open /jobs/new in the browser yourself:
  python -m uvicorn ui.main_ui:app --reload --port 8471
  Confirm:
  - Form renders with all fields and both selects populated
  - "New Job" button visible on /jobs page
  - Submit with all required fields → redirected to job detail
  - Submit with empty company → form reloads with error message
  Stop the server.

Show py_compile output + brief browser description. Wait for my confirmation.

After I confirm:
- Mark Task P6.2 [x] in docs/Tasks_P6.md
- Commit: feat(p6): add job_new.html template and New Job navigation button
- Complete Task Closing Ritual (AI_INSTRUCTIONS.md section 10)
- Do not start Task P6.3


==============================================================================
TASK P6.3 — Completion check + commit
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

Before starting, read:
- docs/Tasks_P6.md Task P6.3 — run all checks listed there

Run all completion checklist items from Tasks_P6.md that are agent-runnable.
For each check, show the command and output.

If all pass:
- Mark Task P6.3 [x] in docs/Tasks_P6.md
- Mark all completion checklist agent items [x]
- Report: "P6 complete. All tasks done. Ready to push when you approve."
- Do NOT push. Do NOT merge to main. Wait for Jiri's approval.
