# Tasks — Phase 4: Learning Loop
# JobRadar | Milestone: P4 — Learning Loop
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Follow the Task Closing Ritual (AI_INSTRUCTIONS.md section 10) after every task
# - Do NOT implement anything outside this file
# - Do NOT start P5 tasks

---

## Context — what P4 builds on

P3 delivered:
  src/generator.py     — CV tailoring + cover letter generation
  main.py              — generate command: --job-id, overwrite detection,
                         rating prompt, applied status update
  DB: documents table  — id, job_id, doc_type, path, version, rating, use_as_example

Existing db.py functions relevant to P4 (already implemented — do not rewrite):
  record_outcome(job_id, reply_type, reply_date=None, notes=None)
  rate_document(doc_id, rating)          — already sets use_as_example correctly
  get_example_letters(min_rating=4, limit=3) — already orders by rating DESC
  get_conn()                             — context manager, NO underscore

Existing main.py (verify state before treating as unstarted):
  cmd_status() may already exist — READ the file first before writing anything

P4 adds or completes:
  src/db.py   — audit record_outcome(); add get_outcomes(), get_weekly_summary()
  main.py     — verify cmd_status(); implement if stub or missing

P4 does NOT add new files.

---

## Progress

- [x] Task P4.1 — db.py: audit record_outcome() + add get_outcomes() + get_weekly_summary()
- [x] Task P4.2 — main.py: verify or complete cmd_status()
- [x] Task P4.3 — Example pool verification
- [x] Task P4.4 — End-to-end test
- [x] Task P4.5 — Completion check + merge to main

---

## Completion Checklist

- [x] python -m py_compile src/db.py — no errors
- [x] python -m py_compile main.py — no errors
- [x] python main.py status — shows list of applied jobs, user selects one
- [x] All five outcome types accepted: no_reply / rejection / positive / interview / offer
- [x] Outcome saved to outcomes table in DB
- [x] Job status updated correctly after outcome entry
- [x] Weekly summary shown when >= 5 outcomes exist
- [x] Rating a letter >= 4 sets use_as_example = 1 in documents table
- [x] get_example_letters() returns letters ordered by rating DESC
- [x] Next generate call picks up a newly added example letter

---

## Task P4.1 — db.py: audit record_outcome() + add get_outcomes() + get_weekly_summary()

**Status:** [x]

Read the entire src/db.py before making any changes.

### Step A — Audit record_outcome()

record_outcome() already exists. Verify it does ALL of the following:

1. Validates reply_type against five allowed values — raises ValueError if invalid
2. Inserts a row into the outcomes table
3. Calls log_action() internally
4. Updates job status within the same transaction — inline SQL inside the "with" block,
   NOT a call to update_job_status() (that function opens its own connection and would
   break atomicity). The mapping:
     no_reply   -> 'closed'
     rejection  -> 'closed'
     positive   -> 'responded'
     interview  -> 'interview'
     offer      -> 'offer'
5. Wraps the outcome INSERT and the status UPDATE in a single "with get_conn() as conn:"
   block — both succeed or both fail together

If any are missing — add them. Do NOT rename the function.
If a fix is needed — py_compile, then commit: fix(p4): complete record_outcome in db.py

Reference implementation if substantial changes are needed:

```python
def record_outcome(
    job_id: str,
    reply_type: str,
    reply_date: str | None = None,
    notes: str | None = None,
) -> None:
    """Record outcome. Updates job status and logs to activity_log."""
    VALID = {'no_reply', 'rejection', 'positive', 'interview', 'offer'}
    if reply_type not in VALID:
        raise ValueError(f"Invalid reply_type: {reply_type!r}. Must be one of {VALID}")

    STATUS_MAP = {
        'no_reply':  'closed',
        'rejection': 'closed',
        'positive':  'responded',
        'interview': 'interview',
        'offer':     'offer',
    }
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO outcomes (job_id, reply_type, reply_date, notes, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (job_id, reply_type, reply_date, notes, ts),
        )
        conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (STATUS_MAP[reply_type], ts, job_id),
        )
    log_action(job_id, 'outcome', detail=reply_type)
```

