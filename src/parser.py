"""EML parsing for JobRadar — Infoagent digest format.

Handles digests containing 50-60 job listings per email,
separated by ~~~ delimiters.

Constraints:
- stdlib only: email, re, urllib.request, dataclasses, pathlib, html.parser
- No AI calls, no DB calls
- parse_eml() returns list[JobStub]
"""

import email
import re
import urllib.request
from dataclasses import dataclass
from email.header import decode_header as _email_decode_header
from html.parser import HTMLParser
from pathlib import Path


@dataclass
class JobStub:
    """One job listing extracted from an Infoagent digest email."""
    title:     str
    company:   str
    location:  str
    url:       str
    source:    str        # e.g. "LinkedIn.de", "indeed.de"
    date_seen: str        # DD.MM.YYYY from Quelle line
    salary:    str | None
    raw_block: str        # original text block, for debugging


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text converter using stdlib html.parser."""

    BLOCK_TAGS = {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}
    SKIP_TAGS  = {"script", "style", "head", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.SKIP_TAGS:
            self._skip = True
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        """Return accumulated plain text with collapsed blank lines."""
        text = "".join(self._parts)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


def _html_to_text(html: str) -> str:
    """Strip HTML tags and return plain text."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
        return extractor.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html).strip()


def _decode_header(value: str) -> str:
    """Decode an RFC 2047 encoded email header value."""
    parts = _email_decode_header(value)
    decoded: list[str] = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return "".join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from an email.Message with encoding fallback."""
    for content_type in ("text/plain", "text/html"):
        for part in msg.walk():
            if part.get_content_type() != content_type:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or ""
            for enc in [charset, "utf-8", "latin-1", "windows-1252"]:
                if not enc:
                    continue
                try:
                    text = payload.decode(enc)
                    return _html_to_text(text) if content_type == "text/html" else text
                except (UnicodeDecodeError, LookupError):
                    continue
    return ""


def _clean_title(text: str) -> str:
    """Strip gender suffixes, category markers, and trailing noise from a title."""
    # Remove gender suffixes: (m/f/d), (m/w/d), (f/m/x), (All Genders), etc.
    text = re.sub(r"\s*\((?:all genders|[mfwdxMFWDX/ ]+)\)\s*", " ", text, flags=re.IGNORECASE)
    # Remove {job category markers}
    text = re.sub(r"\{[^}]*\}", "", text)
    # Strip trailing dashes and whitespace
    text = re.sub(r"\s*[-–]+\s*$", "", text)
    return text.strip()


def _parse_salary(raw: str) -> str | None:
    """Return cleaned salary string, or None if zero or missing."""
    raw = (raw.strip()
             .replace("&euro;", "€")
             .replace("&amp;euro;", "€")
             .replace("\x80", "€"))   # Windows-1252 byte decoded via latin-1
    if not raw or re.fullmatch(r"0\s*€?", raw):
        return None
    return raw


def _parse_title_location(text: str) -> tuple[str, str]:
    """Extract job title and location from the pre-URL header text.

    Uses special cases for hybrid/remote, then greedy matching to find
    the LAST 'in {location}' pattern — avoiding false matches on 'in'
    embedded earlier in the title.
    """
    text = re.sub(r"\s+", " ", text).strip()

    def _strip_trailing_in(t: str) -> str:
        """Remove orphaned trailing ' in' left after location is extracted."""
        return re.sub(r"\s+in\s*$", "", t).strip()

    # Special case: Hybrides Arbeiten in {city}
    m = re.search(r"Hybrides\s+Arbeiten\s+in\s+(\S.+?)$", text, re.IGNORECASE)
    if m:
        title = _strip_trailing_in(_clean_title(text[: m.start()].strip()))
        return title, m.group(1).strip() + " (Hybrid)"

    # Special case: Homeoffice in {city}
    m = re.search(r"Homeoffice\s+in\s+(\S.+?)$", text, re.IGNORECASE)
    if m:
        title = _strip_trailing_in(_clean_title(text[: m.start()].strip()))
        return title, m.group(1).strip() + " (Remote)"

    # General: greedy (.*) finds the LAST standalone 'in {location}'
    m = re.search(r"^(.*)\bin\s+(\S.+)$", text, re.DOTALL)
    if m:
        return _clean_title(m.group(1).strip()), m.group(2).strip()

    return _clean_title(text), "Unknown"


def _parse_job_block(block: str) -> JobStub | None:
    """Parse one Infoagent job block into a JobStub. Returns None if invalid."""
    lines = [l.strip() for l in block.replace("\r\n", "\n").split("\n")]
    lines = [l for l in lines if l]  # drop blank lines

    url_idx = next((i for i, l in enumerate(lines) if l.startswith("https://")), None)
    if url_idx is None:
        return None

    quelle_idx = next((i for i, l in enumerate(lines) if l.startswith("Quelle:")), None)
    if quelle_idx is None:
        return None

    url = lines[url_idx]

    # Company: first line after URL, left of first comma
    company_line = lines[url_idx + 1] if url_idx + 1 < len(lines) else ""
    company = company_line.split(",")[0].strip()

    # Parse Quelle: "Quelle: {source}, {date}, {salary}"
    quelle_body = lines[quelle_idx][len("Quelle: "):]
    quelle_parts = [p.strip() for p in quelle_body.split(",")]
    source    = quelle_parts[0] if len(quelle_parts) > 0 else ""
    date_seen = quelle_parts[1] if len(quelle_parts) > 1 else ""
    salary    = _parse_salary(", ".join(quelle_parts[2:]) if len(quelle_parts) > 2 else "")

    # Title + location from lines before the URL
    pre_url_text = " ".join(lines[:url_idx])
    title, location = _parse_title_location(pre_url_text)

    if not title or not url:
        return None

    return JobStub(
        title=title,
        company=company,
        location=location,
        url=url,
        source=source,
        date_seen=date_seen,
        salary=salary,
        raw_block=block,
    )


def parse_eml(path: Path) -> list[JobStub]:
    """Parse an Infoagent digest EML file and return a list of JobStub objects.

    Args:
        path: Path to the .eml file.

    Returns:
        List of JobStub objects, one per valid job listing found.
    """
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw)
    body = _extract_body(msg)
    if not body:
        return []

    blocks = re.split(r"~+", body)
    stubs: list[JobStub] = []
    for block in blocks:
        block = block.strip()
        if "https://" not in block or "Quelle:" not in block:
            continue
        stub = _parse_job_block(block)
        if stub is not None:
            stubs.append(stub)
    return stubs


def scan_inbox(inbox_dir: Path) -> list[Path]:
    """Return a sorted list of .eml files in the given inbox directory.

    Args:
        inbox_dir: Path to the inbox folder to scan.
    """
    return sorted(inbox_dir.glob("*.eml"))


def fetch_job_description(url: str, timeout: int = 10) -> str:
    """Fetch a full job description from a URL and return plain text.

    Uses stdlib urllib.request only — no requests library.
    Returns empty string on any exception — never raises.
    Truncates output to 5000 characters.

    Args:
        url:     The job listing URL to fetch.
        timeout: Request timeout in seconds (default 10).
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read()
        return _html_to_text(raw.decode(charset, errors="replace"))[:5000]
    except Exception:
        return ""
