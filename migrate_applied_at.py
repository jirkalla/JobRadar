"""One-time migration: add applied_at column to jobs and backfill from job_id slug."""
import sqlite3

conn = sqlite3.connect("data/tracker.db")

cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()]
if "applied_at" not in cols:
    conn.execute("ALTER TABLE jobs ADD COLUMN applied_at TEXT")
    print("Column added.")
else:
    print("Column already exists.")

updated = conn.execute(
    "UPDATE jobs SET applied_at = substr(id, -8) WHERE applied_at IS NULL"
).rowcount
conn.commit()
print(f"Rows backfilled: {updated}")

# Verify — show first 5 rows
rows = conn.execute(
    "SELECT id, company, applied_at FROM jobs ORDER BY applied_at LIMIT 5"
).fetchall()
print("\nSample (first 5 by applied_at):")
for r in rows:
    print(f"  {r[2]}  {r[1]}  [{r[0]}]")

conn.close()
