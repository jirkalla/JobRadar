# Tasks — Phase 0: Scaffold
# job-tracker | Milestone: P0 — Scaffold
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Do NOT implement anything outside this file
# - Do NOT start P1 tasks

---

## Progress

- [x] Task 00 — Git init + .gitignore
- [x] Task 01 — requirements.txt
- [x] Task 02 — setup.py
- [x] Task 03 — src/db.py (database init + all operations)
- [ ] Task 04 — src/ai_client.py (provider abstraction)
- [ ] Task 05 — config/profile.yaml (pre-filled with Jiri's real profile)
- [ ] Task 06 — config/prompts/score.txt
- [ ] Task 07 — config/prompts/generate.txt
- [ ] Task 08 — main.py (CLI shell — commands defined, not yet implemented)
- [ ] Task 09 — copy example letters + CV to examples/

---

## Completion Checklist

- [ ] `git status` — clean working tree, on branch feature/p0-scaffold
- [ ] `git log --oneline` — shows one commit per completed task
- [ ] `pip install -r requirements.txt` — no errors
- [ ] `python setup.py` — prints success, all folders created, DB initialized
- [ ] `python main.py --help` — shows all 5 commands without error
- [ ] `python -c "from src.db import init_db; init_db(); print('DB OK')"` — prints DB OK
- [ ] `python -c "from src.ai_client import get_client; print('AI OK')"` — prints AI OK
- [ ] `data/tracker.db` exists and contains 4 tables
- [ ] `config/profile.yaml` contains Jiri's name, real skills, voice document
- [ ] `config/profile.yaml` is NOT shown in `git status` (gitignored)
- [ ] `examples/letters/` contains 3 cover letter files (copied from uploads)
- [ ] No secrets in any committed file

---

## Task 00 — Git init + .gitignore

**Status:** [x]
**Files:** `.gitignore`, `README.md`

**Description:**
Initialize the Git repository, create .gitignore, create feature branch,
create a minimal README.md. This is the very first action — nothing else
is committed until this task is complete.

Steps in order:
1. `git init`
2. `git checkout -b feature/p0-scaffold`
3. Create `.gitignore` with the full content from AI_INSTRUCTIONS.md section 12
4. Create `README.md` with minimal content (see below)
5. `git add .gitignore README.md`
6. `git commit -m "chore(p0): initialize repository with .gitignore and README"`

README.md content:
```markdown
# JobRadar

Personal job application tracker for Jiri Vosta.

Parses job alert digest emails, scores listings with AI,
generates tailored CVs and cover letters, tracks all activity
for unemployment agency reporting.

## Setup

```bash
python setup.py
```

## Usage

```bash
python main.py --help
```

## Docs

See /docs for architecture, milestones, and task files.
```

**Constraints:**
- `git init` must run before any other file is created
- Feature branch created immediately after init — never commit to main directly
- .gitignore must be committed before any other files so nothing is
  accidentally staged that should be ignored

**Acceptance Criteria:**
- `git status` shows clean working tree on branch feature/p0-scaffold
- `git log --oneline` shows exactly one commit
- `cat .gitignore` shows config/profile.yaml and data/tracker.db listed
- `echo "test" > config/profile.yaml && git status` shows profile.yaml
  as untracked but NOT staged (gitignore working) — then delete the test file

---

## Task 01 — requirements.txt

**Status:** [x]
**Files:** `requirements.txt`

**Description:**
Create requirements.txt with exact versions for all dependencies needed
across all phases. Comment each group.

```
# Core
pyyaml==6.0.2
rich==13.7.1

# EML + document parsing
pypdf==4.3.1
python-docx==1.1.2

# Document generation
python-docx==1.1.2
reportlab==4.2.2

# AI providers (all optional — install only what you use)
google-generativeai==0.8.3
anthropic==0.40.0
openai==1.57.0

# Web UI (Phase 5 — not needed until then)
fastapi==0.115.5
uvicorn==0.32.1
jinja2==3.1.4
python-multipart==0.0.12
```

**Constraints:**
- Do not add packages not listed here
- Versions are pinned — do not change without approval

**Acceptance Criteria:**
- `pip install -r requirements.txt` completes without error on Python 3.13

---

## Task 02 — setup.py

**Status:** [x]
**Files:** `setup.py`

**Description:**
First-run setup script. Creates all required folders, initializes the database,
checks for required config files, and prints a clear status report.

Must create these folders if they don't exist:
  config/prompts/
  src/
  data/processed/
  inbox/
  examples/letters/
  output/reports/
  docs/
  ui/templates/

Must call `init_db()` from src.db to create the SQLite database.

Must check for config/profile.yaml. If missing:
  Copy config/profile.yaml.example to config/profile.yaml and print:
  "IMPORTANT: Fill in config/profile.yaml with your details before running."

Must print a final status summary:
  "Setup complete. Next step: fill in config/profile.yaml, then run: python main.py --help"

**Constraints:**
- Never overwrite an existing config/profile.yaml
- Never overwrite an existing data/tracker.db
- Use pathlib.Path throughout

**Acceptance Criteria:**
- Running setup.py twice is safe (idempotent)
- All folders exist after first run
- data/tracker.db created with correct schema
- Output is clear and human-readable

---

## Task 03 — src/db.py

**Status:** [x]
**Files:** `src/db.py`

**Description:**
All database operations. No AI calls, no parsing. Only sqlite3.

This file was partially written in a previous session. Use the version already
in src/db.py as the base. Verify it contains all of the following and add
anything missing:

Required functions:
  init_db()                                      — create all 4 tables if not exist
  get_conn() -> sqlite3.Connection               — WAL mode, Row factory
  now_iso() -> str                               — UTC ISO timestamp
  make_job_id(company, role, date) -> str        — slug-based ID

  insert_job(data: dict) -> str                  — insert job, return job_id
  update_job_status(job_id, status, notes=None)  — update + log action
  get_jobs(status=None, min_score=0) -> list     — filtered job list
  get_job(job_id) -> dict | None                 — single job by ID
  job_exists_for_eml(source_eml) -> bool         — duplicate check

  log_action(job_id, action, detail=None, source='system')  — append-only

  save_document(job_id, doc_type, path) -> int   — insert document record
  rate_document(doc_id, rating)                  — set rating + use_as_example
  get_example_letters(min_rating=4, limit=3)     — best-rated letters for AI

  record_outcome(job_id, reply_type, reply_date=None, notes=None)

  get_activity_report(date_from, date_to) -> list — for agency export
  get_stats() -> dict                             — summary counts

Full schema (4 tables): jobs, activity_log, documents, outcomes
See /docs/ARCHITECTURE.md section 5 for complete column definitions.

**Constraints:**
- sqlite3 standard library only — no SQLAlchemy, no ORM
- activity_log: INSERT only, never UPDATE or DELETE
- All timestamps: UTC ISO format via now_iso()
- Row factory: sqlite3.Row (allows dict-style access)

**Acceptance Criteria:**
- `python -m py_compile src/db.py` — no errors
- `python -c "from src.db import init_db; init_db(); print('OK')"` — prints OK
- data/tracker.db created with correct 4 tables

---

## Task 04 — src/ai_client.py

**Status:** [ ]
**Files:** `src/ai_client.py`

**Description:**
Provider abstraction layer. All AI calls in the entire project go through
this file. No other file may import google.generativeai, anthropic, or openai directly.

This file was partially written in a previous session.
Use the existing version as the base and verify it contains:

  get_client(config: dict) -> client object
    Reads config['ai']['provider'], config['ai']['model'], config['ai']['api_key_env']
    Returns GeminiClient | ClaudeClient | OpenAIClient
    Raises EnvironmentError if API key env var not set (with clear message)
    Raises ValueError if provider name is unknown

  complete(client, prompt: str) -> str
    Calls the provider and returns response text

  complete_json(client, prompt: str) -> dict
    Calls complete(), strips markdown fences, parses JSON
    Raises ValueError with raw response snippet if JSON is invalid

  class GeminiClient    — uses google.generativeai
  class ClaudeClient    — uses anthropic
  class OpenAIClient    — uses openai

Error message format for missing API key (Windows-friendly):
  "API key not found. Set environment variable: {key_env}\n"
  "Windows CMD:        set {key_env}=your_key_here\n"
  "PowerShell:         $env:{key_env}='your_key_here'"

**Constraints:**
- No business logic in this file
- Provider SDKs imported inside each class method (not at module level)
  so that missing an unneeded SDK doesn't break the whole file
- ImportError from missing SDK must give a clear install instruction

**Acceptance Criteria:**
- `python -m py_compile src/ai_client.py` — no errors
- `python -c "from src.ai_client import get_client; print('OK')"` — prints OK
- Missing API key produces a helpful error, not a traceback

---

## Task 05 — config/profile.yaml

**Status:** [ ]
**Files:** `config/profile.yaml`, `config/profile.yaml.example`

**Description:**
Two files:

1. `config/profile.yaml.example` — template with placeholder values,
   committed to git, safe to share.

2. `config/profile.yaml` — filled in with Jiri's real data below.
   This file is gitignored. Never commit it.

Fill config/profile.yaml with the following real data
(extracted from the uploaded CV and cover letter documents):

```yaml
personal:
  name: "Jiri Vosta"
  email: "jiri@vosta.co.uk"
  phone: "+49 151 18972548"
  location: "Potsdam, Germany"
  age: 50

restrictions:
  hybrid_cities: ["Berlin", "Potsdam"]
  remote_ok: true
  onsite_only_never: true

ai:
  provider: gemini
  model: gemini-1.5-flash
  api_key_env: GEMINI_API_KEY

skills:
  expert:
    - "C#"
    - ".NET / ASP.NET Core"
    - "SQL Server (T-SQL)"
    - "Python"
    - "REST API design"
    - "ETL / data pipelines"
  solid:
    - "Snowflake"
    - "Hadoop"
    - "MySQL"
    - "Flask"
    - "Git"
    - "Automic (workload automation)"
    - "Excel / VBA"
  learning:
    - "LLM integration"
    - "FastAPI"
    - "Go"
  moved_away_from:
    - "VBA (used it, moved on)"
    - "legacy .NET Framework (know it, prefer Core)"

preferences:
  role_types:
    - "senior software engineer"
    - "senior data engineer"
    - "backend developer"
    - "software architect"
    - "tech lead"
  avoid:
    - "pure frontend"
    - "QA / testing only"
    - "DevOps only"
    - "relocation required"
  min_score_to_show: 5

voice: |
  I spent a decade at eBay building backend systems — mostly financial
  data infrastructure, monitoring tools, and migration work. Real scale,
  real stakes. The kind of work where a bug at 3am means someone's numbers
  are wrong.

  I don't separate software engineering from data engineering. Most of my
  best work was at that boundary — C# systems that needed to handle Snowflake
  migrations cleanly, Python pipelines that fed into .NET dashboards used by
  C-level finance teams. I follow what the problem needs, not what's on the
  job title.

  I'm 50 and I'm still curious about new things — not performatively, but
  because I build with them. I've been spending time with LLM integration and
  FastAPI because I find the problems genuinely interesting. That's how I've
  always worked. I don't add a technology to my CV until I've built something
  with it.

  I'm direct. I give honest estimates. I think good architecture matters more
  than clever code. I've coached youth basketball at international level for
  years — that's not filler, it's actually how I think about teams and
  communication.

  My German is limited but I live in Potsdam and I'm working on it. I won't
  pretend otherwise. What I can do is work effectively in an English-speaking
  team in a German-speaking country, which is most of Berlin tech.
```

**Constraints:**
- config/profile.yaml must be listed in .gitignore
- config/profile.yaml.example must use placeholder values only
- The voice section above is a starting point — Jiri should edit it in
  his own words before using the system seriously

**Acceptance Criteria:**
- config/profile.yaml loads without YAML parse error
- config/profile.yaml.example committed to git (safe placeholder values)
- `python -c "import yaml; yaml.safe_load(open('config/profile.yaml'))"` — no errors
- .gitignore contains: config/profile.yaml, .env, data/tracker.db, output/

---

## Task 06 — config/prompts/score.txt

**Status:** [ ]
**Files:** `config/prompts/score.txt`

**Description:**
Scoring prompt template. Read at runtime — user can edit without touching code.
Uses {placeholder} format for runtime substitution.

Required placeholders:
  {name}, {location}, {skills_expert}, {skills_solid}, {skills_learning},
  {skills_moved_away}, {role_types}, {roles_avoid}, {hybrid_cities}, {voice},
  {job_text}

The prompt must instruct the AI to return ONLY valid JSON with this exact structure:
  company, role_title, location, remote_type, language, relevance_score (1-10),
  score_reason (2 sentences max), location_ok (bool), location_reason,
  strong_matches (list), concerns (list), recommended (bool),
  salary_mentioned (str or null), tech_stack (list)

Include explicit instruction: "Respond with JSON only. No markdown. No explanation."

Include honest scoring guidance:
  7+ = genuinely worth applying
  5-6 = marginal, flag it
  below 5 = poor fit, still record it

**Constraints:**
- Plain text file, no YAML, no JSON
- Placeholders in {curly_braces}
- The word "json" must appear in the final instruction line

**Acceptance Criteria:**
- File exists at config/prompts/score.txt
- All required placeholders present
- No hardcoded personal data (all via placeholders)

---

## Task 07 — config/prompts/generate.txt

**Status:** [ ]
**Files:** `config/prompts/generate.txt`

**Description:**
Cover letter generation prompt. Read at runtime — user can edit without touching code.

Required placeholders:
  {name}, {age}, {location}, {voice}, {skills_expert}, {skills_solid},
  {job_text}, {examples_section}, {language}

The prompt must include:

BANNED PHRASES section (never to appear in output):
  leverage, leveraging, excited, passionate, thrilled, synergy, innovative,
  dynamic, results-driven, detail-oriented, team player, hard worker,
  proven track record, fast-paced environment, I am writing to express,
  I would like to apply, I am confident that, I believe I would be a great fit,
  I have seen firsthand, stabilizing force

STRUCTURE rules:
  Max 4 short paragraphs, no bullet points, body text only (no date/address),
  specific to the actual JD, does not start with "I",
  language matches {language} exactly

TONE rules:
  Direct. Write as someone who knows their worth.
  Age and experience are assets — do not hide them, do not over-explain them.
  Slightly dry is acceptable. Opinions are fine.

**Constraints:**
- Plain text file
- {examples_section} placeholder — filled at runtime with 0-3 rated example letters
  or the text "No rated examples yet — use the voice document as the only style guide."

**Acceptance Criteria:**
- File exists at config/prompts/generate.txt
- All required placeholders present
- Banned phrases list is complete

---

## Task 08 — main.py

**Status:** [ ]
**Files:** `main.py`

**Description:**
CLI entry point using argparse. Defines all 5 commands. In this phase,
commands print "Not yet implemented — coming in Phase N" with the correct phase.

Commands:
  process   — "Coming in Phase 1: parse inbox and score jobs"
  review    — "Coming in Phase 1: review scored jobs"
  generate  — "Coming in Phase 3: generate CV and cover letter"
  status    — "Coming in Phase 4: update job status"
  report    — "Coming in Phase 2: export agency report"

Also include:
  --version flag printing "job-tracker v0.1.0"
  A brief description: "Job application tracker for Jiri Vosta"

load_profile() helper function:
  Reads config/profile.yaml using yaml.safe_load
  Raises FileNotFoundError with helpful message if missing:
    "config/profile.yaml not found. Run python setup.py first."
  Returns dict

**Constraints:**
- argparse only — no click, no typer (not in requirements.txt)
- No business logic in main.py — it orchestrates, never decides
- load_profile() used by all commands that need the profile

**Acceptance Criteria:**
- `python main.py --help` shows all commands with descriptions
- `python main.py --version` prints version
- `python main.py process` prints "Coming in Phase 1..." message
- `python -m py_compile main.py` — no errors

---

## Task 09 — Copy example files

**Status:** [ ]
**Files:** `examples/letters/`, `examples/cv_base.docx`

**Description:**
Copy the uploaded example files to the correct locations.
These are Jiri's real documents — they become the style examples
the system learns from.

Files to copy (from /mnt/user-data/uploads/):
  jiri_vosta_cover_letter_20251219.pdf   → examples/letters/cl_20251219_aroundHome.pdf
  jiri_vosta_cover_letter_20260204_topi.pdf → examples/letters/cl_20260204_topi.pdf
  jiri_vosta_cover_letter_20260204_axel.pdf → examples/letters/cl_20260204_axel.pdf
  vosta_jiri_cv_20251205.docx            → examples/cv_base.docx

Create examples/ratings.json:
```json
{
  "cl_20251219_aroundHome.pdf": {"rating": 3, "notes": "bullet point style, good for structured companies"},
  "cl_20260204_topi.pdf": {"rating": 4, "notes": "best so far - specific to company, good opening"},
  "cl_20260204_axel.pdf": {"rating": 3, "notes": "opens with banned phrase - do not use as example"}
}
```

Note on ratings: topi letter (4/5) will be used as style example in generation.
axel letter starts with "I am writing to express" — rated 3, not used as example.
december letter uses bullet points — rated 3, useful only for structured JDs.

**Constraints:**
- Copy files, do not modify them
- examples/ratings.json must be valid JSON
- examples/cv_base.docx is the starting point for all future CV tailoring

**Acceptance Criteria:**
- 3 cover letters exist in examples/letters/
- examples/cv_base.docx exists
- examples/ratings.json is valid JSON with 3 entries
- `python -c "import json; json.load(open('examples/ratings.json'))"` — no error

---

## Commit

When all tasks complete and completion checklist passes:

```
feat(p0): scaffold — project structure, DB, config, prompts, example files
```

Then create Tasks_P1.md before starting Phase 1.