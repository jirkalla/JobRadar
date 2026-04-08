# Tasks — Phase 2: Backfill + Report
# JobRadar | Milestone: P2 — Backfill + Report
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Follow the Task Closing Ritual (AI_INSTRUCTIONS.md section 10) after every task
# - Do NOT implement anything outside this file
# - Do NOT start P3 tasks

---

## Context — what P2 builds on

P1 delivered:
  src/parser.py     — Infoagent digest parser
  src/scorer.py     — AI scoring + location validation
  src/fetcher.py    — Forpsi IMAP download
  main.py           — fetch, process, review commands
  src/db.py         — complete database operations

P2 adds four deliverables, all independent of P1's parsing/scoring:
  1. DB reset command   — clean start for real use (wipe test data)
  2. Duplicate detection — prevent applying to same job twice
  3. Backfill wizard    — enter Oct 2025–Feb 2026 past applications
  4. Agency report      — PDF + CSV export in German for unemployment agency

P2 can be built and used independently of P3/P4.
backfill.py only needs db.py — no AI, no parsing.

---

## Progress

- [x] Task P2.1 — DB reset command (main.py reset)
- [ ] Task P2.2 — Duplicate job detection in db.py + process command
- [ ] Task P2.3 — backfill.py wizard
- [ ] Task P2.4 — src/report.py + main.py report command
- [ ] Task P2.5 — End-to-end test
- [ ] Task P2.6 — Completion check + merge to main

---

## Completion Checklist

- [ ] `python -m py_compile backfill.py` — no errors
- [ ] `python -m py_compile src/report.py` — no errors
- [ ] `python -m py_compile main.py` — no errors
- [ ] `python main.py reset --confirm` — wipes tables, prints confirmation
- [ ] `python backfill.py` — wizard runs, enters one test record, saves to DB
- [ ] `python main.py report` — generates PDF + CSV in output/reports/
- [ ] PDF contains correct German header with name, address, date range
- [ ] PDF contains all activity_log entries in the range
- [ ] Manual entries marked with (M) in report
- [ ] Duplicate detection warns when same company+role seen within 90 days

---

## Task P2.1 — DB reset command

**Status:** [ ]
**Files:**
- `main.py` (EXTEND — add reset command)

**Description:**
Add `python main.py reset` command that wipes all job-related data from the
database. This is used once to clear P1 test data before real use begins.

**What reset does:**
- Requires explicit `--confirm` flag — never runs without it
- Without --confirm: prints warning and exits with instructions
- With --confirm: truncates these tables: jobs, activity_log, documents, outcomes
- Does NOT drop tables — schema stays intact
- Does NOT touch: config/, examples/, inbox/, output/, data/processed/
- Prints count of deleted rows per table
- Prints: "Database cleared. Ready for real use."

**Command behaviour:**
```
python main.py reset
→ "WARNING: This will delete all job data.
   Run: python main.py reset --confirm"

python main.py reset --confirm
→ "Clearing database...
   jobs: 47 rows deleted
   activity_log: 203 rows deleted
   documents: 0 rows deleted
   outcomes: 0 rows deleted
   Database cleared. Ready for real use."
```

**Implementation:**
Add `reset_db()` function to src/db.py:
```python
def reset_db() -> dict:
    """Delete all rows from job-related tables. Schema unchanged."""
    tables = ['outcomes', 'documents', 'activity_log', 'jobs']
    counts = {}
    with get_conn() as conn:
        for table in tables:
            cur = conn.execute(f"DELETE FROM {table}")
            counts[table] = cur.rowcount
    return counts
```

Add `cmd_reset` to main.py:
- Check for --confirm flag
- Call db.reset_db()
- Print counts and confirmation

**Constraints:**
- Never truncate without --confirm
- Never drop tables
- Never touch files outside data/tracker.db

**Acceptance Criteria:**
- `python main.py reset` without flag: warning printed, nothing deleted
- `python main.py reset --confirm`: all tables cleared, counts shown
- `python main.py reset --confirm` run twice: second run shows 0 rows (idempotent)
- DB schema still valid after reset (all 4 tables exist, empty)

---

## Task P2.2 — Duplicate job detection

**Status:** [ ]
**Files:**
- `src/db.py` (EXTEND — add find_similar_job function)
- `main.py` (EXTEND — add duplicate check in process command)

**Description:**
Before inserting a new job, check if a similar job (same company + similar
role title) already exists in the last 90 days. Show a warning and let
Jiri decide whether to skip or keep as a new entry.

