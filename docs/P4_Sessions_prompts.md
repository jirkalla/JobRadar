# P4 Session Prompts — JobRadar
# One prompt per Claude Code session. Copy the block, paste as first message.
# Wait for Task Closing Ritual confirmation before starting the next session.

==============================================================================
TASK P4.1 — db.py: audit record_outcome() + add get_outcomes() + get_weekly_summary()
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p4-learning
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P4.md Task P4.1 — read it fully before touching any file

Then read the ENTIRE src/db.py before writing a single line.
Confirm these facts:
1. The correct connection helper name — is it get_conn() or _get_conn()?
   The correct name is get_conn() (no underscore). Verify in the actual file.
2. How the context manager pattern is used: "with get_conn() as conn:"
3. The existing record_outcome() signature and body — what it currently does
4. Whether get_outcomes() and get_weekly_summary() already exist

Your job — four steps, in order:

Step A: Audit record_outcome() against the spec in Tasks_P4.md Task P4.1.
  Report what is present and what is missing. Make only the missing additions.
  Do not rewrite what already works.
  Critical: the status update must be inline SQL inside the "with get_conn() as conn:"
  block — do NOT call update_job_status() to do this, as that function opens its
  own connection and would break atomicity.
  If changes needed: py_compile, commit: fix(p4): complete record_outcome in db.py

Step B: Add get_outcomes() — only if not already present.

Step C: Add get_weekly_summary() — only if not already present. Threshold: 5 outcomes.

Step D: Verify rate_document() and get_example_letters() — verification only.
  Fix only if the specific issue is present. Commit separately if a fix is needed.

Critical rules:
- Use get_conn() — context manager pattern — never sqlite3.connect() directly
- Do NOT rename record_outcome() — seed_backfill.py calls it with that name
- record_outcome() wraps INSERT + status UPDATE in one "with get_conn() as conn:" block
- log_action() is called after the with block (its own connection — that is intentional)

After all changes:

1. python -m py_compile src/db.py
   Expected: silence.

2. python -c "
   from src.db import record_outcome, get_outcomes, get_weekly_summary, get_example_letters
   print('All functions imported OK')
   print(f'Weekly summary (expect None if < 5 outcomes): {get_weekly_summary()}')
   "
   Expected: imports OK, summary is None.

3. python -c "
   from src.db import record_outcome
   try:
       record_outcome('fake-id', 'invalid_type')
   except ValueError as e:
       print(f'ValueError raised correctly: {e}')
   "
   Expected: ValueError raised naming the bad value.

Show me all 3 outputs. Wait for my confirmation.

After I confirm:
- Commit: feat(p4): add get_outcomes, get_weekly_summary; audit record_outcome in db.py
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P4.2


==============================================================================
TASK P4.2 — main.py: verify or complete cmd_status()
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p4-learning
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 2, 3, 7, 8, and 10
- docs/Tasks_P4.md Task P4.2 — read it fully

Then read the ENTIRE main.py before writing a single line.

Determine the current state of cmd_status():
- Case 1: fully implemented -> run verification only, no code changes
- Case 2: stub -> replace with full implementation from Tasks_P4.md
- Case 3: does not exist -> add subparser + full function

Report which case applies before writing anything.

Critical rules (regardless of case):
- All imports inside cmd_status() function body — no module-top imports
- No load_profile() call — cmd_status() does not use AI
- cmd_status() calls record_outcome() only — NEVER calls update_job_status() directly
- Eligible statuses to filter: 'applied', 'responded', 'interview'
  Note: 'offer' is intentionally excluded in P4 — deliberate scope limit, not an oversight

After any changes (or for Case 1 with no changes):

1. python -m py_compile main.py
   Expected: silence.

2. python main.py --help
   Expected: 'status' listed.

3. python main.py status
   (with no eligible jobs) Expected: yellow message, clean exit.

Show me all 3 outputs. Tell me which case applied. Wait for my confirmation.

After I confirm:
- If Case 1: commit: chore(p4): verify cmd_status already complete
- If Case 2 or 3: commit: feat(p4): implement cmd_status in main.py
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P4.3


==============================================================================
TASK P4.3 — Example pool verification
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p4-learning
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P4.md Task P4.3 — read it fully

