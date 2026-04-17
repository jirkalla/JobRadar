# P5 Session Prompts — JobRadar
# One prompt per Claude Code session. Copy the block, paste as first message.
# Wait for Task Closing Ritual confirmation before starting the next session.
# P5.5 is split into two sessions: P5.5a (research) and P5.5b (implement).

==============================================================================
BEFORE STARTING P5 — YAML decision (already made — action required)
==============================================================================

Decision: Option A — comment-stripping accepted.
Recorded in Tasks_P5.md.

Action required before P5.0 starts (Jiri, not Claude Code):
  1. Open config/profile.yaml
  2. Delete all lines starting with #
  3. Save the file
  4. Commit: chore: remove yaml comments before P5.9 profile save

No new packages needed. Do NOT add ruamel.yaml.


==============================================================================
TASK P5.0 — Bootstrap: deps, db.py additions, scaffold ui/, startup cleanup
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P5.md Task P5.0 — read it fully before touching any file

YAML decision: Option A chosen — do NOT add ruamel.yaml.

Step A: Update requirements.txt.
Read current requirements.txt first — do not duplicate.
Add: fastapi, uvicorn[standard], jinja2, python-multipart
Run: pip install -r requirements.txt. Show output. Stop if errors.

Step B: Add missing db.py functions (commit separately before anything else).
Read src/db.py in full first. Then add any of these three that are absent:
  get_activity_log(job_id=None, action=None, limit=100) → list[dict]
  get_documents(job_id) → list[dict]
  get_document(doc_id) → dict | None
Reference implementations are in Tasks_P5.md Step C.
Add all missing functions in one edit. Only add what is genuinely absent.

After adding:
  python -m py_compile src/db.py
  Expected: silence.
  python -c "from src.db import get_activity_log, get_documents, get_document; print('OK')"
  Expected: OK.

Commit: feat(db): add get_activity_log action filter, get_documents, get_document for P5

Step C: Add output/.tmp/ to .gitignore.

Step D: Download Bootstrap 5.3.8 using urllib.request (stdlib only).
Target URLs and local paths in Tasks_P5.md Step E.
If download fails: use CDN URLs in base.html as fallback and flag clearly.
Bootstrap Icons 1.13.1: CDN link only — add to base.html <head> (see Tasks_P5.md Step E).

Step E: Scaffold ui/
Create: ui/__init__.py (empty)
Create: ui/main_ui.py — include the lifespan startup sweep (Tasks_P5.md Step F has exact code)
Create: ui/templates/base.html — Bootstrap 5.3.8, Bootstrap Icons 1.13.1, navbar, ?msg= flash, blocks
Create: ui/templates/index.html — extends base, placeholder content

Critical rules:
- No business logic in main_ui.py
- lifespan handler must sweep output/.tmp/ on startup
- python -m py_compile ui/main_ui.py must pass before anything else

Step F: Verify
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Expected: starts on port 8000, lifespan handler runs without error.
   Open http://localhost:8000 in your browser yourself.
   Confirm: page loads with Bootstrap navbar and styled content.
   Paste a brief description of what you see in the browser.
   Stop server.

Show all verification outputs + browser description. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): scaffold FastAPI app, Bootstrap 5.3.8, base template
- Complete Task Closing Ritual (AI_INSTRUCTIONS.md section 10)
- Do not start Task P5.1


==============================================================================
TASK P5.1 — Dashboard: GET /
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.1 — read it fully
- Read src/db.py: confirm signatures of get_jobs(), get_activity_log(), get_weekly_summary()

Before using get_jobs(): check whether it supports SQL-level status/score filtering.
If yes, use those parameters. If no, call with no args and filter in Python.

Update dashboard route in ui/main_ui.py and ui/templates/index.html.

Data (all via db.py — no raw sqlite3 in main_ui.py):
  get_jobs() → all jobs (compute stat counts from this list)
  get_activity_log(limit=10) → 10 most recent
  get_weekly_summary() → dict or None

Template: 4 stat cards (Total / Approved / Applied / Closed) + activity table (10 rows)
+ weekly summary panel (conditional on summary not None).

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open http://localhost:8000 in your browser yourself.
   Confirm: stat cards show real numbers, activity table populated, no exception.
   Paste a brief description of what you see.
   Stop server.

Show py_compile output + browser description. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement dashboard with stats and activity feed
- Complete Task Closing Ritual
- Do not start Task P5.2