**Add to src/db.py:**
```python
def find_similar_job(company: str, role_title: str, days: int = 90) -> dict | None:
    """
    Find an existing job with same company and similar role title
    within the last N days. Returns the job dict or None.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        row = conn.execute("""
            SELECT * FROM jobs
            WHERE company = ?
              AND created_at >= ?
              AND status != 'rejected'
            ORDER BY created_at DESC
            LIMIT 1
        """, (company, cutoff)).fetchone()
    if not row:
        return None
    # Check role similarity — both contain at least one common significant word
    existing_words = set(row['role_title'].lower().split())
    new_words = set(role_title.lower().split())
    common = existing_words & new_words - {'senior', 'junior', 'and', 'or', 'the', 'in', 'for', 'm/f/d', 'with'}
    return dict(row) if common else None
```

**Add to main.py process command — before scoring each stub:**
```python
existing = db.find_similar_job(stub.company, stub.title)
if existing:
    console.print(f"\n[yellow]⚠ Similar job already in DB:[/yellow]")
    console.print(f"  {existing['role_title']} at {existing['company']}")
    console.print(f"  Status: {existing['status']}  Score: {existing['score']}/10")
    choice = console.input("  [S]kip / [K]eep as new / [V]iew full details: ").lower()
    if choice == 's':
        continue
    elif choice == 'v':
        console.print(f"  Score reason: {existing['score_reason']}")
        choice = console.input("  [S]kip / [K]eep as new: ").lower()
        if choice == 's':
            continue
```

**Constraints:**
- find_similar_job() in db.py only — no business logic in db.py
- Duplicate check shown only during process command, not during backfill
- User always has final say — never auto-skip

**Acceptance Criteria:**
- `python -c "from src.db import find_similar_job; print('OK')"` — prints OK
- Running process twice on same digest: duplicate warning shown for each job
- Choosing [S] skips without inserting
- Choosing [K] inserts as normal

---

## Task P2.3 — backfill.py wizard

**Status:** [ ]
**Files:**
- `backfill.py` (NEW)

**Description:**
Interactive wizard to enter past job applications manually.
Used to backfill Oct 2025–Feb 2026 activity from Jiri's agency tracking sheet.

**Source data (from agency tracking sheet):**
```
07.10.2025  Enpal              Senior Software Engineer (Backend & Integrations)  Declined
07.10.2025  Adevinta           (Senior) Data / Analytics Engineer                Declined
14.10.2025  Verti/Teltow       Senior Data Engineer DWH                          Declined
24.10.2025  eBay               Senior Software Engineer Security                 Declined
24.10.2025  Enpal              Senior Software Engineer Backend                  Declined
28.10.2025  eBay               MTS 1 Software Engineer Data                      Declined
04.11.2025  SoSafe             Senior Data Engineer                               —
11.11.2025  4flow SE           Senior Data Engineer Logistics                    Declined
18.11.2025  Deepl              Senior Data Engineer                               Declined
18.11.2025  Delivery Hero SE   Senior Data Analyst                               Declined
12.12.2025  AroundHome         Senior Data Engineer Modern Data Platform          Declined
16.12.2025  Axel Springer      (Senior) Software Engineer Data                   Declined
26.12.2025  Parloa             Principal Software Engineer                        Declined
20.01.2026  Andersen           Backend Developer .NET in Germany                  Declined
20.01.2026  DeepLSE            Senior Staff Data Engineer                         Declined
27.01.2026  Zalando SE         Senior Data Platform Engineer                      Declined
30.01.2026  Trinetix           Senior .NET Developer                               —
30.01.2026  Tieto              (Senior) Backend Developer Java & .NET              Declined
04.02.2026  Axel Springer      Senior Software Engineer Data                      Declined
04.02.2026  Topi               Senior Data Engineer                                —
06.02.2026  Andersen           Backend Developer .NET in the EU                   Declined
```

Recruiter contacts (second table from sheet):
```
04.11.2025  Prime People       Registration          Profile created, no suitable position
04.11.2025  Noir Consulting    Job request SSE       Declined - position filled
07.11.2025  IT Recruiting alphacoders  Registration  They never called
07.11.2025  Senior Connect     Job request Full Stack  Declined after profile review
```

**Wizard flow:**

