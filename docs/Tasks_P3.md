# Tasks — Phase 3: Generate Documents
# JobRadar | Milestone: P3 — Generate Documents
#
# INSTRUCTIONS FOR CLAUDE CODE:
# - Read /docs/AI_INSTRUCTIONS.md and /docs/MILESTONES.md before starting
# - Complete tasks in order — dependencies flow top to bottom
# - Mark each task [x] when complete
# - After each file: run python -m py_compile {file} to verify syntax
# - Follow the Task Closing Ritual (AI_INSTRUCTIONS.md section 10) after every task
# - Do NOT implement anything outside this file
# - Do NOT start P4 tasks

---

## Context — what P3 builds on

P1 delivered:
  src/parser.py     — Infoagent digest parser
  src/scorer.py     — AI scoring + location validation
  src/fetcher.py    — Forpsi IMAP download
  main.py           — fetch, process, review commands
  src/db.py         — complete database operations

fix/fetch-pdf-extraction delivered:
  Updated src/parser.py — Playwright-based JD fetch, real jd_text in DB
  Updated src/scorer.py — fetch_failed status

P2 delivered:
  backfill.py       — manual entry wizard
  src/report.py     — PDF + CSV agency export
  seed_backfill.py  — one-off data load

P3 adds one new module and extends main.py:
  src/generator.py  — CV tailoring + cover letter generation (NEW)
  main.py           — cmd_generate() replacing the Phase 3 stub

---

## Progress

- [x] Task P3.1 — src/generator.py (core generation logic)
- [ ] Task P3.2 — main.py generate command
- [ ] Task P3.3 — End-to-end test
- [ ] Task P3.4 — Completion check + merge to main

---

## Completion Checklist

- [ ] `python -m py_compile src/generator.py` — no errors
- [ ] `python -m py_compile main.py` — no errors
- [ ] `python main.py generate` — shows list of approved jobs, user selects one
- [ ] Cover letter generated without any banned phrase
- [ ] CV changes panel shown before saving — Jiri confirms before file is written
- [ ] Output folder created with correct naming convention
- [ ] cv_YYYY-MM-DD_company.docx and cl_YYYY-MM-DD_company.docx saved
- [ ] score.json and jd_snapshot.txt saved alongside documents
- [ ] score.json contains job_id field
- [ ] Rating prompt appears after document review
- [ ] Rating saved to documents table in DB
- [ ] Running generate twice for same job: prompts overwrite/v2/quit — never silently overwrites

---

## Task P3.1 — src/generator.py

**Status:** [x]

**Description:**
All document generation logic lives here. 9 functions total:
  `_slugify()`                  — private helper, used by make_output_dir and importable by main.py
  `build_cover_letter_prompt()` — assembles prompt from profile + JD + examples
  `build_cv_prompt()`           — assembles prompt from profile + JD + base CV text
  `generate_cover_letter()`     — calls ai_client, returns cover letter text
  `generate_cv_changes()`       — calls ai_client, returns dict of proposed CV changes
  `extract_base_cv_text()`      — reads examples/cv_base.docx, returns plain text
  `apply_cv_changes()`          — writes tailored CV as .docx using python-docx
  `write_cover_letter_docx()`   — writes cover letter as .docx using python-docx
  `make_output_dir()`           — builds and returns the output Path for a job

**Allowed imports:**
```python
import re
import json
from pathlib import Path
import yaml
from docx import Document
from src.ai_client import complete, complete_json
from src.db import get_example_letters
```

Do NOT import sqlite3 directly. Do NOT import from src.db anything beyond
get_example_letters — that is the only DB call generator.py makes.

**Layer rules:**
- generator.py calls ai_client.py and db.py only
- No CLI logic — all terminal interaction lives in main.py
- No file writes without an explicit output_path parameter
- No print() statements — generator.py is a library module

---

### Private helper: _slugify()

Define at module level — used internally and importable by main.py:

```python
def _slugify(value: str, max_len: int = 30) -> str:
    """Lowercase, replace non-alphanumeric chars with hyphens, truncate."""
    value = value.lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = value.strip('-')
    return value[:max_len].rstrip('-')
```

---

### Module-level constant: BANNED_PHRASES

Define at module level — not inside any function:

