# AI Instructions — JobRadar

This file defines how all AI assistants (Claude Code, VS Code Claude, GitHub Copilot)
must behave when working inside the JobRadar repository.

======================================================================
1. PROJECT CONTEXT
======================================================================

JobRadar is a personal Python CLI tool + web UI for:
- Parsing job alert digest emails (.eml files from Outlook)
- Scoring job listings against a developer profile using an AI API
- Generating tailored CVs and cover letters that sound human
- Tracking all job application activity for unemployment agency reporting
- Learning from rated letters to improve output quality over time

Tech stack:
  Language:     Python 3.13
  AI API:       Abstracted (Gemini / Claude / OpenAI — switchable via config)
  Database:     SQLite (single file: data/tracker.db)
  CLI:          Rich library for terminal UI
  Web UI:       FastAPI + Jinja2 templates (Phase 5)
  Doc output:   python-docx for .docx generation
  PDF output:   reportlab for agency report export

Project owner: Jiri Vosta, Senior Software & Data Engineer, Potsdam/Berlin
Languages: emails are mixed German/English — system handles both

======================================================================
2. HIGH-LEVEL RULES FOR ALL AI
======================================================================

AI MUST:
- Follow the architecture defined in /docs/ARCHITECTURE.md
- Follow the active milestone in /docs/MILESTONES.md
- Complete tasks in order within the active Tasks_M*.md file
- Mark each task [x] when complete
- Run python -m py_compile or python main.py --help after every file change
  to verify no syntax errors before moving to the next task
- Keep all layers separate: parsing / scoring / generation / storage / UI
  are never mixed into the same file
- Store all user-editable configuration in config/ — never hardcode values
- Respect the abstraction layer: all AI calls go through src/ai_client.py only

AI MUST NOT:
- Implement features for a milestone that is not active
- Change folder structure without explicit instruction
- Add pip packages without approval — check requirements.txt first
- Mix concerns between layers (e.g. no DB calls in parser.py)
- Hardcode personal data (name, email, phone) anywhere in source code
  — all personal data lives in config/profile.yaml
- Call AI provider SDKs directly from any file other than src/ai_client.py
- Delete or overwrite files in data/ or output/ without explicit instruction
- Commit secrets — .env and config/profile.yaml are gitignored
- Modify prompts in config/prompts/ without being explicitly asked to do so
  (prompts are user-controlled, not AI-controlled)

======================================================================
3. ARCHITECTURE RULES
======================================================================

See /docs/ARCHITECTURE.md for full detail. Summary:

Layer rules:
  src/parser.py      — EML parsing only. No AI calls, no DB calls.
  src/scorer.py      — Scoring logic only. Calls ai_client, reads profile. No DB writes.
  src/generator.py   — Document generation only. Calls ai_client. No DB writes.
  src/db.py          — All database operations. No AI calls, no parsing.
  src/ai_client.py   — All AI provider calls. No business logic.
  src/report.py      — Agency report export only. Reads DB, writes PDF/CSV.
  main.py            — CLI entry point. Calls other modules. No business logic.
  backfill.py        — Manual entry wizard. Calls db.py only.
  ui/main_ui.py      — FastAPI app (Phase 5). Calls db.py and other src/ modules.

File naming: snake_case for all Python files.
Config files: YAML for profile, plain text for prompts.
Output files: named as {type}_{YYYY-MM-DD}_{company-slug}.docx

======================================================================
4. DATABASE RULES
======================================================================

- Engine: SQLite via Python standard library sqlite3
- File: data/tracker.db
- Schema defined in src/db.py init_db() — migrations via ALTER TABLE when needed
- Row factory: sqlite3.Row (allows dict-style access)
- WAL mode enabled for reliability
- activity_log table is APPEND ONLY — never UPDATE or DELETE rows in it
- Soft delete not used — jobs are marked with status='rejected' not deleted
- All timestamps in UTC ISO format

