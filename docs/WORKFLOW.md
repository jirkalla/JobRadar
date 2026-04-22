# JobRadar — Daily Workflow

## Overview

| Step | Task | Tool |
|------|------|------|
| 1 | Download EML files from webmail | CLI `fetch` |
| 2 | Process jobs (parse + AI score) | CLI `process` |
| 3 | Review and approve wanted jobs | UI or CLI `review` |
| 4 | Reject unwanted jobs | UI or CLI `review` |
| 5 | Generate CV + Cover Letter | UI (recommended) or CLI `generate` |
| 6 | Edit CV / CL, re-render PDF | `scripts/render.py` |
| 7 | Mark as applied | Auto (UI confirm) or `scripts/set_status.py` |

---

## Step 1 — Download EML files from webmail

**Use: CLI**

```bash
# Fetch today's emails
python main.py fetch

# Fetch a specific date
python main.py fetch --date 2026-04-17

# Fetch a date range
python main.py fetch --since 2026-04-10 --until 2026-04-17
```

> **Fallback:** If IMAP fetch fails, download `.eml` files manually from webmail
> and drop them into `inbox/`. Then proceed to Step 2.

---

## Step 2 — Process jobs (parse + AI score)

**Use: CLI**

```bash
python main.py process
```

What happens:
- Reads all `.eml` files from `inbox/`
- Shows a table of all jobs found in each digest
- Quick pre-filter per job: `ENTER` = keep, `s` = skip, `r` = reject
- AI scores the kept jobs (~2 min per digest)
- Saves scored jobs to the database
- Moves processed `.eml` files to `data/processed/`

---

## Step 3 — Review jobs and approve the ones you want

**Use: UI (preferred) or CLI**

**Start the UI:**
```bash
python start_ui.py
# open http://localhost:8000
```

In the UI: go to `/jobs`, filter by status `new`, open a job → click **Approve**.

**CLI alternative:**
```bash
python main.py review

# Show all including already-reviewed:
python main.py review --all

# Filter by minimum score:
python main.py review --min 6
```

CLI controls per job: `a` = approve, `r` = reject, `n` = add note, `q` = quit

---

## Step 4 — Reject unwanted jobs

**Use: UI (easiest for bulk) or CLI**

In the UI: `/jobs?status=new` → open each → **Reject**

Or use the same `review` session from Step 3 — press `r` per job.

For a specific job by ID:
```bash
python scripts/set_status.py <job_id> rejected
```

---

## Step 5 — Generate CV and Cover Letter

**Use: UI (recommended — preview before saving) or CLI**

**UI way (preferred):**
1. Go to `/jobs?status=approved`
2. Open a job → click **Generate**
3. Preview the cover letter and CV changes
4. Click **Confirm & Save**
   - Files saved to `output/YYYYMMDD/company/`
   - Status automatically set to `applied`

**CLI way:**
```bash
python main.py generate

# Target a specific job directly:
python main.py generate --job-id <job_id>
```

**Generated files per job:**

| File | Description |
|------|-------------|
| `cl_YYYYMMDD_company.md` | Full cover letter (with letterhead) |
| `cl_YYYYMMDD_company_body.md` | Body only — **edit this file** |
| `cl_YYYYMMDD_company.pdf` | Print-ready cover letter PDF |
| `cv_YYYYMMDD_company.md` | Tailored CV in Markdown |
| `cv_YYYYMMDD_company.pdf` | Print-ready CV PDF |
| `score.json` | AI score and reasoning |
| `jd_snapshot.txt` | Job description at time of generation |

---

## Step 6 — Edit CV / Cover Letter, then re-render PDF

**Use: `scripts/render.py`**

Open the file in your editor, make changes, then re-render:

```bash
# After editing cover letter body:
python scripts/render.py output/20260422/company/cl_20260422_company_body.md

# After editing CV:
python scripts/render.py output/20260422/company/cv_20260422_company.md
```

> `render.py` detects the file type automatically:
> - `*_body.md` → rebuilds full cover letter `.md` from letterhead + new body, regenerates PDF
> - `cv_*.md` → regenerates PDF directly from the edited Markdown

---

## Step 7 — Mark as Applied

**Status is set automatically** when you click **Confirm & Save** in the UI.

If you generated via CLI, or need to correct the date:
```bash
python scripts/set_status.py <job_id> applied 20260422
```

> The `applied_at` date (3rd argument, format `YYYYMMDD`) is required for the agency report.

---

## Quick Reference — All CLI Commands

```bash
python main.py fetch                          # download today's emails
python main.py fetch --date 2026-04-17        # specific date
python main.py fetch --since DATE --until DATE # date range
python main.py process                        # parse + score inbox emails
python main.py review                         # review new/reviewed jobs
python main.py review --all --min 6           # review all, score >= 6
python main.py generate                       # generate CV+CL for approved jobs
python main.py generate --job-id <id>         # generate for specific job
python main.py report                         # export agency report (CSV + PDF)
```

```bash
python scripts/render.py <path>               # re-render PDF after editing
python scripts/set_status.py <id> <status> [YYYYMMDD]  # force status change
python scripts/score_job.py <id>              # re-score a manually added job
```

---

## Status Reference

| Status | Meaning |
|--------|---------|
| `new` | Freshly scored, not yet reviewed |
| `reviewed` | Looked at, decision pending |
| `approved` | Selected for CV/CL generation |
| `rejected` | Dismissed, excluded from review |
| `applied` | CV+CL generated and sent |
| `closed` | Position filled / withdrawn |