==============================================================================
TASK P5.2 — Job list: GET /jobs
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.2 — read it fully
- Read src/db.py: check get_jobs() signature — does it support status= and min_score= at SQL level?

Add GET /jobs route to ui/main_ui.py. Create ui/templates/jobs.html.

Route: GET /jobs?status=&min_score=
If get_jobs() supports SQL filtering → use it. Otherwise filter in Python after the call.
Sort by score DESC.

Template: filter bar (GET form: status dropdown, min_score input, Apply) +
job table (Score colour-coded | Company | Role | Location | Status | Date | [View]).

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open /jobs in your browser yourself.
   Confirm: table with jobs, colour-coded scores, filter bar present.
   Apply a status filter — confirm only matching rows shown.
   Paste a brief description of what you see.
   Stop server.

Show py_compile output + browser description. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement job list page with filters
- Complete Task Closing Ritual
- Do not start Task P5.3


==============================================================================
TASK P5.3 — Job detail: GET /jobs/{id}
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.3 — read it fully
- Read src/db.py: confirm get_job(), get_documents(), get_outcomes(), get_activity_log()

Add GET /jobs/{id} route. Create ui/templates/job_detail.html.

REQUIRED — parse JSON fields in the route before passing to template:
  strong_matches, concerns, tech_stack are stored as JSON strings.
  job['strong_matches'] = json.loads(job.get('strong_matches') or '[]')
  job['concerns']       = json.loads(job.get('concerns') or '[]')
  job['tech_stack']     = json.loads(job.get('tech_stack') or '[]')
  Without this, templates render raw ["Python", "FastAPI"] strings.

Template: five sections (tabs or accordion):
  Overview | Job Description (scrollable pre) | Documents (rating stub) |
  Outcomes | Activity

Action buttons conditional on status:
  [Approve] if 'reviewed' | [Generate] if 'approved' |
  [Record Outcome] if in ('applied','responded','interview')

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open /jobs/{a real job id} in your browser yourself.
   Confirm: all five sections render, lists display correctly (not raw JSON).
   Open /jobs/nonexistent — confirm clean 404.
   Paste a brief description of both pages.
   Stop server.

Show py_compile output + browser descriptions. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement job detail page
- Complete Task Closing Ritual
- Do not start Task P5.4


==============================================================================
TASK P5.4 — Status update: POST /jobs/{id}/status
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.4 — read it fully
- Read src/db.py: read update_job_status() implementation in full.
  Does it call log_action() internally? Answer this before writing any code.
  Report which case applies in your task summary.

Add GET /jobs/{id}/status and POST /jobs/{id}/status routes.
Create ui/templates/status_form.html.

Case A (approve/reject):
  Call update_job_status(id, new_status).
  If update_job_status() already calls log_action() internally → do NOT add a second call.
  If it does NOT log internally → add log_action() in the route.
  Duplicate activity_log rows are a data quality bug — avoid them.

Case B (outcome entry):
  GET /jobs/{id}/status → render form with all five reply_type options.
  POST with action='outcome' → record_outcome() → redirect.
  Validate reply_type — return 400 if invalid.

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload

   Test A: Open a reviewed job in browser. Click [Approve].
   Confirm redirect, status shows 'approved'.
   Check activity_log for exactly ONE new row (not two):
   python -c "
   import sqlite3
   c = sqlite3.connect('data/tracker.db')
   rows = c.execute('SELECT ts, job_id, action FROM activity_log ORDER BY ts DESC LIMIT 3').fetchall()
   for r in rows: print(r)
   "

   Test B: Open an applied job in browser. Click [Record Outcome].
   Confirm form with five reply_type options. Submit no_reply. Confirm redirect.
   python -c "
   import sqlite3
   c = sqlite3.connect('data/tracker.db')
   c.row_factory = sqlite3.Row
   print(dict(c.execute('SELECT job_id, reply_type FROM outcomes ORDER BY created_at DESC LIMIT 1').fetchone()))
   "

   Stop server.

Show py_compile output + Test A/B browser descriptions + both DB query results.
Confirm: exactly one activity_log row per approve action, not two.
Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement status update and outcome entry
- Complete Task Closing Ritual
- Do not start Task P5.5a


==============================================================================
TASK P5.5a — Generate (research): read source files, report findings
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

This is a READ-ONLY session. No code is written. No files are modified.