```
python backfill.py

JobRadar — Backfill Wizard
Enter past job applications. Type 'done' at any prompt to finish.

Record type:
  [J] Job application
  [R] Recruiter contact
  [D] Done
Choice: j

Company: Enpal
Role title: Senior Software Engineer Backend
Date applied (YYYY-MM-DD or DD.MM.YYYY): 24.10.2025
Status:
  [A] Applied — no response yet
  [D] Declined by company
  [P] Positive response
  [I] Interview
  [O] Offer
Choice: d

Saved: Enpal — Senior Software Engineer Backend — 24.10.2025 — Declined
```

**For recruiter contacts:**
```
Choice: r

Agency name: Noir Consulting
Action (e.g. Registration / Job request): Job request SSE
Date (YYYY-MM-DD or DD.MM.YYYY): 04.11.2025
Outcome (optional): Declined - position filled

Saved: Recruiter contact — Noir Consulting — 04.11.2025
```

**Implementation rules:**

Date parsing — accept multiple formats:
```python
def parse_date(raw: str) -> str:
    """Accept YYYY-MM-DD or DD.MM.YYYY, return YYYY-MM-DD."""
    raw = raw.strip()
    for fmt in ['%Y-%m-%d', '%d.%m.%Y']:
        try:
            return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {raw}. Use YYYY-MM-DD or DD.MM.YYYY")
```

Job application saved as:
- `db.insert_job()` with status matching choice
- `db.log_action(job_id, 'applied', source='manual')`
- If declined: `db.log_action(job_id, 'rejected', source='manual')`
- `db.record_outcome()` if status is not 'applied'

Recruiter contact saved as:
- `db.insert_job()` with company=agency_name, role_title=action, status='applied'
- `db.log_action(job_id, 'recruiter_contact', detail=outcome, source='manual')`

**Constraints:**
- backfill.py calls db.py only — no AI, no parsing, no scoring
- All entries: source='manual' in activity_log
- Never overwrite existing entries — check for duplicates by company+role+date
- Use Rich for all terminal output

**Acceptance Criteria:**
- `python -m py_compile backfill.py` — no errors
- Wizard runs without crashing
- Both date formats accepted
- Job entry saved to jobs table with correct status
- Recruiter contact saved to jobs table
- All entries have source='manual' in activity_log
- Running twice for same record: warns "Already exists", does not duplicate

---

## Task P2.4 — src/report.py + main.py report command

**Status:** [ ]
**Files:**
- `src/report.py` (NEW)
- `main.py` (EXTEND — add report command)

**Description:**
Export a PDF + CSV report of all job activity in a date range.
Report is in German. Suitable for handing to the unemployment agency.

**PDF layout:**

Page header (every page):
```
JobRadar — Bewerbungsnachweis

Name:           Jiri Vosta
Adresse:        Potsdam, Deutschland
Zeitraum:       01.10.2025 – 28.02.2026
Erstellt am:    08.04.2026                    Seite 1 von 2
```

Table columns (German):
```
Datum | Unternehmen | Position | Aktion | Status
```

Column content:
- Datum: DD.MM.YYYY format
- Unternehmen: company name
- Position: role_title (truncated to 45 chars if needed)
- Aktion: German action label (see mapping below)
- Status: German status label (see mapping below)

Action mapping (activity_log.action → German):
```python
ACTION_LABELS = {
    'applied':            'Beworben',
    'recruiter_contact':  'Kontakt Recruiter',
    'approved':           'Genehmigt',
    'rejected':           'Abgelehnt',
    'responded':          'Antwort erhalten',
    'interview':          'Vorstellungsgespräch',
    'offer':              'Angebot',
    'scored':             'Bewertet',
}
```

Status mapping (jobs.status → German):
```python
STATUS_LABELS = {
    'new':        'Neu',
    'approved':   'Genehmigt',
    'applied':    'Beworben',
    'responded':  'Antwort',
    'rejected':   'Abgelehnt',
    'closed':     'Abgeschlossen',
}
```

Manual entries: append " (M)" to Aktion column value.
Example: "Beworben (M)" for manually backfilled applications.

**PDF generation using reportlab:**
```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
```

**CSV columns (same data, same German labels):**
```
Datum,Unternehmen,Position,Aktion,Status
07.10.2025,Enpal,Senior Software Engineer Backend,Beworben (M),Abgelehnt
```

**main.py report command:**
```
python main.py report

Zeitraum Von (YYYY-MM-DD): 2025-10-01
Zeitraum Bis (YYYY-MM-DD): 2026-02-28

Generating report...
  37 entries found

Saved:
  output/reports/bericht_20251001_bis_20260228.pdf
  output/reports/bericht_20251001_bis_20260228.csv
```

**Output filename pattern:**
```
output/reports/bericht_{from_date}_bis_{to_date}.pdf
output/reports/bericht_{from_date}_bis_{to_date}.csv
```

