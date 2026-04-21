# scripts/set_status.py
# Usage:
#   python scripts/set_status.py <job_id> <status> [applied_at]
# applied_at format: YYYYMMDD  (optional, needed for Report)
# Example:
#   python scripts/set_status.py mobilede-senior-data-engineer-dfm-20260421 applied 20260421

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.db import get_conn

if len(sys.argv) < 3:
    print("Usage: python scripts/set_status.py <job_id> <status> [applied_at]")
    sys.exit(1)

job_id = sys.argv[1]
status = sys.argv[2]
applied_at = sys.argv[3] if len(sys.argv) >= 4 else None

with get_conn() as conn:
    if applied_at:
        conn.execute(
            "UPDATE jobs SET status=?, applied_at=? WHERE id=?",
            (status, applied_at, job_id),
        )
    else:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))

msg = f"Set {job_id} → {status}"
if applied_at:
    msg += f" (applied_at={applied_at})"
print(msg)