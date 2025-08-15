import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import streamlit as st

from src.webui.utils.helpers import get_citation_details
try:
    from src.webui.utils.pii import redact_pii  # type: ignore[import-not-found]
except Exception:
    # Fallback: no-op redactor if module is unavailable at import time
    def redact_pii(text: str) -> str:  # type: ignore
        return text


logger = logging.getLogger(__name__)


# Local file logging setup (optional; disabled by default)
LOG_DIR: Path
try:
    LOG_DIR = Path(os.environ.get("LOG_DIR", "/tmp/streamlit_logs")).resolve()
except Exception:
    LOG_DIR = Path("/tmp/streamlit_logs")

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

LOG_FILE = LOG_DIR / "app.log"
FEEDBACK_FILE = LOG_DIR / "chat_interactions.jsonl"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

_has_file_handler = any(
    isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(LOG_FILE)
    for h in root_logger.handlers
)
if not _has_file_handler and str(os.environ.get("ENABLE_LOCAL_CHAT_LOGS", "")).strip().lower() in ("1", "true", "yes"):
    _fh = RotatingFileHandler(str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3)
    _fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(_fh)


def log_feedback_event(message_index: int, feedback: str) -> None:
    try:
        history = st.session_state.get('chat_history', [])
        if not history or message_index < 0 or message_index >= len(history):
            logger.warning(f"[FEEDBACK] Invalid message index: {message_index}")
            return
        msg = history[message_index]
        query_text = ""
        j = message_index - 1
        while j >= 0:
            if history[j].get('role') == 'user':
                query_text = history[j].get('content', '')
                break
            j -= 1

        def trunc(s: str, n: int = 180) -> str:
            try:
                s = s or ""
                return (s[:n] + "…") if len(s) > n else s
            except Exception:
                return str(s)

        logger.info(
            "[FEEDBACK] index=%s feedback=%s lang=%s query=\"%s\" response=\"%s\"",
            message_index,
            feedback,
            msg.get('language_code', 'en'),
            trunc(query_text),
            trunc(msg.get('content', '')),
        )
        persist_interaction_record(message_index, feedback)
    except Exception as e:
        logger.warning(f"[FEEDBACK] Failed to log feedback: {e}")


def persist_interaction_record(message_index: int, feedback: str) -> None:
    """Append a structured interaction record to JSONL for traceability.
    Fields: session_id, ts, message_index, lang, user_query, assistant_response, feedback, citations
    """
    try:
        history = st.session_state.get('chat_history', [])
        if not history or message_index < 0 or message_index >= len(history):
            return
        msg: dict[str, Any] = history[message_index]
        if msg.get('role') == 'user':
            return
        query_text = ""
        j = message_index - 1
        while j >= 0:
            if history[j].get('role') == 'user':
                query_text = history[j].get('content', '')
                break
            j -= 1

        citations: list[dict[str, Any]] = []
        try:
            for cit in (msg.get('citations') or []):
                d = get_citation_details(cit)
                citations.append({'title': d.get('title'), 'url': d.get('url')})
        except Exception:
            citations = []

        if 'session_id' not in st.session_state or not st.session_state.session_id:
            from uuid import uuid4
            st.session_state.session_id = str(uuid4())

        redacted_user_query = redact_pii(query_text or '')
        redacted_assistant_response = redact_pii(msg.get('content', ''))

        record = {
            'session_id': st.session_state.get('session_id'),
            'ts': datetime.now(timezone.utc).isoformat(),
            'message_index': message_index,
            'language_code': msg.get('language_code', 'en'),
            'user_query': redacted_user_query,
            'assistant_response': redacted_assistant_response,
            'feedback': feedback,
            'citations': citations,
            'retrieval_source': msg.get('retrieval_source'),
            'fallback_reason': msg.get('fallback_reason'),
        }

        if str(os.environ.get("ENABLE_LOCAL_CHAT_LOGS", "")).strip().lower() in ("1", "true", "yes"):
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _persist_record_to_blob(json.dumps(record, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"[FEEDBACK] Persist failed: {e}")


def _persist_record_to_blob(record_str: str) -> None:
    """Append the record to an Azure Append Blob if configured via env.
    Blob name: {prefix}/{session_id}.jsonl
    """
    try:
        def _env(name: str) -> str | None:
            v = os.environ.get(name)
            if not v:
                return None
            v = v.strip()
            if len(v) >= 2 and ((v[0] == v[-1]) and v[0] in ('"', "'")):
                v = v[1:-1]
            return v

        conn_str = (
            _env("BLOB_CONNSTR")
            or _env("Azure_blob")
            or _env("AZURE_BLOB_CONNSTR")
            or _env("AZURE_STORAGE_CONNECTION_STRING")
        )
        container = _env("CHAT_BLOB_CONTAINER") or "chatlogs"
        prefix = _env("CHAT_BLOB_PREFIX") or "interactions"

        if not conn_str:
            return

        try:
            from azure.storage.blob import BlobServiceClient
        except Exception:
            logger.debug("Azure Blob SDK not available; skipping blob persistence")
            return

        bsc = BlobServiceClient.from_connection_string(conn_str)
        container_client = bsc.get_container_client(container)
        try:
            container_client.create_container()
        except Exception:
            pass
        sid = st.session_state.get('session_id') or "unknown_session"
        blob_name = f"{prefix}/{sid}.jsonl"
        blob_client = container_client.get_blob_client(blob_name)
        try:
            blob_client.create_append_blob()
        except Exception:
            pass
        blob_client.append_block((record_str + "\n").encode("utf-8"))
    except Exception as e:
        logger.debug(f"Blob append skipped: {e}")


