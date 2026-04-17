"""All SQLite database operations for JobRadar.

Rules:
- No AI calls, no parsing — sqlite3 standard library only.
- activity_log is APPEND ONLY — never UPDATE or DELETE rows in it.
- All timestamps in UTC ISO format via now_iso().
- Row factory: sqlite3.Row (allows dict-style access).
"""

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DB_PATH = Path("data/tracker.db")


def get_conn() -> sqlite3.Connection:
    """Open and return a WAL-mode SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def make_job_id(company: str, role: str, date: str) -> str:
    """Build a slug-based job ID from company, role, and date.

    Args:
        company: Company name (e.g. 'Acme GmbH')
        role: Role title (e.g. 'Senior Data Engineer')
        date: Date string in YYYYMMDD format (e.g. '20260328')

    Returns:
        Slug string: '{company-slug}-{role-slug}-{date}'
        Example: 'acme-gmbh-senior-data-engineer-20260328'
    """
    def slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")

    return f"{slugify(company)}-{slugify(role)}-{date}"


def insert_job(data: dict, source: str = "system", date_str: str | None = None) -> str:
    """Insert a new job record and log a 'scored' action. Return the job_id.

    Args:
        data: Dict with job fields. Required keys: company, role_title.
              Optional: location, remote_type, language, score, score_reason,
              status, source_eml, jd_text, tech_stack, salary,
              strong_matches, concerns, notes.
        source: 'system' (default) or 'manual' for backfill entries.
        date_str: Date in YYYYMMDD format for the job ID. Defaults to today.
    """
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y%m%d")
    job_id = make_job_id(data.get("company") or "unknown", data.get("role_title") or "unknown", date_str)
    ts = now_iso()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, company, role_title, location, remote_type, url, language,
                score, score_reason, status, source_eml, jd_text,
                tech_stack, salary, strong_matches, concerns, notes,
                created_at, updated_at, applied_at
            ) VALUES (
                :id, :company, :role_title, :location, :remote_type, :url, :language,
                :score, :score_reason, :status, :source_eml, :jd_text,
                :tech_stack, :salary, :strong_matches, :concerns, :notes,
                :created_at, :updated_at, :applied_at
            )
            """,
            {
                "id": job_id,
                "company": data["company"],
                "role_title": data["role_title"],
                "location": data.get("location"),
                "remote_type": data.get("remote_type"),
                "url": data.get("url"),
                "language": data.get("language", "en"),
                "score": data.get("score"),
                "score_reason": data.get("score_reason"),
                "status": data.get("status", "new"),
                "source_eml": data.get("source_eml"),
                "jd_text": data.get("jd_text"),
                "tech_stack": data.get("tech_stack"),
                "salary": data.get("salary"),
                "strong_matches": data.get("strong_matches"),
                "concerns": data.get("concerns"),
                "notes": data.get("notes"),
                "created_at": ts,
                "updated_at": ts,
                "applied_at": None,
            },
        )
        conn.execute(
            "INSERT INTO activity_log (job_id, action, ts, source) VALUES (?, 'scored', ?, ?)",
            (job_id, ts, source),
        )

    return job_id


def update_job_status(job_id: str, status: str, notes: str | None = None, applied_at: str | None = None) -> None:
    """Update a job's status and append an entry to activity_log.

    Args:
        job_id: The job's primary key.
        status: New status value (e.g. 'approved', 'rejected', 'applied').
        notes: Optional free-text note stored on the job row.
        applied_at: Date in YYYYMMDD format. Defaults to today when status is 'applied'.
    """
    ts = now_iso()
    if status == "applied" and applied_at is None:
        applied_at = datetime.now(timezone.utc).strftime("%Y%m%d")
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ?, notes = COALESCE(?, notes)"
            ", applied_at = COALESCE(?, applied_at) WHERE id = ?",
            (status, ts, notes, applied_at, job_id),
        )
        conn.execute(
            "INSERT INTO activity_log (job_id, action, detail, ts) VALUES (?, ?, ?, ?)",
            (job_id, status, notes, ts),
        )


def set_applied_at(job_id: str, date_str: str) -> None:
    """Manually override the applied_at date for a job.

    Args:
        job_id: The job's primary key.
        date_str: Date in YYYYMMDD format.
    """
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET applied_at = ?, updated_at = ? WHERE id = ?",
            (date_str, now_iso(), job_id),
        )