```python
BANNED_PHRASES = [
    'leverage', 'leveraging', 'excited', 'passionate', 'thrilled',
    'synergy', 'innovative', 'dynamic', 'results-driven', 'detail-oriented',
    'team player', 'hard worker', 'proven track record', 'fast-paced environment',
    'i am writing to express', 'i would like to apply', 'i am confident that',
    'i believe i would be a great fit', 'stabilizing force',
]
```

---

### Function: build_cover_letter_prompt()

```python
def build_cover_letter_prompt(
    profile: dict,
    jd_text: str,
    example_letters: list[dict],
    language: str = 'en',
) -> str:
    """
    Assemble the cover letter generation prompt.
    Reads config/prompts/generate.txt at runtime — never cached.
    Substitutes all {placeholders} with profile data and examples.

    profile['voice'] is the top-level 'voice:' key from profile.yaml.
    It is a required key — do not use .get() with a fallback.

    example_letters: list of dicts from db.get_example_letters().
    Each dict has keys: id, job_id, doc_type, path, version,
                        rating, use_as_example, created_at.
    """
```

Prompt file: `config/prompts/generate.txt`
Read on every call — never cache.
If missing: `raise FileNotFoundError("config/prompts/generate.txt not found.")`

Placeholders to substitute:
  {name}             — profile['personal']['name']
  {age}              — profile['personal']['age']
  {location}         — profile['personal']['location']
  {voice}            — profile['voice']
  {skills_expert}    — ', '.join(profile['skills']['expert'])
  {skills_solid}     — ', '.join(profile['skills']['solid'])
  {job_text}         — jd_text parameter
  {language}         — 'German' if language == 'de' else 'English'
  {examples_section} — assembled below

**examples_section assembly:**
If example_letters is empty:
  `"No rated examples yet — use the voice document as the only style guide."`

If not empty: for each letter dict, read the file at `letter['path']`.
  - Skip files with extension `.pdf` — not readable as plain text.
  - For `.docx`: extract text with `Document(path)`, join paragraph texts.
  - For `.txt`: `Path(path).read_text(encoding='utf-8')`.
  - If any file cannot be read for any reason: skip it silently.
  - For each successfully read letter, build:
    `f"--- Example letter (rating {letter['rating']}/5) ---\n{text}\n"`
  - Join all blocks with `"\n\n"`.
  - If all files skipped: use the empty fallback string.

---

### Function: build_cv_prompt()

```python
def build_cv_prompt(
    profile: dict,
    jd_text: str,
    base_cv_text: str,
) -> str:
    """
    Assemble the CV tailoring prompt.
    The AI must respond with JSON only — parsed by the caller via complete_json().
    """
```

The prompt must include:
- `"BASE CV:\n{base_cv_text}"`
- `"JOB DESCRIPTION:\n{jd_text}"`
- Profile skills from profile['skills']['expert'] and profile['skills']['solid']
- Instruction: only propose changes to the professional profile summary
- Instruction: preserve all dates, job titles, company names, and all other content exactly
- Instruction: skills_to_highlight and skills_to_remove are RECOMMENDATIONS for
  the human to apply manually — they will not be auto-applied to the document

End the prompt with this verbatim line:
  `"Respond with JSON only. No markdown. No explanation."`

The AI must return JSON with exactly these four keys:
```json
{
  "profile_summary": "3-4 sentence professional summary tailored to this JD",
  "skills_to_highlight": ["skill1", "skill2"],
  "skills_to_remove": ["skill3"],
  "changes_explained": "One sentence explaining the changes"
}
```

---

### Function: generate_cover_letter()

```python
def generate_cover_letter(
    client,
    profile: dict,
    jd_text: str,
    language: str = 'en',
) -> str:
    """
    Generate a cover letter using the AI.
    Fetches up to 3 highest-rated example letters from DB via get_example_letters().
    Returns the cover letter as a plain text string.
    Raises ValueError if the response contains a banned phrase.
    """
```

**Banned phrase detection — word-boundary regex only:**
```python
for phrase in BANNED_PHRASES:
    if re.search(r'\b' + re.escape(phrase) + r'\b', text, re.IGNORECASE):
        raise ValueError(
            f"Banned phrase found in output: '{phrase}'. Regenerate or edit manually."
        )
```

`\b` word boundaries prevent false positives:
"leveraged" does not match "leverage", "unexcited" does not match "excited".

---

