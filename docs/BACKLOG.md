# JobRadar — Backlog

Items deferred from P5 implementation. Prioritize after P5.10 is merged.

---

## UX — Job List (/jobs)

### Search box
- Add a text search input to the filter bar
- Filter on `company` + `role` fields (case-insensitive)
- Implementation: add `search: str | None = None` param to `get_jobs()` in db.py
  using `LIKE '%?%'` on both columns, or filter in Python post-fetch
- UI: single text input in the filter bar, next to the status dropdown

### Date filtering (default to recent jobs)
- With many jobs the list grows unbounded; default to last 90 days
- Add `days: int = 90` query param, filter by `created_at >= today - days`
- Add a "Show all" toggle link that passes `days=0`
- Consider also a date range picker (date_from / date_to) for precise filtering

### "Needs action" filter presets
- Add one-click preset buttons above the table:
  - **Needs review** → status=reviewed
  - **Ready to apply** → status=approved
  - **In progress** → status in (applied, responded, interview)
  - **Closed** → status in (closed, rejected)
- Implemented as anchor links with pre-filled query params, not a new route

---

## UX — Job Detail (/jobs/{id})

### Reject button on job detail page
- Currently no way to reject a job from the UI — requires CLI (`python main.py review` → `R`)
- Add a red "Reject" button next to the "Approve" button at the top of the job detail page
- Show it when status is `new` or `reviewed` (same condition as Approve)
- Route: POST /jobs/{id}/status with `action=reject` (already handled by `update_job_status`)
- Redirect back to GET /jobs/{id}?msg=Rejected

### Edit applied_at from the UI
- Currently only editable via CLI (`set_applied_at()` in db.py)
- Add a small inline form or modal on the job detail page to update `applied_at`
- Route: POST /jobs/{id}/applied_at with a date input field
- Redirect back to GET /jobs/{id}?msg=Date+updated

---

## UX — Manual Job Entry (/jobs/new)

### AI score-on-demand for manually added jobs
- Manually added jobs enter with `score=0`, `score_reason="(not scored — added manually)"`
- There is currently no way to trigger AI scoring via the UI after manual entry
- Proposed: add a "Score this job" button on the job detail page, visible when score=0
- Route: POST /jobs/{id}/score — calls `scorer.score_job()` with the stored `jd_text`,
  updates `score`, `score_reason`, `tech_stack`, `strong_matches`, `concerns` in DB
- Show on detail page only when `jd_text` is present and `score == 0`
- After scoring: redirect to GET /jobs/{id}?msg=Job+scored

---

## UX — General

### Pagination
- Defer until job count exceeds ~100
- When added: use `LIMIT`/`OFFSET` in `get_jobs()`, pass `page` and `per_page` params
- Show "Page X of Y" and prev/next controls in the table footer
