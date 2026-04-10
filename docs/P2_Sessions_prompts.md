# P2 Session Prompts — JobRadar
# One prompt per Claude Code session. Copy the block, paste as first message.
# Wait for Task Closing Ritual confirmation before starting the next session.

==============================================================================
TASK P2.1 — DB reset command
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p2-backfill-report
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 4, 7, 8, and 10
- docs/Tasks_P2.md Task P2.1

Your job:
1. Add reset_db() to src/db.py as specified in Task P2.1
2. Add cmd_reset and reset command to main.py

Read src/db.py and main.py first to understand existing patterns.

Note to AI: reset_db() must DELETE rows from activity_log along with the
other three tables. This is a deliberate, one-time exception to the
APPEND ONLY rule — the DB contains only P1 test data and must be fully
wiped. Do not apply this exception anywhere else.

Also: cmd_reset must call init_db() before reset_db(), matching the
pattern used by cmd_process and cmd_review.

After implementing:
- Run: python -m py_compile src/db.py
- Run: python -m py_compile main.py
- Run: python main.py reset
  (expected: warning printed, nothing deleted)
- Run: python main.py reset --confirm
  (expected: row counts printed, confirmation message)
- Run: python main.py reset --confirm  (second time)
  (expected: all counts show 0 — idempotent)
- Show me all outputs
- Wait for my confirmation

After I confirm:
- Commit: feat(p2): add reset command to clear test data from DB
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P2.2


==============================================================================
TASK P2.2 — Duplicate job detection
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p2-backfill-report
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 4, 7, 8, and 10
- docs/Tasks_P2.md Task P2.2

Your job:
1. Add find_similar_job() to src/db.py
2. Add duplicate check to the process command in main.py

Read src/db.py and main.py carefully first.
The duplicate check goes BEFORE scoring — if user skips, do not fetch or score.

Critical constraints:
- find_similar_job() in db.py only — no business logic there, just the query
- User always decides — never auto-skip a duplicate
- Do NOT touch parser.py, scorer.py, fetcher.py
- find_similar_job() uses timedelta — add it to the existing
  "from datetime import datetime, timezone" line in db.py

After implementing:
- Run: python -m py_compile src/db.py
- Run: python -m py_compile main.py
- Run: python -c "from src.db import find_similar_job; print('OK')"
- Show me all outputs
- Wait for my confirmation

After I confirm:
- Commit: feat(p2): add duplicate job detection before scoring
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P2.3


==============================================================================
TASK P2.3 — backfill.py wizard + seed_backfill.py data load
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p2-backfill-report
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P2.md Task P2.3

Read src/db.py fully before writing any code.

========================================
PART 1 — Three required changes to src/db.py
========================================

1. Add source and date_str parameters to insert_job()

   Change signature to:
     def insert_job(data: dict, source: str = 'system', date_str: str | None = None) -> str:

   In the body, replace:
     date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
   with:
     date_str = date_str or datetime.now(timezone.utc).strftime("%Y%m%d")

   In the internal activity_log INSERT, add source:
     INSERT INTO activity_log (job_id, action, ts, source) VALUES (?, 'scored', ?, ?)
   passing (job_id, ts, source).

   Existing callers are unaffected — both new params have defaults.

2. Add job_exists_exact() to src/db.py

   def job_exists_exact(company: str, role_title: str, date_str: str) -> bool:
       """Return True if a job with exact company, role_title, and date already exists.
       date_str must be in YYYYMMDD format."""
       with get_conn() as conn:
           row = conn.execute(
               "SELECT 1 FROM jobs WHERE company = ? AND role_title = ?"
               " AND strftime('%Y%m%d', created_at) = ? LIMIT 1",
               (company, role_title, date_str),
           ).fetchone()
       return row is not None

========================================
PART 2 — Create backfill.py wizard
========================================

Create backfill.py exactly as specified in docs/Tasks_P2.md Task P2.3.

