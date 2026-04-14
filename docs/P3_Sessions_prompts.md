# P3 Session Prompts — JobRadar
# One prompt per Claude Code session. Copy the block, paste as first message.
# Wait for Task Closing Ritual confirmation before starting the next session.

==============================================================================
TASK P3.1 — src/generator.py
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p3-generate-docs
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P3.md Task P3.1 — read it fully before writing a single line

Also read these existing files before writing any code:
- src/ai_client.py            — understand complete() and complete_json() signatures
- src/db.py                   — understand get_example_letters() return shape
- config/prompts/generate.txt — understand all {placeholders} you must substitute

Do NOT read or reference examples/ratings.json — it is not used anywhere in P3.
Example letter ratings are read from the DB via get_example_letters(), not that file.

Your job:
Create src/generator.py with these names in this order:
  _slugify()                  — module-level private helper
  BANNED_PHRASES              — module-level constant list
  build_cover_letter_prompt() — reads generate.txt at runtime, substitutes placeholders
  build_cv_prompt()           — builds CV tailoring prompt for complete_json()
  generate_cover_letter()     — calls ai_client, checks banned phrases, raises ValueError
  generate_cv_changes()       — calls extract_base_cv_text() + complete_json(), validates keys, propagates all exceptions
  extract_base_cv_text()      — reads cv_base.docx, returns plain text
  apply_cv_changes()          — writes tailored CV using Run pattern
  write_cover_letter_docx()   — writes cover letter .docx
  make_output_dir()           — builds Path, does NOT create directory

That is 9 names total (_slugify and BANNED_PHRASES count as the first two).

Critical rules — each one will be verified:

1. Allowed imports: re, json, pathlib, yaml, docx.Document, src.ai_client, src.db
   No sqlite3. No argparse. No Rich. No print() statements.

2. BANNED_PHRASES is a module-level constant, not inside any function.
   Detection uses word-boundary regex — NOT bare substring:
     re.search(r'\b' + re.escape(phrase) + r'\b', text, re.IGNORECASE)

3. generate_cv_changes() must:
   - Call extract_base_cv_text(Path('examples/cv_base.docx')) internally to get base_cv_text
   - NOT wrap anything in try/except — let FileNotFoundError and ValueError both propagate
   - Validate all four required keys after parsing:
       REQUIRED = {'profile_summary', 'skills_to_highlight', 'skills_to_remove', 'changes_explained'}
       missing = REQUIRED - result.keys()
       if missing: raise ValueError(f"AI response missing required keys: {missing}")
   - Internal flow: extract_base_cv_text → build_cv_prompt → complete_json → validate keys → return

4. apply_cv_changes() must use the Run pattern — NEVER paragraph.text = value:
     for run in paragraph.runs: run.text = ''
     if paragraph.runs: paragraph.runs[0].text = changes['profile_summary']
     else: paragraph.add_run(changes['profile_summary'])

5. apply_cv_changes() heading detection must handle both English and German Word:
     style_name = p.style.name
     is_heading = style_name.lower().startswith('heading') or 'berschrift' in style_name

6. make_output_dir() must NOT create the directory — return Path only.

7. profile['voice'] is the top-level 'voice:' key from profile.yaml.
   Do not use .get() with a default. It is a required key.

8. get_example_letters() returns dicts with keys including 'path' and 'rating'.
   Use letter['path'] and letter['rating'] — not 'file_path' or 'score'.

After creating:
1. python -m py_compile src/generator.py
   (expected: silence)

2. python -c "
   from src.generator import (
       _slugify, build_cover_letter_prompt, build_cv_prompt,
       generate_cover_letter, generate_cv_changes,
       extract_base_cv_text, apply_cv_changes,
       write_cover_letter_docx, make_output_dir, BANNED_PHRASES
   )
   print(f'All names imported OK. {len(BANNED_PHRASES)} banned phrases.')
   "
   (expected: All names imported OK. 19 banned phrases.)

3. python -c "
   from src.generator import extract_base_cv_text
   from pathlib import Path
   text = extract_base_cv_text(Path('examples/cv_base.docx'))
   print(f'CV text: {len(text)} chars')
   print(text[:200])
   "
   (expected: 500+ chars, readable CV text)

4. python -c "
   from pathlib import Path
   from src.generator import make_output_dir
   p = make_output_dir('Zalando SE', 'Senior Data Platform Engineer', '2026-04-10')
   print(f'Path: {p}')
   print(f'Exists on disk: {p.exists()}')
   "
   (expected: correct path, Exists on disk: False)

Show me all 4 outputs. Wait for my confirmation before Task P3.2.

After I confirm:
- Commit: feat(p3): add src/generator.py with cover letter and CV generation
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P3.2


==============================================================================
TASK P3.2 — main.py generate command
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p3-generate-docs
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P3.md Task P3.2 — read it fully before touching main.py

