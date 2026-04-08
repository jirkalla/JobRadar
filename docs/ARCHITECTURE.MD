# Architecture — JobRadar
## v1.2 | March 2026

======================================================================
1. SYSTEM OVERVIEW
======================================================================

JobRadar is a personal Python tool with two entry points:
- CLI (main.py) — fetch emails, process jobs, review, generate, report
- Web UI (ui/main_ui.py, Phase 5) — browser dashboard for history and management

Both entry points share the same src/ modules and the same SQLite database.
No data is duplicated. The web UI adds no new business logic — it exposes
what the CLI already does via HTTP routes.

======================================================================
2. FOLDER STRUCTURE
======================================================================

JobRadar/
├── main.py                   CLI entry point — fetch, process, review, generate, report
├── backfill.py               Manual entry wizard for past applications
├── setup.py                  First-run: creates folders, installs deps, checks config
├── requirements.txt
├── .env                      Secrets — gitignored, never committed
├── .env.example              Template with placeholder values — committed
│
├── config/
│   ├── profile.yaml          Personal data, skills, restrictions, AI config, voice
│   ├── profile.yaml.example  Placeholder template — committed
│   └── prompts/
│       ├── score.txt         Scoring prompt template (user-editable)
│       └── generate.txt      Generation prompt template (user-editable)
│
├── src/
│   ├── fetcher.py            Forpsi IMAP — download job digest emails to inbox/
│   ├── ai_client.py          AI provider abstraction (Gemini / Claude / OpenAI)
│   ├── parser.py             EML parsing — Infoagent digest format
│   ├── scorer.py             AI scoring + location validation
│   ├── generator.py          CV + cover letter generation — calls ai_client
│   ├── db.py                 All SQLite operations
│   └── report.py             Agency report export (PDF + CSV)
│
├── ui/
│   ├── main_ui.py            FastAPI application (Phase 5)
│   └── templates/            Jinja2 HTML templates (Phase 5)
│
├── examples/
│   ├── cv_base.docx          Master CV template
│   ├── letters/              Rated cover letters (style examples)
│   └── ratings.json          Letter ratings 1-5
│
├── inbox/                    EML files waiting to be processed
├── data/
│   ├── tracker.db            SQLite database
│   └── processed/            EML files moved here after processing
│
├── output/                   Generated documents
│   ├── YYYY-MM-DD_company-role/
│   │   ├── cv_YYYY-MM-DD_company.docx
│   │   ├── cl_YYYY-MM-DD_company.docx
│   │   ├── jd_snapshot.txt   Job description at time of application
│   │   └── score.json        AI score and reasoning
│   └── reports/              Agency export files
│
└── docs/
    ├── AI_INSTRUCTIONS.md
    ├── ARCHITECTURE.md       (this file)
    ├── MILESTONES.md
    └── Tasks_P*.md           Active milestone task file

======================================================================
3. LAYER RULES — STRICT
======================================================================

Each src/ file has one responsibility. Cross-layer calls are forbidden
except as listed here:

  main.py
    → fetcher.py      (download emails from Forpsi IMAP)
    → parser.py       (parse inbox EML files)
    → scorer.py       (AI score + location validation)
    → db.py           (read/write jobs, activity, documents)
    → generator.py    (generate CV + cover letter)
    → report.py       (export agency report)

  backfill.py
    → db.py only

  fetcher.py
    → no src/ imports — stdlib imaplib, email, os, pathlib only

  scorer.py
    → ai_client.py    (complete_json)
    → reads config/profile.yaml and config/prompts/score.txt

  generator.py
    → ai_client.py    (complete)
    → db.py           (get_example_letters)
    → reads config/profile.yaml and config/prompts/generate.txt

  parser.py
    → no src/ imports — stdlib + pypdf only

  db.py
    → no src/ imports — stdlib sqlite3 only

  report.py
    → db.py only

  ai_client.py
    → no src/ imports — provider SDKs only

FORBIDDEN:
  - fetcher.py calling db.py or ai_client.py
  - parser.py calling db.py or ai_client.py
  - db.py calling anything in src/
  - ai_client.py containing any business logic
  - main.py containing business logic (it orchestrates, never decides)
  - scorer.py calling parser.py or fetcher.py

======================================================================
4. PROCESS PIPELINE — COMPLETE FLOW
======================================================================