def set_job_url(job_id: str, url: str) -> None:
    """Set or update the url for a job row."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET url = ?, updated_at = ? WHERE id = ?",
            (url, now_iso(), job_id),
        )


def get_jobs(status: str | None = None, min_score: int = 0) -> list[dict]:
    """Return jobs filtered by status and minimum score, ordered by score descending.

    Args:
        status: If provided, only return jobs with this status.
        min_score: Only return jobs with score >= this value (default 0 = all).
    """
    with get_conn() as conn:
        if status is not None:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? AND COALESCE(score, 0) >= ? ORDER BY score DESC",
                (status, min_score),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE COALESCE(score, 0) >= ? ORDER BY score DESC",
                (min_score,),
            ).fetchall()
    return [dict(row) for row in rows]


def get_job(job_id: str) -> dict | None:
    """Return a single job by ID, or None if not found."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def job_exists_for_eml(source_eml: str) -> bool:
    """Return True if any job has already been imported from this EML file."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM jobs WHERE source_eml = ? LIMIT 1", (source_eml,)
        ).fetchone()
    return row is not None


def log_action(
    job_id: str,
    action: str,
    detail: str | None = None,
    source: str = "system",
) -> None:
    """Append a row to activity_log. This table is APPEND ONLY — never update or delete.

    Args:
        job_id: The related job's primary key.
        action: Action label (e.g. 'scored', 'approved', 'applied').
        detail: Optional free-text detail.
        source: 'system' (default) or 'manual' for backfill entries.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (job_id, action, detail, ts, source) VALUES (?, ?, ?, ?, ?)",
            (job_id, action, detail, now_iso(), source),
        )


def save_document(job_id: str, doc_type: str, path: str) -> int:
    """Insert a document record and return its new row ID.

    Args:
        job_id: The related job's primary key.
        doc_type: 'cv' or 'cover_letter'.
        path: File path to the saved document.
    """
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO documents (job_id, doc_type, path, created_at) VALUES (?, ?, ?, ?)",
            (job_id, doc_type, path, now_iso()),
        )
        return cursor.lastrowid


def rate_document(doc_id: int, rating: int) -> None:
    """Set a document's rating and mark it as a style example if rating >= 4.

    Args:
        doc_id: The document's primary key.
        rating: Integer rating 1-5.
    """
    use_as_example = 1 if rating >= 4 else 0
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET rating = ?, use_as_example = ? WHERE id = ?",
            (rating, use_as_example, doc_id),
        )


def get_example_letters(min_rating: int = 4, limit: int = 3) -> list[dict]:
    """Return the highest-rated cover letters marked as style examples.

    Args:
        min_rating: Minimum rating threshold (default 4).
        limit: Maximum number of letters to return (default 3).
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM documents
            WHERE doc_type = 'cover_letter'
              AND use_as_example = 1
              AND rating >= ?
            ORDER BY rating DESC
            LIMIT ?
            """,
            (min_rating, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def record_outcome(
    job_id: str,
    reply_type: str,
    reply_date: str | None = None,
    notes: str | None = None,
) -> None:
    """Record outcome. Updates job status and logs to activity_log.

    Args:
        job_id: The related job's primary key.
        reply_type: One of: no_reply | rejection | positive | interview | offer.
        reply_date: Optional date of the reply (ISO string).
        notes: Optional free-text notes.
    """
    VALID = {'no_reply', 'rejection', 'positive', 'interview', 'offer'}
    if reply_type not in VALID:
        raise ValueError(f"Invalid reply_type: {reply_type!r}. Must be one of {VALID}")

    STATUS_MAP = {
        'no_reply':  'closed',
        'rejection': 'closed',
        'positive':  'responded',
        'interview': 'interview',
        'offer':     'offer',
    }
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO outcomes (job_id, reply_type, reply_date, notes, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (job_id, reply_type, reply_date, notes, ts),
        )
        conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (STATUS_MAP[reply_type], ts, job_id),
        )
    log_action(job_id, 'outcome', detail=reply_type)


def get_outcomes(job_id: str) -> list[dict]:
    """Return all outcomes for a job, ordered by created_at ASC.

    Args:
        job_id: The related job's primary key.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM outcomes WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_weekly_summary() -> dict | None:
    """Return summary stats if >= 5 outcomes exist, else return None.

    Keys:
      total_outcomes      int   -- total rows in outcomes table
      response_rate       float -- % of outcomes that are NOT no_reply
      avg_score_responded float -- avg AI score of jobs with positive/interview/offer outcome
      top_status          str   -- most common reply_type
    """
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
        if total < 5:
            return None

        responded = conn.execute(
            "SELECT COUNT(*) FROM outcomes WHERE reply_type != 'no_reply'"
        ).fetchone()[0]

        avg_row = conn.execute(
            """SELECT AVG(j.score) FROM outcomes o
               JOIN jobs j ON j.id = o.job_id
               WHERE o.reply_type IN ('positive', 'interview', 'offer')"""
        ).fetchone()
        avg_score = avg_row[0] if avg_row[0] is not None else 0.0

        top_row = conn.execute(
            """SELECT reply_type FROM outcomes
               GROUP BY reply_type ORDER BY COUNT(*) DESC LIMIT 1"""
        ).fetchone()
        top_status = top_row[0] if top_row else 'n/a'

    return {
        'total_outcomes':      total,
        'response_rate':       responded / total * 100,
        'avg_score_responded': avg_score,
        'top_status':          top_status,
    }


def get_activity_report(date_from: str, date_to: str) -> list[dict]:
    """Return one row per job in the applied_at date range, with latest action.

    Args:
        date_from: Start of range in YYYYMMDD format (inclusive).
        date_to: End of range in YYYYMMDD format (inclusive).
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                j.applied_at, j.company, j.role_title, j.location,
                j.status, j.score,
                a.action, a.detail, a.source
            FROM jobs j
            LEFT JOIN activity_log a ON a.job_id = j.id
              AND a.action = (
                  SELECT action FROM activity_log
                  WHERE job_id = j.id
                  ORDER BY ts DESC LIMIT 1
              )
            WHERE j.applied_at >= ? AND j.applied_at <= ?
            ORDER BY j.applied_at ASC
            """,
            (date_from, date_to),
        ).fetchall()
    return [dict(row) for row in rows]


def get_stats() -> dict:
    """Return summary counts across the jobs and activity_log tables."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) as count FROM jobs GROUP BY status"
        ).fetchall()
        total_actions = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]

    stats: dict = {
        "total_jobs": total,
        "total_actions": total_actions,
        "by_status": {row["status"]: row["count"] for row in by_status},
    }
    return stats


