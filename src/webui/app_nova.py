# CRITICAL: This must be the very first code in your file
# Place this at the absolute top, before ANY other imports

import os
import sys
import warnings

# === STEP 1: DISABLE ALL STREAMLIT WATCHERS PERMANENTLY ===
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_WATCH_DIRS"] = "false"
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

# === STEP 2: DISABLE PYTORCH JIT AND PROBLEMATIC FEATURES ===
os.environ["PYTORCH_JIT"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_USE_CUDA_DSA"] = "0"
os.environ["TORCH_USE_RTLD_GLOBAL"] = "YES"
os.environ["HF_HOME"] = os.environ.get("TEMP", "/tmp") + "/huggingface"

# === STEP 3: COMPREHENSIVE TORCH._CLASSES PATCH ===
import types
import builtins

class SafePyTorchClassesMock:
    """Safe mock for torch._classes that prevents __path__ access issues"""
    def __init__(self):
        self._original_classes = None
    
    def __getattr__(self, item):
        if item == "__path__":
            # Return a mock path object that won't break Streamlit
            return types.SimpleNamespace(_path=[])
        elif item == "_path":
            return []
        # For any other attributes, try to delegate to original if available
        if self._original_classes and hasattr(self._original_classes, item):
            return getattr(self._original_classes, item)
        return None
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        # Ignore other attribute setting to prevent issues

# Store the original import function
_original_import = builtins.__import__

def _patched_import(name, *args, **kwargs):
    """Patched import that fixes torch._classes on import"""
    module = _original_import(name, *args, **kwargs)
    
    if name == "torch" or name.startswith("torch."):
        if hasattr(module, "_classes"):
            # Store reference to original if it exists
            mock = SafePyTorchClassesMock()
            if hasattr(module._classes, '__dict__'):
                mock._original_classes = module._classes
            module._classes = mock
    
    return module

# Apply the import patch
builtins.__import__ = _patched_import

# === STEP 4: HANDLE EXISTING TORCH IMPORTS ===
if "torch" in sys.modules:
    torch_module = sys.modules["torch"]
    if hasattr(torch_module, "_classes"):
        mock = SafePyTorchClassesMock()
        mock._original_classes = torch_module._classes
        torch_module._classes = mock

# === STEP 5: SUPPRESS WARNINGS ===
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

# === STEP 5.1: FILE LOGGING SETUP (before importing app modules) ===
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from uuid import uuid4
from datetime import datetime, timezone
import json

# Allow overriding the log directory via env var (useful for Azure-mounted storage)
CHAT_LOG_DIR_ENV = os.environ.get("CHAT_LOG_DIR", "").strip()
if CHAT_LOG_DIR_ENV:
    LOG_DIR = Path(CHAT_LOG_DIR_ENV).expanduser().resolve()
else:
    LOG_DIR = Path.home() / ".streamlit/logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Fallback to /tmp if home-based log dir is unavailable
if not LOG_DIR.exists():
    LOG_DIR = Path("/tmp/streamlit_logs")
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

LOG_FILE = LOG_DIR / "app.log"
FEEDBACK_FILE = LOG_DIR / "chat_interactions.jsonl"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Avoid duplicating file handlers across reruns
_has_file_handler = any(
    isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(LOG_FILE)
    for h in root_logger.handlers
)
if not _has_file_handler and str(os.environ.get("ENABLE_LOCAL_CHAT_LOGS", "")).strip().lower() in ("1", "true", "yes"):
    _fh = RotatingFileHandler(str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3)
    _fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(_fh)

# Dedicated helper to log user feedback on messages
def log_feedback_event(message_index: int, feedback: str) -> None:
    try:
        history = st.session_state.get('chat_history', [])
        if not history or message_index < 0 or message_index >= len(history):
            logger.warning(f"[FEEDBACK] Invalid message index: {message_index}")
            return
        msg = history[message_index]
        # Find the nearest preceding user query
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
        # Also persist structured record
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
        msg = history[message_index]
        if msg.get('role') == 'user':
            return
        # Find nearest preceding user query
        query_text = ""
        j = message_index - 1
        while j >= 0:
            if history[j].get('role') == 'user':
                query_text = history[j].get('content', '')
                break
            j -= 1

        # Normalize citations
        citations = []
        try:
            for cit in (msg.get('citations') or []):
                d = get_citation_details(cit)
                citations.append({'title': d.get('title'), 'url': d.get('url')})
        except Exception:
            citations = []

        # Ensure we have a session id
        if 'session_id' not in st.session_state or not st.session_state.session_id:
            st.session_state.session_id = str(uuid4())

        # Apply PII redaction to sensitive fields
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
            'citations': citations,  # Citations typically don't contain PII
            # Optional provenance fields if present on the message
            'retrieval_source': msg.get('retrieval_source'),
            'fallback_reason': msg.get('fallback_reason'),
        }

        # Local JSONL logging disabled by default for production; enable by setting ENABLE_LOCAL_CHAT_LOGS=1
        if str(os.environ.get("ENABLE_LOCAL_CHAT_LOGS", "")).strip().lower() in ("1", "true", "yes"): 
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        # Always try to append to Azure Blob (if configured)
        _persist_record_to_blob(json.dumps(record, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"[FEEDBACK] Persist failed: {e}")

def _persist_record_to_blob(record_str: str) -> None:
    """Append the record to an Azure Append Blob if BLOB_CONNSTR is configured.
    Uses container CHAT_BLOB_CONTAINER (default: chatlogs) and prefix CHAT_BLOB_PREFIX (default: interactions).
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

        # Prefer connection string if provided
        conn_str = (
            _env("BLOB_CONNSTR")
            or _env("Azure_blob")
            or _env("AZURE_BLOB_CONNSTR")
            or _env("AZURE_STORAGE_CONNECTION_STRING")
        )
        container_name = _env("CHAT_BLOB_CONTAINER") or "chatlogs"
        blob_prefix = _env("CHAT_BLOB_PREFIX") or "interactions"
        session_id = st.session_state.get('session_id', 'unknown')
        blob_name = f"{blob_prefix}/{session_id}.jsonl"

        from azure.storage.blob import BlobClient, BlobServiceClient

        if conn_str:
            # Use connection string
            svc = BlobServiceClient.from_connection_string(conn_str)
        else:
            # Fall back to account name + key
            account_name = (
                _env("BLOB_ACCOUNT_NAME")
                or _env("BLOB_ACCOUNT")
                or _env("AZURE_STORAGE_ACCOUNT")
                or _env("AZURE_ACCOUNT_NAME")
            )
            account_key = (
                _env("BLOB_KEY")
                or _env("AZURE_BLOB_KEY")
                or _env("AZURE_STORAGE_KEY")
                or _env("STORAGE_ACCOUNT_KEY")
            )
            if not (account_name and account_key):
                return
            account_url = f"https://{account_name}.blob.core.windows.net"
            svc = BlobServiceClient(account_url=account_url, credential=account_key)

        # Ensure container exists
        try:
            cc = svc.get_container_client(container_name)
            cc.create_container()
        except Exception:
            pass

        # Get blob client
        blob_client = cc.get_blob_client(blob_name)

        # Append the new record (single upload); also log timing
        import time as _t
        _t0 = _t.time()
        try:
            existing = ""
            try:
                existing = blob_client.download_blob().readall().decode()
            except Exception:
                existing = ""
            new_content = (existing + record_str + "\n").encode("utf-8")
            blob_client.upload_blob(new_content, overwrite=True)
            _ms = int((_t.time() - _t0) * 1000)
            try:
                _host = blob_client.url.split('/')[2]
            except Exception:
                _host = "blob.core.windows.net"
            logger.info(f"dep=azure_blob host={_host} op=upload ms={_ms} status=OK")
        except Exception as _e:
            _ms = int((_t.time() - _t0) * 1000)
            logger.warning(f"dep=azure_blob op=upload ms={_ms} status=ERR err={str(_e)[:120]}")
    except Exception as e:
        logger.warning(f"[FEEDBACK] Blob persist failed: {e}")

# === STEP 6: SETUP EVENT LOOP BEFORE STREAMLIT ===
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# === PREPARE VALUES FOR PAGE CONFIG (FAVICON) BEFORE STREAMLIT IMPORT ===
import base64

_APP_FILE_DIR = Path(__file__).resolve().parent
ASSETS_DIR_FOR_FAVICON = _APP_FILE_DIR / "assets"
TREE_ICON_PATH_FOR_FAVICON = str(ASSETS_DIR_FOR_FAVICON / "tree.ico")

calculated_favicon = "🌳"  # Default emoji fallback
if (ASSETS_DIR_FOR_FAVICON / "tree.ico").exists():
    try:
        with open(TREE_ICON_PATH_FOR_FAVICON, "rb") as f:
            favicon_data = base64.b64encode(f.read()).decode()
            calculated_favicon = f"data:image/x-icon;base64,{favicon_data}"
    except Exception as e:
        print(f"[CONFIG WARNING] Could not load favicon: {e}")

print("✓ PyTorch-Streamlit compatibility patches applied successfully")

# === NOW IMPORT STREAMLIT AND SET PAGE CONFIG (ONLY ONCE) ===
import streamlit as st
from src.webui.components.modals import show_consent_dialog
from src.webui.components.header import render_mobile_header as render_mobile_header_component
from src.webui.components import render_sidebar_component
from src.webui.components.chat import render_message_actions_ui
from src.webui.utils.helpers import (
    get_query_param_single_value,
    set_query_params_robust,
    get_all_query_params_single_values,
    get_base64_image,
    get_citation_details,
)
from src.webui.setup.logging_config import log_feedback_event, persist_interaction_record
from src.webui.utils.mobile_detection import is_mobile_device as is_mobile_device_util
from src.webui.styles.loader import load_css_files

# Optional device-detection helpers (imported defensively so the app runs even if missing)
try:
    from streamlit_user_device import user_device as _user_device  # type: ignore
except Exception:
    _user_device = None
try:
    from st_screen_stats import ScreenData as _ScreenData  # type: ignore
except Exception:
    _ScreenData = None
try:
    from streamlit_javascript import st_javascript as _st_javascript  # type: ignore
    from user_agents import parse as _parse_user_agent  # type: ignore
except Exception:
    _st_javascript = None
    _parse_user_agent = None

# Robustly force initial sidebar state by temporarily flipping the state,
# triggering a rerun, then applying the desired state. This overrides any
# browser-persisted user choice Streamlit keeps.
SIDEBAR_STATE = {True: "expanded", False: "collapsed"}


# --- Query param helpers replaced by utils.helpers ---
_get_query_param_single_value = get_query_param_single_value
_set_query_params_robust = set_query_params_robust
_get_all_query_params_single_values = get_all_query_params_single_values
def _pop_feedback_action_from_query_params():
    from src.webui.utils.helpers import pop_feedback_action_from_query_params as _pop
    return _pop()

def is_mobile_device() -> bool:
    # Delegate to util using our param getter
    return is_mobile_device_util(get_query_param_single_value)


def render_device_debug_banner() -> None:
    """Render a small, dismissible banner with device-detection info when ?mobiledebug=1."""
    try:
        raw = _get_query_param_single_value("mobiledebug") or _get_query_param_single_value("dev")
        if not (isinstance(raw, str) and raw.lower() in ("1", "true", "yes", "y")):
            return
    except Exception:
        return
    info = st.session_state.get("device_detection_info", {}) or {}
    detected = st.session_state.get("is_mobile_detected")
    msg = f"device='{info.get('device_type')}' width={info.get('width')} method={info.get('method')} mobile={detected}"
    try:
        st.info(f"Device debug: {msg}")
    except Exception:
        st.write(f"Device debug: {msg}")

def load_mobile_css() -> None:
    """Deprecated local: use src.webui.styles.loader.load_mobile_css instead."""
    from src.webui.styles.loader import load_mobile_css as _load
    _load()

def _update_language_from_mobile_select() -> None:
    sel = st.session_state.get("mobile_language_select")
    if isinstance(sel, str) and sel:
        st.session_state.selected_language = sel
        st.session_state.language_confirmed = True

def render_mobile_header(chatbot) -> None:
    """Deprecated local: use src.webui.components.header.render_mobile_header instead."""
    from src.webui.components.header import render_mobile_header as _render
    return _render(chatbot, CCC_ICON_B64)


# Determine desired sidebar open/closed from query param if present (sb=1/0)
_desired_open_default = True
try:
    _params = st.query_params  # Streamlit ≥1.30
except Exception:
    try:
        _params = st.experimental_get_query_params()
    except Exception:
        _params = {}

_sb = (_params.get("sb") if isinstance(_params, dict) else None)
if isinstance(_sb, list):
    _sb = _sb[0] if _sb else None
if _sb in ("0", 0):
    _desired_open_default = False
elif _sb in ("1", 1):
    _desired_open_default = True

if "_sb_open" not in st.session_state:
    st.session_state._sb_open = _desired_open_default
    st.session_state._sb_rerun = False
else:
    # If query param changes desired state during a session, adopt it and flip once
    if _sb in ("0", "1", 0, 1):
        new_open = (_sb in ("1", 1))
        if new_open != st.session_state._sb_open:
            st.session_state._sb_open = new_open
            st.session_state._sb_rerun = True

# Single page config, no reruns around it (prevents fragment errors)
st.set_page_config(
    layout="wide",
    page_title="Multilingual Climate Chatbot",
    page_icon=calculated_favicon,
    initial_sidebar_state=SIDEBAR_STATE[st.session_state._sb_open],
)

        # On load: if a previous action requested closing the sidebar via sessionStorage,
# perform a best-effort close using the native collapse control or CSS transform.
## Removed JS-driven sidebar auto-close to avoid reload-induced fragment errors

## Removed reset_ui reload logic to prevent fragment errors and unexpected reruns

# === NOW OTHER IMPORTS AND SETUP ===
import time
import re
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from streamlit.components.v1 import html as st_html

# Configure logging
logger = logging.getLogger(__name__)

# === PII REDACTION FUNCTIONALITY ===
def redact_pii(text: str) -> str:
    """Deprecated local: use src.webui.utils.pii.redact_pii instead."""
    from src.webui.utils.pii import redact_pii as _redact  # type: ignore[import-not-found]
    return _redact(text)

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Configure PyTorch after safe import
import torch
torch.set_num_threads(1)
if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True

# Prevent any remaining torch path issues
if hasattr(torch.utils.data, '_utils'):
    torch.utils.data._utils.MP_STATUS_CHECK_INTERVAL = 0

# NOW import your custom modules
from src.utils.env_loader import load_environment

# Load environment
load_environment()

# Asset paths for general use
ASSETS_DIR = _APP_FILE_DIR / "assets"
TREE_ICON = str(ASSETS_DIR / "tree.ico") if (ASSETS_DIR / "tree.ico").exists() else None
CCC_ICON = str(ASSETS_DIR / "CCCicon.png") if (ASSETS_DIR / "CCCicon.png").exists() else None
WALLPAPER = str(ASSETS_DIR / "wallpaper.png") if (ASSETS_DIR / "wallpaper.png").exists() else None

# Pre-encode logo for header alignment (if available) via helper
CCC_ICON_B64 = get_base64_image(CCC_ICON) if CCC_ICON else None

def disable_streamlit_watcher():
    """Additional runtime disabling of Streamlit file watcher"""
    try:
        import streamlit.watcher
        if hasattr(streamlit.watcher, 'LocalSourcesWatcher'):
            original_get_module_paths = streamlit.watcher.local_sources_watcher.get_module_paths
            def safe_get_module_paths(module):
                try:
                    return original_get_module_paths(module)
                except (RuntimeError, AttributeError):
                    return []
            streamlit.watcher.local_sources_watcher.get_module_paths = safe_get_module_paths
    except Exception as e:
        print(f"Warning: Could not patch Streamlit watcher: {e}")

def create_event_loop():
    """Deprecated local: use src.webui.utils.async_helpers.create_event_loop instead."""
    from src.webui.utils.async_helpers import create_event_loop as _create
    return _create()

def run_async(coro):
    """Deprecated local: use src.webui.utils.async_helpers.run_async instead."""
    from src.webui.utils.async_helpers import run_async as _run
    return _run(coro)

@st.cache_resource
def init_chatbot():
    """Deprecated local: use src.webui.chatbot.init.init_chatbot instead."""
    from src.webui.chatbot.init import init_chatbot as _init
    return _init()

def get_citation_details(citation):
    """Deprecated local: use src.webui.utils.helpers.get_citation_details instead."""
    from src.webui.utils.helpers import get_citation_details as _g
    return _g(citation)

def display_source_citations(citations, base_idx=0):
    """Deprecated local: use src.webui.components.chat.display_source_citations instead."""
    from src.webui.components.chat import display_source_citations as _display
    return _display(citations, base_idx)

def display_progress(progress_placeholder):
    """Deprecated local: use src.webui.components.progress.display_progress instead."""
    from src.webui.components.progress import display_progress as _display
    _display(progress_placeholder)

def _render_loading_ui(container, stage_text: str, progress_value: float) -> None:
    """Deprecated local: use src.webui.components.progress._render_loading_ui instead."""
    from src.webui.components.progress import _render_loading_ui as _render
    _render(container, stage_text, progress_value)

def _run_query_background(chatbot, query: str, language_name: str, conversation_history: list, result_holder: dict, q: "queue.Queue", skip_cache: bool) -> None:
    """Deprecated local: use src.webui.components.progress._run_query_background instead."""
    from src.webui.components.progress import _run_query_background as _run
    _run(chatbot, query, language_name, conversation_history, result_holder, q, skip_cache)

def run_query_with_interactive_progress(chatbot, query: str, language_name: str, conversation_history: list, response_placeholder, skip_cache: bool = False):
    """Deprecated local: use src.webui.components.progress.run_query_with_interactive_progress instead."""
    from src.webui.components.progress import run_query_with_interactive_progress as _run
    return _run(chatbot, query, language_name, conversation_history, response_placeholder, skip_cache)

from src.webui.components.chat import (
    is_rtl_language,
    clean_html_content,
    render_user_bubble,
    display_chat_messages,
)

## chat components moved to src/webui/components/chat.py

def load_custom_css():
    """Deprecated local: use src.webui.styles.loader.load_custom_css instead."""
    from src.webui.styles.loader import load_custom_css as _load
    _load()



def load_responsive_css():
    """Deprecated local: use src.webui.styles.loader.load_responsive_css instead."""
    from src.webui.styles.loader import load_responsive_css as _load
    _load()



def generate_chat_history_text():
    """Deprecated local: use src.webui.utils.helpers.generate_chat_history_text instead."""
    from src.webui.utils.helpers import generate_chat_history_text as _generate
    return _generate(st.session_state.get('chat_history', []))


def format_message_for_copy(message_index: int) -> str:
    """Deprecated local: use src.webui.utils.helpers.format_message_for_copy instead."""
    from src.webui.utils.helpers import format_message_for_copy as _fmt
    return _fmt(message_index, st.session_state.get('chat_history', []))


def display_chat_history_section():
    from src.webui.components.sidebar import display_chat_history_in_sidebar as _render_history
    _render_history()


def display_chat_history_section():
    from src.webui.components.sidebar import display_chat_history_in_sidebar as _render_history
    _render_history()

def display_consent_form():
    """Deprecated local: use src.webui.components.modals.show_consent_dialog instead."""
    from src.webui.components.modals import show_consent_dialog as _consent
    _consent()


def show_consent_dialog():
    """Deprecated local: use src.webui.components.modals.show_consent_dialog instead."""
    from src.webui.components.modals import show_consent_dialog as _consent_dialog
    _consent_dialog()


def main():
    # Add this as the first line
    disable_streamlit_watcher()
    
    # Initialize session state first
    if 'selected_source' not in st.session_state:
        st.session_state.selected_source = None
    if 'session_id' not in st.session_state or not st.session_state.get('session_id'):
        st.session_state.session_id = str(uuid4())
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    # REMOVED has_asked_question - we'll use chat_history length instead
    if 'language_confirmed' not in st.session_state:
        st.session_state.language_confirmed = False
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = 'english'
    # Ensure FAQ popup flag always exists before any path references it
    if 'show_faq_popup' not in st.session_state:
        st.session_state.show_faq_popup = False
    if 'event_loop' not in st.session_state:
        st.session_state.event_loop = create_event_loop()
    if 'chatbot_init' not in st.session_state:
        st.session_state.chatbot_init = None
    if 'consent_given' not in st.session_state:
        st.session_state.consent_given = False
    if 'show_faq' not in st.session_state:
        st.session_state.show_faq = False
    if 'needs_rerun' not in st.session_state:
        st.session_state.needs_rerun = False
    
    # Define sidebar toggle callback at the top of main() so it can be shared
    def toggle_sidebar() -> None:
        new_open = not st.session_state.get('_sb_open', True)
        st.session_state._sb_open = new_open
        st.session_state._sb_rerun = True
        # Keep URL param in sync so top-of-file logic doesn't override user toggle
        try:
            _set_query_params_robust({"sb": "1" if new_open else "0"}, merge=True)
        except Exception:
            pass

    # Decide mobile vs desktop early
    mobile = is_mobile_device()
    # Always load CSS; mobile styles are guarded by media queries
    load_css_files()
    load_mobile_css()
    load_custom_css()
    load_responsive_css()
    # Expose a tiny banner for debugging in dev tools
    try:
        st.markdown(
            f"""
            <div style=\"display:none\" id=\"mlcc-mobile-debug\" data-mobile=\"{str(bool(mobile)).lower()}\"></div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass
    # Removed visible debug banner in production
    # Close button CSS: maximize specificity and exclude from global button rules
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] button[key="sb_close_btn"],
        section[data-testid="stSidebar"] .sb-close-button-container .stButton > button,
        section[data-testid="stSidebar"] div.stButton:first-child button,
        section[data-testid="stSidebar"] > div > div > div > div:first-child button {
          background-color: #303030 !important;
          color: #ffffff !important;
          border: 1px solid #4f4f4f !important;
          box-shadow: none !important;
          padding: 4px 8px !important;
          border-radius: 8px !important;
          min-width: 0 !important;
          font-size: 18px !important;
          margin-bottom: 10px !important;
        }
        section[data-testid="stSidebar"] button[key="sb_close_btn"]:hover,
        section[data-testid="stSidebar"] .sb-close-button-container .stButton > button:hover,
        section[data-testid="stSidebar"] div.stButton:first-child button:hover,
        section[data-testid="stSidebar"] > div > div > div > div:first-child button:hover {
          background-color: #444444 !important;
          border-color: #555555 !important;
          color: #ffffff !important;
          transform: none !important;
        }
        /* General button styling for others; exclude the close button by key */
        .stButton > button:not([key="sb_close_btn"]) {
          background-color: #009376;
          color: white;
          border-radius: 8px;
          border: none;
          padding: 10px 24px;
          font-weight: 600;
          font-size: 16px;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Consent gate: show only the dialog and stop rendering anything else
    if not st.session_state.get("consent_given", False):
        show_consent_dialog()
        st.stop()

    # Initialize chatbot AFTER consent to avoid duplicate widgets and hidden inputs
        if st.session_state.chatbot_init is None:
            st.session_state.chatbot_init = init_chatbot()

    # Always render the main app content; show consent as overlay at the end if needed
    try:
        # Get the already-initialized chatbot
        chatbot_init = st.session_state.chatbot_init
        if not isinstance(chatbot_init, dict):
            # Try to initialize again if previous state was missing
            chatbot_init = init_chatbot()
            st.session_state.chatbot_init = chatbot_init
        if not isinstance(chatbot_init, dict):
            chatbot_init = {"success": False, "chatbot": None, "error": "Chatbot initialization returned no result"}
        if not chatbot_init.get("success", False):
            st.error(chatbot_init.get("error", "Failed to initialize chatbot. Please check your configuration."))
            st.warning("Make sure all required API keys are properly configured in your environment")
            return

        chatbot = chatbot_init.get("chatbot")
        
        # Handle sidebar force-open via query param
        try:
            params = st.query_params  # Streamlit 1.30+
        except Exception:
            try:
                params = st.experimental_get_query_params()  # fallback for older versions
            except Exception:
                params = {}
        sb = (params.get("sb") if isinstance(params, dict) else None)
        if sb:
            val = sb[0] if isinstance(sb, list) else sb
            if str(val) == "1":
                st.session_state._force_sidebar_open = True
            elif str(val) == "0":
                st.session_state._force_sidebar_open = False

        # Do not force sidebar visibility via CSS; rely on page_config + toggle button

        # Sidebar (modularized)
        render_sidebar_component(
            chatbot=chatbot,
            mobile_mode=bool(mobile),
            toggle_sidebar=toggle_sidebar,
            set_query_params=_set_query_params_robust,
            tree_icon_path=TREE_ICON,
        )

        # Sidebar toggle control in main content area (only shows when sidebar is closed and not mobile)
        if (not st.session_state.get("MOBILE_MODE", False)) and not st.session_state.get('_sb_open', True):
            arrow_icon = "➡️"
            # Anchor element to uniquely target the very next st.button with CSS
            st.markdown('<div id="sb-toggle-anchor"></div>', unsafe_allow_html=True)
            # Subtle, light-grey, fixed-position styling near the top-left; fills on hover
            st.markdown(
                """
<style>
                #sb-toggle-anchor + div.stButton {
                    position: fixed; top: 8px; left: 10px; z-index: 100;
                }
                #sb-toggle-anchor + div.stButton > button {
                    background: transparent !important;
                    color: #666666 !important;
                    border: 1px solid #d9d9d9 !important;
                    border-radius: 8px !important;
                    padding: 4px 8px !important;
                    font-size: 14px !important;
                    min-width: 0 !important;
                    box-shadow: none !important;
                }
                #sb-toggle-anchor + div.stButton > button:hover:not(:disabled) {
                    background: #e9e9e9 !important;
                    color: #444444 !important;
                }
                #sb-toggle-anchor + div.stButton > button:active:not(:disabled) {
                    background: #dcdcdc !important;
                    color: #333333 !important;
                }
                    /* Ensure the toggle button remains visible on mobile */
                    @media (max-width: 768px) {
                        #sb-toggle-anchor + div.stButton { display: block !important; }
                    }
</style>
                """,
                unsafe_allow_html=True,
            )
            st.button(arrow_icon, key="sb_toggle_btn", help="Toggle sidebar", on_click=toggle_sidebar)

        # Drive UI path from detector and single switch
        st.session_state.MOBILE_MODE = bool(mobile)

        # Ensure desktop always opens sidebar and syncs URL param once
        if not st.session_state.MOBILE_MODE:
            try:
                st.session_state._sb_open = True
                st.session_state._sb_rerun = False
                params_now = _get_all_query_params_single_values()
                if (params_now.get("sb") != "1") and (not st.session_state.get("_desktop_sb_synced", False)):
                    _set_query_params_robust({"sb": "1"}, merge=True)
                    st.session_state._desktop_sb_synced = True
                    st.rerun()
            except Exception:
                pass

        def activate_mobile_mode(chatbot) -> None:
            from src.webui.components.header import activate_mobile_mode as _activate_mobile
            _activate_mobile(chatbot, CCC_ICON_B64)

        if st.session_state.MOBILE_MODE:
            activate_mobile_mode(chatbot)
            if len(st.session_state.chat_history) == 0:
                st.markdown(
                    """
                    <div style=\"text-align:center; margin:12px 0 16px 0;\"> 
                      <h3 style=\"margin:0; color:#009376;\">Multilingual Climate Chatbot</h3>
                      <div style=\"color:#6b6b6b; font-size:14px;\">Ask me anything about climate change!</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            from src.webui.components.header import render_desktop_header as _render_desktop
            _render_desktop(CCC_ICON_B64)

        # Remove floating toggle; sidebar collapse is disabled and sidebar always visible via CSS

        # FAQ Popup Modal using delegated component
        if st.session_state.show_faq_popup:
            from src.webui.components.modals import render_faq_modal
            render_faq_modal()

        # Chat area delegated
        from src.webui.components.chat import handle_chat_turn as _handle_chat_turn
        if not st.session_state.language_confirmed:
            from src.webui.components.modals import render_language_confirmation_banner
            render_language_confirmation_banner()
        _handle_chat_turn(chatbot)
    except Exception as e:
        st.error(f"Error initializing chatbot: {str(e)}")
        st.info("Make sure the .env file exists in the project root directory")

    # Finally, show consent overlay if not yet given
    if not st.session_state.get("consent_given", False):
        show_consent_dialog()
        try:
            # Get the already-initialized chatbot
            chatbot_init = st.session_state.chatbot_init

            if not chatbot_init.get("success", False):
                st.error(chatbot_init.get("error", "Failed to initialize chatbot. Please check your configuration."))
                st.warning("Make sure all required API keys are properly configured in your environment")
                return

            chatbot = chatbot_init.get("chatbot")

            # Sidebar (modularized second path)
            render_sidebar_component(
                chatbot=chatbot,
                mobile_mode=bool(mobile),
                toggle_sidebar=toggle_sidebar,
                set_query_params=_set_query_params_robust,
                tree_icon_path=TREE_ICON,
            )

            # Main header content with proper alignment
            if CCC_ICON_B64:
                st.markdown(
                    f"""
                    <div class="mlcc-header desktop">
                        <img class="mlcc-logo" src="data:image/png;base64,{CCC_ICON_B64}" alt="Logo" />
                        <h1 style="margin:0;">Multilingual Climate Chatbot</h1>
                    </div>
                    <div class="mlcc-subtitle desktop">Ask me anything about climate change!</div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.title("Multilingual Climate Chatbot")
                st.write("Ask me anything about climate change!")

            # FAQ Popup Modal using Streamlit native components
            if st.session_state.show_faq_popup:
                # Create a full-screen overlay effect using CSS
                st.markdown(
                    """
                <style>
                /* Create overlay effect */
                .stApp > div > div > div > div > div > section > div {
                    background-color: rgba(0, 0, 0, 0.7) !important;
                }
                
                /* Style the popup container */
                div[data-testid="column"]:has(.faq-popup-marker) {
                    background-color: white;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                    max-height: 80vh;
                    overflow-y: auto;
                }

                /* Subtle link-style button for feedback */
                a.feedback-button {
                    display: inline-block;
                    padding: 6px 10px;
                    border-radius: 6px;
                    border: 1px solid #d0d7de;
                    background: #f6f8fa;
                    color: #24292f !important;
                    text-decoration: none;
                    font-size: 14px;
                }
                a.feedback-button:hover {
                    background: #eef2f6;
                }
                
                /* Mobile font size normalization for FAQ popup */
                @media (max-width: 768px) {
                    div[data-testid="column"]:has(.faq-popup-marker) {
                        padding: 12px !important;
                        max-height: 85vh !important;
                    }
                    div[data-testid="column"]:has(.faq-popup-marker) h1 { 
                        font-size: 1.2rem !important; 
                        margin-bottom: 8px !important;
                    }
                    div[data-testid="column"]:has(.faq-popup-marker) h2 { 
                        font-size: 1.05rem !important; 
                        margin: 12px 0 6px 0 !important;
                    }
                    div[data-testid="column"]:has(.faq-popup-marker) h3 { 
                        font-size: 0.95rem !important; 
                        margin: 8px 0 4px 0 !important;
                    }
                    div[data-testid="column"]:has(.faq-popup-marker) p,
                    div[data-testid="column"]:has(.faq-popup-marker) div,
                    div[data-testid="column"]:has(.faq-popup-marker) li { 
                        font-size: 0.9rem !important; 
                        line-height: 1.4 !important;
                    }
                    div[data-testid="column"]:has(.faq-popup-marker) .stExpander > div > div > div { 
                        font-size: 0.9rem !important; 
                    }
                    div[data-testid="column"]:has(.faq-popup-marker) [data-testid="stMarkdownContainer"] { 
                        font-size: 0.9rem !important; 
                    }
                }
                </style>
                """,
                    unsafe_allow_html=True,
                )
                
                # Create centered columns for the popup
                col1, col2, col3 = st.columns([1, 6, 1])
                
                with col2:
                    # Add a marker class for CSS targeting
                    st.markdown('<div class="faq-popup-marker"></div>', unsafe_allow_html=True)
                    
                    # Header with close button
                    header_col1, header_col2 = st.columns([11, 1])
                    with header_col1:
                        st.markdown("# Support & FAQs")
                    with header_col2:
                        if st.button("✕", key="close_faq", help="Close FAQ"):
                            st.session_state.show_faq_popup = False
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # Information Accuracy Section
                    with st.container():
                        st.markdown("## 📊 Information Accuracy")
                        
                        with st.expander("How accurate is the information provided by the chatbot?", expanded=True):
                            st.write(
                                """
                            Our chatbot uses Retrieval-Augmented Generation (RAG) technology to provide verified information exclusively 
                            from government reports, academic research, and established non-profit organizations' publications. Every 
                            response includes citations to original sources, allowing you to verify the information directly. The system 
                            matches your questions with relevant, verified information rather than generating content independently.
                            """
                            )
                        
                        with st.expander("What sources does the chatbot use?", expanded=True):
                            st.write(
                                """
                            All information comes from three verified source types: government climate reports, peer-reviewed academic 
                            research, and established non-profit organization publications. Each response includes citations linking 
                            directly to these sources.
                            """
                            )
                    
                    st.markdown("---")
                    
                    # Privacy Protection Section
                    with st.container():
                        st.markdown("## 🔒 Privacy Protection")
                        
                        with st.expander("What information does the chatbot collect?", expanded=True):
                            st.write("We maintain a strict privacy-first approach:")
                            st.markdown(
                                """
                            - No personal identifying information (PII) is collected
                            - Questions are automatically screened to remove any personal details
                            - Only anonymized questions are cached to improve service quality
                            - No user accounts or profiles are created
                            """
                            )
                        
                        with st.expander("How is the cached data used?", expanded=True):
                            st.write(
                                """
                            Cached questions, stripped of all identifying information, help us improve response accuracy and identify 
                            common climate information needs. We regularly delete cached questions after analysis.
                            """
                            )
                    
                    st.markdown("---")
                    
                    # Trust & Transparency Section
                    with st.container():
                        st.markdown("## 🤝 Trust & Transparency")
                        
                        with st.expander("How can I trust this tool?", expanded=True):
                            st.write("Our commitment to trustworthy information rests on:")
                            st.markdown(
                                """
                            - Citations for every piece of information, linking to authoritative sources
                            - Open-source code available for public review  
                            - Community co-design ensuring real-world relevance
                            - Regular updates based on user feedback and new research
                            """
                            )
                        
                        with st.expander("How can I provide feedback or report issues?", expanded=True):
                            st.write("We welcome your input through:")
                            st.markdown(
                                """
                            - The feedback button within the chat interface
                            - [Our GitHub repository](https://github.com/Climate-Resilient-Communities/climate-multilingual-chatbot) for technical contributions
                            - Community feedback sessions
                            """
                            )
                            # Subtle feedback button linking to a Google Form
                            st.markdown(
                                '<a class="feedback-button" href="https://forms.gle/7mXRSc3JAF8ZSTmr9" target="_blank" title="Report bugs or share feedback (opens Google Form)">📝 Submit Feedback</a>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                'For technical support or to report issues, please visit our <a href="https://github.com/Climate-Resilient-Communities/climate-multilingual-chatbot" target="_blank">GitHub repository</a>.',
                                unsafe_allow_html=True,
                            )
                    
                    # Add some space at the bottom
                    st.markdown("<br><br>", unsafe_allow_html=True)
                
                # Stop rendering anything else while popup is shown
                st.stop()

            # Display chat messages; if a retry is in progress, we get a placeholder to render loader/result inline
            retry_req = st.session_state.get('retry_request') if isinstance(st.session_state.get('retry_request'), dict) else None
            injected_retry_placeholder = display_chat_messages(retry_req)

            if st.session_state.language_confirmed:
                query = st.chat_input("Ask Climate Change Bot")
                # Append user question immediately after input
                if query:
                    try:
                        from src.utils.logging_setup import ensure_file_logger
                        ensure_file_logger(os.getenv("PIPELINE_LOG_FILE", os.path.join(os.getcwd(), "logs", "pipeline_debug.log")))
                        logger.info("UI IN → raw_query repr=%r codepoints(first20)=%s", query, [ord(c) for c in query[:20]])
                    except Exception:
                        pass
                    st.session_state.chat_history.append({'role': 'user', 'content': query})
                    # REMOVED: has_asked_question update - not needed anymore
            else:
                # Just show a language selection banner under the main title
                # No extra welcome message, just the green banner
                st.markdown(
                    """
                <div style="margin-top: 10px; margin-bottom: 30px; background-color: #009376; padding: 10px; border-radius: 5px; color: white; text-align: center;">
                Please select your language and click Confirm to start chatting.
                </div>
                """,
                    unsafe_allow_html=True
                )
                query = None

            # Check for needs_rerun flag first and reset it to prevent loops
            if st.session_state.get('needs_rerun', False):
                st.session_state.needs_rerun = False
                # Don't process any queries on this run, as we're just updating the UI
                pass
            elif (query or retry_req) and chatbot:
                # User message is already added to chat history above
                # Display the user message
                if query:
                    st.chat_message("user").markdown(render_user_bubble(query), unsafe_allow_html=True)
                    render_message_actions_ui(len(st.session_state.chat_history) - 1, st.session_state.chat_history[-1])

                # Choose where to render the assistant placeholder:
                # - If this is a retry, use the injected placeholder under the same user message
                # - Otherwise, create a new assistant container at the end
                if retry_req and injected_retry_placeholder is not None:
                    typing_message = injected_retry_placeholder
                else:
                    response_placeholder = st.chat_message("assistant")
                    typing_message = response_placeholder.empty()
                # Replace plain text with interactive progress UI below
                
                try:
                    # Build conversation history for process_query
                    conversation_history = []
                    chat_hist = st.session_state.chat_history
                    i = 0
                    while i < len(chat_hist) - 1:
                        if chat_hist[i]["role"] == "user" and chat_hist[i+1]["role"] == "assistant":
                            conversation_history.append({
                                "query": chat_hist[i]["content"],
                                "response": chat_hist[i+1]["content"],
                                "language_code": chat_hist[i+1].get("language_code", "en"),
                                "language_name": st.session_state.selected_language,
                                "timestamp": None
                            })
                            i += 2
                        else:
                            i += 1
                    # If a retry was requested, use that captured query; else use current input
                    retry_req = st.session_state.get('retry_request') if isinstance(st.session_state.get('retry_request'), dict) else None
                    retry_query = retry_req.get('query') if retry_req else None
                    effective_query = retry_query or query

                    # Process query with interactive progress UI
                    result = run_query_with_interactive_progress(
                        chatbot=chatbot,
                        query=effective_query,
                        language_name=st.session_state.selected_language,
                        conversation_history=conversation_history,
                        response_placeholder=typing_message,
                        skip_cache=bool(retry_req)
                    )
                    
                    typing_message.empty()
                    
                    # FIXED: Enhanced handling of successful responses vs off-topic questions
                    if result and result.get('success', False):
                        # Clean and prepare the response content
                        response_content = result['response']
                        
                        # Ensure proper markdown formatting for headings
                        if response_content and isinstance(response_content, str):
                            # Strip any leading/trailing whitespace
                            response_content = response_content.strip()
                            
                            # If content starts with a heading, ensure it's properly formatted
                            if response_content.startswith('#'):
                                # Make sure there's a space after the # symbols
                                response_content = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', response_content)
                        
                        # Update response without header formatting
                        final_response = {
                            'role': 'assistant',
                            'language_code': result.get('language_code', 'en'),
                            'content': response_content,  # Use the cleaned content
                            'citations': result.get('citations', []),
                            'retrieval_source': result.get('retrieval_source'),
                            'fallback_reason': result.get('fallback_reason'),
                        }
                        # If retry, insert at the original assistant index; otherwise append
                        if retry_req and isinstance(retry_req.get('assistant_index'), int):
                            insert_at = min(retry_req['assistant_index'], len(st.session_state.chat_history))
                            st.session_state.chat_history.insert(insert_at, final_response)
                            # Log the retry interaction
                            try:
                                persist_interaction_record(insert_at, "none")
                            except Exception as log_err:
                                logger.warning(f"Failed to log retry interaction: {log_err}")
                        else:
                            st.session_state.chat_history.append(final_response)
                            # Log the interaction to local and Azure blob storage
                            try:
                                persist_interaction_record(len(st.session_state.chat_history) - 1, "none")
                            except Exception as log_err:
                                logger.warning(f"Failed to log Q&A interaction: {log_err}")
                        
                        # Display final response without markdown header formatting
                        language_code = final_response['language_code']
                        text_align = 'right' if is_rtl_language(language_code) else 'left'
                        direction = 'rtl' if is_rtl_language(language_code) else 'ltr'
                        
                        content = clean_html_content(final_response['content'])

                        typing_message.markdown(
                            f"""<div style="direction: {direction}; text-align: {text_align}">
                            {content}
                            </div>""",
                            unsafe_allow_html=True
                        )
                        
                        # Store exactly what was displayed for this assistant message for Copy
                        try:
                            if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                                st.session_state.copy_texts = {}
                            st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = content or final_response['content'] or ''
                        except Exception:
                            pass
                        
                        # Display citations if available
                        if result.get('citations'):
                            if retry_req and isinstance(retry_req.get('assistant_index'), int):
                                message_idx = min(retry_req['assistant_index'], len(st.session_state.chat_history) - 1)
                            else:
                                message_idx = len(st.session_state.chat_history) - 1
                            display_source_citations(result['citations'], base_idx=message_idx)
                        # Render message actions for assistant message
                        if retry_req and isinstance(retry_req.get('assistant_index'), int):
                            render_message_actions_ui(message_idx, final_response)
                        else:
                            render_message_actions_ui(len(st.session_state.chat_history) - 1, final_response)
                    else:
                        # Handle off-topic questions and other errors more comprehensively
                        # Prefer 'message' but fall back to 'response' when pipeline uses that field
                        error_message = (
                            result.get('message')
                            or result.get('response')
                            or 'An error occurred'
                        )

                        # Normalize for checks
                        error_lower = error_message.lower() if isinstance(error_message, str) else ''

                        # Detect off-topic climate rejections
                        if (
                            "not about climate" in error_lower
                            or "climate change" in error_lower
                            or result.get('error_type') == "off_topic"
                            or (result.get('validation_result', {}).get('reason') == "not_climate_related")
                        ):
                            off_topic_response = (
                                "I'm a climate change assistant and can only help with questions about climate, environment, and sustainability. "
                                "Please ask me about topics like climate change causes, effects, or solutions."
                            )

                            st.session_state.chat_history.append({
                                'role': 'assistant',
                                'content': off_topic_response,
                                'language_code': 'en'
                            })

                            # Log the off-topic interaction
                            try:
                                persist_interaction_record(len(st.session_state.chat_history) - 1, "none")
                            except Exception as log_err:
                                logger.warning(f"Failed to log off-topic interaction: {log_err}")

                            typing_message.markdown(off_topic_response)
                            try:
                                if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                                    st.session_state.copy_texts = {}
                                st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = off_topic_response
                            except Exception:
                                pass
                        else:
                            # Generic error surfaced to user
                            st.session_state.chat_history.append({
                                'role': 'assistant',
                                'content': str(error_message),
                                'language_code': 'en'
                            })
                            typing_message.error(str(error_message))
                            try:
                                if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                                    st.session_state.copy_texts = {}
                                st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = str(error_message)
                            except Exception:
                                pass
                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    st.session_state.chat_history.append({
                        'role': 'assistant', 
                        'content': error_msg,
                        'language_code': 'en'
                    })
                    typing_message.error(error_msg)
                    # Render actions even for error messages
                    render_message_actions_ui(len(st.session_state.chat_history) - 1, st.session_state.chat_history[-1])
                    try:
                        if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                            st.session_state.copy_texts = {}
                        st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = error_msg
                    except Exception:
                        pass

                # After answering, clear retry flags
                if retry_req:
                    st.session_state.retry_request = None
                    st.session_state.last_retry_applied = None
                # Normal UI refresh after answering
                st.session_state.needs_rerun = True
                st.rerun()
            
            # Don't run cleanup after every message - only when the app is closing
            # This would be handled by st.cache_resource's cleanup mechanism
            
        except Exception as e:
            # Suppress noisy UI error; log instead to avoid breaking UX
            logger.error(f"Error initializing chatbot: {str(e)}")
            st.info("Make sure the .env file exists in the project root directory")

if __name__ == "__main__":
    main()