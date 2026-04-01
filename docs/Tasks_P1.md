# Tasks — Phase 1: Parse + Score
# JobRadar | Milestone: P1 — Parse + Score
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Follow the Task Closing Ritual (AI_INSTRUCTIONS.md section 10) after every task
# - Do NOT implement anything outside this file
# - Do NOT start P2 tasks

---

## What was built in P1.1–P1.4

The following were built by Claude Code and committed to feature/p1-parse-score:

  src/parser.py   — Infoagent digest parser, JobStub dataclass, fetch_job_description()
  src/scorer.py   — AI scoring, location validation, build_score_prompt()
  main.py         — process command (with quick filter) + review command

Design decisions in the built version:
  - Quick filter: shown before URL fetching (user marks obvious skips)
  - Location validation: inside scorer.py using profile.yaml rules
  - JD truncation: 5000 chars
  - Review: approve/reject/skip with --all and --min flags

These are tested in P1.5 as-is. Improvements are noted but not changed
before testing — never refactor untested code.

---

## Progress

- [x] Task P1.1 — Rewrite src/parser.py for Infoagent digest format
- [x] Task P1.2 — Create src/scorer.py
- [x] Task P1.3 — Implement main.py process command
- [x] Task P1.4 — Implement main.py review command
- [x] Task P1.5 — End-to-end test on real EML file
- [x] Task P1.6 — Create src/fetcher.py + main.py fetch command
- [ ] Task P1.7 — Completion check + merge to main

---

## Completion Checklist

- [ ] `python -m py_compile src/parser.py` — no errors
- [ ] `python -m py_compile src/scorer.py` — no errors
- [ ] `python -m py_compile src/fetcher.py` — no errors
- [ ] `python -m py_compile main.py` — no errors
- [ ] `python main.py fetch` — connects to Forpsi, reports new emails
- [ ] `python main.py process` — runs on inbox EML without crashing
- [ ] Scored results table shown with colours
- [ ] `python main.py review` — shows Rich table, score descending
- [ ] EML moved to data/processed/ after processing
- [ ] Running process twice on same EML: "Already processed"

---

## Task P1.5 — End-to-end test on real EML

**Status:** [ ]
**Files:** none — verification only. No code changes in this task.

**Important:** This task will likely reveal bugs. That is expected and good.
Fix any bug found before moving to P1.6. Never skip a failing test.

**Setup — before running:**
Make sure your Gemini API key is set in the environment:
```powershell
$env:GEMINI_API_KEY='your_key_here'
```
Confirm with:
```powershell
python -c "import os; print('KEY SET' if os.environ.get('GEMINI_API_KEY') else 'MISSING')"
```

**Step 1 — Verify syntax of all built files:**
```
python -m py_compile src/parser.py
python -m py_compile src/scorer.py
python -m py_compile main.py
```
All must produce no output (silence = success).

**Step 2 — Test the parser in isolation:**
Copy the real EML to inbox/ first:
```
copy "Suche__Infoagent_JiriVosta_260203.eml" inbox\
```
Then:
```
python -c "
from src.parser import parse_eml
from pathlib import Path
stubs = parse_eml(Path('inbox/Suche__Infoagent_JiriVosta_260203.eml'))
print(f'Found: {len(stubs)} jobs')
print(f'First: {stubs[0].title} | {stubs[0].company} | {stubs[0].location}')
print(f'Sample URL: {stubs[0].url[:80]}')
"
```
Expected: 50+ jobs found, sensible title/company/location, valid URL.

**Step 3 — Run process end-to-end:**
```
python main.py process
```
- Quick filter appears with ~57 jobs
- Skip at least 40 obvious misses (Elixir, Rust, Bangkok, Safety Engineer, etc.)
- Scoring runs on remaining jobs (~10-15)
- Results table appears with scores and colours

Watch for:
- Any Python exception (stack trace = bug, fix before continuing)
- Jobs with score=0 and reason="Could not fetch" — normal, some URLs block scrapers
- Jobs with score=0 and reason="Scoring failed" — potential API key issue

**Step 4 — Verify database:**
```
python -c "
from src.db import get_jobs, get_stats
stats = get_stats()
print(f'Total jobs: {stats[\"total\"]}')
print(f'By status: {stats[\"by_status\"]}')
jobs = get_jobs()
for j in jobs[:5]:
    print(f'  {j[\"score\"]}/10  {j[\"company\"][:25]}  {j[\"role_title\"][:35]}')
"
```
Expected: jobs in DB with varying scores, status=new.