Note: "with get_conn() as conn:" commits automatically on exit.
log_action() opens its own connection after the with block — that is intentional.

### Step B — Add get_outcomes()

Add only if not already present:

```python
def get_outcomes(job_id: str) -> list[dict]:
    """Return all outcomes for a job, ordered by created_at ASC."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM outcomes WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
    return [dict(row) for row in rows]
```

### Step C — Add get_weekly_summary()

Add only if not already present. Threshold is 5 outcomes.

avg_score_responded measures whether high-scored jobs (AI match score from screening)
tend to get positive responses. It is a screening quality indicator, not a letter
quality metric. The UI in cmd_status() labels it accordingly.

```python
def get_weekly_summary() -> dict | None:
    """
    Return summary stats if >= 5 outcomes exist, else return None.

    Keys:
      total_outcomes      int   -- total rows in outcomes table
      response_rate       float -- % of outcomes that are NOT no_reply
      avg_score_responded float -- avg AI score of jobs with positive/interview/offer outcome
      top_status          str   -- most common reply_type
    """
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
        if total < 5:
            return None

        responded = conn.execute(
            "SELECT COUNT(*) FROM outcomes WHERE reply_type != 'no_reply'"
        ).fetchone()[0]

        avg_row = conn.execute(
            """SELECT AVG(j.score) FROM outcomes o
               JOIN jobs j ON j.id = o.job_id
               WHERE o.reply_type IN ('positive', 'interview', 'offer')"""
        ).fetchone()
        avg_score = avg_row[0] if avg_row[0] is not None else 0.0

        top_row = conn.execute(
            """SELECT reply_type FROM outcomes
               GROUP BY reply_type ORDER BY COUNT(*) DESC LIMIT 1"""
        ).fetchone()
        top_status = top_row[0] if top_row else 'n/a'

    return {
        'total_outcomes':      total,
        'response_rate':       responded / total * 100,
        'avg_score_responded': avg_score,
        'top_status':          top_status,
    }
```

### Step D — Verify rate_document() and get_example_letters()

VERIFICATION ONLY — do not rewrite unless the specific issue is present.

- rate_document(): confirm use_as_example = 1 when rating >= 4. Fix if missing.
- get_example_letters(): confirm ORDER BY rating DESC. Fix if missing.

If a fix is needed — commit separately: fix(p4): correct rate_document / get_example_letters

**Verification commands after all changes:**

```
python -m py_compile src/db.py
```
Expected: silence.

```
python -c "
from src.db import record_outcome, get_outcomes, get_weekly_summary, get_example_letters
print('All functions imported OK')
print(f'Weekly summary (expect None if < 5 outcomes): {get_weekly_summary()}')
"
```

```
python -c "
from src.db import record_outcome
try:
    record_outcome('fake-id', 'invalid_type')
except ValueError as e:
    print(f'ValueError raised correctly: {e}')
"
```

Show all 3 outputs. Wait for confirmation.

Commit after confirmation:
  feat(p4): add get_outcomes, get_weekly_summary; audit record_outcome in db.py

---

## Task P4.2 — main.py: verify or complete cmd_status()

**Status:** [x]
**File:** main.py

Read the ENTIRE main.py before writing anything.

### Step A — Determine current state

Check:
1. Is 'status' registered as a subparser?
2. Does cmd_status() exist?
3. If it exists — stub or fully implemented?

Three possible outcomes:

Case 1 — fully implemented:
Run verification commands in Step C. If all pass — no code changes.
Commit: chore(p4): verify cmd_status already complete

Case 2 — stub exists:
Replace stub with full implementation below.

Case 3 — does not exist:
Add subparser registration + full function.

### Step B — Full implementation spec (Cases 2 and 3)

