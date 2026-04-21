"""Score a manually added job using the AI scorer.

Usage:
    python scripts/score_job.py <job_id>

Example:
    python scripts/score_job.py mobilede-senior-data-engineer-dfm-20260421
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from dotenv import load_dotenv
from src.ai_client import complete_json, get_client
from src.db import get_conn, get_job
from src.scorer import JobStub, build_score_prompt

load_dotenv(Path(__file__).parent.parent / ".env")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/score_job.py <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]
    job = get_job(job_id)
    if job is None:
        print(f"Error: job not found: {job_id}")
        sys.exit(1)

    if not job.get("jd_text"):
        print(f"Error: job {job_id} has no jd_text — cannot score.")
        sys.exit(1)

    profile = yaml.safe_load(Path("config/profile.yaml").read_text(encoding="utf-8"))
    client = get_client(profile)
    prompt_template = Path("config/prompts/score.txt").read_text(encoding="utf-8")

    stub = JobStub(
        title=job["role_title"],
        company=job["company"],
        location=job["location"] or "",
        url=job["url"] or "",
        source="manual",
        date_seen="",
        salary=None,
        raw_block="",
    )

    print(f"Scoring {job['company']} — {job['role_title']}...")
    prompt = build_score_prompt(stub, job["jd_text"], profile, prompt_template)
    result = complete_json(client, prompt)

    score = result.get("relevance_score", 0)
    score_reason = result.get("score_reason", "")
    tech_stack = json.dumps(result.get("tech_stack") or [])
    strong_matches = json.dumps(result.get("strong_matches") or [])
    concerns = json.dumps(result.get("concerns") or [])

    with get_conn() as conn:
        conn.execute(
            """UPDATE jobs
               SET score=?, score_reason=?, tech_stack=?, strong_matches=?, concerns=?
               WHERE id=?""",
            (score, score_reason, tech_stack, strong_matches, concerns, job_id),
        )

    print(f"Score:  {score}/10")
    print(f"Reason: {score_reason}")


if __name__ == "__main__":
    main()