Critical constraints:
- backfill.py calls db.py only — no AI, no parser, no scorer
- All entries: source='manual' in activity_log — never 'system'
  (pass source='manual' to insert_job() and every log_action() call)
- Both date formats must work: YYYY-MM-DD and DD.MM.YYYY
- Duplicate check: call job_exists_exact() before every insert —
  if True, print warning and skip
- Pass parsed date as date_str (YYYYMMDD) to insert_job()
- Use Rich for all terminal output

========================================
PART 3 — Create seed_backfill.py
========================================

Create seed_backfill.py — a one-off script that loads all real job data
into the database. It hardcodes the records as a Python list and calls
db functions directly. No wizard, no user input.

It must:
- Call db.init_db() at the start
- For each record: call job_exists_exact() first — if already exists, print
  "Skipped (duplicate): {company} — {role}" and continue
- Call insert_job(data, source='manual', date_str=YYYYMMDD)
- For job applications: call log_action(job_id, 'applied', source='manual')
- If status is Declined: also call log_action(job_id, 'rejected', source='manual')
  and db.record_outcome(job_id, 'rejection')
- For recruiter contacts: call log_action(job_id, 'recruiter_contact',
  detail=outcome, source='manual')
- Print "Saved: {company} — {role}" for each successful insert

Status mapping: Declined → status='rejected', Applied (no response) → status='applied'

Hardcoded job data (21 job applications):
date        | company                | role                                              | status   | location
07.10.2025  | Enpal                  | Senior Software Engineer (Backend & Integrations) | Declined |
07.10.2025  | Adevinta               | (Senior) Data / Analytics Engineer                | Declined |
14.10.2025  | Verti Versicherung     | Senior Data Engineer (m/w/d) DWH                  | Declined | Teltow
24.10.2025  | eBay                   | Senior Software Engineer, Security                | Declined |
24.10.2025  | Enpal                  | Senior Software Engineer Backend                  | Declined |
28.10.2025  | eBay                   | MTS 1, Software Engineer, Data                    | Declined |
04.11.2025  | SoSafe                 | Senior Data Engineer (m/f/d)                      | Applied  | Berlin/Remote
11.11.2025  | 4flow SE               | Senior Data Engineer (Logistics)                  | Declined |
18.11.2025  | DeepL                  | Senior Data Engineer                              | Declined | Remote/Berlin
18.11.2025  | Delivery Hero SE       | Senior Data Analyst                               | Declined |
12.12.2025  | AroundHome             | Senior Data Engineer (Modern Data Platform)       | Declined |
16.12.2025  | Axel Springer          | (Senior) Software Engineer Data                   | Declined |
26.12.2025  | Parloa                 | Principal Software Engineer                       | Declined |
20.01.2026  | Andersen               | Backend Developer (.NET) in Germany               | Declined |
20.01.2026  | DeepLSE                | Senior Staff Data Engineer                        | Declined |
27.01.2026  | Zalando SE             | Senior Data Platform Engineer                     | Declined |
30.01.2026  | Trinetix               | Senior .NET Developer                             | Applied  |
30.01.2026  | Tieto                  | (Senior) Backend Developer Java & .NET (m/f/d)    | Declined |
04.02.2026  | Axel Springer          | Senior Software Engineer (m/f/d) Data             | Declined |
04.02.2026  | Topi                   | Senior Data Engineer                              | Applied  |
06.02.2026  | Andersen               | Backend Developer (.NET) in the EU                | Declined |

Hardcoded recruiter contact data (4 entries):
date        | agency                      | action                                       | outcome
04.11.2025  | Prime People                | Registration                                 | Input profile created, currently without a suitable position.
04.11.2025  | Noir Consulting             | Request for a Job - Senior Software Engineer | Declined - position filled or profile mismatch.
07.11.2025  | IT Recruiting alphacoders   | Registration                                 | They were supposed to call, no one contacted me.
07.11.2025  | Senior Connect              | Request for a Job - Full Stack Developer     | Declined after reviewing the profile.