Subparser registration (add after existing subparsers if missing):
```python
status_parser = subparsers.add_parser('status', help='Record outcome for an applied job')
status_parser.set_defaults(func=cmd_status)
```

All imports inside function body — follow existing command pattern.
No load_profile() — no AI call in this command.

```python
def cmd_status(args) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from src.db import (
        init_db, get_jobs, get_job,
        record_outcome, get_outcomes, get_weekly_summary,
    )
```

Flow:

Step 1 — init_db(). get_jobs() filtered in Python for statuses: 'applied', 'responded', 'interview'.
Note: 'offer' is intentionally excluded in P4. A job at offer stage cannot receive
a follow-up outcome in this phase. This is a deliberate scope limit for P4,
not an oversight. Can be revisited in P5.
If none eligible: yellow "No applied jobs to update." and return.

Step 2 — Rich table: #, Company, Role, Status, Score, Applied (applied_at or "-").
Accept 1..N or 'q'. Re-prompt once on invalid, then return.

Step 3 — get_outcomes(job_id). If any, print each:
  f"  {o['created_at'][:10]}  {o['reply_type']}  {o['notes'] or ''}"

Step 4 — Prompt:
  Outcome type:
    1) no_reply    -- no response received
    2) rejection   -- rejected by company
    3) positive    -- positive reply or callback
    4) interview   -- interview scheduled or completed
    5) offer       -- job offer received
  Enter number (1-5):
Map: 1->no_reply, 2->rejection, 3->positive, 4->interview, 5->offer. Re-prompt until valid.

Step 5 — "Reply date (YYYY-MM-DD, or Enter to skip): " Empty -> None.

Step 6 — "Notes (optional, Enter to skip): " Empty -> None.

Step 7 — Print summary. "Save? [Y/n]: " (Y default).
If Y: call record_outcome(job_id, reply_type, reply_date, notes). Green "Outcome recorded."
If n: "Cancelled." and return.

Step 8 — get_weekly_summary(). If not None, Rich Panel:
  Activity summary ({total_outcomes} outcomes tracked)
  Response rate:                {response_rate:.0f}%
  Avg score (positive replies): {avg_score_responded:.1f}
  Most common outcome:          {top_status}

### Step C — Verification commands

```
python -m py_compile main.py
```
```
python main.py --help
```
Expected: 'status' listed.

```
python main.py status
```
(no eligible jobs) Expected: yellow message, clean exit.

Show all 3. Wait for confirmation.

Commit after confirmation:
  feat(p4): implement cmd_status in main.py

---

## Task P4.3 — Example pool verification

**Status:** [x]
**Files:** none — verification only.
If a bug is found: fix, py_compile, commit as fix(p4): <description>, then continue.

Requires at least one document row in DB from P3.
If none: run python main.py generate, save, rate >= 4.

Step 1:
```
python -c "
from src.db import get_example_letters
letters = get_example_letters()
print(f'Current examples: {len(letters)}')
for l in letters:
    print(f'  id={l[\"id\"]} rating={l[\"rating\"]} use_as_example={l[\"use_as_example\"]} path={l[\"path\"]}')
"
```

Step 2:
```
python -c "
import sqlite3
conn = sqlite3.connect('data/tracker.db')
rows = conn.execute('SELECT id, doc_type, rating, use_as_example FROM documents ORDER BY created_at DESC').fetchall()
for r in rows: print(r)
"
```

Step 3 — Force rating of 4 if no letter is rated >= 4:
```
python -c "
import sqlite3
conn = sqlite3.connect('data/tracker.db')
row = conn.execute(
    'SELECT id FROM documents WHERE doc_type=\"cover_letter\" ORDER BY created_at DESC LIMIT 1'
).fetchone()
if row:
    from src.db import rate_document
    rate_document(row[0], 4)
    print(f'Rated document {row[0]} as 4')
else:
    print('No cover letter in DB -- run python main.py generate first')
"
```

Step 4: Re-run Step 2. Confirm use_as_example = 1.

