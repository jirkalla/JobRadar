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

---

## Prompt & AI — Structural Improvements

### 1. Voice block — structural problem across all prompts 🔴
**Problem:** `voice` in `profile.yaml` serves two incompatible purposes. It is written as a cover letter narrative (biographical facts, eBay decade, basketball, Potsdam) but is injected into prompts as a tone/style signal. Every prompt using `{voice}` must warn the AI to ignore the factual content — an unreliable instruction.

**Root cause:** No dedicated fact-free tone signal exists. `voice` is doing two jobs and does neither cleanly.

**Fix:** Add a separate `background` key to `profile.yaml` — 2–3 sentences, structured facts only, for scoring and CV context. Keep `voice` for `generate.txt` only, where biographical narrative is useful as a style calibrator.

```yaml
background: |
  A decade at eBay building financial reporting infrastructure and data pipelines
  at enterprise scale — C# backend systems, Python automation, Snowflake migration,
  SQL processes where correctness was non-negotiable because C-level finance teams
  read the output.
```

**Affected files:**
- `config/profile.yaml` — add `background` key
- `config/prompts/score.txt` — add `{background}` block (already designed, held back)
- `src/scorer.py` — pass `background` into `build_score_prompt()` `template.format()`
- `config/prompts/cv.txt` — replace `{voice}` with `{background}` (CV tailoring doesn't need biographical tone)
- `src/generator.py` — pass `background` into `build_cv_prompt()` `template.format()`
- `generate.txt` keeps `{voice}` — the one context where full narrative is appropriate

---

### 2. base_cv_text — not wired into cover letter generation 🟠
**Problem:** `generate.txt` lacks a CV fact source, so paragraph 2 in cover letters has no authoritative anchoring. The placeholder and code support already exist for CV tailoring (`cv.txt` + `build_cv_prompt()`) but were not extended to cover letter generation.

**Fix:**
1. Add `{base_cv_text}` section to `config/prompts/generate.txt`
2. In `src/generator.py` `build_cover_letter_prompt()`:
   - Read `examples/cv_base.md`
   - Pass `base_cv_text=base_cv_text` in `template.format()`
   - Update all callers accordingly

**Affected files:**
- `config/prompts/generate.txt`
- `src/generator.py` — `build_cover_letter_prompt()` + callers
- `main.py` — if it calls `build_cover_letter_prompt()` directly

**Note:** A session prompt for this task was already written (see session history).

---

### 3. BANNED_PHRASES dead code in generator.py 🟡
**Problem:** `BANNED_PHRASES` is defined in `generator.py` (~line 27) but never used in the generation flow. The banned phrases list in `generate.txt` is the only enforcement. The two lists are already out of sync — the code list is missing `'i have seen firsthand'`, `'spannend'`, `'begeistert'`.

**Recommended fix:** Wire `BANNED_PHRASES` into a post-generation check that scans output and warns (CLI output or UI message) if a banned phrase appears — adds real enforcement without blocking generation.

**Alternative:** Remove `BANNED_PHRASES` from `generator.py` entirely as dead code.

**Affected files:**
- `src/generator.py`

---

### Dependency order for Prompt & AI items
1. `profile.yaml` — add `background` key
2. `scorer.py` — wire `{background}` (unblocks `score.txt` improvement)
3. `generator.py` — pass `base_cv_text` (unblocks `generate.txt` improvement)
4. `generator.py` — resolve `BANNED_PHRASES` dead code
5. Prompt commits — `score.txt`, `cv.txt` updates (separate from code commits)

Items 1–2 (background key) and item 3 (base_cv_text) are independent and can be done in parallel.