Read these files in full:
  src/generator.py
  src/pdf_writer.py
  main.py  — find and read cmd_generate specifically

Then provide a structured report with these sections:

## generator.py functions
  For each public function: name, full signature, return type, one-line description.

## pdf_writer.py functions
  For each public function: name, full signature, return type, one-line description.

## cmd_generate flow
  Step-by-step in plain language — what does it do from start to finish?

## Return values and file paths
  What exactly does the generation pipeline produce?
  File paths? Content strings? Both? What is returned vs written to disk?

## DB functions needed
  Which db.py functions does cmd_generate call to save document records?
  Do those functions exist in db.py? If not, name the missing ones.

## Output path pattern
  What is the exact directory and filename pattern used for permanent output?

## State required
  What config, profile, or other state must be loaded before calling generator.py?

## Same-day re-generation risk
  If output/{date_slug}/ already exists and generate is called again on the same day —
  what happens? Overwrite? Error? Check the code and report.

## Risks for the web implementation
  Any complications you foresee in adapting the CLI flow to four HTTP routes.

Do not write any code. Do not propose an implementation. Report only.

No commit for this task.
Wait for my confirmation and any follow-up questions before P5.5b starts.


==============================================================================
TASK P5.5b — Generate (implement): four-POST temp-file flow
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

IMPORTANT: Do not start this session without my explicit confirmation after P5.5a.
The approach for this session was agreed in P5.5a — implement exactly that.

Before writing any code:
1. Confirm output/.tmp/ is in .gitignore (check the file)
2. Confirm the startup lifespan sweep is in main_ui.py
3. If any db.py function for saving document records is missing (identified in P5.5a):
   add it to db.py first, python -m py_compile src/db.py, commit separately as feat(db): ...

Implement the four-POST flow in ui/main_ui.py.
Create ui/templates/generate_result.html.

Four routes:

POST /jobs/{id}/generate
  → get_job(id): 404 if not found, 400 if status != 'approved'
  → call generator.py + pdf_writer.py (exact calls from P5.5a findings)
  → write to output/.tmp/{job_id}/ (delete first if it already exists)
  → render generate_result.html:
       full cover letter body text in a scrollable block
       CV filename + brief summary of what changed
       notes textarea (optional, placeholder "Feedback for regeneration…")
       [Save] | [Revise] | [Discard]

POST /jobs/{id}/generate/confirm
  → guard: if output/.tmp/{job_id}/ missing → redirect /jobs/{id}?msg=Already+saved
  → determine permanent path output/{YYYYMMDD}_{company-slug}_{role-slug}/
  → if that path already exists (same-day re-generation): append _v2, _v3, etc.
  → move all files from .tmp/{job_id}/ to permanent path
  → save document records to DB
  → update_job_status('applied') — check if it logs internally (same rule as P5.4)
  → delete .tmp/{job_id}/
  → redirect to /jobs/{id}?msg=Documents+saved

POST /jobs/{id}/generate/discard
  → delete output/.tmp/{job_id}/ (ignore if already gone)
  → redirect to /jobs/{id}?msg=Generation+discarded

POST /jobs/{id}/generate/revise
  → read 'notes' field from form (optional)
  → jd_with_notes = job['jd_text'] + f"\n\nRegeneration notes: {notes}"
  → re-run generator.py + pdf_writer.py with jd_with_notes
  → delete output/.tmp/{job_id}/, recreate with new files
  → re-render generate_result.html with updated preview
  No DB writes. No status change.

Critical rules:
- No AI calls in main_ui.py
- No auto-save — user must click [Save]
- Same-day re-generation uses _v2 suffix, not overwrite

NOTE: This task makes a live AI API call. Confirm API key is set before running.
NOTE: Do not save editor files while the preview page is open — uvicorn --reload
      re-runs the lifespan handler and deletes output/.tmp/ mid-test.

Verification:
1. python -m py_compile ui/main_ui.py
   python -m py_compile src/db.py
   Expected: silence for both.

