"""One-time script: backfill urls for the 17 jobs imported from the 260217 EML.

The AI normalises company names during scoring (e.g. "Friendsurance.de / Alecto GmbH"
→ "friendsurance"), so exact matching fails for ~11 rows.  Instead we use token-overlap
scoring: split camelCase, tokenise on non-alphanumeric, keep tokens >= 3 chars, then
count the intersection between the DB company name and the stub company name.  Role
title overlap is used as a tiebreaker when multiple stubs match the same company.

Run once after the url column migration has been applied.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import init_db, set_job_url, get_conn
from src.parser import parse_eml

EML_PATH = Path("data/processed/Suche_Infoagent_JiriVosta_260217.eml")
SOURCE_EML = EML_PATH.name  # "Suche_Infoagent_JiriVosta_260217.eml"


def _tokens(name: str) -> set[str]:
    """Split camelCase, tokenise on non-alphanumeric, keep tokens >= 3 chars."""
    split = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return {w for w in re.sub(r"[^a-z0-9]", " ", split.lower()).split() if len(w) >= 3}


def _overlap(a: str, b: str) -> int:
    return len(_tokens(a) & _tokens(b))


def main() -> None:
    init_db()

    stubs = parse_eml(EML_PATH)
    print(f"Parsed {len(stubs)} stubs from {SOURCE_EML}")

    with get_conn() as conn:
        db_rows = [dict(r) for r in conn.execute(
            "SELECT id, company, role_title, url FROM jobs WHERE source_eml = ?",
            (SOURCE_EML,),
        ).fetchall()]

    already_set = sum(1 for r in db_rows if r["url"])
    pending = [r for r in db_rows if not r["url"]]
    print(f"DB rows: {len(db_rows)} total, {already_set} already have url, {len(pending)} pending\n")

    used_urls: set[str] = set()
    updated = 0
    failed = 0

    for row in pending:
        # Score each stub: primary = company token overlap, secondary = role_title overlap
        scored = []
        for stub in stubs:
            if stub.url in used_urls:
                continue
            c_score = _overlap(row["company"], stub.company)
            if c_score == 0:
                continue
            t_score = _overlap(row["role_title"], stub.title)
            scored.append((c_score, t_score, stub))

        if not scored:
            print(f"  FAIL  {row['company']!r} — no stub matched")
            failed += 1
            continue

        best_stub = max(scored, key=lambda x: (x[0], x[1]))[2]
        set_job_url(row["id"], best_stub.url)
        used_urls.add(best_stub.url)
        print(f"  OK    {row['company']!r}  ←  {best_stub.company!r}")
        updated += 1

    print(f"\nDone — newly updated: {updated}, already had url: {already_set}, unmatched: {failed}")


if __name__ == "__main__":
    main()