Step 5: Re-run Step 1. Confirm letter appears.

Step 6:
```
python -c "
import yaml
from pathlib import Path
from src.db import get_example_letters
from src.generator import build_cover_letter_prompt

profile = yaml.safe_load(Path('config/profile.yaml').read_text())
examples = get_example_letters()
prompt = build_cover_letter_prompt(
    profile=profile,
    jd_text='Test JD text for verification only.',
    example_letters=examples,
    language='en',
)
print(f'Examples passed: {len(examples)}')
print(f'Prompt contains example block: {\"--- Example letter\" in prompt}')
print(f'Prompt uses fallback: {\"No rated examples yet\" in prompt}')
print(f'Prompt length: {len(prompt)} chars')
"
```
Expected: example block True, fallback False.

Acceptance Criteria:
- rate_document(id, 4) sets use_as_example = 1
- get_example_letters() returns that letter
- build_cover_letter_prompt() includes example block, not fallback
- No unhandled exceptions in any step

No commit if no bugs found.

---

## Task P4.4 — End-to-end test

**Status:** [x]
**Files:** none — verification only.
If a bug is found: fix, py_compile, commit as fix(p4): <description>, then continue.

**Pre-conditions — require at least 2 eligible jobs:**

Steps 1 and 2 each consume one eligible job (Step 1 closes a job via no_reply,
leaving it ineligible for Step 2). You need at least 2 jobs with status in
('applied', 'responded', 'interview') before starting.

```
python -c "
from src.db import get_jobs
eligible = [j for j in get_jobs() if j['status'] in ('applied','responded','interview')]
print(f'Eligible jobs: {len(eligible)}')
for j in eligible: print(f'  {j[\"id\"]} | {j[\"company\"]} | {j[\"status\"]}')
"
```

If fewer than 2: run python main.py generate once more, save, mark as applied.
Do not proceed with fewer than 2 eligible jobs.

---

Step 1 — no_reply path:
python main.py status -> choose job A -> outcome 1 (no_reply) -> skip date/notes -> confirm Y.

Verify:
```
python -c "
import sqlite3
conn = sqlite3.connect('data/tracker.db')
conn.row_factory = sqlite3.Row
print(dict(conn.execute('SELECT job_id, reply_type FROM outcomes ORDER BY created_at DESC LIMIT 1').fetchone()))
print(dict(conn.execute('SELECT id, status FROM jobs WHERE status=\"closed\" ORDER BY updated_at DESC LIMIT 1').fetchone()))
"
```
Expected: reply_type='no_reply', job status='closed'.

---

Step 2 — interview path:
python main.py status -> choose job B (different from Step 1) -> outcome 4 (interview)
-> date 2026-04-20 -> note "Phone screen" -> confirm Y.

Verify:
```
python -c "
import sqlite3
conn = sqlite3.connect('data/tracker.db')
conn.row_factory = sqlite3.Row
o = conn.execute('SELECT * FROM outcomes ORDER BY created_at DESC LIMIT 1').fetchone()
print(dict(o))
j = conn.execute('SELECT id, status FROM jobs WHERE id = ?', (o['job_id'],)).fetchone()
print(dict(j))
"
```
Expected: reply_type='interview', reply_date='2026-04-20', notes='Phone screen',
job status='interview'.

---

Step 3 — Cancel path:
python main.py status -> any eligible job -> any outcome -> type n at Save prompt.
Expected: "Cancelled." No new outcome row.

Verify count is same as after Step 2:
```
python -c "import sqlite3; print(sqlite3.connect('data/tracker.db').execute('SELECT COUNT(*) FROM outcomes').fetchone()[0])"
```

---

Step 4 — Weekly summary trigger:

Check current count:
```
python -c "import sqlite3; print(sqlite3.connect('data/tracker.db').execute('SELECT COUNT(*) FROM outcomes').fetchone()[0])"
```

