# Plan: Add date-range support to `fetch` command
# JobRadar | Amendment to P1.6 — targeted fetcher improvement
# Status: ready to implement

---

## TL;DR

Add optional `--since` and `--until` flags to `python main.py fetch` so you can
download emails from a specific date range. Both flags use ISO format YYYY-MM-DD.
The code translates to IMAP's DD-Mon-YYYY format internally. The user never sees
the IMAP format.

---

## User-facing behaviour after this change

  python main.py fetch
    Default behaviour — UNSEEN emails only (normal Tuesday use). Unchanged.

  python main.py fetch --since 2026-02-16
    All emails from 16 Feb onwards, read or unread.

  python main.py fetch --since 2026-02-16 --until 2026-02-22
    Emails from 16 Feb to 22 Feb inclusive. --until is inclusive from user
    perspective — code adds +1 day internally for IMAP BEFORE.

  python main.py fetch --date 2026-03-31
    Single-day shortcut. Unchanged.

  python main.py fetch --until 2026-02-22
    ERROR — --until requires --since. Clear error message, no download.

---

## Changes required

### fetcher.py

1. Update fetch_digests() signature:
   ```python
   def fetch_digests(
       inbox_dir: Path,
       processed_dir: Path,
       env: dict,
       since: str | None = None,    # YYYY-MM-DD, optional
       until: str | None = None,    # YYYY-MM-DD, inclusive, optional
   ) -> tuple[int, list[str]]:
   ```

2. Update docstring:
   ```
   since: lower bound date (YYYY-MM-DD). Replaces UNSEEN filter when set.
   until: upper bound date (YYYY-MM-DD, inclusive). Requires since.
          Translates to IMAP BEFORE (exclusive) by adding 1 day internally.
   ```

3. IMAP search parts builder — replace current UNSEEN-only logic:
   ```python
   from datetime import date, timedelta

   def _to_imap_date(iso: str) -> str:
       """Convert YYYY-MM-DD to DD-Mon-YYYY for IMAP."""
       d = date.fromisoformat(iso)
       return d.strftime("%d-%b-%Y")  # e.g. "16-Feb-2026"

   # Build search criteria
   parts = ['FROM "info@anzeigendaten.de"']

   if since:
       parts.append(f'SINCE {_to_imap_date(since)}')
       if until:
           # IMAP BEFORE is exclusive — add 1 day to make until inclusive
           until_exclusive = date.fromisoformat(until) + timedelta(days=1)
           parts.append(f'BEFORE {until_exclusive.strftime("%d-%b-%Y")}')
   else:
       parts.append('UNSEEN')   # default: unread only

   _, msg_ids = imap.search(None, *parts)
   ```

### main.py

1. Add --since and --until to fetch_parser argument block:
   ```python
   fetch_parser.add_argument(
       '--since', metavar='YYYY-MM-DD',
       help='Download emails from this date (inclusive). Replaces UNSEEN filter.'
   )
   fetch_parser.add_argument(
       '--until', metavar='YYYY-MM-DD',
       help='Download emails up to and including this date. Requires --since.'
   )
   ```

2. Add validation in cmd_fetch() before calling fetch_digests():
   ```python
   if args.until and not args.since:
       console.print("[red]Error: --until requires --since[/red]")
       console.print("Example: python main.py fetch --since 2026-02-16 --until 2026-02-22")
       return
   ```

3. Pass new args to fetch_digests():
   ```python
   count, files = fetch_digests(
       inbox_dir=Path('inbox'),
       processed_dir=Path('data/processed'),
       env=os.environ,
       since=args.since or None,
       until=args.until or None,
   )
   ```

---

## Decisions

- YYYY-MM-DD for ALL user-facing flags (--since, --until, --date) — consistent
- IMAP DD-Mon-YYYY format is internal only — never typed by the user
- --until is INCLUSIVE from user perspective; +1 day added internally for IMAP BEFORE
- --until without --since → clear error, no download
- --date single-day shortcut: untouched
- Default UNSEEN path: untouched
- Already-processed files still skipped even with date range (duplicate check by filename)

---

## Verification steps

1. Syntax check:
   ```
   python -m py_compile src/fetcher.py
   python -m py_compile main.py
   ```
   Expected: no output (silence = success)

2. Flag validation — --until without --since:
   ```
   python main.py fetch --until 2026-02-22
   ```
   Expected: red error "Error: --until requires --since" and example shown

3. Date range fetch — week 16-22 Feb 2026:
   ```
   python main.py fetch --since 2026-02-16 --until 2026-02-22
   ```
   Expected: downloads only emails from that week OR "No new job digests found."
   Check filenames in inbox/ — all should have dates within 16-22 Feb

4. Boundary check — confirm 22 Feb IS included, 23 Feb is NOT:
   ```
   python -c "
   from pathlib import Path
   files = list(Path('inbox').glob('*.eml'))
   for f in files:
       print(f.name)
   "
   ```
   All filenames should show dates 20260216–20260222 only

5. Default path unchanged:
   ```
   python main.py fetch
   ```
   Expected: UNSEEN behaviour unchanged — no date filtering

6. Single-day path unchanged:
   ```
   python main.py fetch --date 2026-03-31
   ```
   Expected: single day behaviour unchanged

---

## Files changed

  src/fetcher.py  — fetch_digests() signature, docstring, IMAP parts builder
  main.py         — --since/--until args, validation guard, pass to fetch_digests()

## Files NOT changed

  src/parser.py, src/scorer.py, src/db.py, src/ai_client.py — untouched
  process command, review command — untouched
  .env.example — untouched (no new env vars needed)