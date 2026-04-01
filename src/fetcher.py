"""Forpsi IMAP email fetcher — downloads unread Infoagent digest emails to inbox/.

Stdlib only: imaplib, email, os, pathlib.
No AI calls. No DB calls.
"""

import imaplib
import email as email_lib
import os
from pathlib import Path
from email.utils import parsedate_to_datetime


def _parse_date_yymmdd(date_header: str) -> str:
    """Parse an RFC 2822 Date header to YYMMDD string. Returns 'unknown' on failure."""
    try:
        dt = parsedate_to_datetime(date_header)
        return dt.strftime("%y%m%d")
    except Exception:
        return "unknown"


def fetch_digests(
    inbox_dir: Path,
    processed_dir: Path,
    env: dict,
    sender: str = "info@anzeigendaten.de",
    subject: str | None = None,
    since: str | None = None,
    on_date: str | None = None,
    filename_prefix: str = "Suche_Infoagent",
) -> tuple[int, list[str]]:
    """Connect to Forpsi IMAP and download unread digest emails.

    Searches INBOX for UNSEEN messages matching sender, optional subject,
    and optional since date. Saves each match as inbox/{filename_prefix}_{YYMMDD}.eml
    and marks it read on the server. Skips files already in inbox_dir or
    processed_dir.

    Args:
        inbox_dir: Directory to write downloaded .eml files to.
        processed_dir: Directory to check for already-processed files.
        env: Environment variable dict (pass os.environ).
        sender: FROM address to filter on (default: info@anzeigendaten.de).
        subject: Optional SUBJECT keyword to filter on.
        since: Optional date string in IMAP format "DD-Mon-YYYY" (e.g. "01-Mar-2026").
               If provided, only messages on or after this date are fetched.
        on_date: Optional ISO date string "YYYY-MM-DD" (e.g. "2026-03-31").
                 If provided, fetches only messages from that exact day (overrides since).
        filename_prefix: Prefix for saved .eml filenames (e.g. "Suche_Infoagent_JiriVosta").

    Returns:
        (count_downloaded, list_of_saved_filenames)

    Raises:
        EnvironmentError: If FORPSI_EMAIL or FORPSI_PASSWORD are missing.
        ConnectionError: If the IMAP connection or login fails.
    """
    server = env.get("FORPSI_IMAP_SERVER", "imap.forpsi.com")
    port_str = env.get("FORPSI_IMAP_PORT", "993")
    port = int(port_str)

    try:
        username = env["FORPSI_EMAIL"]
    except KeyError:
        raise EnvironmentError(
            "Missing env var: FORPSI_EMAIL\n"
            "Add to .env: FORPSI_EMAIL=your_email@yourdomain.com"
        )

    try:
        password = env["FORPSI_PASSWORD"]
    except KeyError:
        raise EnvironmentError(
            "Missing env var: FORPSI_PASSWORD\n"
            "Add to .env: FORPSI_PASSWORD=your_forpsi_webmail_password"
        )

    saved_files: list[str] = []

    try:
        imap = imaplib.IMAP4_SSL(server, port)
    except OSError as exc:
        raise ConnectionError(f"Could not connect to {server}:{port}") from exc

    try:
        try:
            imap.login(username, password)
        except imaplib.IMAP4.error as exc:
            raise ConnectionError(
                f"Could not login to {server}:{port} — check FORPSI_EMAIL and FORPSI_PASSWORD"
            ) from exc

        imap.select("INBOX")

        # NOTE: Forpsi IMAP does not support substring SUBJECT search across
        # underscore word boundaries, so subject filtering is done in Python
        # after fetching headers — not as an IMAP search criterion.
        #
        # UNSEEN is omitted when --date is given: an explicit date request
        # means "give me that day's email" regardless of read/unread status.
        parts: list[str] = [f'FROM "{sender}"']
        if on_date:
            from datetime import date, timedelta
            day = date.fromisoformat(on_date)
            next_day = day + timedelta(days=1)
            imap_fmt = "%d-%b-%Y"
            parts.append(f'SINCE {day.strftime(imap_fmt)}')
            parts.append(f'BEFORE {next_day.strftime(imap_fmt)}')
        else:
            # Normal run: only fetch unread messages
            parts.insert(0, "UNSEEN")
            if since:
                parts.append(f'SINCE {since}')

        search_criteria = "(" + " ".join(parts) + ")"
        _, msg_ids_raw = imap.search(None, search_criteria)
        msg_ids = msg_ids_raw[0].split() if msg_ids_raw and msg_ids_raw[0] else []

        subject_filter = subject.lower() if subject else None

        for msg_id in msg_ids:
            try:
                # Fetch headers only first — cheap, avoids downloading large bodies
                _, hdr_data = imap.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE FROM)])")
                hdr_raw: bytes = hdr_data[0][1]
                hdr_msg = email_lib.message_from_bytes(hdr_raw)

                # Apply subject filter in Python (case-insensitive substring)
                if subject_filter:
                    msg_subject = hdr_msg.get("Subject", "").lower()
                    if subject_filter not in msg_subject:
                        continue

                date_header = hdr_msg.get("Date", "")
                date_yymmdd = _parse_date_yymmdd(date_header)
                filename = f"{filename_prefix}_{date_yymmdd}.eml"

                if (inbox_dir / filename).exists() or (processed_dir / filename).exists():
                    imap.store(msg_id, "+FLAGS", "\\Seen")
                    continue

                # Subject matched — now fetch the full message body
                _, fetch_data = imap.fetch(msg_id, "(RFC822)")
                raw: bytes = fetch_data[0][1]

                inbox_dir.mkdir(parents=True, exist_ok=True)
                (inbox_dir / filename).write_bytes(raw)

                imap.store(msg_id, "+FLAGS", "\\Seen")
                saved_files.append(filename)

            except Exception as exc:
                import warnings
                warnings.warn(f"Skipping message {msg_id}: {exc}")
                continue

    finally:
        try:
            imap.logout()
        except Exception:
            pass

    return len(saved_files), saved_files