**Step 5 — Verify EML moved:**
```
python -c "
from pathlib import Path
inbox = list(Path('inbox').glob('*.eml'))
processed = list(Path('data/processed').glob('*.eml'))
print(f'Inbox: {len(inbox)}, Processed: {len(processed)}')
"
```
Expected: Inbox 0, Processed 1.

**Step 6 — Test review command:**
```
python main.py review
```
- Rich table appears sorted by score
- Approve at least 2 jobs (type number, then 'a')
- Reject at least 2 jobs (type number, then 'r')
- 'q' to quit

**Step 7 — Verify review updated DB:**
```
python -c "
from src.db import get_jobs
approved = get_jobs(status='approved')
rejected = get_jobs(status='rejected')
print(f'Approved: {len(approved)}, Rejected: {len(rejected)}')
"
```
Expected: matches what you approved/rejected in Step 6.

**Step 8 — Test duplicate detection:**
```
copy "data\processed\Suche__Infoagent_JiriVosta_260203.eml" inbox\
python main.py process
```
Expected: "Already processed: Suche__Infoagent_JiriVosta_260203.eml" — no re-scoring.

**Bugs to fix before P1.6:**
If any step fails, fix the bug and re-run that step before continuing.
Common issues to expect:
- Encoding errors in parser → fix charset handling
- JSON parse error from AI → add better error message in scorer.py
- Rich table crashes on empty data → add empty-state guard in main.py
- API rate limit hit → add a 1-second sleep between scoring calls

**Acceptance Criteria:**
- All 8 steps complete without unhandled exceptions
- Jobs in DB with correct scores and metadata
- EML moved correctly after processing
- Duplicate detection works
- Review updates statuses correctly

---

## Task P1.6 — Create src/fetcher.py + main.py fetch command

**Status:** [x]
**Files:**
- `src/fetcher.py` (NEW)
- `main.py` (EXTEND — add fetch command)
- `.env.example` (EXTEND — add Forpsi IMAP vars)

**Context:**
Job digest emails arrive in Forpsi webmail (jiri@vosta.co.uk).
Gmail fetches from Forpsi via POP3 — but we connect directly to Forpsi IMAP,
which is simpler (no OAuth, no App Password, just email credentials).
The fetch command downloads unread Infoagent digests to inbox/ as .eml files,
then the existing process command handles them unchanged.

**Forpsi IMAP settings (confirmed from Forpsi documentation):**
```
Server:   imap.forpsi.com
Port:     993
Security: SSL/TLS
Username: full email address (from FORPSI_EMAIL env var)
Password: Forpsi email password (from FORPSI_PASSWORD env var)
```

**src/fetcher.py — public function:**

```python
def fetch_digests(
    inbox_dir: Path,
    processed_dir: Path,
    env: dict
) -> tuple[int, list[str]]:
    """
    Connect to Forpsi IMAP, download unread Infoagent digest emails.

    Returns (count_downloaded, list_of_saved_filenames).
    Raises EnvironmentError if required env vars are missing.
    Raises ConnectionError if IMAP connection fails.
    """
```

**Implementation rules:**

Connection:
```python
import imaplib
server   = env.get('FORPSI_IMAP_SERVER', 'imap.forpsi.com')
port     = int(env.get('FORPSI_IMAP_PORT', '993'))
username = env['FORPSI_EMAIL']      # raise KeyError → caught, EnvironmentError
password = env['FORPSI_PASSWORD']   # raise KeyError → caught, EnvironmentError

with imaplib.IMAP4_SSL(server, port) as imap:
    imap.login(username, password)
    imap.select('INBOX')
```

Search — both criteria must match:
```python
_, msg_ids = imap.search(None, 'UNSEEN', 'FROM "info@anzeigendaten.de"')
```

For each message:
1. `imap.fetch(msg_id, '(RFC822)')` → raw bytes
2. Parse just enough for filename:
   ```python
   import email as email_lib
   msg = email_lib.message_from_bytes(raw)
   date_str = msg.get('Date', '')[:16].strip()
   # Parse to YYYYMMDD, fallback to 'unknown'
   filename = f"infoagent_{date_yyyymmdd}_{msg_id.decode()}.eml"
   ```
3. Skip if already exists in `inbox_dir` OR `processed_dir`
4. Write raw bytes: `(inbox_dir / filename).write_bytes(raw)`
5. Mark as read: `imap.store(msg_id, '+FLAGS', '\\Seen')`
6. Append filename to results list