========================================
PART 4 — Verification
========================================

Run in this exact order:

1. python -m py_compile src/db.py
   (expected: no output)

2. python -m py_compile backfill.py
   (expected: no output)

3. python -m py_compile seed_backfill.py
   (expected: no output)

4. python backfill.py
   Enter one test record: Enpal / Senior Software Engineer Backend / 24.10.2025 / Declined
   Then type 'done'
   (expected: "Saved: Enpal — Senior Software Engineer Backend")

5. python backfill.py
   Enter the same record again, then type 'done'
   (expected: "Already exists" warning, nothing inserted)

6. python seed_backfill.py
   (expected: 21 "Saved:" lines + 4 "Saved:" lines; the Enpal 24.10.2025 entry
   should print "Skipped (duplicate)" since it was entered in step 4)

7. python -c "
   from src.db import get_jobs
   jobs = get_jobs()
   print(f'Total jobs: {len(jobs)}')
   for j in jobs:
       print(f'{j[\"company\"]} | {j[\"role_title\"]} | {j[\"status\"]}')
   "
   (expected: 25 records — 1 test entry + 20 new jobs + 4 recruiters;
   Enpal Senior Software Engineer Backend 24.10.2025 counted once only)

8. python -c "
   import sqlite3
   conn = sqlite3.connect('data/tracker.db')
   rows = conn.execute('SELECT DISTINCT source FROM activity_log').fetchall()
   print([r[0] for r in rows])
   "
   (expected: ['manual'] — no 'system' entries)

Show me all outputs.
Wait for my confirmation.

========================================
AFTER I CONFIRM
========================================

- Commit: feat(p2): add backfill wizard and seed all job data
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P2.4


==============================================================================
TASK P2.4 — src/report.py + report command
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p2-backfill-report
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P2.md Task P2.4 (full PDF layout, German labels, filename pattern)

Your job:
1. Create src/report.py
2. Add report command to main.py

Read src/db.py first (specifically get_activity_report).
Read config/profile.yaml — report.py reads name and location from there.

========================================
CRITICAL — applied_at column
========================================

The jobs table has an applied_at column (YYYYMMDD text) that stores the real
application date. This was added in a pre-P2.4 fix.

- get_activity_report(date_from, date_to) already filters by j.applied_at
  and returns j.applied_at in each row. Use this function as-is.
- date_from and date_to must be passed as YYYYMMDD strings (e.g. '20251001')
- Datum column in the report must use row['applied_at'], formatted as DD.MM.YYYY
- Do NOT use a.ts or j.created_at for dates — those are all April 9, 2026

When main.py prompts for the date range (YYYY-MM-DD input), strip the dashes
before passing to get_activity_report: '2025-10-01' → '20251001'

If either date input cannot be parsed with datetime.strptime(value, "%Y-%m-%d"),
print a German error message and exit with sys.exit(1). Do not re-prompt.

========================================

Critical constraints:
- All column headers and labels in German (see ACTION_LABELS and STATUS_LABELS in task)
- cmd_report prompts must be in German:
    Zeitraum Von (JJJJ-MM-TT): 
    Zeitraum Bis (JJJJ-MM-TT): 
- After generating, cmd_report must print exactly:
    "{N} Einträge gefunden."
  followed by the two file paths (PDF and CSV)
- Manual entries show "(M)" marker in Aktion column.
  Detect via: row.get('source') == 'manual'
  get_activity_report() already returns source from activity_log.
  If source is NULL (no activity_log row), treat as non-manual — no marker.
- Personal data from config/profile.yaml — never hardcoded.
  Use profile['personal']['name'] and profile['personal']['location'] as-is.
  Note: location in the YAML is "Potsdam, Germany" — use that value verbatim.
