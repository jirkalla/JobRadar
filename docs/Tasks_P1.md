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

## Context — what P0 built, what P1 needs

P0 produced:
  src/db.py          — complete, all DB operations
  src/ai_client.py   — complete, provider abstraction
  src/parser.py      — EXISTS but wrong format (single-email parser)
                       Must be REPLACED in Task P1.1
  main.py            — CLI shell, commands print "not yet implemented"
  config/profile.yaml — filled in by Jiri
  config/prompts/    — score.txt and generate.txt

P1 builds on this to deliver:
  src/parser.py      — REWRITTEN for Infoagent digest format (57 jobs per email)
  src/scorer.py      — NEW: AI scoring using ai_client + profile
  main.py            — EXTENDED: process + review commands implemented

The EML format is a digest — one email contains 50-60 job listings
separated by ~~~ delimiters. Each block has title, location, URL,
company, source, date. The URL must be fetched to get the full JD.
See /docs/ARCHITECTURE.md section 4 for the exact format.

---

## Progress

- [x] Task P1.1 — Rewrite src/parser.py for Infoagent digest format
- [x] Task P1.2 — Create src/scorer.py
- [x] Task P1.3 — Implement main.py process command
- [x] Task P1.4 — Implement main.py review command
- [ ] Task P1.5 — End-to-end test on real EML file
- [ ] Task P1.6 — Completion check + merge to main

---

## Completion Checklist

- [ ] `python -m py_compile src/parser.py` — no errors
- [ ] `python -m py_compile src/scorer.py` — no errors
- [ ] `python -m py_compile main.py` — no errors
- [ ] `python main.py process` — runs on inbox EML without crashing
- [ ] Quick filter shows title + company + location for each job
- [ ] Kept jobs fetched from URL and scored — results in jobs table
- [ ] `python main.py review` — shows Rich table, score descending
- [ ] Location violations shown in red
- [ ] EML moved to data/processed/ after completion
- [ ] Running process twice on same EML skips already-processed jobs

---

## Task P1.1 — Rewrite src/parser.py for Infoagent digest format

**Status:** [x]
**Files:**
- `src/parser.py` (REWRITE — replaces the existing single-email version)

**Why rewrite:** The existing parser.py handles single-job emails.
The real EML format is a digest with 57 job listings per email,
separated by ~~~ delimiters. The entire parsing logic must change.

**What the new parser must do:**

1. Read an EML file (handles encoding: try UTF-8, fall back to latin-1)
2. Extract the plain text body
3. Detect Infoagent digest format: split on ~~~ delimiters,
   find blocks that contain both a URL and a "Quelle:" line
4. Parse each job block into a JobStub dataclass
5. Provide fetch_job_description(url) to retrieve the full JD from the URL

**JobStub dataclass** — must contain exactly these fields:
```python
@dataclass
class JobStub:
    title:     str
    company:   str
    location:  str
    url:       str
    source:    str       # e.g. "LinkedIn.de", "indeed.de"
    date_seen: str       # DD.MM.YYYY from Quelle line
    salary:    str | None
    raw_block: str       # original text block, for debugging
```

**Infoagent block format** (confirmed from real EML):
```
Senior Power BI Engineer (m/f/d)
in Berlin
https://db.advertsdata.com/matching/matching.cfm?id=...
AroundHome GmbH, Wittestr. 30, 13509 Berlin
Kontakt: Max Boikov, timothy@...

Quelle: Xing.de, 02.02.2026, 699 &euro;
```

Parsing rules for each block:
- Title: all lines before the "in {location}" line, joined with space
  Strip gender suffixes: (m/f/d), (m/w/d), (f/m/x), (m/f/x)
- Location: line starting with "in " — extract city after "in "
  Special case: "Hybrides Arbeiten in {city}" → "{city} (Hybrid)"
  Special case: "Homeoffice in {city}" → "{city} (Remote)"
- URL: line starting with "https://"
- Company: line after URL, split on first comma, take left side only
- Quelle line: "Quelle: {source}, {date}, {salary}"
  Salary: null if value is "0" or "0 €" or "0 &euro;"
  Decode &euro; → €