### Function: generate_cv_changes()

```python
def generate_cv_changes(
    client,
    profile: dict,
    jd_text: str,
) -> dict:
    """
    Ask the AI to propose targeted CV changes for this JD.
    Returns a dict with exactly these keys:
      profile_summary, skills_to_highlight, skills_to_remove, changes_explained

    Internally calls extract_base_cv_text(Path('examples/cv_base.docx')) to
    supply base_cv_text to build_cv_prompt(). If cv_base.docx is missing,
    FileNotFoundError propagates to the caller — do NOT catch it here.

    Raises ValueError if:
      - complete_json() cannot parse the response (propagated unchanged)
      - the returned dict is missing any required key

    Does NOT catch any exceptions — let them propagate to the caller (main.py Step 4).
    """
```

**Internal flow:**
```python
base_cv_text = extract_base_cv_text(Path('examples/cv_base.docx'))
prompt = build_cv_prompt(profile, jd_text, base_cv_text)
result = complete_json(client, prompt)
```

**Do NOT wrap any of the above in try/except.** Both FileNotFoundError and
ValueError must propagate unchanged to main.py Step 4, which handles them.

**After complete_json() returns, validate required keys:**
```python
REQUIRED_CV_KEYS = {'profile_summary', 'skills_to_highlight', 'skills_to_remove', 'changes_explained'}
missing = REQUIRED_CV_KEYS - result.keys()
if missing:
    raise ValueError(f"AI response missing required keys: {missing}")
```

---

### Function: extract_base_cv_text()

```python
def extract_base_cv_text(cv_path: Path) -> str:
    """
    Extract plain text from examples/cv_base.docx for use in the CV prompt.
    Returns all non-empty paragraph texts joined with newlines.
    Raises FileNotFoundError if the file does not exist.
    Never modifies the source file.
    """
```

```python
doc = Document(cv_path)
lines = [p.text for p in doc.paragraphs if p.text.strip()]
return '\n'.join(lines)
```

---

### Function: apply_cv_changes()

```python
def apply_cv_changes(
    cv_path: Path,
    changes: dict,
    output_path: Path,
) -> None:
    """
    Apply the AI-proposed profile summary to the base CV and save as a new .docx.

    Only the profile summary paragraph is replaced. Skills changes are NOT
    applied — they are recommendations for the user to apply manually.

    Reads from cv_path. Writes to output_path. Never touches cv_base.docx.
    """
```

**CRITICAL — use Run pattern, never paragraph.text assignment:**

`paragraph.text = value` destroys all existing Run objects and loses inline
formatting (font size, bold, italic). Always use:

```python
for run in paragraph.runs:
    run.text = ''
if paragraph.runs:
    paragraph.runs[0].text = changes['profile_summary']
else:
    paragraph.add_run(changes['profile_summary'])
```

**Heading detection — locale-aware (English and German Word):**

English Word uses style names like `'Heading 1'`.
German Word uses `'Überschrift 1'`.
The detection must handle both:

```python
style_name = p.style.name
is_heading = (
    style_name.lower().startswith('heading')
    or 'berschrift' in style_name
)
```

When `is_heading` is True AND `p.text` contains any of these strings
(case-insensitive): `'profile'`, `'summary'`, `'about'`, `'profil'`
— the NEXT non-empty paragraph is the summary to replace.

If no matching heading found: `doc.add_paragraph(changes['profile_summary'])`
and print to stdout:
`"Warning: profile summary heading not found — summary appended. Review before sending."`

Save: `doc.save(output_path)`

---

### Function: write_cover_letter_docx()

```python
def write_cover_letter_docx(
    text: str,
    output_path: Path,
    profile: dict,
) -> None:
    """
    Write cover letter text to a .docx file.
    Structure: name heading, blank line, body paragraphs split on double newline.
    """
```

```python
doc = Document()
doc.add_heading(profile['personal']['name'], level=1)
doc.add_paragraph('')
for chunk in text.split('\n\n'):
    if chunk.strip():
        doc.add_paragraph(chunk.strip())
doc.save(output_path)
```

---

### Function: make_output_dir()

```python
def make_output_dir(company: str, role_title: str, date_str: str) -> Path:
    """
    Build and return the output directory Path. Does NOT create it.
    Caller is responsible for mkdir().

    Naming: output/{date_str}_{company-slug}_{role-slug}/
    date_str format: YYYY-MM-DD
    """
```