Error handling:
- Missing env var → `raise EnvironmentError(f"Missing env var: {var_name}\nAdd to .env: {var_name}=your_value")`
- IMAP login failure → `raise ConnectionError(f"Could not login to {server}:{port} — check FORPSI_EMAIL and FORPSI_PASSWORD")`
- Connection timeout → `raise ConnectionError(f"Could not connect to {server}:{port}")`
- Per-message failure → log warning, skip that message, continue

**main.py fetch command:**
```python
def cmd_fetch(args, profile):
    import os
    from src.fetcher import fetch_digests

    try:
        count, files = fetch_digests(
            inbox_dir=Path('inbox'),
            processed_dir=Path('data/processed'),
            env=os.environ
        )
    except EnvironmentError as e:
        console.print(f"[red]{e}[/red]")
        return
    except ConnectionError as e:
        console.print(f"[red]{e}[/red]")
        console.print("[yellow]Tip: place .eml files in inbox/ manually and run: python main.py process[/yellow]")
        return

    if count == 0:
        console.print("[yellow]No new job digests found.[/yellow]")
        console.print("Tip: check that Forpsi is receiving emails from info@anzeigendaten.de")
    else:
        console.print(f"[green]Downloaded {count} digest(s):[/green]")
        for f in files:
            console.print(f"  {f}")
        console.print("\nRun: python main.py process")
```

**.env.example additions:**
```
# Forpsi IMAP — for python main.py fetch
# Get these from your Forpsi account settings
FORPSI_IMAP_SERVER=imap.forpsi.com
FORPSI_IMAP_PORT=993
FORPSI_EMAIL=your_email@yourdomain.com
FORPSI_PASSWORD=your_forpsi_webmail_password
```

**Constraints:**
- `fetcher.py` uses stdlib only: `imaplib`, `email`, `os`, `pathlib`
- No DB calls in fetcher.py
- No AI calls in fetcher.py
- Missing env vars must produce helpful error message — never a bare KeyError

**Acceptance Criteria:**
- `python -m py_compile src/fetcher.py` — no errors
- `python -c "from src.fetcher import fetch_digests; print('OK')"` — prints OK
- `python main.py fetch` with missing env vars: clear error naming which var
- `python main.py fetch` with correct env vars and Forpsi credentials:
  downloads new digests OR prints "No new job digests found."
- Downloaded files appear in inbox/ as .eml files
- Already-processed files are not re-downloaded

---

## Task P1.7 — Completion check + merge to main

**Status:** [ ]
**Files:** `docs/MILESTONES.md` (status update only)

**Steps in order:**

1. Run the full Completion Checklist above — every item must pass.
   Show Jiri the output of each command.
   Stop if anything fails. Wait for Jiri's confirmation.

2. Update docs/MILESTONES.md:
   Change P1 status from "⏳ Active" to "✅ Done"

3. Commit:
   ```
   docs(p1): mark P1 complete in MILESTONES.md
   ```

4. Merge to main:
   ```
   git checkout main
   git merge feature/p1-parse-score --no-ff -m "feat(p1): merge Phase 1 parse and score"
   ```

5. Create P2 branch:
   ```
   git checkout -b feature/p2-backfill-report
   ```

6. Confirm:
   ```
   git branch --show-current
   git log --oneline -5
   ```
   Expected: on feature/p2-backfill-report, merge commit at top.

**Constraints:**
- NEVER merge without Jiri's explicit "ok to merge" in chat
- NEVER push without asking Jiri first

**Acceptance Criteria:**
- All checklist items pass
- MILESTONES.md shows P1 ✅ Done
- Currently on branch feature/p2-backfill-report

---

## Notes for Claude Code

### What was already built — do not rewrite
- src/parser.py — Infoagent digest parser, working
- src/scorer.py — AI scoring + location validation, working
- main.py — process (with quick filter) + review, working

### What P1.6 adds
- src/fetcher.py — new file, Forpsi IMAP only
- main.py fetch command — new command only, do not touch process or review

### Planned improvements (NOT in this phase)
These design improvements were discussed but are deferred until after P1 is merged:
- Remove quick filter (automate scoring of all location-valid jobs)
- Increase JD truncation from 5000 to 8000 chars
- Add [V]iew option in review command
- Add deterministic location pre-filter before AI calls
These belong in a future improvement task, not in P1.

### Hard rules
- fetcher.py: stdlib only, no DB, no AI
- parser.py, scorer.py: do not modify in P1.6 or P1.7
- main.py: add fetch command only, do not refactor existing commands