**fetch_job_description(url, timeout=10) → str:**
- Uses stdlib urllib.request only — no requests library
- User-Agent header: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
- Returns plain text of the fetched page (strip HTML)
- Truncate to 5000 chars maximum
- Return empty string on ANY exception — never raise
  (failed fetch handled gracefully by scorer)

**Other functions to keep:**
- scan_inbox(inbox_dir: Path) → list[Path]
  Returns sorted list of .eml files in inbox/
- _html_to_text(html: str) → str  (internal helper, already exists)
- _decode_header(value: str) → str  (internal helper, already exists)

**Constraints:**
- stdlib only: email, re, urllib.request, dataclasses, pathlib
- No requests, no BeautifulSoup
- parse_eml() MUST return a list of JobStub objects — not a dict
  (this breaks the old interface deliberately — scorer uses the new one)

**Acceptance Criteria:**
- `python -m py_compile src/parser.py` — no errors
- Run this test:
  ```
  python -c "
  from src.parser import parse_eml, scan_inbox
  from pathlib import Path
  stubs = parse_eml(Path('inbox/Suche__Infoagent_JiriVosta_260203.eml'))
  print(f'Found {len(stubs)} jobs')
  print(f'First: {stubs[0].title} | {stubs[0].company} | {stubs[0].location}')
  print(f'URL: {stubs[0].url[:60]}')
  "
  ```
  Expected: prints "Found 57 jobs" (or similar count), first job details, URL

---

## Task P1.2 — Create src/scorer.py

**Status:** [x]
**Files:**
- `src/scorer.py` (NEW)

**NOTE — salary field is a placement fee, not candidate salary:**
The `salary` field in JobStub (and `salary_mentioned` in the DB) contains the
recruiter placement fee (Vermittlungshonorar) from the Quelle line — not the
candidate's compensation. Before completing this task, update config/prompts/score.txt
to add this note so the AI interprets it correctly:

  "Note: salary_mentioned is the recruiter placement fee (Vermittlungshonorar),
  not the candidate's salary. Treat it as context only — do not use it to assess
  compensation."

Commit the prompt change separately: prompt(p1): clarify salary_mentioned is placement fee

**What scorer.py does:**
1. Reads config/profile.yaml to build the scoring context
2. Reads config/prompts/score.txt prompt template
3. For each JobStub: fetches the full JD via parser.fetch_job_description()
4. Builds the prompt by substituting profile values into the template
5. Calls ai_client.complete_json() to get the score
6. Returns a scored result dict ready for db.insert_job()

**Public functions:**

```python
def score_job(
    stub: JobStub,
    profile: dict,
    client,           # ai_client client object
    prompt_template: str
) -> dict:
```
Returns a dict with all fields needed for db.insert_job():
  company, role_title, location, remote_type, language,
  relevance_score, score_reason, location_ok, location_reason,
  strong_matches (JSON string), concerns (JSON string),
  tech_stack (JSON string), salary_mentioned,
  jd_text (the fetched text), source_eml, status

If fetch returns empty string:
  Set jd_text = ""
  Set score_reason = "Could not fetch job description"
  Set relevance_score = 0
  Set recommended = False
  Do not call AI — return immediately

If AI call fails or returns invalid JSON:
  Set relevance_score = 0
  Set score_reason = f"Scoring failed: {error message}"
  Log the error, do not raise

```python
def build_score_prompt(
    stub: JobStub,
    jd_text: str,
    profile: dict,
    template: str
) -> str:
```
Substitutes these placeholders in the template:
  {name}, {location}, {skills_expert}, {skills_solid},
  {skills_learning}, {skills_moved_away}, {role_types},
  {roles_avoid}, {hybrid_cities}, {voice}, {job_text}

Lists converted to comma-separated strings for prompt readability.

```python
def check_location(
    result: dict,
    profile: dict
) -> tuple[bool, str]:
```
Applies profile.yaml restriction rules:
  - remote_type == "remote" → always OK
  - remote_type == "hybrid" and location city in hybrid_cities → OK
  - remote_type == "onsite" and location city in hybrid_cities → OK
  - anything else → NOT OK, return reason string
Returns (location_ok: bool, location_reason: str)