```python
return Path('output') / f"{date_str}_{_slugify(company)}_{_slugify(role_title)}"
```

Example:
  `make_output_dir('Zalando SE', 'Senior Data Platform Engineer', '2026-04-10')`
  → `Path('output/2026-04-10_zalando-se_senior-data-platform-engineer')`

---

**Constraints:**
- Do NOT use `paragraph.text = value` in apply_cv_changes() — always Run pattern
- Heading detection must cover both English and German Word style names
- Skills changes are recommendations only — never auto-applied to .docx
- generate_cv_changes() must validate required keys and raise ValueError if any missing
- generate_cv_changes() must NOT catch ValueError from complete_json()
- make_output_dir() must NOT create the directory — returns Path only
- profile['voice'] is required — do not use .get() with a default

**Acceptance Criteria:**
- `python -m py_compile src/generator.py` — no errors
- All 8 public names importable without error
- `extract_base_cv_text(Path('examples/cv_base.docx'))` returns 500+ chars
- `make_output_dir('Zalando SE', 'Senior Data Platform Engineer', '2026-04-10')`
  returns correct path AND does not create a folder on disk

---

## Task P3.2 — main.py generate command

**Status:** [ ]
**Files:**
- `main.py` (EXTEND — replace `cmd_generate()` stub with real implementation)

**Description:**
Replace the current `cmd_generate()` stub (which just prints "Coming in Phase 3")
with a full implementation. Everything else in main.py is left untouched.

**Read main.py before writing a single line.** Confirm:
- The stub is `cmd_generate()` — extend it in place
- The subparser variable is `generate_parser` (not `parser_generate`)
- `--job-id` is already defined on `generate_parser` — do NOT add it again
- The attribute on `args` is `args.job_id` (argparse converts `--job-id` to `job_id`)

---

**Imports — follow the existing pattern in main.py exactly.**

Every command uses function-level imports inside the command function body.
There is no `from src import db` at the top of the file.
Follow the same pattern in `cmd_generate()`:

```python
def cmd_generate(args: argparse.Namespace) -> None:
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    from src.db import (
        init_db, get_jobs, get_job,
        save_document, rate_document,
        log_action, update_job_status,
    )
    from src.ai_client import get_client
    from src import generator
    from src.generator import _slugify

    console = Console()
    try:
        profile = load_profile()
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    init_db()
```

**`get_client()` takes the full profile dict** — not a sub-dict:
```python
client = get_client(profile)   # CORRECT
# NOT: get_client(profile['ai'])  ← this crashes with KeyError: 'ai'
```
Confirmed by reading ai_client.py: `get_client()` does `config["ai"]` internally.

---

**Module-level helper — add near top of main.py, outside any function:**

```python
def _parse_json_field(value) -> list:
    """Safely parse a DB field that may be None, a list, or a JSON string."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []
```

This must be at module level, not nested inside cmd_generate(). It requires
`import json` in the global namespace — add it at the top of main.py alongside
the existing top-level imports (argparse, shutil, pathlib), not inside any function.
A local `import json` inside cmd_generate() does NOT satisfy this requirement.

---

**Command flow — 8 steps:**

**Step 1 — Select job:**

If `args.job_id` is set:
```python
job = get_job(args.job_id)
if job is None:
    console.print(f"[red]Job not found: {args.job_id}[/red]")
    return
if job['status'] != 'approved':
    console.print(f"[red]Job status is '{job['status']}' — only approved jobs can be generated.[/red]")
    return
```

If no `--job-id`:
```python
jobs = get_jobs(status='approved')
if not jobs:
    console.print("[yellow]No approved jobs. Run: python main.py review[/yellow]")
    return
```
Display as Rich table — columns: `#`, `Company`, `Role`, `Score`, `Location`, `Created`.
Ask: `"Enter job number to generate documents (or 'q' to quit): "`
Validate: integer 1..len(jobs) or 'q'. 'q' → return. Invalid → re-prompt once, then return.
```python
job = get_job(jobs[choice - 1]['id'])
```

**Step 2 — Validate jd_text:**

```python
if not job.get('jd_text'):
    console.print("[red]No job description stored for this job. Cannot generate.[/red]")
    console.print("Tip: this job may have been entered via backfill. Run fetch+process for a scored job.")
    return
```

