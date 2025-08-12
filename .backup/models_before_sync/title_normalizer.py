import csv
import os
import re
from functools import lru_cache
from typing import Any, Optional, Union, Dict
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

    # 0) Curated map override (if present)
    mapped = _lookup_curated_title(title, url)
    if mapped:
        return mapped

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


# === Curated mapping support ===

@lru_cache(maxsize=1)
def _load_title_map() -> Dict[str, str]:
    """Load curated title normalization map from CSV if available.

    CSV columns expected: file_name, article_name, normalized_title
    Keys built:
      - article_name (lowercased/stripped) -> normalized_title
      - full file_name (lowercased) -> normalized_title
      - basename of file_name (lowercased) -> normalized_title
    """
    mapping: Dict[str, str] = {}
    # Resolve path via env or default location
    path = os.getenv(
        "TITLE_MAP_CSV",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "normalized_file_title_map.csv"),
    )
    try:
        if not os.path.exists(path):
            return mapping
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    art = (row.get("article_name") or "").strip()
                    fn = (row.get("file_name") or "").strip()
                    norm = (row.get("normalized_title") or "").strip()
                    if not norm:
                        continue
                    if art:
                        mapping[_norm_key(art)] = norm
                    if fn:
                        mapping[_norm_key(fn)] = norm
                        base = os.path.basename(fn)
                        if base:
                            mapping[_norm_key(base)] = norm
                except Exception:
                    continue
    except Exception:
        return {}
    return mapping


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _lookup_curated_title(raw_title: str, url: Union[str, list, None]) -> Optional[str]:
    """Return curated normalized title if a mapping entry matches title or URL."""
    mp = _load_title_map()
    if not mp:
        return None

    # 1) Exact article_name match (case-insensitive, space-normalized)
    tkey = _norm_key(raw_title)
    if tkey in mp:
        return mp[tkey]

    # 2) URL-based matching by file name or path substring
    url_str = None
    if isinstance(url, list):
        url_str = str(url[0]) if url else None
    elif isinstance(url, str):
        url_str = url
    if url_str:
        url_l = url_str.lower()
        # try basename
        try:
            parsed = urlparse(url_str)
            last = unquote((parsed.path or "").strip("/").split("/")[-1])
            bkey = _norm_key(last)
            if bkey in mp:
                return mp[bkey]
        except Exception:
            pass
        # try substring match for known file_name entries
        for k, v in mp.items():
            # keys from file_name may include directory separators
            if ("/" in k) or ("\\" in k):
                if k in url_l:
                    return v
    return None