**Constraints:**
- No DB calls in scorer.py — returns dict, caller writes to DB
- No direct AI SDK imports — only through ai_client
- Read profile.yaml at call time — never cache it
- All list fields (strong_matches, concerns, tech_stack) stored as
  JSON strings for SQLite compatibility

**Acceptance Criteria:**
- `python -m py_compile src/scorer.py` — no errors
- Import test:
  ```
  python -c "from src.scorer import score_job, build_score_prompt; print('OK')"
  ```
- No DB calls anywhere in scorer.py (grep check)

---

## Task P1.3 — Implement main.py process command

**Status:** [x]
**Files:**
- `main.py` (EXTEND — replace the "Coming in Phase 1" stub for process)

**What process command does:**
1. Scan inbox/ for .eml files
2. For each EML: parse into JobStub list
3. Show quick filter table (Rich) — user marks obvious skips
4. For kept jobs: fetch JD + score with AI
5. Write results to DB
6. Move EML to data/processed/
7. Show summary: N scored, N skipped, N failed

**Quick filter UI (Rich table):**
Columns: #, Title (truncated to 45 chars), Company, Location, Date
User input per job: ENTER = keep, 's' = skip, 'r' = reject
Show count at top: "Found 57 jobs — mark obvious skips before scoring"
After filter: "Keeping 12 jobs. Fetching and scoring... (this takes ~2 min)"

**Progress during scoring (Rich):**
Show a progress bar while fetching + scoring:
  "[3/12] Scoring: Senior Power BI Engineer — AroundHome..."

**After scoring:**
Show Rich table of results, score descending:
  Columns: Score, Title, Company, Location, Remote, Salary, Reason
  Score colour: green >=7, yellow 5-6, red <=4
  Location violation: show "NO-LOC" badge in red in Location column

**Duplicate handling:**
Before scoring, call db.job_exists_for_eml(eml_filename)
If True: skip the entire EML, print "Already processed: {filename}"

**load_profile() helper** — already in main.py from P0.
Use it: profile = load_profile()

**AI client setup:**
```python
from src.ai_client import get_client, complete_json
client = get_client(profile)
```

**Constraints:**
- Rich for all terminal output — no plain print() for tables
- process command calls parser, scorer, db — never directly
- Move EML only after all jobs processed successfully
- If API key missing: print the helpful error from ai_client, exit cleanly

**Acceptance Criteria:**
- `python main.py process` with no EML in inbox: prints "No .eml files found in inbox/"
- `python main.py process` with EML: shows quick filter table
- After filter + scoring: results table shown with colours
- EML moved to data/processed/ after completion
- `python main.py process` again: prints "Already processed: {filename}"

---

## Task P1.4 — Implement main.py review command

**Status:** [x]
**Files:**
- `main.py` (EXTEND — replace the "Coming in Phase 1" stub for review)

**What review command does:**
Shows all jobs with status='new' or status='reviewed', ordered by score desc.
User can approve, reject, or skip each one.

**Display (Rich table):**
  Columns: Score, Title, Company, Location, Remote, Salary, Status
  Below table: show count "12 jobs to review"

**Per-job actions:**
After showing the table, prompt:
  "Enter job number to act on (or 'q' to quit): "
  Then: "[A]pprove / [R]eject / [S]kip / [N]otes: "

Actions:
  A → update status to 'approved', log_action('approved')
  R → update status to 'rejected', log_action('rejected')
  S → no change, move to next
  N → prompt for notes text, save to jobs.notes, log_action('noted')

After action: refresh and redisplay the table.
'q' exits review mode.

**Filter flags (argparse):**
  --all     Show all statuses including rejected
  --min N   Show only jobs with score >= N (default: profile min_score_to_show)

**Constraints:**
- Rich for all output
- All DB writes through db.py functions
- Never show jobs with status='applied' or later in default view

**Acceptance Criteria:**
- `python main.py review` with no jobs: prints "No jobs to review."
- `python main.py review` with jobs: Rich table shown, sorted by score
- Approve/reject/skip all update DB correctly
- `python main.py review --min 7` shows only high-scoring jobs

---

## Task P1.5 — End-to-end test on real EML

**Status:** [ ]
**Files:** none — this is a verification task only

**Description:**
Run the full pipeline on the real Infoagent EML file and verify
every step works correctly. This task produces no code changes —
only runs commands and checks results.