This is a verification task. No code changes unless a bug is found.
If a bug is found: fix it, py_compile, commit as fix(p4): <description>, then continue.

Pre-condition: at least one document row must exist in DB from P3.
If none: run python main.py generate for any approved job, save, rate >= 4 — then proceed.

Run all 6 steps from Tasks_P4.md Task P4.3 in order.
Show me the exact command and full output for each step.

For Step 3: only run the force-rating script if no letter is already rated >= 4.
If you run Step 3, re-run Steps 1 and 2 to confirm the flag was set.

After all steps pass:
- Report PASS or FAIL for each acceptance criterion from Task P4.3
- No commit if no bugs were found
- Wait for my confirmation
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P4.4 until I say so


==============================================================================
TASK P4.4 — End-to-end test
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p4-learning
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/Tasks_P4.md Task P4.4 — all 5 steps and pre-conditions

This is a verification task. No code changes unless a bug is found.
If a bug is found: fix it, py_compile, commit as fix(p4): <description>, then continue.

IMPORTANT — run the pre-condition check first and stop if fewer than 2 eligible jobs:
```
python -c "
from src.db import get_jobs
eligible = [j for j in get_jobs() if j['status'] in ('applied','responded','interview')]
print(f'Eligible jobs: {len(eligible)}')
for j in eligible: print(f'  {j[\"id\"]} | {j[\"company\"]} | {j[\"status\"]}')
"
```
Step 1 records a no_reply outcome which closes job A, removing it from the eligible pool.
Step 2 needs a separate job B. If fewer than 2 eligible jobs exist — stop, tell me,
and run python main.py generate once more before starting.

Three technical rules for this task:
1. Verification scripts using raw sqlite3.connect() must set conn.row_factory = sqlite3.Row
   immediately after connecting, before any fetchone() passed to dict(). Already included
   in the scripts in Tasks_P4.md — do not remove it.
2. Synthetic outcomes in Step 4 use reply_type='positive' (maps to status='responded'),
   which keeps those jobs in the eligible pool. Never use 'no_reply' for synthetics —
   it closes jobs and would exhaust the pool before the summary panel can be triggered.
3. cmd_status() calls record_outcome() only — never update_job_status() directly.

Steps 1, 2, and 3 require interactive terminal input — run `python main.py status`
yourself in the terminal, drive the prompts, then paste the full terminal output here.
After each of those steps I will run the verification script and confirm the DB state.
Steps 4 and 5 I will drive in full.

Note: Step 5 makes a live AI API call (python main.py generate). Ensure your API key
is set and you are comfortable with one generation token cost.

After all 5 steps pass:
- Report PASS or FAIL for each acceptance criterion from Task P4.4
- No commit if no bugs were found
- Wait for my confirmation
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Do not start Task P4.5 until I say so


==============================================================================
TASK P4.5 — Completion check + merge to main
==============================================================================

You are working on the JobRadar project.
Project folder: C:\Users\jiriv\source\repos\JobRadar

First, verify you are on the correct branch:
- Run: git branch --show-current
- Expected: feature/p4-learning
- If different: stop immediately and tell me. Do not proceed.

Before starting, read:
- docs/AI_INSTRUCTIONS.md sections 8, 9, and 10
- docs/Tasks_P4.md — Completion Checklist and Task P4.5

PART 1 — Run every item in the Completion Checklist from Tasks_P4.md.
Run each in order. Show me the exact output.
Report PASS or FAIL for each item.
Stop here and wait for my confirmation before doing anything else.

--- wait for Jiri to say "ok to merge" ---

PART 2 — Only after I explicitly say "ok to merge":

1. Update docs/MILESTONES.md: P4 status -> "Done"
2. Commit: docs(p4): mark P4 complete in MILESTONES.md
3. Run:
   git checkout main
   git merge feature/p4-learning --no-ff -m "feat(p4): merge Phase 4 learning loop"
   git checkout -b feature/p5-web-ui
4. Run: git branch --show-current   (expected: feature/p5-web-ui)
5. Run: git log --oneline -5
6. Show me both outputs
7. Wait for my final confirmation

After I confirm:
- Complete the Task Closing Ritual from AI_INSTRUCTIONS.md section 10
- Report: "Phase 4 complete. On branch feature/p5-web-ui. Ready for P5."