**Constraints:**
- report.py reads from db.py only — no AI, no parsing
- Personal data (name, address) read from config/profile.yaml
- reportlab for PDF — already in requirements.txt
- All labels in German
- PDF must be printable on A4

**Acceptance Criteria:**
- `python -m py_compile src/report.py` — no errors
- `python main.py report` — prompts for dates, generates both files
- PDF opens correctly and shows German header with correct dates
- PDF table contains all activity_log entries in the date range
- Manual entries show "(M)" marker
- CSV opens in Excel without errors

---

## Task P2.5 — End-to-end test

**Status:** [ ]
**Files:** none — verification only

**Steps:**

1. Reset the database:
   ```
   python main.py reset --confirm
   ```
   Expected: all tables cleared, counts printed

2. Enter 3 test records via backfill:
   ```
   python backfill.py
   ```
   Enter: Enpal / Senior Software Engineer Backend / 24.10.2025 / Declined
   Enter: Noir Consulting (recruiter) / Job request / 04.11.2025
   Enter: Zalando SE / Senior Data Platform Engineer / 27.01.2026 / Declined

3. Verify DB:
   ```
   python -c "
   from src.db import get_jobs, get_stats
   stats = get_stats()
   print(f'Total: {stats[\"total\"]}')
   print(f'By status: {stats[\"by_status\"]}')
   "
   ```
   Expected: 3 jobs, all with status reflecting what was entered

4. Generate report for full backfill range:
   ```
   python main.py report
   ```
   Enter: 2025-10-01 to 2026-02-28
   Expected: PDF + CSV created in output/reports/

5. Verify PDF:
   - Open the PDF
   - Confirm German header shows correct name, date range, generation date
   - Confirm 3 entries visible in table
   - Confirm manual entries show "(M)" marker

6. Test duplicate detection:
   ```
   python backfill.py
   ```
   Enter Enpal / Senior Software Engineer Backend again
   Expected: "Already exists" warning, not saved again

7. Enter all real backfill data from the agency tracking sheet (21 jobs + 4 recruiter contacts)

8. Generate final report for Oct 2025–Feb 2026:
   ```
   python main.py report
   ```
   Enter: 2025-10-01 to 2026-02-28
   Expected: 25 entries, all correct

**Acceptance Criteria:**
- All 8 steps complete without errors
- PDF is ready to hand to unemployment agency
- Duplicate detection works for backfill entries

---

## Task P2.6 — Completion check + merge to main

**Status:** [ ]
**Files:** `docs/MILESTONES.md` (status update only)

**Steps in order:**

1. Run the full Completion Checklist above — every item must pass.
   Show Jiri the output of each command. Stop if anything fails.
   Wait for Jiri's confirmation.

2. Update docs/MILESTONES.md: P2 status → "✅ Done"

3. Commit:
   ```
   docs(p2): mark P2 complete in MILESTONES.md
   ```

4. Merge:
   ```
   git checkout main
   git merge feature/p2-backfill-report --no-ff -m "feat(p2): merge Phase 2 backfill and report"
   ```

5. Create P3 branch:
   ```
   git checkout -b feature/p3-generate-docs
   ```

6. Confirm:
   ```
   git branch --show-current
   git log --oneline -5
   ```
   Expected: on feature/p3-generate-docs, merge commit at top.

**Constraints:**
- NEVER merge without Jiri's explicit "ok to merge" in chat
- NEVER push without asking Jiri first

**Acceptance Criteria:**
- All checklist items pass
- MILESTONES.md shows P2 ✅ Done
- Currently on branch feature/p3-generate-docs

---

## Notes for Claude Code

### Layer rules for P2
- backfill.py → db.py only. No AI, no parser, no scorer.
- report.py → db.py only. No AI, no parser, no scorer.
- db.py → stdlib sqlite3 only. No business logic.
- main.py → orchestrates only. No business logic.

### Hard rules
- All backfill entries: source='manual' in activity_log — never 'system'
- report.py reads personal data from config/profile.yaml — never hardcode name/address
- Reset command requires --confirm — never wipes without it
- Duplicate check in process command: user always decides — never auto-skip

### Reference data — agency tracking sheet
The exact backfill data is in Task P2.3 above. Use those exact dates and
company names. Do not invent or approximate.

### Planned but not in P2
- Learning loop (P4) — ratings feed back into generation
- Cover letter generation (P3) — builds on P2's DB foundation
- Web UI (P5) — report can be triggered from browser