NOTE ON CURRENT STATE vs PLANNED IMPROVEMENTS:
  Built (P1):       quick filter before fetching, location validated by AI
                    via scoring prompt in scorer.py, 5000 char JD truncation,
                    silent skip on failed URL fetch
  Planned (post-P1): remove quick filter, move location to deterministic
                    Python pre-filter before AI call, increase to 8000 chars,
                    add paste-on-fail prompt for failed URL fetches

Tuesday workflow:
  python main.py fetch      (~5 seconds)   — added in P1.6
  python main.py process    (~2 minutes)
  python main.py review     (~10 minutes)

Detailed pipeline (as built in P1):

  FETCH (P1.6)
  ├── Connect to Forpsi IMAP (imap.forpsi.com:993 SSL)
  ├── Search INBOX: UNSEEN + FROM "info@anzeigendaten.de"
  ├── Download each match as raw RFC 2822 bytes
  ├── Save to inbox/{slug}_{date}.eml
  ├── Skip if already exists in inbox/ or data/processed/
  ├── Mark as read on server
  └── Report: "Downloaded N new digests"

  PROCESS (built in P1.3)
  ├── Scan inbox/ for .eml files
  ├── Skip any EML already in jobs table (duplicate check by filename)
  ├── For each EML: parse → extract ~57 JobStubs
  │     JobStub: title, company, location, url, source, date, salary
  │
  ├── QUICK FILTER (user-driven, before URL fetching)
  │     Show Rich table: title, company, location for each stub
  │     User marks obvious skips — reduces 57 to ~10-15
  │
  ├── FETCH JOB DESCRIPTIONS (kept stubs only)
  │     urllib fetches redirect target → strip HTML → max 5000 chars
  │     Failed fetch: job recorded with score=0, reason="Could not fetch"
  │
  ├── AI SCORING (includes location validation)
  │     prompt = jd_text + profile skills + restrictions + voice
  │     Gemini returns JSON: score 1-10, reason, location_ok,
  │                          matches, concerns, tech_stack, salary
  │
  ├── SAVE to SQLite (jobs + activity_log)
  │
  ├── SHOW RANKED TABLE
  │     Score colour: green ≥7, yellow 5-6, red ≤4
  │     Location violations flagged with NO-LOC badge
  │
  └── MOVE EML to data/processed/

  REVIEW (built in P1.4)
  ├── Show jobs with status=new, sorted by score desc
  ├── Default: score ≥ profile.preferences.min_score_to_show
  ├── --all flag to show all statuses
  ├── --min N flag to override score threshold
  └── Per job: [A]pprove / [R]eject / [S]kip / [N]otes

======================================================================
5. EML FORMAT — INFOAGENT DIGEST
======================================================================

The primary email format is the Infoagent job alert digest.
One email contains 50-60 job listings, separated by ~~~ delimiters.

