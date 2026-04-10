# One-time data load — already executed. Do not run again unless DB is reset.
"""JobRadar — Seed backfill data.

One-off script to load all real job applications and recruiter contacts
into the database. Calls db.py only. All entries: source='manual'.
Safe to run multiple times — duplicates are skipped.
"""

from src import db

JOBS = [
    {"date": "20251007", "company": "Enpal",             "role": "Senior Software Engineer (Backend & Integrations)", "status": "rejected", "location": None},
    {"date": "20251007", "company": "Adevinta",           "role": "(Senior) Data / Analytics Engineer",                "status": "rejected", "location": None},
    {"date": "20251014", "company": "Verti Versicherung", "role": "Senior Data Engineer (m/w/d) DWH",                  "status": "rejected", "location": "Teltow"},
    {"date": "20251024", "company": "eBay",               "role": "Senior Software Engineer, Security",                "status": "rejected", "location": None},
    {"date": "20251024", "company": "Enpal",              "role": "Senior Software Engineer Backend",                  "status": "rejected", "location": None},
    {"date": "20251028", "company": "eBay",               "role": "MTS 1, Software Engineer, Data",                   "status": "rejected", "location": None},
    {"date": "20251104", "company": "SoSafe",             "role": "Senior Data Engineer (m/f/d)",                     "status": "applied",  "location": "Berlin/Remote"},
    {"date": "20251111", "company": "4flow SE",           "role": "Senior Data Engineer (Logistics)",                 "status": "rejected", "location": None},
    {"date": "20251118", "company": "DeepL",              "role": "Senior Data Engineer",                             "status": "rejected", "location": "Remote/Berlin"},
    {"date": "20251118", "company": "Delivery Hero SE",   "role": "Senior Data Analyst",                              "status": "rejected", "location": None},
    {"date": "20251212", "company": "AroundHome",         "role": "Senior Data Engineer (Modern Data Platform)",      "status": "rejected", "location": None},
    {"date": "20251216", "company": "Axel Springer",      "role": "(Senior) Software Engineer Data",                  "status": "rejected", "location": None},
    {"date": "20251226", "company": "Parloa",             "role": "Principal Software Engineer",                      "status": "rejected", "location": None},
    {"date": "20260120", "company": "Andersen",           "role": "Backend Developer (.NET) in Germany",              "status": "rejected", "location": None},
    {"date": "20260120", "company": "DeepLSE",            "role": "Senior Staff Data Engineer",                       "status": "rejected", "location": None},
    {"date": "20260127", "company": "Zalando SE",         "role": "Senior Data Platform Engineer",                    "status": "rejected", "location": None},
    {"date": "20260130", "company": "Trinetix",           "role": "Senior .NET Developer",                            "status": "applied",  "location": None},
    {"date": "20260130", "company": "Tieto",              "role": "(Senior) Backend Developer Java & .NET (m/f/d)",   "status": "rejected", "location": None},
    {"date": "20260204", "company": "Axel Springer",      "role": "Senior Software Engineer (m/f/d) Data",            "status": "rejected", "location": None},
    {"date": "20260204", "company": "Topi",               "role": "Senior Data Engineer",                             "status": "applied",  "location": None},
    {"date": "20260206", "company": "Andersen",           "role": "Backend Developer (.NET) in the EU",               "status": "rejected", "location": None},
]

RECRUITERS = [
    {"date": "20251104", "agency": "Prime People",              "action": "Registration",                              "outcome": "Input profile created, currently without a suitable position."},
    {"date": "20251104", "agency": "Noir Consulting",           "action": "Request for a Job - Senior Software Engineer", "outcome": "Declined - position filled or profile mismatch."},
    {"date": "20251107", "agency": "IT Recruiting alphacoders", "action": "Registration",                              "outcome": "They were supposed to call, no one contacted me."},
    {"date": "20251107", "agency": "Senior Connect",            "action": "Request for a Job - Full Stack Developer",  "outcome": "Declined after reviewing the profile."},
]


def main() -> None:
    db.init_db()
    saved = 0
    skipped = 0

    print("Loading job applications...")
    for j in JOBS:
        company = j["company"]
        role = j["role"]
        date_str = j["date"]

        if db.job_exists_exact(company, role, date_str):
            print(f"  Skipped (duplicate): {company} — {role}")
            skipped += 1
            continue

        job_id = db.insert_job(
            {"company": company, "role_title": role, "status": j["status"], "location": j["location"]},
            source="manual",
            date_str=date_str,
        )
        db.log_action(job_id, "applied", source="manual")
        if j["status"] == "rejected":
            db.log_action(job_id, "rejected", source="manual")
            db.record_outcome(job_id, "rejection")

        print(f"  Saved: {company} — {role}")
        saved += 1

    print("\nLoading recruiter contacts...")
    for r in RECRUITERS:
        agency = r["agency"]
        action = r["action"]
        date_str = r["date"]

        if db.job_exists_exact(agency, action, date_str):
            print(f"  Skipped (duplicate): {agency} — {action}")
            skipped += 1
            continue

        job_id = db.insert_job(
            {"company": agency, "role_title": action, "status": "applied"},
            source="manual",
            date_str=date_str,
        )
        db.log_action(job_id, "recruiter_contact", detail=r["outcome"], source="manual")

        print(f"  Saved: {agency} — {action}")
        saved += 1

    print(f"\nDone. {saved} records saved, {skipped} duplicates skipped.")


if __name__ == "__main__":
    main()