**Step 3 — Generate cover letter:**

Initialise client once here — do not re-create it in later steps:
```python
try:
    client = get_client(profile)
except EnvironmentError as exc:
    console.print(f"[red]{exc}[/red]")
    return
```

Retry loop — max 3 total attempts.
The `with console.status()` block wraps only the AI call. Error printing and
`input()` are outside it so the spinner is not active when the user types:
```python
cl_text = None
banned_error = None
for attempt in range(1, 4):
    with console.status(f"Generating cover letter (attempt {attempt}/3)..."):
        try:
            cl_text = generator.generate_cover_letter(
                client, profile, job['jd_text'], job.get('language', 'en')
            )
            break
        except ValueError as exc:
            banned_error = str(exc)
    # spinner has stopped — safe to print and accept input
    if cl_text is None:
        console.print(f"[red]{banned_error}[/red]")
        if attempt == 3:
            console.print("[red]Could not produce a clean letter after 3 attempts. Quit and edit manually.[/red]")
            return
        choice = input("[Y] Try again / [Q] Quit: ").strip().lower()
        if choice != 'y':
            return
```

Print cover letter:
```python
console.print(Panel(cl_text, title=f"Cover Letter — {job['company']}", expand=False))
```

**Step 4 — Generate CV changes:**

```python
cv_changes = None
with console.status("Generating CV tailoring suggestions..."):
    try:
        cv_changes = generator.generate_cv_changes(client, profile, job['jd_text'])
    except FileNotFoundError:
        console.print("[red]examples/cv_base.docx not found — skipping CV tailoring.[/red]")
    except ValueError:
        console.print("[red]AI returned invalid response for CV changes. Skipping CV tailoring.[/red]")
```

If `cv_changes` is not None:
```python
lines = [
    f"Summary:   {cv_changes['profile_summary']}",
    f"Highlight: {', '.join(cv_changes['skills_to_highlight'])}",
    f"Remove:    {', '.join(cv_changes['skills_to_remove'])}",
    f"Why:       {cv_changes['changes_explained']}",
    "",
    "Note: skills changes are recommendations — apply them manually to the saved CV.",
]
console.print(Panel('\n'.join(lines), title=f"Proposed CV Changes — {job['company']}", expand=False))
```

**Step 5 — Confirm before saving:**

```python
console.print("\nReview the output above.")
if cv_changes is not None:
    prompt = "[S] Save both / [C] Cover letter only / [Q] Quit without saving: "
    valid = {'s', 'c', 'q'}
else:
    prompt = "[C] Save cover letter / [Q] Quit without saving: "
    valid = {'c', 'q'}

while True:
    save_choice = input(prompt).strip().lower()
    if save_choice in valid:
        break
    console.print(f"[yellow]Please enter one of: {', '.join(sorted(valid)).upper()}[/yellow]")

if save_choice == 'q':
    console.print("Nothing saved.")
    return
```

**Step 6 — Overwrite check and save:**

```python
today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
output_dir = generator.make_output_dir(job['company'], job['role_title'], today_date)
cl_doc_id: int | None = None   # must be initialised here — Step 7 checks it
```

Overwrite detection before mkdir:
```python
if output_dir.exists():
    console.print(f"[yellow]Output folder already exists: {output_dir}[/yellow]")
    ow = input("[O] Overwrite / [V] Save as new version / [Q] Quit: ").strip().lower()
    if ow == 'q':
        console.print("Nothing saved.")
        return
    elif ow == 'v':
        base = str(output_dir)
        for n in range(2, 10):
            candidate = Path(f"{base}_v{n}")
            if not candidate.exists():
                output_dir = candidate
                break
        else:
            console.print("[red]Too many versions already exist. Clean up output/ manually.[/red]")
            return
    # 'o' → proceed with existing output_dir, files will be overwritten

output_dir.mkdir(parents=True, exist_ok=True)
company_slug = _slugify(job['company'])
```