def get_activity_log(
    job_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return activity log rows, most recent first.

    Optionally filter by job_id and/or action type.

    Args:
        job_id: If provided, return only rows for this job.
        action: If provided, return only rows with this action label.
        limit: Maximum number of rows to return (default 100).
    """
    query = "SELECT * FROM activity_log WHERE 1=1"
    params: list = []
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if action:
        query += " AND action = ?"
        params.append(action)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_documents(job_id: str) -> list[dict]:
    """Return all documents for a job, ordered by created_at DESC.

    Args:
        job_id: The related job's primary key.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(doc_id: int) -> dict | None:
    """Return a single document row by id, or None if not found.

    Args:
        doc_id: The document's primary key.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def init_db() -> None:
    """Create all four database tables if they do not already exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id            TEXT PRIMARY KEY,
                company       TEXT NOT NULL,
                role_title    TEXT NOT NULL,
                location      TEXT,
                remote_type   TEXT,
                url           TEXT,
                language      TEXT DEFAULT 'en',
                score         INTEGER,
                score_reason  TEXT,
                status        TEXT DEFAULT 'new',
                source_eml    TEXT,
                jd_text       TEXT,
                tech_stack    TEXT,
                salary        TEXT,
                strong_matches TEXT,
                concerns      TEXT,
                notes         TEXT,
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL,
                applied_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id  TEXT NOT NULL,
                action  TEXT NOT NULL,
                detail  TEXT,
                ts      TEXT NOT NULL,
                source  TEXT DEFAULT 'system'
            );

            CREATE TABLE IF NOT EXISTS documents (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id         TEXT NOT NULL,
                doc_type       TEXT NOT NULL,
                path           TEXT NOT NULL,
                version        INTEGER DEFAULT 1,
                rating         INTEGER,
                use_as_example INTEGER DEFAULT 0,
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outcomes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      TEXT NOT NULL,
                reply_type  TEXT,
                reply_date  TEXT,
                notes       TEXT,
                created_at  TEXT NOT NULL
            );
        """)

    # Migration: add url column if not present in existing DB
    try:
        with get_conn() as conn:
            conn.execute("ALTER TABLE jobs ADD COLUMN url TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists


def job_exists_exact(company: str, role_title: str, date_str: str) -> bool:
    """Return True if a job with exact company, role_title, and date already exists.

    Args:
        company: Company name to match exactly.
        role_title: Role title to match exactly.
        date_str: Date in YYYYMMDD format.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM jobs WHERE company = ? AND role_title = ?"
            " AND applied_at = ? LIMIT 1",
            (company, role_title, date_str),
        ).fetchone()
    return row is not None


def find_similar_job(company: str, role_title: str, days: int = 90) -> dict | None:
    """Find an existing job with same company and similar role title within the last N days.

    Args:
        company: Company name to match exactly.
        role_title: Role title to compare for word overlap.
        days: Look-back window in days (default 90).

    Returns:
        The most recent matching job as a dict, or None if no match found.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM jobs
            WHERE company = ?
              AND created_at >= ?
              AND status != 'rejected'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (company, cutoff),
        ).fetchone()
    if not row:
        return None
    # Check role similarity — at least one common significant word
    stopwords = {"senior", "junior", "and", "or", "the", "in", "for", "m/f/d", "with"}
    existing_words = set(row["role_title"].lower().split()) - stopwords
    new_words = set(role_title.lower().split()) - stopwords
    return dict(row) if existing_words & new_words else None


def reset_db() -> dict:
    """Delete all rows from job-related tables. Schema unchanged.

    NOTE: Deleting from activity_log is a deliberate one-time exception
    to the APPEND ONLY rule, used to wipe P1 test data. Do not reuse
    this pattern elsewhere.
    """
    tables = ["outcomes", "documents", "activity_log", "jobs"]
    counts = {}
    with get_conn() as conn:
        for table in tables:
            cur = conn.execute(f"DELETE FROM {table}")
            counts[table] = cur.rowcount
    return counts
