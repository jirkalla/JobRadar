"""AI scoring for JobRadar.

Scores each JobStub against the candidate profile using an AI provider.
Calls ai_client.complete_json() — no direct SDK imports.
No DB calls — returns a dict ready for db.insert_job().
"""

import json
import logging

from src.ai_client import complete_json
from src.parser import JobStub, fetch_job_description

logger = logging.getLogger(__name__)


def build_score_prompt(
    stub: JobStub,
    jd_text: str,
    profile: dict,
    template: str,
) -> str:
    """Build the scoring prompt by substituting profile values into the template.

    Args:
        stub:     The job stub (used for fallback context only).
        jd_text:  Fetched full job description text.
        profile:  Loaded config/profile.yaml dict.
        template: Content of config/prompts/score.txt.

    Returns:
        Fully substituted prompt string ready to send to the AI.
    """
    personal     = profile["personal"]
    skills       = profile["skills"]
    prefs        = profile["preferences"]
    restrictions = profile["restrictions"]

    def join(lst: list) -> str:
        return ", ".join(lst) if lst else ""

    return template.format(
        name=personal["name"],
        location=personal["location"],
        skills_expert=join(skills.get("expert", [])),
        skills_solid=join(skills.get("solid", [])),
        skills_learning=join(skills.get("learning", [])),
        skills_moved_away=join(skills.get("moved_away_from", [])),
        role_types=join(prefs.get("role_types", [])),
        roles_avoid=join(prefs.get("avoid", [])),
        hybrid_cities=join(restrictions.get("hybrid_cities", [])),
        job_text=jd_text,
    )


def check_location(result: dict, profile: dict) -> tuple[bool, str]:
    """Check whether the job's location is acceptable per profile restrictions.

    Rules (in order):
    - remote → always OK
    - hybrid + city in hybrid_cities → OK
    - onsite + city in hybrid_cities → OK (commutable)
    - anything else → NOT OK

    Args:
        result:  AI score result dict (must contain remote_type and location).
        profile: Loaded config/profile.yaml dict.

    Returns:
        Tuple of (location_ok: bool, location_reason: str).
    """
    remote_type  = (result.get("remote_type") or "unclear").lower()
    location     = result.get("location") or ""
    hybrid_cities = [
        c.lower()
        for c in profile.get("restrictions", {}).get("hybrid_cities", [])
    ]
    city_match = any(city in location.lower() for city in hybrid_cities)

    if remote_type == "remote":
        return True, "Remote role — acceptable anywhere"

    if remote_type == "hybrid":
        if city_match:
            return True, f"Hybrid in acceptable city: {location}"
        return False, f"Hybrid role outside acceptable cities: {location}"

    if remote_type == "onsite":
        if city_match:
            return True, f"Onsite in commutable city: {location}"
        return False, f"Onsite role outside acceptable cities: {location}"

    # unclear
    if city_match:
        return True, f"Location OK — work arrangement unclear: {location}"
    return False, f"Location not acceptable: {location} (remote_type: {remote_type})"


def _failed_result(stub: JobStub, reason: str, jd_text: str = "", status: str = "new") -> dict:
    """Return a minimal result dict when scoring cannot proceed."""
    return {
        "company":       stub.company,
        "role_title":    stub.title,
        "location":      stub.location,
        "remote_type":   "unclear",
        "url":           stub.url,
        "language":      "en",
        "score":         0,
        "score_reason":  reason,
        "status":        status,
        "source_eml":    None,
        "jd_text":       jd_text,
        "tech_stack":    "[]",
        "salary":        stub.salary,
        "strong_matches": "[]",
        "concerns":      json.dumps([reason]),
        "location_ok":   False,
        "location_reason": reason,
        "recommended":   False,
    }


def score_job(
    stub: JobStub,
    profile: dict,
    client,
    prompt_template: str,
) -> dict:
    """Score a job stub using the AI provider and return a DB-ready result dict.

    Fetches the full job description, builds the scoring prompt, calls the AI,
    applies location validation, and returns a dict ready for db.insert_job().
    Does not write to the database — that is the caller's responsibility.

    Args:
        stub:            Parsed job stub from parser.parse_eml().
        profile:         Loaded config/profile.yaml dict (read at call time).
        client:          AI client object from ai_client.get_client().
        prompt_template: Content of config/prompts/score.txt.

    Returns:
        Dict with all fields needed by db.insert_job(), plus
        location_ok, location_reason, and recommended for caller use.
        source_eml is set to None — caller must fill it in before inserting.
    """
    jd_text = fetch_job_description(stub.url)

    if len(jd_text) < 300:
        return _failed_result(stub, "Could not fetch job description", status="fetch_failed")

    prompt = build_score_prompt(stub, jd_text, profile, prompt_template)

    try:
        result = complete_json(client, prompt)
    except Exception as exc:
        logger.error("Scoring failed for %s — %s", stub.url, exc)
        return _failed_result(stub, f"Scoring failed: {exc}", jd_text)

    loc_ok, loc_reason = check_location(result, profile)

    return {
        "company":        result.get("company") or stub.company,
        "role_title":     result.get("role_title") or stub.title,
        "location":       result.get("location", stub.location),
        "remote_type":    result.get("remote_type", "unclear"),
        "language":       result.get("language", "en"),
        "score":          result.get("relevance_score", 0),
        "score_reason":   result.get("score_reason", ""),
        "status":         "new",
        "source_eml":     None,
        "url":            stub.url,
        "jd_text":        jd_text,
        "tech_stack":     json.dumps(result.get("tech_stack") or []),
        "salary":         result.get("salary_mentioned"),
        "strong_matches": json.dumps(result.get("strong_matches") or []),
        "concerns":       json.dumps(result.get("concerns") or []),
        "location_ok":    loc_ok,
        "location_reason": loc_reason,
        "recommended":    result.get("recommended", False),
    }