2. python -m uvicorn ui.main_ui:app --reload

   Test generate + save:
   Open an approved job in browser. Click [Generate].
   Confirm: preview page with full cover letter, CV summary, notes textarea, [Save], [Revise] and [Discard] visible.
   Click [Save]. Confirm redirect to job detail.
   python -c "
   from pathlib import Path
   files = [f for f in sorted(Path('output').rglob('*'))
            if '.tmp' not in str(f) and f.is_file()]
   for f in files: print(f)
   "
   Expected: files under output/{date_slug}/, nothing under .tmp/.

   Test same-day re-generation:
   Cannot reuse same job — status is 'applied' after first [Save].
   Manual setup: mkdir output\{YYYYMMDD}_{any-slug}\ by hand (any name matching
   today's date_company_role pattern), then open a DIFFERENT approved job →
   Click [Generate] → Click [Save]. Confirm output directory ends in _v2.

   Test discard:
   Click [Generate] on a different approved job. Click [Discard].
   Confirm output/.tmp/ is empty.

   Test revise:
   Open an approved job. Click [Generate]. Enter feedback in Notes. Click [Revise].
   Confirm preview reloads. Click [Save]. Confirm files saved to permanent path.

   Stop server.

Show both py_compile outputs + browser descriptions for all four tests + file listings.
Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement document generation with temp-file preview flow
- Complete Task Closing Ritual
- Do not start Task P5.6


==============================================================================
TASK P5.6 — Rate document: POST /documents/{id}/rate
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.6 — read it fully
- Read src/db.py: confirm rate_document() and get_document() are present

Verify get_document() exists (added in P5.0):
  python -c "from src.db import get_document; print('OK')"
  Expected: OK. If missing — stop and tell me.

Add POST /documents/{id}/rate to ui/main_ui.py.
Add inline rating form to Documents section of job_detail.html (number input 1-5, [Rate] button).

Route: validate 1 ≤ rating ≤ 5 (400 if not), call rate_document(), get job_id via
get_document(), redirect to /jobs/{job_id}.

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open a job detail with at least one document in browser.
   Submit rating 4. Confirm redirect back to job detail.
   Stop server.
   python -c "
   import sqlite3
   c = sqlite3.connect('data/tracker.db')
   c.row_factory = sqlite3.Row
   print(dict(c.execute('SELECT id, rating, use_as_example FROM documents ORDER BY created_at DESC LIMIT 1').fetchone()))
   "
   Expected: rating=4, use_as_example=1.

Show py_compile output + browser description + DB result. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement document rating route
- Complete Task Closing Ritual
- Do not start Task P5.7


==============================================================================
TASK P5.7 — History: GET /history
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.7 — read it fully

Verify get_activity_log() has the action filter (added in P5.0):
  python -c "import inspect; from src.db import get_activity_log; print(inspect.signature(get_activity_log))"
  Expected: signature includes action parameter.
  If missing — stop and tell me. Do not proceed.

Add GET /history route to ui/main_ui.py. Create ui/templates/history.html.

Route: GET /history?job_id=&action=&limit=50 (clamp max 200).
Call get_activity_log(job_id=..., action=..., limit=...).

Template: filter bar (GET form) + table (Timestamp | Job ID link | Action | Detail | Source).
source='manual' rows: italic or badge. "Showing N rows" count above table.

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open /history in browser yourself.
   Confirm rows render, filter bar present.
   Apply action filter — confirm only matching rows shown.
   Confirm Job ID links go to /jobs/{id}.
   Paste a brief description of what you see.
   Stop server.

Show py_compile output + browser description. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement history page with activity log
- Complete Task Closing Ritual
- Do not start Task P5.8


==============================================================================
TASK P5.8 — Report: GET /report + POST /report/export
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.8 — read it fully
- Read src/report.py in full — confirm generate_report() signature and return value

If generate_report() signature differs from what Tasks_P5.md shows: report to me
before implementing. Do not change report.py's internal logic.

Add GET /report and POST /report/export routes. Create ui/templates/report.html.

GET /report: default date range = today minus 30 days to today. Show form + preview table.
  NOTE: The preview table calls get_activity_report() which expects YYYYMMDD (no dashes).
  Use separate variables: date_from_fmt/date_to_fmt for the DB call, date_from_form/date_to_form
  for <input type="date"> pre-fill. See exact code in Tasks_P5.md P5.8 GET section.

POST /report/export:
  CRITICAL — date format conversion required:
    Browser date input submits YYYY-MM-DD. generate_report() expects YYYYMMDD.
    date_from_fmt = date_from.replace('-', '')  # "2026-01-17" → "20260117"
    date_to_fmt   = date_to.replace('-', '')
    Skipping this causes a ValueError in strptime at runtime.

  Call generate_report(date_from_fmt, date_to_fmt) → returns (pdf_path, csv_path, count).
  If count == 0: re-render form with message, no download.
  Otherwise serve with FileResponse. See exact code in Tasks_P5.md.
  Files remain in output/reports/ — intentional.

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open /report in browser yourself. Confirm form and preview render.
   Set a date range with known activity.
   Select PDF → confirm browser downloads a file. Open it — confirm it has data.
   Select CSV → confirm browser downloads. Open it — confirm it has rows.
   Paste descriptions of both downloads.
   Stop server.

Show py_compile output + browser/download descriptions. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement agency report export page
- Complete Task Closing Ritual
- Do not start Task P5.9


==============================================================================
TASK P5.9 — Profile: GET /profile + POST /profile
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P5.md Task P5.9 — read it fully
- Read config/profile.yaml to confirm actual key names

Add GET /profile and POST /profile routes. Create ui/templates/profile.html.

Editable fields (listed in Tasks_P5.md — do not expose more):
  preferences.min_score_to_show, restrictions.hybrid_cities (comma-sep),
  personal.name, personal.email,
  ai.provider (select), ai.model

CRITICAL: surgical save only — never overwrite the full file.
Load → update listed fields only → write back.
See exact code in Tasks_P5.md.

YAML library: use whichever option Jiri chose before P5.0.
  Option A: yaml.dump() — note comment-stripping was accepted.
  Option B: ruamel.yaml round-trip — use CommentedMap loader/dumper.

After save: redirect to GET /profile?msg=Profile+saved.

Verification:
1. python -m py_compile ui/main_ui.py
   Expected: silence.
2. python -m uvicorn ui.main_ui:app --reload
   Open /profile in browser yourself. Confirm all listed fields show current values.
   Change min_score_to_show. Click Save. Confirm success message appears.
   Stop server.
   python -c "
   import yaml
   p = yaml.safe_load(open('config/profile.yaml'))
   print('min_score_to_show:', p['preferences']['min_score_to_show'])
   print('skills present:', bool(p.get('skills')))
   print('ai.provider:', p['ai']['provider'])
   "
   Expected: updated value, skills still present, ai.provider unchanged.
   Change min_score_to_show back to original. Confirm.

Show py_compile output + browser description + script output. Wait for my confirmation.

After I confirm:
- Commit: feat(p5): implement profile view and edit page
- Complete Task Closing Ritual
- Do not start Task P5.10


==============================================================================
TASK P5.10 — Completion check + merge to main
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p5-web-ui
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 8, 9, and 10
- docs/Tasks_P5.md — Completion Checklist and Task P5.10

PART 1 — Run all agent-verifiable checks. Show exact output. Report PASS or FAIL.

```
python -m py_compile ui/main_ui.py
python -m py_compile src/db.py
```

```
python -m uvicorn ui.main_ui:app --reload
# confirm clean startup with lifespan handler — then Ctrl+C
```

HTTP status checks (run with server running in a separate terminal):
```
python -c "
import urllib.request
for path in ['/', '/jobs', '/history', '/report', '/profile']:
    r = urllib.request.urlopen(f'http://localhost:8000{path}')
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
Expected: no duplicate (ts, job_id, action) pairs from approve/reject actions.

DB integrity:
```
python -c "
import sqlite3
c = sqlite3.connect('data/tracker.db')
c.row_factory = sqlite3.Row
doc = c.execute('SELECT id, rating, use_as_example FROM documents WHERE rating >= 4 LIMIT 1').fetchone()
print('Rated doc:', dict(doc) if doc else 'None found')
print('Outcome count:', c.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0])
"
```

Profile integrity:
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

Show all outputs. Report PASS or FAIL for each.
Stop here. Wait for me to say "ok to merge".

--- wait for Jiri to say "ok to merge" ---

PART 2 — Only after I explicitly say "ok to merge":

1. Update docs/MILESTONES.md: P5 status → "Done"
2. Commit: docs(p5): mark P5 complete in MILESTONES.md
3. Run:
   git checkout main
   git merge feature/p5-web-ui --no-ff -m "feat(p5): merge Phase 5 web UI"
4. git branch --show-current   (expected: main)
5. git log --oneline -8
6. Show both outputs. Wait for my final confirmation.

After I confirm:
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Report: "Phase 5 complete. JobRadar v1.0 delivered. On branch main."
