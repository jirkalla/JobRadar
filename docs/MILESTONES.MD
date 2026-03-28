# Milestones — job-tracker
## v1.0 | March 2026

> **Project:** job-tracker — personal job application management system
> **Owner:** Jiri Vosta, Potsdam, Germany
> **Stack:** Python 3.13, SQLite, Rich CLI, FastAPI (Phase 5), Claude/Gemini/OpenAI API
> **Architecture reference:** /docs/ARCHITECTURE.md
> **AI rules:** /docs/AI_INSTRUCTIONS.md

---

## Milestone Overview

| # | Name | Status | Goal |
|---|------|--------|------|
| P0 | Scaffold | ⏳ Active | Project structure, deps, DB, profile, voice doc |
| P1 | Parse + Score | ⏳ Planned | Digest parser, URL fetcher, AI scorer, ranked terminal list |
| P2 | Backfill + Report | ⏳ Planned | Manual entry wizard, agency PDF/CSV export — URGENT |
| P3 | Generate Documents | ⏳ Planned | CV tailoring, cover letter, versioned .docx output |
| P4 | Learning Loop | ⏳ Planned | Ratings feed examples, outcome tracking, quality improvement |
| P5 | Web UI | ⏳ Planned | FastAPI dashboard — all controls in browser |

---

## Phase 0 — Scaffold

**Goal:** Working project structure. Dependencies installed. Database created.
Profile.yaml filled in by Jiri. Voice document written. Running `python main.py --help`
shows available commands without errors.

**Status:** ⏳ Active
**Branch:** feature/p0-scaffold
**Task file:** /docs/Tasks_P0.md

**Acceptance Criteria:**
- All folders exist as defined in ARCHITECTURE.md
- `pip install -r requirements.txt` completes without error
- `python setup.py` runs without error and prints confirmation
- `python main.py --help` shows all commands
- `data/tracker.db` created with all four tables
- `config/profile.yaml` filled in with Jiri's real profile
- `examples/letters/` contains the three existing cover letters
- `examples/cv_base.docx` contains the base CV

---

## Phase 1 — Parse + Score

**Goal:** Drop one or more .eml files into inbox/ and run `python main.py process`.
The system parses the Infoagent digest format (50-60 jobs per email), shows a quick
filter list, fetches full job descriptions for kept jobs, scores them with AI, and
displays a ranked list in the terminal. All results written to SQLite.

**Status:** ⏳ Planned
**Branch:** feature/p1-parse-score
**Task file:** /docs/Tasks_P1.md (created when P0 is complete)

**Key design decisions:**
- One EML = one digest = 50-60 job stubs
- User quick-filters obvious misses before URL fetching (saves API calls)
- URL fetch via stdlib urllib — no requests dependency
- Score prompt reads from config/prompts/score.txt at runtime
- Location validation against profile.yaml restrictions built into scorer
- Processed EML files moved to data/processed/ after scoring

**Acceptance Criteria:**
- `python main.py process` runs end-to-end on the real Infoagent EML
- Quick filter shows title + company + location, accepts enter/s input
- Kept jobs fetched and scored — results in SQLite jobs table
- Ranked list displayed in terminal (Rich table, score descending)
- Location violations flagged clearly (red, not just low score)
- EML moved to data/processed/ after completion
- Running process twice on same EML skips already-processed jobs

---

## Phase 2 — Backfill + Report

**Goal:** Solve the immediate agency problem. Two deliverables:
1. `python backfill.py` — fast wizard to enter past applications manually
   (Jiri has ~30 records to enter from Oct 2025 – Feb 2026)
2. `python main.py report` — exports PDF and CSV of all activity in a date range

This phase must be buildable and usable independently of Phase 1.

**Status:** ⏳ Planned
**Branch:** feature/p2-backfill-report
**Task file:** /docs/Tasks_P2.md (created when P1 is complete)

**Backfill wizard design:**
- Guided terminal prompts — one field at a time
- Natural date input: "2025-10-07", "last tuesday", "07.10.2025" all accepted
- Each record takes < 60 seconds to enter
- Activity logged with source='manual' in activity_log
- All 30 backfill records enterable in one ~45 minute session

**Agency report design:**
- Date range input (from / to)
- PDF: clean table — date, company, role, action, status
- CSV: same data, importable to Excel
- Saved to output/reports/ with filename including date range
- Covers: all job contacts, recruiter contacts, status updates

**Acceptance Criteria:**
- `python backfill.py` wizard runs, accepts all date formats, saves to DB
- Entering one backfill record takes under 60 seconds
- `python main.py report` asks for date range, exports PDF and CSV
- Report contains all activity_log entries in the range
- source='manual' entries visually distinct in report (italic or note)
- Report is ready to show to unemployment agency

---

## Phase 3 — Generate Documents