Tables: jobs, activity_log, documents, outcomes
Full schema: see /docs/ARCHITECTURE.md

======================================================================
5. CONFIGURATION RULES
======================================================================

- config/profile.yaml — personal data, skills, restrictions, AI provider, voice
- config/prompts/score.txt — scoring prompt template (user edits this)
- config/prompts/generate.txt — generation prompt template (user edits this)
- examples/letters/ — rated cover letters used as style examples
- examples/cv_base.docx — master CV template

AI MUST read config/profile.yaml at runtime — never cache or hardcode values.
If profile.yaml is missing a key, fail with a clear error message naming
the missing key — never silently use a default.

======================================================================
6. AI PROVIDER RULES
======================================================================

- All AI calls go through src/ai_client.py — no exceptions
- Provider is set in config/profile.yaml under ai.provider
- Switching provider requires only a config change — no code changes
- Supported providers: gemini, claude, openai
- API keys are read from environment variables — never from files
- If API key env var is missing, fail with a clear message showing
  which variable to set and how (Windows + PowerShell examples)

======================================================================
7. CODING STANDARDS
======================================================================

Python:
- Python 3.13 — use modern syntax (match/case, | union types, etc.)
- Type hints on all function signatures
- Docstrings on all public functions (one-line for simple, multi-line for complex)
- f-strings for all string formatting
- Pathlib.Path for all file paths — never os.path
- Exception handling: catch specific exceptions, never bare except:
- No global mutable state — pass config/db connection as parameters
- Functions do one thing — if a function is over 40 lines, split it

Naming:
- snake_case for functions, variables, files
- UPPER_SNAKE for constants
- Classes: PascalCase (only used where genuinely needed)
- Job ID format: {company-slug}-{role-slug}-{YYYYMMDD}

======================================================================
8. COMMIT CONVENTIONS
======================================================================

Format: type(scope): short description

Types:
- feat    — new code or new feature
- fix     — bug fix or correction
- docs    — changes to /docs files only
- chore   — config, .gitignore, requirements, setup tooling
- test    — test scripts or validation runs
- prompt  — changes to config/prompts/ files only (separate type —
             prompt changes affect AI output quality and must be
             trackable independently of code changes)

Scope: phase or module
  p0, p1, p2, p3, p4, p5   — milestone phases
  parser, scorer, db, ui    — specific modules
  docs, config, prompt      — non-code areas

Examples:
  feat(p1): add digest parser for Infoagent EML format
  fix(scorer): handle missing location field in AI JSON response
  docs(docs): update ARCHITECTURE.md with FastAPI routes
  chore(p0): add .gitignore and initialize repository
  prompt(prompt): tighten banned phrases list in generate.txt
  feat(p3): add CV diff view before saving output

Rules:
- Subject line max 72 characters
- Imperative mood: "add", "fix", "handle" — not "added" or "adds"
- One logical change per commit — never mix feat + docs in one commit
- prompt changes are always a separate commit from code changes
- AI MUST ask before running git push — always, no exceptions
- AI MUST ask before merging any branch into main — always
- Never commit these files (all gitignored):
    .env
    config/profile.yaml
    data/tracker.db
    output/
    examples/letters/
    examples/cv_base.docx

======================================================================
9. BRANCHING
======================================================================

AI MUST create a feature branch before starting any milestone.
All milestone work is committed to the feature branch — never directly to main.

Branch naming: feature/p{N}-{short-description}

Examples:
  feature/p0-scaffold
  feature/p1-parse-score
  feature/p2-backfill-report
  feature/p3-generate-docs

Rules:
- Create branch as the very first action before writing any code or files
- All tasks within the milestone are committed to this branch
- AI MUST ask before merging to main — merging is always Jiri's decision
- AI MUST ask before running git push — always
- Hotfixes may go directly on main only with explicit approval in chat

Merge strategy:
  git merge feature/{branch} --no-ff
  (preserves milestone boundary as a visible event in git history)

======================================================================
10. TASK CLOSING RITUAL
======================================================================

