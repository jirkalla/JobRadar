# Plan: Improve Job Description Fetching
# JobRadar | Fix — targeted fix for advertsdata.com PDF extraction
# Status: ✅ Done — merged to main 2026-04-10
# Branch: fix/fetch-pdf-extraction (created from main after P2 merge)

---

## Problem

The current `fetch_job_description()` in `src/parser.py` uses a simple urllib
HTTP request. advertsdata.com returns ~5000 chars of homepage HTML — never the
actual job description — because the server requires a session cookie.

The real JD is a PDF embedded in an iframe. The PDF URL follows this pattern:

  https://db.advertsdata.com/dokuserver/anzeigen/YYYY/MM/DD/HH/O-LINK_XXXXXXXXX.pdf

The PDF URL is NOT present in the raw HTML source (requires auth cookie to render).
It is only discoverable by running JavaScript in a real browser — specifically by
inspecting the iframe frame URLs after page load.

Confirmed working:
- Playwright (headless=False) navigates to the tracking URL
- After 4s wait, the PDF URL appears as a frame URL
- Direct urllib download of that PDF URL works with no auth (no cookie needed)
- pypdf extracts ~4800 chars of clean job description text

---

## Branching

This fix is implemented after P2 is merged to main.
It goes on its own branch off main — not mixed into any milestone branch.

Pre-condition: confirm P2 is merged before starting.
```
git log --oneline -3   # should show P2 merge commit at top on main
```

Then create the branch:
```
git checkout main
git checkout -b fix/fetch-pdf-extraction
```

After all verification steps pass and Jiri confirms:
```
git checkout main
git merge fix/fetch-pdf-extraction --no-ff -m "fix(parser): two-step PDF extraction for advertsdata.com"
```

AI MUST ask Jiri before merging. Never push without asking.

---

## Solution — Playwright frame inspection + urllib PDF download

Step 1: Launch Playwright browser (headless=False — headless is detected as bot).
        Navigate to the advertsdata.com tracking URL.
        Wait 4 seconds for the PDF iframe to render.
        Inspect all frame URLs — find the one matching dokuserver/anzeigen/...pdf.
        Close the browser.

Step 2: Download the PDF directly with urllib (no auth needed for dokuserver URLs).
        Extract text with pypdf.PdfReader.

Fallback: if no PDF frame URL found (or any exception), return ''.
          scorer.py marks job as fetch_failed. Continue processing.

For non-advertsdata.com URLs: existing urllib HTML extraction unchanged.

New dependency: playwright (+ `playwright install chromium` for Chromium binary).

---

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Storage | SQLite only (jd_text column) | Already in schema, no extra files needed |
| Fetch failure | Return '' + mark fetch_failed in scorer | Never block the batch for one failed URL |
| Workflow | Inside existing process command | No friction added to daily fetch→process→review flow |
| Caching | Deferred — not in this fix | `insert_job()` already stores `jd_text`; cache lookup requires URL→job_id pre-query before scoring — deferred to later |
| URL scope | advertsdata.com only for now | Only confirmed source; fallback handles everything else |
| Truncation | Increase from 5000 to 8000 chars | PDFs are longer; was already planned in P1 notes |
| Playwright headless | headless=False required | headless=True is detected as bot — PDF iframe never loads (confirmed by testing) |
| Browser flash | Acceptable — ~4-8s per job, browser opens and closes | Confirmed acceptable by Jiri |
| applied_at column | Not touched by this fix | applied_at is set at insert time via date_str in insert_job(). Fetch logic does not read or write applied_at. |

---

## Changes required

### src/parser.py

Replace `fetch_job_description()` entirely. No other functions touched.