Always write these two files:
```python
(output_dir / 'jd_snapshot.txt').write_text(job['jd_text'] or '', encoding='utf-8')

score_data = {
    'job_id':         job['id'],
    'score':          job['score'],
    'score_reason':   job['score_reason'],
    'strong_matches': _parse_json_field(job.get('strong_matches')),
    'concerns':       _parse_json_field(job.get('concerns')),
    'tech_stack':     _parse_json_field(job.get('tech_stack')),
    'salary':         job.get('salary'),
    'generated_at':   datetime.now(timezone.utc).isoformat(),
}
(output_dir / 'score.json').write_text(
    json.dumps(score_data, indent=2, ensure_ascii=False), encoding='utf-8'
)
```

Save cover letter (save_choice 's' or 'c'):
```python
cl_path = output_dir / f"cl_{today_date}_{company_slug}.docx"
generator.write_cover_letter_docx(cl_text, cl_path, profile)
cl_doc_id = save_document(job['id'], 'cover_letter', str(cl_path))
console.print(f"[green]Cover letter saved: {cl_path}[/green]")
```

Save CV (save_choice 's' only, and cv_changes is not None):
```python
if save_choice == 's' and cv_changes is not None:
    cv_base = Path('examples/cv_base.docx')
    if not cv_base.exists():
        console.print("[red]examples/cv_base.docx not found — skipping CV save.[/red]")
    else:
        cv_path = output_dir / f"cv_{today_date}_{company_slug}.docx"
        generator.apply_cv_changes(cv_base, cv_changes, cv_path)
        save_document(job['id'], 'cv', str(cv_path))
        console.print(f"[green]CV saved: {cv_path}[/green]")
```

Log:
```python
log_action(job['id'], 'generated', detail=str(output_dir))
```

**Step 7 — Rate the cover letter:**

Only runs if cl_doc_id is not None:
```python
if cl_doc_id is not None:
    rating_input = input("Rate this cover letter 1-5 (or press Enter to skip): ").strip()
    if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
        rate_document(cl_doc_id, int(rating_input))
        if int(rating_input) >= 4:
            console.print("[green]Letter added to example pool for future generations.[/green]")
        else:
            console.print("Rating saved.")
    else:
        console.print("Rating skipped.")
```

**Step 8 — Update job status:**

```python
apply_choice = input("Mark this job as applied? [Y/N]: ").strip().lower()
if apply_choice == 'y':
    update_job_status(job['id'], 'applied')
    console.print("[green]Job status updated to 'applied'.[/green]")
else:
    console.print("Status unchanged (still 'approved').")
```

---

**Constraints:**
- All imports are inside cmd_generate() — follow existing main.py pattern
- `get_client(profile)` — full profile dict, not `profile['ai']`
- `cl_doc_id: int | None = None` initialised before save blocks — prevents NameError in Step 7
- `_parse_json_field()` is at module level — not nested inside cmd_generate()
- `--job-id` is already defined in `generate_parser` — do NOT add it again
- No file writes before user confirms in Step 5

**Acceptance Criteria:**
- `python -m py_compile main.py` — no errors
- `python main.py --help` — generate listed with description
- `python main.py generate` with no approved jobs: yellow message, no crash
- Full 8-step flow runs to completion with an approved job
- Cover letter printed in Panel before saving
- CV changes shown in Panel with recommendations note
- Nothing saved without user confirmation in Step 5
- Overwrite prompt shown when output folder already exists
- score.json contains job_id field
- Step 7 never raises NameError (cl_doc_id always defined before Step 7)

---

## Task P3.3 — End-to-end test

**Status:** [ ]
**Files:** none — verification only

**Pre-conditions — verify ALL before running any step:**

Run this check first:
```
python -c "
import os, yaml
from src.db import get_jobs

jobs = [j for j in get_jobs(status='approved') if j.get('jd_text')]
print(f'Approved jobs with jd_text: {len(jobs)}')
for j in jobs[:3]:
    print(f'  {j[\"id\"]} | {j[\"company\"]} | score {j[\"score\"]}')

key = os.environ.get('GEMINI_API_KEY')
print(f'API key: {\"SET\" if key else \"MISSING\"}')

profile = yaml.safe_load(open('config/profile.yaml'))
voice = profile.get('voice', '')
is_placeholder = 'Write your own words' in voice or len(voice.strip()) < 50
print(f'Voice document: {\"PLACEHOLDER — fill in profile.yaml before testing\" if is_placeholder else \"OK\"}')
"
```