- reportlab for PDF — already in requirements.txt
- Output filenames use the YYYYMMDD strings (date_from / date_to):
    output/reports/bericht_{date_from}_bis_{date_to}.pdf
    output/reports/bericht_{date_from}_bis_{date_to}.csv
  Example: bericht_20251001_bis_20260228.pdf
- report.py must create output/reports/ before writing:
    Path("output/reports").mkdir(parents=True, exist_ok=True)
- PDF pagination footer: show only "Seite {N}" per page.
  Do NOT implement total page count ("von N") — out of scope.

========================================

After creating:
- Run: python -m py_compile src/report.py
  (expected: no output)
- Run: python -m py_compile main.py
  (expected: no output)
- Run: python main.py report
  Enter: 2025-10-01 for Von, 2026-02-28 for Bis
  (expected output: "25 Einträge gefunden." + two file paths)
- Verify the CSV dates are correct by running:
  python -c "
  import csv
  with open('output/reports/bericht_20251001_bis_20260228.csv', encoding='utf-8') as f:
      rows = list(csv.DictReader(f))
  print(f'{len(rows)} rows')
  print('First Datum:', rows[0]['Datum'])
  print('Last Datum:', rows[-1]['Datum'])
  "
  (expected: 25 rows, dates like 07.10.2025 — NOT 10.04.2026)
- Show me all terminal output above
- Wait for my confirmation
  (I will open the PDF manually to verify layout and dates)

After I confirm:
- Commit: feat(p2): add agency report export — PDF + CSV in German
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P2.5


==============================================================================
TASK P2.5 — End-to-end test
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p2-backfill-report
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P2.md Task P2.5 (all 8 steps)

This is a verification-only task. No code changes.

Run every step in Task P2.5 in order.
Show me the exact command and output for each step.
Stop at any step that fails — do not continue.

IMPORTANT — Step 7 verifies backfill data (already loaded in P2.3):
All 25 records (21 job applications + 4 recruiter contacts) were loaded
by seed_backfill.py in P2.3. Do NOT re-enter them. Instead, verify:

- Run: python -c "
  from src.db import get_jobs
  jobs = get_jobs()
  print(f'Total records: {len(jobs)}')
  for j in jobs:
      print(f'{j[\"company\"]} | {j[\"role_title\"]} | {j[\"status\"]}')
  "
  (expected: 25 records)

- Run: python -c "
  import sqlite3
  conn = sqlite3.connect('data/tracker.db')
  rows = conn.execute('SELECT DISTINCT source FROM activity_log').fetchall()
  print([r[0] for r in rows])
  "
  (expected: ['manual'] only — no 'system' entries)

After all 8 steps:
- Report PASS or FAIL for each acceptance criterion
- Wait for my confirmation
- No commit for this task
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P2.6 until I say so


==============================================================================
TASK P2.6 — Completion check + merge to main
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p2-backfill-report
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 8, 9, and 10
- docs/Tasks_P2.md Task P2.6 and the Completion Checklist

PART 1 — Run the full completion checklist.
Run every command in the Completion Checklist section of Tasks_P2.md.
Show me the exact output of each command.
Report PASS or FAIL clearly for each item.
Stop here and wait for my confirmation before doing anything else.

--- wait for Jiri to say "ok to merge" ---

PART 2 — Only after I explicitly say "ok to merge":

1. Update docs/MILESTONES.md: P2 status → "✅ Done"
2. Commit: docs(p2): mark P2 complete in MILESTONES.md
3. Run:
   git checkout main
   git merge feature/p2-backfill-report --no-ff -m "feat(p2): merge Phase 2 backfill and report"
   git checkout -b feature/p3-generate-docs
4. Run: git branch --show-current  (expected: feature/p3-generate-docs)
5. Run: git log --oneline -5
6. Show me both outputs
7. Wait for my final confirmation

After I confirm:
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Report: "Phase 2 complete. On branch feature/p3-generate-docs. Ready for P3."