If fewer than 5, insert synthetic outcomes using reply_type='positive' (maps to
status='responded', keeping those jobs eligible for cmd_status — do NOT use 'no_reply'
here, which would close jobs and exhaust the eligible pool):
```
python -c "
import sqlite3
from src.db import get_jobs, record_outcome
count = sqlite3.connect('data/tracker.db').execute('SELECT COUNT(*) FROM outcomes').fetchone()[0]
needed = max(0, 5 - count)
jobs = get_jobs()
for i in range(needed):
    j = jobs[i % len(jobs)]
    record_outcome(j['id'], 'positive')
    print(f'Synthetic: {j[\"id\"]}')
print(f'Added {needed}.')
"
```

python main.py status -> record one outcome -> confirm Y.
Expected: Activity summary panel appears.

---

Step 5 — Generate -> rate -> pool cycle:
python main.py generate -> save -> rate >= 4.
Re-run P4.3 Step 6 to confirm example block present in prompt.

---

Acceptance Criteria:
- All 5 steps complete without unhandled exceptions
- no_reply: outcome saved, job -> closed
- interview: outcome saved with date+notes, job -> interview
- Cancel: no row inserted
- Weekly summary appears at >= 5 outcomes
- Example pool grows; prompt picks up new letter

---

## Task P4.5 — Completion check + merge to main

**Status:** [x]
**Files:** docs/MILESTONES.md (status update only)

1. Run every item in the Completion Checklist. Show Jiri the output.
   Stop if anything fails. Wait for Jiri's confirmation.

2. Update docs/MILESTONES.md: P4 status -> "Done"

3. Commit: docs(p4): mark P4 complete in MILESTONES.md

4. Merge:
   git checkout main
   git merge feature/p4-learning --no-ff -m "feat(p4): merge Phase 4 learning loop"

5. Branch: git checkout -b feature/p5-web-ui

6. Verify: git branch --show-current (expected: feature/p5-web-ui)
   git log --oneline -5 — show both outputs.

Constraints:
- NEVER merge without Jiri's explicit "ok to merge"
- NEVER push without asking

---

## Notes for Claude Code

### Confirmed db.py API — read from source before assuming

```
get_conn()                                 -- context manager, NO underscore
now_iso()                                  -- UTC ISO timestamp helper
record_outcome(job_id, reply_type,         -- EXISTING; audit in P4.1
               reply_date=None, notes=None) -> None
rate_document(doc_id, rating)              -- EXISTING; verification only in P4.1
get_example_letters(min_rating=4,          -- EXISTING; verification only in P4.1
                    limit=3) -> list[dict]
get_outcomes(job_id) -> list[dict]         -- NEW in P4.1
get_weekly_summary() -> dict | None        -- NEW in P4.1
```

### Status lifecycle after P4

```
new -> reviewed -> approved -> applied
                            -> responded  (positive outcome)
                            -> interview  (interview outcome)
                            -> offer      (offer outcome)
                            -> closed     (no_reply or rejection outcome)
              -> rejected    (during review)
```

### Hard rules

- get_conn() — context manager, no underscore — never sqlite3.connect() directly in src/
- Do NOT rename record_outcome() — seed_backfill.py already calls it
- record_outcome() updates job status inline (SQL in the with block) — never via update_job_status()
- record_outcome() calls log_action() after the with block — that is intentional
- cmd_status() calls record_outcome() only — never update_job_status() directly
- 'offer' excluded from cmd_status() eligible statuses in P4 — intentional scope limit
- No business logic in main.py — orchestration only
- 'interview' and 'offer' are valid job status values — jobs.status is TEXT, no migration needed
- Bug found in P4.3 or P4.4 -> fix + commit before continuing, never untracked
- Verification scripts using raw sqlite3.connect() must set conn.row_factory = sqlite3.Row
  before any fetchone() that will be passed to dict()
- Synthetic outcomes in P4.4 Step 4 use reply_type='positive' — never 'no_reply',
  which would close jobs and exhaust the eligible pool for cmd_status()