Stop if any of these are true — do not proceed until resolved:
- Approved jobs with jd_text = 0 → tell Jiri; need `python main.py fetch` then `python main.py process`
- API key = MISSING → tell Jiri; set `$env:GEMINI_API_KEY='...'` in PowerShell
- Voice document = PLACEHOLDER → tell Jiri; `profile['voice']` in profile.yaml must
  contain the real voice document text before the AI will produce good output

---

**Step 1 — Syntax checks:**
```
python -m py_compile src/generator.py
python -m py_compile main.py
```
Expected: silence.

**Step 2 — Isolate generator functions:**
```
python -c "
from src.generator import extract_base_cv_text
from pathlib import Path
text = extract_base_cv_text(Path('examples/cv_base.docx'))
print(f'CV text: {len(text)} chars')
print(text[:300])
"
```
Expected: 500+ chars of readable CV text.

```
python -c "
from pathlib import Path
from src.generator import make_output_dir
p = make_output_dir('Zalando SE', 'Senior Data Platform Engineer', '2026-04-10')
print(f'Path: {p}')
print(f'Exists on disk: {p.exists()}')
"
```
Expected: correct path printed, `Exists on disk: False`.

**Step 3 — Full interactive flow:**

```
python main.py generate
```

- Select an approved job
- Cover letter appears in Panel — review manually:
  - No banned phrases (check against BANNED_PHRASES in generator.py)
  - Specific to the actual JD — not generic
  - Does not start with "I"
  - 4 paragraphs or fewer
  - Correct language (de or en)
- CV changes panel appears — confirm recommendations note is visible
- Choose **S** to save both
- Rate the letter (e.g. 3)
- Choose **N** for applied status — keep job as 'approved' for Step 8 overwrite test

**Step 4 — Verify output files:**
```
python -c "
from pathlib import Path
import json
folders = [f for f in sorted(Path('output').glob('2*/')) if not f.name.startswith('report')]
for f in folders:
    print(f.name + ':')
    for ff in sorted(f.iterdir()):
        print(f'  {ff.name}')

for sf in Path('output').glob('*/score.json'):
    d = json.loads(sf.read_text())
    print(f'score.json job_id: {d[\"job_id\"]}')
    print(f'score.json score:  {d[\"score\"]}')
"
```
Expected: one folder with cl_*.docx, cv_*.docx, score.json, jd_snapshot.txt.
score.json job_id must be non-empty.

**Step 5 — Verify DB records:**
```
python -c "
import sqlite3
conn = sqlite3.connect('data/tracker.db')
print('--- documents ---')
for r in conn.execute('SELECT id, job_id, doc_type, path, rating FROM documents ORDER BY created_at DESC LIMIT 5').fetchall():
    print(r)
print('--- activity_log (generated) ---')
for r in conn.execute('SELECT job_id, action, detail FROM activity_log WHERE action=\"generated\" ORDER BY ts DESC LIMIT 3').fetchall():
    print(r)
"
```
Expected: document records with correct job_id and rating from Step 3.

**Step 6 — Open .docx files manually:**
Open cl_*.docx in Word or LibreOffice.
Confirm: name heading at top, body readable, no garbled characters.
Open cv_*.docx — profile summary changed, all other content identical to base CV.

**Step 7 — Test --job-id flag:**
```
python main.py generate --job-id {job_id_from_step_3}
```
Expected: skips selection table, goes directly to generation.

**Step 8 — Test overwrite detection:**

The job from Step 3 should still be 'approved' (you chose N in Step 3).
Confirm: `python -c "from src.db import get_job; j = get_job('{job_id}'); print(j['status'])"`
If status is 'applied' (you accidentally chose Y): reset it:
```
python -c "from src.db import update_job_status; update_job_status('{job_id}', 'approved')"
```

Then run generate again for the same job and choose S:
```
python main.py generate
```
Expected: yellow warning about existing folder, O/V/Q prompt appears.
Choose V — verify a _v2 folder is created:
```
python -c "
from pathlib import Path
names = [f.name for f in sorted(Path('output').glob('2*/')) if not f.name.startswith('report')]
print(names)
"
```
Expected: two names — original and _v2 variant.

**Step 9 — Test edge case: no jd_text:**

