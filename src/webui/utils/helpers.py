import base64
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_base64_image(image_path: str | Path) -> str | None:
    """Convert image to base64 string for CSS embedding."""
    try:
        p = Path(image_path)
        if not p.exists():
            return None
        with open(p, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {str(e)}")
        return None


def escape_html(text: str) -> str:
    try:
        return (
            (text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    except Exception:
        return str(text)


def get_citation_details(citation: Any) -> Dict[str, Any]:
    """Safely extract citation details from dict-like or object-like inputs."""
    try:
        if isinstance(citation, dict):
            return {
                "title": citation.get("title", "Untitled Source"),
                "url": citation.get("url", ""),
                "content": citation.get("content", ""),
                "snippet": citation.get("snippet", (citation.get("content", "")[:200] + "...") if citation.get("content") else ""),
            }
        elif hasattr(citation, "title"):
            return {
                "title": getattr(citation, "title", "Untitled Source"),
                "url": getattr(citation, "url", ""),
                "content": getattr(citation, "content", ""),
                "snippet": getattr(citation, "snippet", (getattr(citation, "content", "")[:200] + "...") if getattr(citation, "content", "") else ""),
            }
    except Exception as e:
        logger.error(f"Error processing citation: {str(e)}")

    return {"title": "Untitled Source", "url": "", "content": "", "snippet": ""}


def generate_chat_history_text(chat_history: list[Dict[str, Any]]) -> str:
    """Convert chat history to downloadable text format."""
    history_text = "Chat History\n\n"
    for msg in chat_history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('content','')}\n\n"
        if msg.get("citations"):
            history_text += "Sources:\n"
            for citation in msg["citations"]:
                details = get_citation_details(citation)
                history_text += f"- {details['title']}\n"
                if details.get("url"):
                    history_text += f"  URL: {details['url']}\n"
                if details.get("snippet"):
                    history_text += f"  Content: {details['snippet']}\n"
            history_text += "\n"
    return history_text


def format_message_for_copy(message_index: int, chat_history: list[Dict[str, Any]]) -> str:
    """Create a normalized plain-text snippet for one chat turn."""
    try:
        if not chat_history or message_index < 0 or message_index >= len(chat_history):
            return ""

        msg = chat_history[message_index]
        lines: list[str] = []

        if msg.get("role") == "assistant":
            # Preceding user question for context
            j = message_index - 1
            while j >= 0 and chat_history[j].get("role") != "user":
                j -= 1
            if j >= 0:
                lines.append(f"User: {chat_history[j].get('content','')}")

        role = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content','')}")

        if msg.get("role") == "assistant" and msg.get("citations"):
            lines.append("Sources:")
            for cit in msg["citations"]:
                d = get_citation_details(cit)
                title = d.get("title", "Untitled Source")
                url = d.get("url") or ""
                snippet = d.get("snippet") or ""
                lines.append(f"- {title}")
                if url:
                    lines.append(f"  URL: {url}")
                if snippet:
                    lines.append(f"  Content: {snippet}")

        return "\n".join(lines) + "\n"
    except Exception:
        msg = chat_history[message_index] if 0 <= message_index < len(chat_history) else {}
        return str(msg.get("content", ""))


# ---------------- Query param helpers (Streamlit-compatible) ---------------- #
import streamlit as st


def get_query_param_single_value(name: str, default: Any = None) -> Any:
    """Return a single string value for a query param across Streamlit versions."""
    try:
        params = st.query_params
    except Exception:
        try:
            params = st.experimental_get_query_params()
        except Exception:
            return default
    try:
        value = params.get(name)
    except Exception:
        value = None
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def get_all_query_params_single_values() -> Dict[str, str]:
    """Return current query params as {str: str} with list values collapsed to first element."""
    try:
        params = st.query_params
    except Exception:
        try:
            params = st.experimental_get_query_params()
        except Exception:
            return {}
    collapsed: Dict[str, str] = {}
    try:
        items = params.items() if hasattr(params, "items") else []
        for key, value in items:
            if isinstance(value, list):
                collapsed[key] = value[0] if value else ""
            else:
                collapsed[key] = value
    except Exception:
        pass
    return collapsed


def set_query_params_robust(new_params: Dict[str, Any], merge: bool = True) -> None:
    """Set query params using new API when available, with optional merge of existing params."""
    try:
        current = get_all_query_params_single_values() if merge else {}
        for k, v in (new_params or {}).items():
            if v is None:
                continue
            current[str(k)] = str(v)
        try:
            st.query_params = current  # Streamlit ≥1.30
        except Exception:
            try:
                st.experimental_set_query_params(**current)
            except Exception:
                pass
    except Exception:
        pass


def pop_feedback_action_from_query_params():
    """Return (action, index) if a feedback action is encoded in the URL, then remove it."""
    try:
        current = get_all_query_params_single_values()
        action = (current.get("fb") or current.get("action") or "").strip()
        idx_raw = current.get("i") or current.get("idx") or current.get("message_index")
        if not action:
            return None, None
        try:
            idx = int(idx_raw) if idx_raw is not None else None
        except Exception:
            idx = None
        # Remove the action params to avoid repeat on rerun
        current.pop("fb", None)
        current.pop("action", None)
        current.pop("i", None)
        current.pop("idx", None)
        current.pop("message_index", None)
        set_query_params_robust(current, merge=False)
        return action, idx
    except Exception:
        return None, None



