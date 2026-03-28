# Architecture — job-tracker
## v1.0 | March 2026

======================================================================
1. SYSTEM OVERVIEW
======================================================================

job-tracker is a personal Python tool with two entry points:
- CLI (main.py) — daily job processing, review, generation, reporting
- Web UI (ui/main_ui.py, Phase 5) — browser dashboard for history and management

Both entry points share the same src/ modules and the same SQLite database.
No data is duplicated. The web UI adds no new business logic — it exposes
what the CLI already does via HTTP routes.

======================================================================
2. FOLDER STRUCTURE
======================================================================

job-tracker/
├── main.py                   CLI entry point — process, review, generate, report
├── backfill.py               Manual entry wizard for past applications
├── setup.py                  First-run: creates folders, installs deps, checks config
├── requirements.txt
├── .env.example              Template — actual .env is gitignored
│
├── config/
│   ├── profile.yaml          Personal data, skills, restrictions, AI config, voice
│   └── prompts/
│       ├── score.txt         Scoring prompt template (user-editable)
│       └── generate.txt      Generation prompt template (user-editable)
│
├── src/
│   ├── ai_client.py          AI provider abstraction (Gemini / Claude / OpenAI)
│   ├── parser.py             EML parsing — digest format + single job emails
│   ├── scorer.py             AI scoring logic — reads profile, calls ai_client
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
├── inbox/                    Drop .eml files here before running process
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
    └── Tasks_M*.md           Active milestone task file

======================================================================
3. LAYER RULES — STRICT
======================================================================

Each src/ file has one responsibility. Cross-layer calls are forbidden
except as listed here:

  main.py
    → parser.py       (parse inbox)
    → scorer.py       (score job stubs)
    → db.py           (read/write jobs, activity, documents)
    → generator.py    (generate CV + cover letter)
    → report.py       (export agency report)

  backfill.py
    → db.py only

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
  - parser.py calling db.py or ai_client.py
  - db.py calling anything in src/
  - ai_client.py containing any business logic
  - main.py containing business logic (it orchestrates, never decides)

======================================================================
4. EML FORMAT — INFOAGENT DIGEST
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

The tracking URL does NOT contain the job description.
The system must follow the URL and fetch the full JD from the target page.

Parser output: list of JobStub objects (title, company, location, url, source, date)
Full JD text: fetched separately by scorer.py before calling AI

======================================================================
5. DATABASE SCHEMA
======================================================================

--- jobs ---
id           TEXT PRIMARY KEY     -- {company-slug}-{role-slug}-{YYYYMMDD}
company      TEXT NOT NULL
role_title   TEXT NOT NULL
location     TEXT
remote_type  TEXT                 -- remote | hybrid | onsite | unclear
language     TEXT DEFAULT 'en'   -- de | en
score        INTEGER              -- 1-10 from AI
score_reason TEXT
status       TEXT DEFAULT 'new'  -- see lifecycle below
source_eml   TEXT                 -- original EML filename
jd_text      TEXT                 -- full job description at time of scoring
tech_stack   TEXT                 -- JSON array
salary       TEXT
strong_matches TEXT               -- JSON array
concerns     TEXT                 -- JSON array
notes        TEXT
created_at   TEXT NOT NULL        -- UTC ISO
updated_at   TEXT NOT NULL        -- UTC ISO

Job status lifecycle:
  new → reviewed → approved → applied → responded → closed
                ↘ rejected (logged, never deleted)

--- activity_log ---  (APPEND ONLY — never UPDATE or DELETE)
id       INTEGER PRIMARY KEY AUTOINCREMENT
job_id   TEXT NOT NULL
action   TEXT NOT NULL    -- scored | approved | rejected | applied | responded | etc.
detail   TEXT
ts       TEXT NOT NULL    -- UTC ISO
source   TEXT DEFAULT 'system'   -- system | manual (backfill entries)

--- documents ---
id           INTEGER PRIMARY KEY AUTOINCREMENT
job_id       TEXT NOT NULL
doc_type     TEXT NOT NULL    -- cv | cover_letter
path         TEXT NOT NULL
version      INTEGER DEFAULT 1
rating       INTEGER          -- 1-5, set by user after sending
use_as_example INTEGER DEFAULT 0   -- 1 when rating >= 4
created_at   TEXT NOT NULL

--- outcomes ---
id           INTEGER PRIMARY KEY AUTOINCREMENT
job_id       TEXT NOT NULL
reply_type   TEXT             -- no_reply | rejection | positive | interview | offer
reply_date   TEXT
notes        TEXT
created_at   TEXT NOT NULL

======================================================================
6. AI ABSTRACTION
======================================================================

Single interface in src/ai_client.py:

  get_client(config: dict) → client object
  complete(client, prompt: str) → str
  complete_json(client, prompt: str) → dict

Provider is set in config/profile.yaml:
  ai:
    provider: gemini          # gemini | claude | openai
    model: gemini-1.5-flash
    api_key_env: GEMINI_API_KEY

Switching provider = change two lines in profile.yaml. Zero code changes.

======================================================================
7. OUTPUT FILE NAMING
======================================================================

Generated documents saved to:
  output/{YYYY-MM-DD}_{company-slug}_{role-slug}/
    cv_{YYYY-MM-DD}_{company-slug}.docx
    cl_{YYYY-MM-DD}_{company-slug}.docx
    jd_snapshot.txt
    score.json

Agency reports saved to:
  output/reports/agency_{YYYY-MM-DD}_{date-from}_to_{date-to}.pdf
  output/reports/agency_{YYYY-MM-DD}_{date-from}_to_{date-to}.csv

======================================================================
8. CLI COMMANDS
======================================================================

python main.py process              Parse inbox → quick filter → fetch JDs → score
python main.py review               Show ranked list → approve / reject / skip
python main.py generate [--job-id]  Generate CV + cover letter for approved jobs
python main.py status               Update job status (applied, responded, etc.)
python main.py report               Export agency report for a date range

python backfill.py                  Interactive wizard for past applications

======================================================================
9. WEB UI (PHASE 5)
======================================================================

Framework: FastAPI + Jinja2 templates
Start:     python -m uvicorn ui.main_ui:app --reload
Port:      8000 (local only — never exposed publicly)

Routes mirror CLI commands:
  GET  /                    Dashboard — stats, recent activity
  GET  /jobs                Job list with filters
  GET  /jobs/{id}           Job detail
  POST /jobs/{id}/status    Update status
  GET  /profile             Profile editor
  POST /profile             Save profile changes
  GET  /history             Full activity log
  GET  /report              Agency report generator

UI uses Bootstrap 5 loaded from static/ — no CDN dependency.
All FastAPI routes call the same src/ functions as the CLI.
No business logic lives in ui/main_ui.py — only routing and template rendering.

======================================================================
END OF ARCHITECTURE
======================================================================