```python
def fetch_job_description(url: str, timeout: int = 15) -> str:
    """
    Fetch full job description text from a job listing URL.

    For advertsdata.com URLs:
      1. Opens Playwright browser (headless=False — headless detected as bot)
      2. Navigates to tracking URL, waits 4s for PDF iframe to render
      3. Finds frame URL matching dokuserver/anzeigen/...pdf pattern
      4. Downloads PDF directly with urllib (no auth needed for dokuserver)
      5. Extracts text with pypdf.PdfReader

    For all other URLs:
      Falls back to existing urllib HTML text extraction.

    Returns empty string on failure — caller handles gracefully.
    """
    import io
    import re as _re

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        if "advertsdata.com" in url:
            # Step 1: use Playwright to discover PDF URL from iframe frame
            from playwright.sync_api import sync_playwright
            pdf_url = None
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                pw_page = browser.new_page()
                pw_page.goto(url, wait_until="networkidle", timeout=25_000)
                pw_page.wait_for_timeout(4000)
                for frame in pw_page.frames:
                    if "dokuserver/anzeigen" in frame.url and frame.url.endswith(".pdf"):
                        pdf_url = frame.url
                        break
                browser.close()

            if not pdf_url:
                return ""

            # Step 2: download PDF — no auth needed for dokuserver URLs
            pdf_req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(pdf_req, timeout=timeout) as pdf_resp:
                pdf_bytes = pdf_resp.read()
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join(pdf_page.extract_text() or "" for pdf_page in reader.pages)

        else:
            # Fallback: plain HTML extraction for non-advertsdata URLs
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                html = resp.read(200_000).decode(charset, errors="replace")
            text = _html_to_text(html)

        # Normalise whitespace
        text = _re.sub(r"\n{3,}", "\n\n", text)
        text = _re.sub(r" {2,}", " ", text)

        # Truncate (increased from 5000 to 8000 — PDFs are longer)
        if len(text) > 8000:
            text = text[:8000] + "\n\n[truncated]"

        return text.strip()

    except Exception:
        return ""  # Caller checks for empty string and marks fetch_failed
```

### requirements.txt

Add `playwright` on a new line (after the existing entries).

After adding, run:
```
playwright install chromium
```
Expected: Chromium binary downloaded (~150MB). Only needed once per machine.

### src/db.py

No changes required. `insert_job()` already persists `jd_text` via the result
dict returned by `score_job()`. A separate `save_jd_text()` function is not needed.

### src/scorer.py

Two targeted changes only. Read the current `src/scorer.py` first.

**Change 1** — add `status` parameter to `_failed_result()`:

Replace the function signature:
  def _failed_result(stub: JobStub, reason: str, jd_text: str = "") -> dict:

With:
  def _failed_result(stub: JobStub, reason: str, jd_text: str = "", status: str = "new") -> dict:

And in its return dict, replace:
      "status":        "new",
With:
      "status":        status,

**Change 2** — fix the fetch failure check in `score_job()`:

Replace:
  jd_text = fetch_job_description(stub.url)

  if len(jd_text) < 300:
      return _failed_result(stub, "Could not fetch job description")

With:
  jd_text = fetch_job_description(stub.url)

  if not jd_text:
      return _failed_result(stub, "Could not fetch job description", status="fetch_failed")

IMPORTANT: do NOT set or modify applied_at. Do NOT touch any other function.
Do NOT add imports.

---

## Status handling for fetch failures

fetch_failed is a new status value in the jobs lifecycle:

  new → fetch_failed   (URL returned nothing useful)
  new → reviewed → ... (normal path)

fetch_failed jobs:
- Stored in DB with all EML metadata (title, company, location)
- jd_text = NULL
- Not shown in review list (score = NULL, no point reviewing)

No DB schema change needed — status column already accepts any text value.

---

## Verification steps

After each file change: python -m py_compile {file} — silence = success.
Follow task closing ritual after each file. Wait for Jiri to confirm each one.

1. Syntax checks:
   ```
   python -m py_compile src/parser.py
   python -m py_compile src/scorer.py
   ```
   Expected: no output.

2. Unit test fetch in isolation — use a fresh URL from a newly fetched EML:
   ```
   python -c "
   from src.parser import fetch_job_description
   url = '<paste a fresh matching.cfm URL from inbox EML>'
   text = fetch_job_description(url)
   print('Length:', len(text), 'chars')
   print(text[:500])
   "
   ```
   Expected: browser opens briefly, closes, then 3000+ chars printed.
   Note: matching.cfm URLs contain session tokens that expire.
         Always use a fresh URL from a recently downloaded EML.

3. Fetch failure test:
   ```
   python -c "
   from src.parser import fetch_job_description
   text = fetch_job_description('https://db.advertsdata.com/matching/matching.cfm?id=INVALID')
   print(repr(text))
   "
   ```
   Expected: empty string '', no exception raised.

4. Full end-to-end:
   ```
   python main.py fetch
   python main.py process
   python main.py review
   ```
   Expected: jobs shown with real scores based on actual JD content.

---

## Files changed

  src/parser.py    — fetch_job_description() replaced with Playwright approach
  src/scorer.py    — failure threshold fixed, fetch_failed status added
  requirements.txt — playwright added

## Files NOT changed

  src/db.py, src/fetcher.py, src/ai_client.py, src/generator.py, src/report.py
  main.py, config/

---

## Commit sequence

  fix(parser): replace fetch_job_description with Playwright PDF extraction
  fix(scorer): fix fetch failure threshold and add fetch_failed status
  chore(deps): add playwright to requirements