Each job block contains:
  Line 1-2:   Job title (may wrap to second line)
  Line 3:     "in {location}" — may include "Hybrides Arbeiten in {city}"
  Line 4:     Tracking URL (https://db.advertsdata.com/matching/...)
  Line 5:     Company name, street address
  Line 6+:    Optional contact name and email
  Last line:  "Quelle: {source}, {DD.MM.YYYY}, {salary} €"

Location handling — as built in P1:
  The built JobStub has a raw location string (e.g. "Hybrides Arbeiten in Berlin").
  scorer.py extracts remote_type and city from this string and validates
  against profile.yaml rules. This is done inside scorer.py, not parser.py.

  Location string examples and their meaning:
    "Homeoffice"                     → remote
    "Homeoffice in Berlin"           → remote
    "Remote" / "Remote/Europe"       → remote
    "Hybrides Arbeiten in {city}"    → hybrid, city extracted
    "{city}" (no hybrid/remote)      → onsite, city extracted
    anything unrecognised            → unclear

  Location rules applied in scorer.py:
    remote                                          → always OK
    hybrid  AND city in profile.hybrid_cities       → OK
    onsite  AND city in profile.hybrid_cities       → OK
    onsite  AND city NOT in profile.hybrid_cities   → flag as location issue
    unclear                                         → AI decides via scoring prompt

  NOTE: In built P1 code, location validation is part of the AI scoring prompt.
  Planned improvement: move to deterministic Python code that runs BEFORE
  the AI call, rejecting hard misses without spending an API call.

======================================================================
6. DATABASE SCHEMA
======================================================================

--- jobs ---
id                 TEXT PRIMARY KEY  -- {company-slug}-{role-slug}-{YYYYMMDD}
company            TEXT NOT NULL
role_title         TEXT NOT NULL
location           TEXT
remote_type        TEXT              -- remote | hybrid | onsite | unclear
language           TEXT DEFAULT 'en'
score              INTEGER           -- 1-10 from AI
score_reason       TEXT
status             TEXT DEFAULT 'new'
source_eml         TEXT
jd_text            TEXT
tech_stack         TEXT              -- JSON array
salary             TEXT
strong_matches     TEXT              -- JSON array
concerns           TEXT              -- JSON array
notes              TEXT
created_at         TEXT NOT NULL
updated_at         TEXT NOT NULL

Job status lifecycle:
  new → reviewed → approved → applied → responded → closed
                ↘ rejected

--- activity_log ---  (APPEND ONLY — never UPDATE or DELETE)
id       INTEGER PRIMARY KEY AUTOINCREMENT
job_id   TEXT NOT NULL
action   TEXT NOT NULL
detail   TEXT
ts       TEXT NOT NULL
source   TEXT DEFAULT 'system'   -- system | manual

--- documents ---
id             INTEGER PRIMARY KEY AUTOINCREMENT
job_id         TEXT NOT NULL
doc_type       TEXT NOT NULL      -- cv | cover_letter
path           TEXT NOT NULL
version        INTEGER DEFAULT 1
rating         INTEGER            -- 1-5
use_as_example INTEGER DEFAULT 0  -- 1 when rating >= 4
created_at     TEXT NOT NULL

--- outcomes ---
id         INTEGER PRIMARY KEY AUTOINCREMENT
job_id     TEXT NOT NULL
reply_type TEXT        -- no_reply | rejection | positive | interview | offer
reply_date TEXT
notes      TEXT
created_at TEXT NOT NULL

======================================================================
7. AI ABSTRACTION
======================================================================

Single interface in src/ai_client.py:

  get_client(config: dict) → client object
  complete(client, prompt: str) → str
  complete_json(client, prompt: str) → dict

Provider set in config/profile.yaml:
  ai:
    provider: gemini
    model: gemini-3-flash
    api_key_env: GEMINI_API_KEY

Switching provider = change two lines in profile.yaml. Zero code changes.
Supported: gemini | claude | openai

======================================================================
8. ENVIRONMENT VARIABLES
======================================================================

All secrets in .env — gitignored, never committed, never hardcoded.

  # AI provider
  GEMINI_API_KEY=your_gemini_api_key_here

  # Forpsi IMAP (for python main.py fetch)
  FORPSI_IMAP_SERVER=imap.forpsi.com
  FORPSI_IMAP_PORT=993
  FORPSI_EMAIL=your_email@yourdomain.com
  FORPSI_PASSWORD=your_forpsi_email_password

.env.example contains all keys with placeholder values — committed.
If any required env var is missing the command fails with a clear error
showing exactly which variable to set and how (Windows + PowerShell).

======================================================================
9. OUTPUT FILE NAMING
======================================================================

Generated documents:
  output/{YYYY-MM-DD}_{company-slug}_{role-slug}/
    cv_{YYYY-MM-DD}_{company-slug}.docx
    cl_{YYYY-MM-DD}_{company-slug}.docx
    jd_snapshot.txt
    score.json

Agency reports:
  output/reports/agency_{YYYY-MM-DD}_{date-from}_to_{date-to}.pdf
  output/reports/agency_{YYYY-MM-DD}_{date-from}_to_{date-to}.csv

======================================================================
10. CLI COMMANDS
======================================================================

python main.py fetch                Download new digests from Forpsi IMAP → inbox/
python main.py process              Parse inbox → quick filter → fetch JDs → AI score
python main.py review               Ranked list → approve / reject / skip
python main.py generate [--job-id]  Generate CV + cover letter for approved jobs
python main.py status               Update job status (applied, responded, etc.)
python main.py report               Export agency report for a date range

python backfill.py                  Interactive wizard for past applications

======================================================================
11. WEB UI (PHASE 5)
======================================================================

Framework: FastAPI + Jinja2 templates
Start:     python -m uvicorn ui.main_ui:app --reload
Port:      8000 (local only — never exposed publicly)

Routes:
  GET  /                    Dashboard — stats, recent activity
  GET  /jobs                Job list with filters
  GET  /jobs/{id}           Job detail
  POST /jobs/{id}/status    Update status
  GET  /profile             Profile editor
  POST /profile             Save profile changes
  GET  /history             Full activity log
  GET  /report              Agency report generator

Bootstrap 5 from static/ — no CDN.
No business logic in ui/main_ui.py — routing and templates only.

======================================================================
END OF ARCHITECTURE
======================================================================