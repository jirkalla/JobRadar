"""All SQLite database operations for JobRadar.

Rules:
- No AI calls, no parsing — sqlite3 standard library only.
- activity_log is APPEND ONLY — never UPDATE or DELETE rows in it.
- All timestamps in UTC ISO format via now_iso().
- Row factory: sqlite3.Row (allows dict-style access).
"""

import re
import sqlite3
from datetime import datetime, timezone
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


def insert_job(data: dict) -> str:
    """Insert a new job record and log a 'scored' action. Return the job_id.

    Args:
        data: Dict with job fields. Required keys: company, role_title.
              Optional: location, remote_type, language, score, score_reason,
              status, source_eml, jd_text, tech_stack, salary,
              strong_matches, concerns, notes.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    job_id = make_job_id(data["company"], data["role_title"], date_str)
    ts = now_iso()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, company, role_title, location, remote_type, language,
                score, score_reason, status, source_eml, jd_text,
                tech_stack, salary, strong_matches, concerns, notes,
                created_at, updated_at
            ) VALUES (
                :id, :company, :role_title, :location, :remote_type, :language,
                :score, :score_reason, :status, :source_eml, :jd_text,
                :tech_stack, :salary, :strong_matches, :concerns, :notes,
                :created_at, :updated_at
            )
            """,
            {
                "id": job_id,
                "company": data["company"],
                "role_title": data["role_title"],
                "location": data.get("location"),
                "remote_type": data.get("remote_type"),
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
            },
        )
        conn.execute(
            "INSERT INTO activity_log (job_id, action, ts) VALUES (?, 'scored', ?)",
            (job_id, ts),
        )

    return job_id


def update_job_status(job_id: str, status: str, notes: str | None = None) -> None:
    """Update a job's status and append an entry to activity_log.

    Args:
        job_id: The job's primary key.
        status: New status value (e.g. 'approved', 'rejected', 'applied').
        notes: Optional free-text note stored on the job row.
    """
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ?, notes = COALESCE(?, notes) WHERE id = ?",
            (status, ts, notes, job_id),
        )
        conn.execute(
            "INSERT INTO activity_log (job_id, action, detail, ts) VALUES (?, ?, ?, ?)",
            (job_id, status, notes, ts),
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
    """Record the outcome of a job application.

    Args:
        job_id: The related job's primary key.
        reply_type: One of: no_reply | rejection | positive | interview | offer.
        reply_date: Optional date of the reply (ISO string).
        notes: Optional free-text notes.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO outcomes (job_id, reply_type, reply_date, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, reply_type, reply_date, notes, now_iso()),
        )


def get_activity_report(date_from: str, date_to: str) -> list[dict]:
    """Return activity log entries joined with job data for a date range.

    Args:
        date_from: Start of range, UTC ISO string (inclusive).
        date_to: End of range, UTC ISO string (inclusive).
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                a.ts, a.action, a.detail, a.source,
                j.company, j.role_title, j.location, j.status, j.score
            FROM activity_log a
            LEFT JOIN jobs j ON a.job_id = j.id
            WHERE a.ts >= ? AND a.ts <= ?
            ORDER BY a.ts ASC
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
                updated_at    TEXT NOT NULL
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