**Goal:** For any approved job, `python main.py generate` produces a tailored CV
and cover letter as .docx files. The cover letter uses Jiri's voice document and
existing letters as style examples. A diff of changes to the base CV is shown before
saving. Jiri reviews and approves before anything is saved to output/.

**Status:** ⏳ Planned
**Branch:** feature/p3-generate
**Task file:** /docs/Tasks_P3.md (created when P2 is complete)

**Human-sounding cover letter rules (enforced in generate.txt prompt):**
Banned phrases: leverage, excited, passionate, thrilled, synergy, innovative,
dynamic, results-driven, detail-oriented, team player, proven track record,
I am writing to express my interest, I would like to apply, I am confident that
Rules: max 4 short paragraphs, no bullet points, specific to the actual JD,
does not start with "I", language matches JD language (de or en)

**CV tailoring rules:**
- Base structure always preserved
- Only professional profile summary and skills sections adjusted
- Changes shown as diff before saving
- Jiri confirms before file is written

**Acceptance Criteria:**
- `python main.py generate` works for any job with status='approved'
- Cover letter uses voice.txt and rated example letters as style input
- Banned phrases are never present in output
- CV diff shown, Jiri confirms, then .docx saved to output/
- Output folder named correctly: output/YYYY-MM-DD_company-slug_role-slug/
- score.json and jd_snapshot.txt saved alongside the documents
- Jiri can rate the letter 1-5 immediately after review

---

## Phase 4 — Learning Loop

**Goal:** The system improves automatically as Jiri rates letters. Letters rated 4-5
are saved to examples/letters/ and used as style examples in future generation.
Outcome tracking (got reply / interview / rejection) feeds back into the scoring
weights over time.

**Status:** ⏳ Planned
**Branch:** feature/p4-learning
**Task file:** /docs/Tasks_P4.md (created when P3 is complete)

**Learning mechanism (simple, no ML):**
- Rating >= 4: document.use_as_example set to 1 in DB
- generator.py reads up to 3 highest-rated letters as examples
- Letter saved to examples/letters/ with rating in filename
- Over time: system converges toward Jiri's preferred style

**Outcome tracking:**
- `python main.py status` — update job to responded/interview/offer/closed
- Outcome recorded in outcomes table
- After 10+ outcomes: weekly summary shown (response rate, avg score of replied jobs)

**Acceptance Criteria:**
- Rating a letter 4-5 automatically adds it to example pool
- Next generated letter visibly references example style
- Status command works for all outcome types
- Weekly summary shown when enough data exists

---

## Phase 5 — Web UI

**Goal:** Full browser-based dashboard. Everything the CLI does, accessible from
a browser. Profile editing, job history, rating letters, running process, generating
documents, exporting agency report — all in one UI.

**Status:** ⏳ Planned
**Branch:** feature/p5-web-ui
**Task file:** /docs/Tasks_P5.md (created when P4 is complete)

**Stack:** FastAPI + Jinja2 + Bootstrap 5 (loaded from static/)
**No JavaScript framework** — htmx for dynamic updates (optional)
**Same src/ modules** — no new business logic in ui/

**Key pages:**
- / — dashboard: stats, recent activity, pending approvals
- /jobs — job list with filters (status, score, date)
- /jobs/{id} — job detail, generate button, rate letter
- /profile — edit skills, voice, restrictions
- /history — full activity log, filterable
- /report — date range picker, export PDF/CSV

**Acceptance Criteria:**
- `uvicorn ui.main_ui:app --reload` starts without error
- All pages render without exception
- Process can be triggered from UI (runs same logic as CLI)
- Profile editable and saved from UI
- Agency report exportable from UI
- Works on Chrome/Edge on Windows

---

## Notes for Claude Code

### Where to start each phase
- P0: Run setup.py first — nothing else can proceed without DB and profile
- P1: Start with parser.py (Task P1.1) — scorer depends on parsed output
- P2: Can be started independently of P1 — backfill.py only needs db.py
- P3: Requires P1 (needs scored jobs with jd_text) and P2 (DB schema complete)
- P4: Requires P3 (needs rated documents in DB)
- P5: Requires P0-P4 complete — UI wraps existing functionality only

### Reference implementations (use as patterns)
- AI abstraction pattern: src/ai_client.py
- DB operation pattern: src/db.py (insert_job, log_action)
- EML parsing pattern: src/parser.py (parse_eml, _parse_job_block)
- Profile reading: any file that calls yaml.safe_load(profile_path)
- Rich terminal table: python main.py review (when implemented)

### Hard rules (never violate)
- All AI calls through src/ai_client.py only
- All DB operations through src/db.py only
- activity_log is append-only — never UPDATE or DELETE
- Personal data in config/profile.yaml — never in source code
- Prompts in config/prompts/ — user controls these, AI does not modify them
- Output files confirmed by Jiri before writing — never auto-save silently
- .env and config/profile.yaml are gitignored — never commit them