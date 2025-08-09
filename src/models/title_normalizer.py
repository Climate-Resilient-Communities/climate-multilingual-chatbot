import re
from typing import Any, Optional, Union
from urllib.parse import urlparse, unquote


GENERIC_SECTIONS = {
    "introduction", "abstract", "summary", "table of contents", "contents",
    "references", "bibliography", "appendix", "annex", "acknowledgements",
    "copyright", "preface", "foreword"
}

ACRONYMS = {"IPCC", "NASA", "NOAA", "AQI", "PM2.5", "EV", "EVSE", "CSA", "NEMA"}


def _is_sluggy(text: str) -> bool:
    if not text:
        return True
    # Looks like a file slug or hash-like code
    if re.match(r"^[A-Za-z0-9_.\-]{18,}$", text) and ("-" in text or "_" in text):
        return True
    # Common publisher slug patterns (e.g., 1-s2.0-S2667278222000359-main)
    if re.match(r"^\d+-s\.[0-9]+-S[0-9A-Za-z\-]+$", text, flags=re.IGNORECASE):
        return True
    # Purely numeric-ish with separators
    if re.match(r"^[\d_\-]+$", text):
        return True
    return False


def _title_case_keep_acronyms(text: str) -> str:
    if not text:
        return text
    words = re.split(r"(\s+)", text.strip())
    out = []
    for w in words:
        if not w or w.isspace():
            out.append(w)
            continue
        w_clean = re.sub(r"[^A-Za-z0-9.]+", "", w)
        if w_clean.upper() in ACRONYMS:
            out.append(w_clean.upper())
        else:
            out.append(w.capitalize())
    return "".join(out).strip()


def _infer_from_url(url_value: Union[str, list, None]) -> Optional[str]:
    if not url_value:
        return None
    url = url_value[0] if isinstance(url_value, list) else url_value
    try:
        parsed = urlparse(str(url))
        path = unquote(parsed.path or "").strip("/")
        if not path:
            return None
        last = path.split("/")[-1]
        # Strip extension
        last = re.sub(r"\.(pdf|html?|md|docx?)$", "", last, flags=re.IGNORECASE)
        # Replace separators
        last = last.replace("_", " ").replace("-", " ")
        # Collapse whitespace
        last = re.sub(r"\s+", " ", last).strip()
        if not last:
            return None
        # Basic cleanup of boilerplate tokens
        last = re.sub(r"\b(main|converted|final|draft|download|view)\b", "", last, flags=re.IGNORECASE)
        last = re.sub(r"\s+", " ", last).strip()
        if not last:
            return None
        return _title_case_keep_acronyms(last)
    except Exception:
        return None


def normalize_title(raw_title: str, section_title: Optional[str] = None, url: Union[str, list, None] = None) -> str:
    """Normalize document titles for cleaner citations.

    Heuristics:
    - Prefer a human title when present; otherwise infer from section_title or URL slug.
    - Clean file-suffixed or sluggy titles.
    - Title-case while preserving domain acronyms (IPCC, AQI, EV, etc.).
    """
    title = (raw_title or "").strip()

    # Remove common file artifacts
    title = re.sub(r"\.(pdf|html?|md|docx?)$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"[_-]", " ", title).strip()
    title = re.sub(r"\s+", " ", title).strip()

    # If empty/sluggy/non-descriptive, try alternatives
    if not title or _is_sluggy(title) or title.lower() in {"no title", "untitled", "untitled source"}:
        sec = (section_title or "").strip()
        sec_l = sec.lower()
        if sec and sec_l not in GENERIC_SECTIONS and len(sec) >= 4:
            title = sec
        else:
            inferred = _infer_from_url(url)
            if inferred:
                title = inferred

    # Final polish: title-case with acronym preservation
    title = _title_case_keep_acronyms(title)
    return title