Find a backfill job and temporarily approve it:
```
python -c "
from src.db import get_jobs, update_job_status
candidates = [j for j in get_jobs() if not j.get('jd_text') and j['status'] in ('applied', 'rejected')]
if candidates:
    j = candidates[0]
    update_job_status(j['id'], 'approved')
    print(f'Approved: {j[\"id\"]} — {j[\"company\"]}')
    print(f'Remember this id to revert: {j[\"id\"]}')
else:
    print('No backfill job found. Enter one via python backfill.py first.')
"
```

Run `python main.py generate` and select that job.
Expected: clear red error about missing jd_text, no crash, no files created.

Revert the job immediately after:
```
python -c "from src.db import update_job_status; update_job_status('{job_id}', 'rejected')"
```
Confirm it no longer appears in the approved list.

**Acceptance Criteria:**
- All 9 steps pass without unhandled exceptions
- Cover letter specific to JD, no banned phrases, sounds human
- Output files saved with correct naming
- score.json contains non-empty job_id field
- DB records correct in documents and activity_log tables
- Overwrite detection works — _v2 folder created in Step 8
- Edge case handled gracefully — Step 9 shows error, no files saved
- Backfill job reverted to 'rejected' after Step 9

---

## Task P3.4 — Completion check + merge to main

**Status:** [ ]
**Files:** `docs/MILESTONES.md` (status update only)

**Steps in order:**

1. Run every item in the Completion Checklist. Show Jiri the output.
   Stop if anything fails. Wait for Jiri's confirmation.

2. Update docs/MILESTONES.md: P3 status → "✅ Done"

3. Commit:
   ```
   docs(p3): mark P3 complete in MILESTONES.md
   ```

4. Merge:
   ```
   git checkout main
   git merge feature/p3-generate-docs --no-ff -m "feat(p3): merge Phase 3 document generation"
   ```

5. Create P4 branch:
   ```
   git checkout -b feature/p4-learning
   ```

6. Confirm:
   ```
   git branch --show-current
   git log --oneline -5
   ```
   Expected: on feature/p4-learning, merge commit at top.

**Constraints:**
- NEVER merge without Jiri's explicit "ok to merge" in chat
- NEVER push without asking Jiri first

**Acceptance Criteria:**
- All checklist items pass
- MILESTONES.md shows P3 ✅ Done
- Currently on branch feature/p4-learning

---

## Notes for Claude Code

### Confirmed facts about the real codebase — verified by reading the source files

**main.py patterns — must match exactly:**
- All imports are inside each command function body — not at module top
- Every command calls `init_db()` as its first DB operation
- Every command calls `load_profile()` and handles `FileNotFoundError`
- The generate subparser variable is `generate_parser`
- `--job-id` is already defined on `generate_parser` with attribute `args.job_id`
- `get_client()` takes the full profile dict — it does `config["ai"]` internally

**db.py function signatures — verified:**
```
init_db()                                              → None
get_jobs(status=None, min_score=0)                     → list[dict]
get_job(job_id)                                        → dict | None
save_document(job_id, doc_type, path)                  → int  (lastrowid)
rate_document(doc_id, rating)                          → None
log_action(job_id, action, detail=None, source='system') → None
update_job_status(job_id, status, notes=None)          → None
get_example_letters(min_rating=4, limit=3)             → list[dict]
```

**get_example_letters() dict keys:**
`id, job_id, doc_type, path, version, rating, use_as_example, created_at`
The file path key is `path`. The rating key is `rating`.

**ai_client.py:**
`get_client(config)` — config is the full profile dict, not the ai sub-dict.
`complete(client, prompt)` → str
`complete_json(client, prompt)` → dict, raises ValueError on bad JSON

### Hard rules
- All DB calls via direct imports from src.db — no `from src import db`
- All AI calls through src/ai_client.py only — never directly
- `get_client(profile)` — full dict only
- Never `paragraph.text = value` — always Run pattern
- Heading detection covers English and German Word style names
- `cl_doc_id` initialised to None before save blocks
- `_parse_json_field()` at module level in main.py
- generate_cv_changes() validates required keys, does not catch ValueError or FileNotFoundError
- make_output_dir() returns Path only — does not create directory

### File naming convention
  Output folder:  output/{YYYY-MM-DD}_{company-slug}_{role-slug}/
  CV file:        cv_{YYYY-MM-DD}_{company-slug}.docx
  Cover letter:   cl_{YYYY-MM-DD}_{company-slug}.docx
  Snapshot:       jd_snapshot.txt
  Score:          score.json  (contains job_id field)