After every completed task — before moving to the next one — AI MUST:

1. SUMMARY
   Print a clear summary of what was done:
   - Files created (with paths)
   - Files modified (with what changed and why)
   - Any decisions made that weren't explicit in the task

2. VERIFICATION STEPS
   Print exact steps for Jiri to verify the work:
   - Commands to run (copy-pasteable)
   - What the expected output looks like
   - What to check in the browser or file system if applicable
   Example:
     "Run: python -m py_compile src/db.py
      Expected: no output (silence = success)
      Then run: python -c 'from src.db import init_db; init_db(); print(\"DB OK\")'
      Expected: prints 'DB OK' and creates data/tracker.db"

3. WAIT FOR CONFIRMATION
   Do not proceed to the next task until Jiri confirms.
   Accepted confirmations: "ok", "looks good", "confirmed", "next", or similar.
   If Jiri reports an error — fix it before moving on. Never skip.

4. ONLY AFTER CONFIRMATION:
   - Mark the task [x] in the Tasks_P*.md file
   - Commit with the correct message format from section 8
   - Report: "Task XX complete. Ready for Task XX+1 when you are."

This ritual applies to every task without exception.
AI must never auto-proceed through multiple tasks without Jiri confirming each one.

======================================================================
11. PROMPT IMPROVEMENT WORKFLOW
======================================================================

Prompts in config/prompts/ are Jiri's editorial control over AI output.
AI never modifies them without being explicitly asked.

When to improve prompts:
- After Phase 3 is working: review generate.txt against first 3 real letters
- After Phase 4 is working: review score.txt against first 10 scored jobs
- Any time Jiri notices output quality issues

How to improve prompts (triggered by Jiri, not AI):
1. Jiri says "let's improve the generate prompt" (or similar)
2. AI suggests specific changes and explains why
3. Jiri approves the changes
4. AI edits the prompt file
5. AI commits with type: prompt(prompt): description of what changed and why
6. Jiri tests the next generation and confirms improvement

AI MUST NOT:
- Edit prompts as part of a feat or fix commit
- Silently adjust prompt wording "to make it work better"
- Bundle prompt changes with code changes in the same commit

======================================================================
12. GIT SETUP RULES
======================================================================

Repository: Git (initialized in Task 00 of Phase 0)
Default branch: main

.gitignore MUST include:
  # Secrets and personal data
  .env
  config/profile.yaml

  # Database and generated output
  data/tracker.db
  data/processed/
  output/

  # Personal documents (never commit)
  examples/letters/
  examples/cv_base.docx
  examples/ratings.json

  # Python
  __pycache__/
  *.pyc
  *.pyo
  .venv/
  venv/
  *.egg-info/

  # VS Code
  .vscode/

  # OS
  .DS_Store
  Thumbs.db

config/profile.yaml.example IS committed — it contains placeholder values only,
no real personal data. It serves as the template for new installations.

======================================================================
13. HOW AI SHOULD RESPOND
======================================================================

When starting a session:
- Read AI_INSTRUCTIONS.md first
- Read MILESTONES.md to confirm which phase is active
- Read the active Tasks_P*.md file
- Confirm: "Ready to work on Phase N. Active task: Task XX — {name}."

When writing code:
- Complete tasks in listed order — never skip ahead
- After each file: run python -m py_compile {file} to verify syntax
- After each task: follow the Task Closing Ritual (section 10)
- Reference existing files as patterns before creating new ones
- If a file already exists from a previous session — read it first,
  then extend or correct rather than overwrite

When asked for design decisions:
- Reference ARCHITECTURE.md and MILESTONES.md
- Propose options within constraints
- Ask before implementing anything not in the active task file

When something is unclear:
- Ask one specific question — do not make assumptions
- Do not proceed with guesswork on file paths, field names, or behaviour
- One question at a time — do not ask multiple things at once

======================================================================
END OF AI INSTRUCTIONS
======================================================================