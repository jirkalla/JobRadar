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

### Edit applied_at from the UI
- Currently only editable via CLI (`set_applied_at()` in db.py)
- Add a small inline form or modal on the job detail page to update `applied_at`
- Route: POST /jobs/{id}/applied_at with a date input field
- Redirect back to GET /jobs/{id}?msg=Date+updated

---

## UX — General

### Pagination
- Defer until job count exceeds ~100
- When added: use `LIMIT`/`OFFSET` in `get_jobs()`, pass `page` and `per_page` params
- Show "Page X of Y" and prev/next controls in the table footer