**Steps:**

1. Copy the real EML to inbox/:
   ```
   copy "Suche__Infoagent_JiriVosta_260203.eml" inbox\
   ```

2. Run process:
   ```
   python main.py process
   ```
   - Confirm quick filter table appears with ~57 jobs
   - Skip at least 40 obvious misses (wrong tech, wrong location, etc.)
   - Let it score the remaining jobs
   - Confirm scored results table appears

3. Check the database:
   ```
   python -c "
   from src.db import get_jobs, get_stats
   jobs = get_jobs()
   stats = get_stats()
   print(f'Jobs in DB: {stats[\"total\"]}')
   print(f'By status: {stats[\"by_status\"]}')
   for j in jobs[:5]:
       print(f'  {j[\"score\"]}/10  {j[\"company\"]}  {j[\"role_title\"]}')
   "
   ```

4. Verify EML moved:
   ```
   python -c "
   from pathlib import Path
   processed = list(Path('data/processed').glob('*.eml'))
   inbox = list(Path('inbox').glob('*.eml'))
   print(f'Processed: {len(processed)}, Inbox: {len(inbox)}')
   "
   ```
   Expected: Processed: 1, Inbox: 0

5. Run review:
   ```
   python main.py review
   ```
   - Approve at least 2 jobs
   - Reject at least 2 jobs
   - Confirm DB status updated

6. Run process again on same EML:
   ```
   copy "data\processed\Suche__Infoagent_JiriVosta_260203.eml" inbox\
   python main.py process
   ```
   Expected: "Already processed: Suche__Infoagent_JiriVosta_260203.eml"

**Acceptance Criteria:**
- All 6 steps complete without errors
- Jobs visible in DB with correct scores and metadata
- EML correctly moved after processing
- Duplicate detection works
- Review command updates statuses correctly

---

## Task P1.6 — Completion check + merge to main

**Status:** [ ]
**Files:** `docs/MILESTONES.md` (status update only)

**Description:**
Run the full completion checklist, verify everything passes,
merge the P1 branch into main, and create the P2 branch.
This is always the last task of every phase.

**Steps in order:**

1. Run the full Completion Checklist above — every item must pass.
   Show Jiri the output of each command. Stop if anything fails.
   Wait for Jiri's confirmation before proceeding.

2. Update docs/MILESTONES.md:
   Change P1 status from "⏳ Active" to "✅ Done"

3. Commit the status update:
   ```
   docs(p1): mark P1 complete in MILESTONES.md
   ```

4. Merge to main:
   ```
   git checkout main
   git merge feature/p1-parse-score --no-ff -m "feat(p1): merge Phase 1 parse and score"
   ```

5. Create the P2 branch:
   ```
   git checkout -b feature/p2-backfill-report
   ```

6. Confirm the result:
   ```
   git branch
   git log --oneline -5
   ```
   Expected: currently on feature/p2-backfill-report,
   log shows merge commit at top

**Constraints:**
- NEVER push to remote without asking Jiri first
- NEVER merge without Jiri's explicit confirmation in chat
- Only proceed to step 4 after Jiri says "ok to merge" or similar

**Acceptance Criteria:**
- All completion checklist items pass
- MILESTONES.md shows P1 as ✅ Done
- `git log --oneline` shows merge commit: "feat(p1): merge Phase 1 parse and score"
- Currently on branch feature/p2-backfill-report
- `git branch` shows main, feature/p0-scaffold, feature/p1-parse-score,
  and feature/p2-backfill-report

---

## Notes for Claude Code

### Key design decisions
- parser.py returns List[JobStub] — not a dict — breaking change from P0 stub
- scorer.py never writes to DB — only returns dicts
- main.py orchestrates: parse → filter → fetch → score → write → display
- All Rich output in main.py — never in src/ modules

### Reference implementations
- DB write pattern: src/db.py insert_job()
- AI call pattern: src/ai_client.py complete_json()
- Profile reading: load_profile() in main.py

### Hard rules
- src/parser.py — no DB calls, no AI calls
- src/scorer.py — no DB calls, calls ai_client only
- main.py — no business logic, orchestrates only
- Never import requests — use urllib.request (already in stdlib)