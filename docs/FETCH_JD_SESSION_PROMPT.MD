# Claude Code Session Prompt — Fix: Job Description Fetch
# Use this after P2 is merged to main.
# Copy and paste this entire block as your first message to Claude Code.

---

Read docs/AI_INSTRUCTIONS.md and docs/FETCH_JD_PLAN.md before doing anything.

We are implementing a fix for the job description fetching in src/parser.py.
This is a standalone fix — not part of any milestone. It runs after P2 is merged.

## Pre-condition check — do this first, before touching any file:

```
git branch --show-current
git log --oneline -3
```

Expected: currently on main, P2 merge commit visible at top.
If not on main or P2 not merged — stop and tell me. Do not proceed.

## Create the branch:

```
git checkout -b fix/fetch-pdf-extraction
```

Confirm you are on fix/fetch-pdf-extraction before touching any file.

---

## Context — what was discovered

The current fetch_job_description() in src/parser.py fails on advertsdata.com
URLs because the server requires a session cookie — without it, urllib receives
only homepage HTML (~5000 chars, no JD content).

The real JD is a PDF embedded in an iframe. Testing confirmed:
- The PDF URL is NOT in the raw HTML source — only available after JS executes
- Playwright (headless=False) finds the PDF URL in frame 3 after ~4s wait
- headless=True fails — detected as bot, PDF iframe never loads (confirmed)
- Direct urllib download of the dokuserver/...pdf URL works with no auth
- pypdf extracts ~4800 chars of clean JD content (confirmed working)
- playwright must be added to requirements.txt
- After pip install: run `playwright install chromium` once (~150MB download)

---

## The two tasks — do them in this order, one at a time

### Task 1 — src/parser.py + requirements.txt
Read the current src/parser.py first.
Replace fetch_job_description() with the Playwright implementation in FETCH_JD_PLAN.md.
Do not touch any other function in the file.
Add `playwright` as a new line in requirements.txt.
After editing parser.py: python -m py_compile src/parser.py
Then run verification step 2 from FETCH_JD_PLAN.md (use a fresh URL from inbox EML).
Wait for my confirmation before Task 2.
Commits (two separate commits):
  fix(parser): replace fetch_job_description with Playwright PDF extraction
  chore(deps): add playwright to requirements

### Task 2 — src/scorer.py
Read the current src/scorer.py first.
Make the two targeted changes described in FETCH_JD_PLAN.md:
  1. Add status parameter to _failed_result()
  2. Replace the len(jd_text) < 300 check with the fetch_failed path
Do not touch any other function in the file.
After editing: python -m py_compile src/scorer.py
Run verification steps 3 and 4 from FETCH_JD_PLAN.md.
Wait for my confirmation before merging.
Commit: fix(scorer): fix fetch failure threshold and add fetch_failed status

---

## After both tasks pass

Show me the git log and ask:
"Both tasks complete. Ready to merge fix/fetch-pdf-extraction to main. Confirm?"

Do NOT merge until I say yes.
Do NOT push until I say yes.

Merge command (only after my confirmation):
```
git checkout main
git merge fix/fetch-pdf-extraction --no-ff -m "fix(parser): two-step PDF extraction for advertsdata.com"
```

---

## Hard rules for this session

- Read each file before editing it — never overwrite blindly
- One task at a time — wait for my confirmation after each
- Do not touch: main.py, db.py, fetcher.py, ai_client.py, generator.py, report.py, config/
- Only new package allowed: playwright (already confirmed by Jiri)
- Follow the task closing ritual from AI_INSTRUCTIONS.md section 10 after every task