Then read the ENTIRE main.py file before writing a single line.
Confirm these facts by reading the file — do not assume:

1. The stub is the function `cmd_generate()` — it just prints "Coming in Phase 3"
2. The generate subparser variable is `generate_parser` (not `parser_generate`)
3. `--job-id` is already defined on `generate_parser`. Do NOT add it again.
   Adding a duplicate will crash: ArgumentError: conflicting option string(s): --job-id
4. The attribute on args is `args.job_id`
5. Every other command (cmd_process, cmd_review) imports inside the function body.
   There is no `from src import db` at module top. Follow the same pattern.
6. Every other command calls `init_db()` as its first DB operation.
7. `get_client()` is called as `get_client(profile)` — full profile dict.
   NOT `get_client(profile['ai'])` — that crashes with KeyError: 'ai'.
   Confirmed: ai_client.py does config["ai"] internally.

Your job:
Replace the cmd_generate() stub with a full implementation.
Implement all 8 steps exactly as specified in Tasks_P3.md Task P3.2.
Add _parse_json_field() at module level (outside any function).

Critical rules:

1. All imports inside cmd_generate() body — follow existing pattern.
   Required imports for this function:
     import json
     from datetime import datetime, timezone
     from pathlib import Path
     from rich.console import Console
     from rich.panel import Panel
     from src.db import (init_db, get_jobs, get_job, save_document,
                         rate_document, log_action, update_job_status)
     from src.ai_client import get_client
     from src import generator
     from src.generator import _slugify

2. get_client(profile) — full dict. Never get_client(profile['ai']).

3. cl_doc_id: int | None = None — initialise at start of Step 6,
   before any save blocks. Step 7 checks `if cl_doc_id is not None`.

4. _parse_json_field() — module-level function, add near top of file.
   It requires `import json` in the GLOBAL namespace — at module top, not inside
   cmd_generate(). Adding `import json` only inside cmd_generate() is NOT sufficient:
   module-level functions run in the global namespace, so they need top-level imports.
   Add `import json` near the top of main.py alongside the other existing top-level
   imports (argparse, shutil, pathlib). If it is already there, skip this step.

5. --job-id is already wired. Do not touch generate_parser at all.

After editing:
1. python -m py_compile main.py
   (expected: silence)

2. python main.py --help
   (expected: generate listed with description)

3. python main.py generate
   (with no approved jobs in DB — expected: yellow message, no crash)

4. python main.py generate --job-id nonexistent-id-123
   (expected: red "Job not found" message, no crash)

Show me all 4 outputs. Wait for my confirmation before Task P3.3.

After I confirm:
- Commit: feat(p3): implement generate command in main.py
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P3.3


==============================================================================
TASK P3.3 — End-to-end test
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p3-generate-docs
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P3.md Task P3.3 — all 9 steps and all pre-conditions

This is a verification task. No code changes unless a bug is found.
If a bug is found: fix it, py_compile the changed file, re-run the failing step, then continue.

Run this pre-condition check first — stop if anything is not OK:
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
print(f'Voice document: {\"PLACEHOLDER - fill in profile.yaml\" if is_placeholder else \"OK\"}')
"
```

Stop conditions:
- Approved jobs with jd_text = 0  → tell Jiri; fetch+process must run first
- API key = MISSING               → tell Jiri; set the key in PowerShell
- Voice document = PLACEHOLDER    → tell Jiri; profile.yaml voice must be filled in

Important for Step 3: choose N when asked "Mark as applied?" — this keeps the job
as 'approved' so the overwrite test in Step 8 can find it.

Run every step in Task P3.3 in order.
Show me the exact command and full output for each step.
Stop at any step that fails — fix before continuing.

After all 9 steps pass:
- Report PASS or FAIL for each acceptance criterion from Task P3.3
- Wait for my confirmation
- No commit for this task
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P3.4 until I say so


==============================================================================
TASK P3.4 — Completion check + merge to main
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p3-generate-docs
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 8, 9, and 10
- docs/Tasks_P3.md — Completion Checklist and Task P3.4

PART 1 — Run every item in the Completion Checklist from Tasks_P3.md.
Run each in order. Show me the exact output.
Report PASS or FAIL for each item.
Stop here and wait for my confirmation before doing anything else.

--- wait for Jiri to say "ok to merge" ---

PART 2 — Only after I explicitly say "ok to merge":

1. Update docs/MILESTONES.md: P3 status → "✅ Done"
2. Commit: docs(p3): mark P3 complete in MILESTONES.md
3. Run:
   git checkout main
   git merge feature/p3-generate-docs --no-ff -m "feat(p3): merge Phase 3 document generation"
   git checkout -b feature/p4-learning
4. Run: git branch --show-current  (expected: feature/p4-learning)
5. Run: git log --oneline -5
6. Show me both outputs
7. Wait for my final confirmation

After I confirm:
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Report: "Phase 3 complete. On branch feature/p4-learning. Ready for P4."