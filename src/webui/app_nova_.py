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
from streamlit.components.v1 import html as st_html

# Robustly force initial sidebar state by temporarily flipping the state,
# triggering a rerun, then applying the desired state. This overrides any
# browser-persisted user choice Streamlit keeps.
SIDEBAR_STATE = {True: "expanded", False: "collapsed"}

# --- Query param helpers (robust across Streamlit versions) ---
def _get_query_param_single_value(name, default=None):
    """Return a single string value for a query param across Streamlit versions.
    Handles both st.query_params (QueryParams) and st.experimental_get_query_params (dict[str, list[str]]).
    """
    try:
        params = st.query_params
    except Exception:
        try:
            params = st.experimental_get_query_params()
        except Exception:
            return default

    # Access value
    try:
        value = params.get(name)
    except Exception:
        value = None

    # Normalize lists
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default

def _is_mobile_from_query_params():
    """Determine mobile intent from query params (?mobile=1 or ?m=1/true/yes)."""
    raw = _get_query_param_single_value("mobile") or _get_query_param_single_value("m")
    if isinstance(raw, str) and raw.lower() in ("1", "true", "yes", "y"):  # allow a few truthy forms
        return True
    return False

def _get_all_query_params_single_values():
    """Return current query params as {str: str} with list values collapsed to first element."""
    try:
        params = st.query_params
    except Exception:
        try:
            params = st.experimental_get_query_params()
        except Exception:
            return {}
    collapsed = {}
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

def _set_query_params_robust(new_params: dict, merge: bool = True) -> None:
    """Set query params using new API when available, with optional merge of existing params."""
    try:
        current = _get_all_query_params_single_values() if merge else {}
        # ensure string values
        for k, v in (new_params or {}).items():
            if v is None:
                continue
            current[str(k)] = str(v)
        try:
            st.query_params = current  # Streamlit ≥1.30
        except Exception:
            try:
                st.experimental_set_query_params(**current)  # Fallback
            except Exception:
                pass
    except Exception:
        pass

def _pop_feedback_action_from_query_params():
    """Return (action, index) if a feedback action is encoded in the URL, then remove it.
    Action is one of {up, down, retry}. Index is int.
    """
    try:
        current = _get_all_query_params_single_values()
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
        _set_query_params_robust(current, merge=False)
        return action, idx
    except Exception:
        return None, None

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

if st.session_state.get("_sb_rerun", False):
    st.set_page_config(
        layout="wide", 
        page_title="Multilingual Climate Chatbot",
        page_icon=calculated_favicon,
        initial_sidebar_state=SIDEBAR_STATE[not st.session_state._sb_open],
    )
    st.session_state._sb_rerun = False
    st.rerun()

# Final page config with the desired sidebar state
st.set_page_config(
    layout="wide",
    page_title="Multilingual Climate Chatbot",
    page_icon=calculated_favicon,
    initial_sidebar_state=SIDEBAR_STATE[st.session_state._sb_open],
)

# On load: if a previous action requested closing the sidebar via sessionStorage,
# perform a best-effort close using the native collapse control or CSS transform.
st_html(
    """
<script>
try {
  if (sessionStorage.getItem('closeSidebarOnLoad') === '1') {
    sessionStorage.removeItem('closeSidebarOnLoad');
    const tryClose = () => {
      const collapseBtn = document.querySelector('[data-testid="collapsedControl"]') ||
                          document.querySelector('[aria-label*="Collapse"]') ||
                          document.querySelector('button[kind="header"]');
      if (collapseBtn && collapseBtn.getAttribute('aria-expanded') === 'true') {
        collapseBtn.click();
      }
      const sidebar = document.querySelector('section[data-testid="stSidebar"]');
      if (sidebar) {
        sidebar.style.transition = 'transform 0.2s ease';
        sidebar.style.transform = 'translateX(-100%)';
      }
    };
    setTimeout(tryClose, 50);
    setTimeout(tryClose, 200);
  }
} catch (e) {}
</script>
""",
    height=0,
)

# Optional: allow URL param reset_ui=1 to clear any persisted UI prefs in the browser
# and force a fresh load with sidebar open. This is helpful when a user's stored
# preference keeps the sidebar collapsed despite our initial state.
try:
    _params2 = st.query_params
except Exception:
    try:
        _params2 = st.experimental_get_query_params()
    except Exception:
        _params2 = {}

_reset_ui = None
if isinstance(_params2, dict):
    _reset_ui = _params2.get("reset_ui") or _params2.get("sb_reset")
    if isinstance(_reset_ui, list):
        _reset_ui = _reset_ui[0] if _reset_ui else None

if _reset_ui in ("1", 1, True) and not st.session_state.get("_did_reset_ui"):
    # Clear local/session storage keys related to Streamlit UI and reload
    st_html(
        """
<script>
try {
  // Clear Streamlit/UI-related items from localStorage
  const keys = Object.keys(localStorage);
  for (const k of keys) {
    const kl = k.toLowerCase();
    if (kl.includes('streamlit') || kl.includes('sidebar') || kl.startsWith('st-') || kl.includes('siderbar')) {
      localStorage.removeItem(k);
    }
  }
  // Also clear sessionStorage to be safe
  try { sessionStorage.clear(); } catch(e) {}
  // Reload without reset_ui param and with sb=1 to ensure open
  const url = new URL(window.location.href);
  url.searchParams.delete('reset_ui');
  url.searchParams.delete('sb_reset');
  url.searchParams.set('sb','1');
  window.location.replace(url.toString());
} catch (e) { console.error('UI reset error', e); }
</script>
        """,
        height=0,
    )
    st.session_state._did_reset_ui = True
    st.stop()

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
    """
    Redact personally identifiable information from text.

    This function identifies and replaces common PII patterns with redacted placeholders.
    Patterns include: emails, phone numbers, credit cards, SSNs, names, addresses, etc.
    """
    if not text or not isinstance(text, str):
        return text

    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)

    # Credit card numbers (16, 15, 14, or 13 digits with optional spaces/dashes) - Check FIRST before phone numbers
    text = re.sub(r'\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{4}[-\s]?\d{6}[-\s]?\d{5}|\d{4}[-\s]?\d{6}[-\s]?\d{4}|\d{4}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3})\b', '[CREDIT_CARD_REDACTED]', text)

    # Phone numbers (various formats) - Check AFTER credit cards to avoid conflicts
    # US formats: (123) 456-7890, 123-456-7890, 123.456.7890, 123 456 7890, +1 123 456 7890
    phone_patterns = [
        r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',  # US phone numbers
        r'\b\d{3}-\d{3}-\d{4}\b',  # XXX-XXX-XXXX
        r'\b\d{3}\.\d{3}\.\d{4}\b',  # XXX.XXX.XXXX
        r'\(\d{3}\)\s?\d{3}-\d{4}',  # (XXX) XXX-XXXX
        r'\b(?<!\d)\d{10}(?!\d)\b',  # 10 consecutive digits not part of longer number
    ]
    for pattern in phone_patterns:
        text = re.sub(pattern, '[PHONE_REDACTED]', text)

    # Social Security Numbers (XXX-XX-XXXX or 9 consecutive digits)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
    text = re.sub(r'\b(?<!\d)\d{9}(?!\d)\b', '[SSN_REDACTED]', text)  # 9 digits not part of longer number

    # IP addresses
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_REDACTED]', text)

    # Common name patterns (basic - catches "My name is X" or "I'm X")
    text = re.sub(r'\b(?:my name is|i\'?m|call me)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b', r'my name is [NAME_REDACTED]', text, flags=re.IGNORECASE)

    # Address patterns (basic street addresses)
    text = re.sub(r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|place|pl)\b', '[ADDRESS_REDACTED]', text, flags=re.IGNORECASE)

    # Date of birth patterns (MM/DD/YYYY, MM-DD-YYYY, YYYY/MM/DD, YYYY-MM-DD)
    text = re.sub(r'\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b', '[DOB_REDACTED]', text)
    text = re.sub(r'\b(?:19|20)\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])\b', '[DOB_REDACTED]', text)

    # Government ID patterns (basic - alphanumeric IDs)
    text = re.sub(r'\b[A-Z]{1,2}\d{6,8}\b', '[ID_REDACTED]', text)

    # Bank account patterns (8-17 digits, but be careful not to redact legitimate numbers)
    text = re.sub(r'\b(?:account|acct)[\s#:]*(\d{8,17})\b', r'account [ACCOUNT_REDACTED]', text, flags=re.IGNORECASE)

    # License plate patterns (basic - 2-3 letters followed by 3-4 numbers)
    text = re.sub(r'\b[A-Z]{2,3}[-\s]?[0-9]{3,4}\b', '[LICENSE_PLATE_REDACTED]', text)

    return text

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
from src.main_nova import MultilingualClimateChatbot

# Load environment
load_environment()

# Asset paths for general use
ASSETS_DIR = _APP_FILE_DIR / "assets"
TREE_ICON = str(ASSETS_DIR / "tree.ico") if (ASSETS_DIR / "tree.ico").exists() else None
CCC_ICON = str(ASSETS_DIR / "CCCicon.png") if (ASSETS_DIR / "CCCicon.png").exists() else None
WALLPAPER = str(ASSETS_DIR / "wallpaper.png") if (ASSETS_DIR / "wallpaper.png").exists() else None

def get_base64_image(image_path):
    """Convert image to base64 string for CSS embedding."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {str(e)}")
        return None

# Pre-encode logo for header alignment (if available)
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
    """Create and configure a new event loop."""
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.set_debug(False)
        return loop
    except Exception as e:
        st.error(f"Failed to create event loop: {str(e)}")
        raise

def run_async(coro):
    """Helper function to run coroutines in a dedicated event loop"""
    loop = None
    try:
        loop = create_event_loop()
        
        with ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: loop.run_until_complete(coro))
            return future.result()
    except Exception as e:
        st.error(f"Async execution error: {str(e)}")
        raise
    finally:
        if loop and not loop.is_closed():
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.wait_for(
                    asyncio.gather(*pending, return_exceptions=True),
                    timeout=2.0
                ))
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Task cleanup warning: {str(e)}")
            finally:
                try:
                    loop.stop()
                    loop.close()
                except Exception:
                    pass

@st.cache_resource
def init_chatbot():
    """Initialize the chatbot with proper error handling."""
    try:
        index_name = os.environ.get("PINECONE_INDEX_NAME", "climate-change-adaptation-index-10-24-prod")
        chatbot = MultilingualClimateChatbot(index_name)
        # Eager init: pipeline now initializes heavy components on construction
        return {"success": True, "chatbot": chatbot, "error": None}
    except Exception as e:
        error_message = str(e)
        if "404" in error_message and "Resource" in error_message and "not found" in error_message:
            return {
                "success": False,
                "chatbot": None,
                "error": f"Failed to initialize chatbot: Pinecone index not found. Please check your environment configuration."
            }
        else:
            return {
                "success": False, 
                "chatbot": None,
                "error": f"Failed to initialize chatbot: {error_message}"
            }

def get_citation_details(citation):
    """Safely extract citation details."""
    try:
        # Handle citations as dictionary
        if isinstance(citation, dict):
            return {
                'title': citation.get('title', 'Untitled Source'),
                'url': citation.get('url', ''),
                'content': citation.get('content', ''),
                'snippet': citation.get('snippet', citation.get('content', '')[:200] + '...' if citation.get('content') else '')
            }
        # Handle citation objects (backup)
        elif hasattr(citation, 'title'):
            return {
                'title': getattr(citation, 'title', 'Untitled Source'),
                'url': getattr(citation, 'url', ''),
                'content': getattr(citation, 'content', ''),
                'snippet': getattr(citation, 'snippet', getattr(citation, 'content', '')[:200] + '...' if getattr(citation, 'content', '') else '')
            }
    except Exception as e:
        logger.error(f"Error processing citation: {str(e)}")
    
    return {
        'title': 'Untitled Source',
        'url': '',
        'content': '',
        'snippet': ''
    }

def display_source_citations(citations, base_idx=0):
    """Display citations in a visually appealing way."""
    if not citations:
        return

    st.markdown("---")
    # Start scoped section wrapper so we can style sizes without affecting other buttons
    st.markdown('<div class="sources-section">', unsafe_allow_html=True)
    st.markdown('<div class="sources-heading">Sources</div>', unsafe_allow_html=True)

    # Create a dictionary to store unique sources
    unique_sources = {}

    for citation in citations:
        details = get_citation_details(citation)
        
        # Use title as key for deduplication
        if details['title'] not in unique_sources:
            unique_sources[details['title']] = details

    # Display each unique source
    for idx, (title, source) in enumerate(unique_sources.items()):
        with st.container():
            # Create a unique key using the message index and source index
            unique_key = f"source_{base_idx}_{idx}"
            # Compute friendlier label for Drive-like sources
            url_val = source.get('url') or ''
            url_str = str(url_val)
            is_drive_like = any(k in url_str for k in [
                'drive.google.com', 'docs.google.com', '/content/drive', '/MyDrive', '/drive/'
            ])
            display_title = title

            # Show the actual title if we have one; only fall back to neutral label when title is missing/too short
            safe_title = (title or '').strip()
            if not safe_title or len(safe_title) < 4:
                btn_text = 'Content sourced from leading climate specialist'
            else:
                btn_text = safe_title[:100]
            button_label = f"📄 {btn_text}..."
            if st.button(button_label, key=unique_key):
                st.session_state.selected_source = f"{base_idx}_{title}"

            # Show details if selected
            if st.session_state.get('selected_source') == f"{base_idx}_{title}":
                with st.expander("Source Details", expanded=True):
                    if title:
                        st.markdown(f"**Title:** {title}")

                    # Show source information
                    url_val = source.get('url', '')
                    if url_val and url_val.strip():
                        if is_drive_like:
                            # For drive-like sources, show a descriptive source label
                            st.markdown("**Source:** Verified climate research document")
                        else:
                            # For regular URLs, show the actual URL
                            st.markdown(f"**URL:** [{url_val}]({url_val})")
                    else:
                        # If no URL, show that this is from a verified source
                        st.markdown("**Source:** Verified climate research document")

                    if source.get('snippet'):
                        st.markdown("**Cited Content:**")
                        st.markdown(source['snippet'])
                    if source.get('content'):
                        st.markdown("**Full Content:**")
                        st.markdown(source['content'][:500] + '...' if len(source['content']) > 500 else source['content'])

    # Close wrapper
    st.markdown('</div>', unsafe_allow_html=True)

def display_progress(progress_placeholder):
    """Display simple progress bar."""
    progress_bar = progress_placeholder.progress(0)
    status_text = progress_placeholder.empty()

    stages = [
        ("🔍 Searching...", 0.2),
        ("📚 Retrieving documents...", 0.4),
        ("✍️ Generating response...", 0.7),
        ("✔️ Verifying response...", 0.9),
        ("✨ Complete!", 1.0)
    ]

    for stage_text, progress in stages:
        status_text.text(stage_text)
        progress_bar.progress(progress)
        time.sleep(0.5)  # Brief pause between stages

    progress_placeholder.empty()

def _render_loading_ui(container, stage_text: str, progress_value: float) -> None:
    """Render a compact animated loading UI with stage text and a progress bar."""
    progress_percent = max(0, min(100, int(progress_value * 100)))
    container.markdown(
        f"""
        <style>
        .mlcc-loading {{
            display: flex; align-items: center; gap: 12px; padding: 10px 12px;
            border: 1px solid #e7e7e7; border-radius: 10px; background: #fafafa;
        }}
        .mlcc-loading .cloud {{ font-size: 22px; }}
        .mlcc-loading .spinner {{
            width: 16px; height: 16px; border: 3px solid #e0e0e0; border-top-color: #009376;
            border-radius: 50%; animation: mlcc-spin 0.8s linear infinite; margin-left: auto;
        }}
        .mlcc-loading .stage {{ font-weight: 600; color: #444; font-size: 0.95rem; }}
        .mlcc-loading .bar {{
            width: 180px; height: 8px; background: #eee; border-radius: 6px; overflow: hidden;
        }}
        .mlcc-loading .fill {{
            height: 100%; background: linear-gradient(90deg, #00b894, #009376);
            width: {progress_percent}%; transition: width 250ms ease;
        }}
        @keyframes mlcc-spin {{
            from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }}
        }}
        </style>
        <div class="mlcc-loading">
            <div class="cloud">☁️</div>
            <div class="content">
                <div class="stage">{stage_text}</div>
                <div class="bar"><div class="fill"></div></div>
            </div>
            <div class="spinner"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _run_query_background(chatbot, query: str, language_name: str, conversation_history: list, result_holder: dict, q: "queue.Queue", skip_cache: bool) -> None:
    """Worker to execute the async pipeline and store result/exceptions, streaming progress via queue."""
    try:
        async def _runner():
            return await chatbot.pipeline.process_query(  # Prefer unified pipeline when available
                query=query,
                language_name=language_name,
                conversation_history=conversation_history,
                progress_callback=lambda stage, pct: q.put({"stage": stage, "pct": pct}),
                skip_cache=skip_cache,
            )

        # Fallback if pipeline absent
        if hasattr(chatbot, "pipeline") and chatbot.pipeline:
            result = run_async(_runner())
        else:
            result = run_async(
                chatbot.process_query(
                    query=query,
                    language_name=language_name,
                    conversation_history=conversation_history,
                )
            )
        result_holder["result"] = result
    except Exception as exc:  # noqa: BLE001
        result_holder["error"] = exc

def run_query_with_interactive_progress(chatbot, query: str, language_name: str, conversation_history: list, response_placeholder, skip_cache: bool = False):
    """Run the query while rendering an animated multi-stage progress UI.

    Returns the pipeline result (or raises if worker errored).
    """
    stages = [
        "Thinking…",
        "Retrieving documents…",
        "Formulating response…",
        "Verifying answer…",
    ]

    progress_container = response_placeholder.empty()
    progress_events: "queue.Queue" = queue.Queue()

    # Start worker in a background thread
    result_holder: dict = {"result": None, "error": None}
    worker = threading.Thread(target=_run_query_background, args=(chatbot, query, language_name, conversation_history, result_holder, progress_events, skip_cache), daemon=True)
    worker.start()

    # Animate until the worker completes
    start_time = time.time()
    progress_value = 0.0
    stage_text = "Thinking…"

    def _simplify_stage(stage: str) -> str:
        if not stage:
            return "Thinking…"
        s = stage.lower()
        if any(k in s for k in ["routing", "rewrite", "validat", "thinking"]):
            return "Thinking…"
        if any(k in s for k in ["retriev", "document"]):
            return "Retrieving documents…"
        if any(k in s for k in ["formulat", "draft", "verif", "quality", "translat", "response"]):
            return "Generating response…"
        if "final" in s:
            return "Finalizing…"
        if "complete" in s:
            return "Complete"
        return "Thinking…"

    while worker.is_alive():
        # Drain any progress events from pipeline and render
        try:
            while True:
                ev = progress_events.get_nowait()
                stage_text = _simplify_stage(ev.get("stage", stage_text))
                progress_value = max(progress_value, float(ev.get("pct", 0.0)))
        except queue.Empty:
            pass

        # Keep a gentle heartbeat if pipeline sends sparse updates
        progress_value = min(progress_value + 0.01, 0.95)
        _render_loading_ui(progress_container, stage_text, progress_value)
        time.sleep(0.15)

    worker.join()
    # Finish the bar
    _render_loading_ui(progress_container, "Finalizing…", 1.0)
    time.sleep(0.15)
    progress_container.empty()

    if result_holder.get("error") is not None:
        raise result_holder["error"]
    return result_holder.get("result")

def is_rtl_language(language_code):
        return language_code in {'fa', 'ar', 'he'}

def clean_html_content(content):
    """Clean content from stray HTML tags that might break rendering."""
    # Handle the case where content is None
    if content is None:
        return ""
    
    # Replace any standalone closing div tags
    content = re.sub(r'</div>\s*$', '', content)
    
    # Replace other potentially problematic standalone tags
    content = re.sub(r'</?div[^>]*>\s*$', '', content)
    content = re.sub(r'</?span[^>]*>\s*$', '', content)
    content = re.sub(r'</?p[^>]*>\s*$', '', content)
    
    # Fix unbalanced markdown or code blocks
    # Check if there are uneven numbers of triple backticks
    backtick_count = content.count('```')
    if backtick_count % 2 != 0:
        content += '\n```'  # Add closing code block
    
    # Ensure content is a string
    return str(content)

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

def render_user_bubble(text: str, language_code: str = "en") -> str:
    direction = 'rtl' if is_rtl_language(language_code) else 'ltr'
    escaped = escape_html(text)
    return (
        f"""
        <div style="display:flex; justify-content:flex-end;">
            <div style="direction:{direction}; max-width:85%; background:#e8f5f1; color:#222; padding:10px 14px; border-radius:12px 12px 0 12px; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                {escaped}
            </div>
        </div>
        """
    )

def render_message_actions_ui(message_index: int, message: dict) -> None:
    if 'message_feedback' not in st.session_state:
        st.session_state.message_feedback = {}
    if 'show_copy_panel' not in st.session_state or not isinstance(st.session_state.show_copy_panel, dict):
        st.session_state.show_copy_panel = {}
    # Build normalized copy text based on the same format used for downloads
    content_for_copy = format_message_for_copy(message_index)
    role = message.get('role', 'assistant')
    is_assistant = role != 'user'
    # Only show actions for assistant messages
    if not is_assistant:
        return
    # Alternative simpler approach: render custom HTML buttons that encode action in URL
    up_clicked = False
    down_clicked = False
    retry_clicked = False
    st.markdown(
        f"""
        <div class=\"msg-actions-custom\" style=\"display:flex; gap:8px; margin:8px 0;\">
          <button onclick=\"(function(){{try{{var u=new URL(window.location.href);u.searchParams.set('fb','up');u.searchParams.set('i','{message_index}');window.history.replaceState({{}},'',u);window.location.reload();}}catch(e){{}}}})()\" 
                  style=\"width:44px;height:44px;border-radius:10px;border:1px solid #e0e0e0;background:white;font-size:20px;cursor:pointer;\">👍</button>
          <button onclick=\"(function(){{try{{var u=new URL(window.location.href);u.searchParams.set('fb','down');u.searchParams.set('i','{message_index}');window.history.replaceState({{}},'',u);window.location.reload();}}catch(e){{}}}})()\" 
                  style=\"width:44px;height:44px;border-radius:10px;border:1px solid #e0e0e0;background:white;font-size:20px;cursor:pointer;\">👎</button>
          <button onclick=\"(function(){{try{{var u=new URL(window.location.href);u.searchParams.set('fb','retry');u.searchParams.set('i','{message_index}');window.history.replaceState({{}},'',u);window.location.reload();}}catch(e){{}}}})()\" 
                  style=\"width:44px;height:44px;border-radius:10px;border:1px solid #e0e0e0;background:white;font-size:20px;cursor:pointer;\">↻</button>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if retry_clicked:
        prior_query = ''
        user_index = -1
        j = message_index - 1
        hist = st.session_state.chat_history
        while j >= 0:
            if hist[j].get('role') == 'user':
                prior_query = hist[j].get('content', '')
                user_index = j
                break
            j -= 1
        # Remove the current assistant message immediately so the loader can occupy its spot
        try:
            if 0 <= message_index < len(st.session_state.chat_history):
                st.session_state.chat_history.pop(message_index)
        except Exception as _e:
            logger.warning(f"Retry removal failed: {_e}")
        # Mark retry request with exact user index and query; pipeline will run inline at that spot
        st.session_state.retry_request = {
            'assistant_index': message_index,
            'user_index': user_index,
            'query': prior_query,
        }
        st.rerun()
    # Handle thumbs feedback after rendering to avoid double-rerun conflicts
    if up_clicked:
        st.session_state.message_feedback[message_index] = 'up'
        log_feedback_event(message_index, 'up')
    if down_clicked:
        st.session_state.message_feedback[message_index] = 'down'
        log_feedback_event(message_index, 'down')

    # Minimal CSS for custom buttons
    st.markdown(
        """
        <style>
        .msg-actions-custom button:hover { background: rgba(10,143,121,0.08) !important; border-color:#0a8f79 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def display_chat_messages(retry_request=None):
    """Display chat messages in a custom format.

    If a retry_request is provided, a temporary assistant placeholder will be
    injected immediately after the associated user message and returned so the
    caller can render a loading UI and final response in-place.
    """
    # Add CSS to control heading sizes inside chat messages
    st.markdown(
        """
        <style>
        /* Shrink headings that appear *inside* any chat message */
        [data-testid="stChatMessage"] h1     {font-size: 1.50rem !important;} /* ≈24 px */
        [data-testid="stChatMessage"] h2     {font-size: 1.25rem !important;} /* ≈20 px */
        [data-testid="stChatMessage"] h3     {font-size: 1.10rem !important;} /* ≈18 px */
        [data-testid="stChatMessage"] h4,
        [data-testid="stChatMessage"] h5,
        [data-testid="stChatMessage"] h6     {font-size: 1rem   !important;} /* ≈16 px */
        </style>
        """,
        unsafe_allow_html=True,
    )
    retry_user_index = None
    if isinstance(retry_request, dict):
        retry_user_index = retry_request.get('user_index')

    injected_retry_placeholder = None
    
    # Process any feedback action encoded in query params (from custom buttons)
    try:
        fb_action, fb_index = _pop_feedback_action_from_query_params()
        if fb_action and fb_index is not None:
            if fb_action == 'up':
                st.session_state.message_feedback[fb_index] = 'up'
                log_feedback_event(fb_index, 'up')
            elif fb_action == 'down':
                st.session_state.message_feedback[fb_index] = 'down'
                log_feedback_event(fb_index, 'down')
            elif fb_action == 'retry':
                # Emulate retry button behavior
                prior_query = ''
                user_index = -1
                j = fb_index - 1
                hist = st.session_state.chat_history
                while j >= 0:
                    if hist[j].get('role') == 'user':
                        prior_query = hist[j].get('content', '')
                        user_index = j
                        break
                    j -= 1
                try:
                    if 0 <= fb_index < len(st.session_state.chat_history):
                        st.session_state.chat_history.pop(fb_index)
                except Exception as _e:
                    logger.warning(f"Retry removal failed: {_e}")
                st.session_state.retry_request = {
                    'assistant_index': fb_index,
                    'user_index': user_index,
                    'query': prior_query,
                }
                st.rerun()
    except Exception:
        pass

    for i, message in enumerate(st.session_state.chat_history):
        if message['role'] == 'user':
            user_msg = st.chat_message("user")
            user_code = message.get('language_code', 'en')
            user_msg.markdown(render_user_bubble(message.get('content', ''), user_code), unsafe_allow_html=True)
            render_message_actions_ui(i, message)
            # If a retry is active for this user message, inject an assistant placeholder right after it
            if retry_user_index is not None and retry_user_index == i and injected_retry_placeholder is None:
                retry_msg_container = st.chat_message("assistant")
                injected_retry_placeholder = retry_msg_container.empty()
        else:
            assistant_message = st.chat_message("assistant")
            # Clean the content before displaying
            content = clean_html_content(message.get('content', ''))
            
            language_code = message.get('language_code', 'en')
            text_align = 'right' if is_rtl_language(language_code) else 'left'
            direction = 'rtl' if is_rtl_language(language_code) else 'ltr'
            
            # Display the response with proper markdown rendering
            try:
                # For RTL languages, we need the HTML wrapper
                if is_rtl_language(language_code):
                    assistant_message.markdown(
                        f"""<div style="direction: {direction}; text-align: {text_align}">
                        {content}
                        </div>""",
                        unsafe_allow_html=True
                    )
                else:
                    # For LTR languages, ensure proper markdown rendering
                    # Add a newline at the start if content starts with #
                    if content.strip().startswith('#'):
                        # Ensure the heading is on its own line
                        content = '\n' + content.strip()
                    
                    # Use direct markdown for better header rendering
                    assistant_message.markdown(content)
            except Exception as e:
                # Fallback if markdown rendering fails
                logger.error(f"Error rendering message: {str(e)}")
                assistant_message.text("Error displaying formatted message. Raw content:")
                assistant_message.text(content)
            
            if message.get('citations'):
                display_source_citations(message['citations'], base_idx=i)
            render_message_actions_ui(i, message)

    return injected_retry_placeholder

def load_custom_css():
    """SIMPLIFIED CSS - removed problematic JavaScript and complex theme detection"""
    
    # Get wallpaper if available
    wallpaper_base64 = None
    if WALLPAPER and Path(WALLPAPER).exists():
        wallpaper_base64 = get_base64_image(WALLPAPER)
    
    # Hide Streamlit header
    st.markdown("""
    <style>
        header[data-testid="stHeader"] {
            display: none;
        }
        /* Hide toolbar but KEEP sidebar collapse toggle hidden and force sidebar visible */
        .stToolbar { display: none; }
        button[kind="header"] { display: none; }
    </style>
    """, unsafe_allow_html=True)
    
    # Basic wallpaper CSS (if available)
    if wallpaper_base64:
        st.markdown(f"""
        <style>
        .stApp::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('data:image/png;base64,{wallpaper_base64}');
            background-repeat: repeat;
            background-size: 1200px;
            opacity: 0.1;
            pointer-events: none;
            z-index: -1;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # SIMPLIFIED CSS - no complex theme detection, no visibility tricks
    st.markdown("""
    <style>
    /* Basic styling */
    .main .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    
    /* Button styling */
    .stButton > button {
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
    
    .stButton > button:hover:not(:disabled) {
        background-color: #007e65;
        transform: translateY(-2px);
    }
    
    .stButton > button:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        cursor: not-allowed;
        transform: none;
    }
    
    /* Chat messages */
    [data-testid="stChatMessage"] h1 {font-size: 1.50rem !important;}
    [data-testid="stChatMessage"] h2 {font-size: 1.25rem !important;}
    [data-testid="stChatMessage"] h3 {font-size: 1.10rem !important;}
    [data-testid="stChatMessage"] h4,
    [data-testid="stChatMessage"] h5,
    [data-testid="stChatMessage"] h6 {font-size: 1rem !important;}
    
    /* Remove default gray bubble background so custom bubbles show cleanly */
    [data-testid="stChatMessage"] > div:has(div[data-testid="stMarkdownContainer"]) {
        background: transparent !important;
        box-shadow: none !important;
    }
    
    /* Sidebar styling; allow collapse/expand to function */
    section[data-testid="stSidebar"] {
        background-color: #303030 !important; /* brand dark */
    }
    /* Hide the default collapse affordance entirely (we provide our own button) */
    [data-testid="stSidebar"] [data-testid="stSidebarNavButton"],
    [data-testid="stSidebar"] button[title*="Collapse"],
    [data-testid="stSidebarCollapseControl"] { display: none !important; }
    section[data-testid="stSidebar"] > div { padding-top: 0 !important; margin-top: 0 !important; }
    section[data-testid="stSidebar"] * { color: #ffffff !important; }
    
    /* Language selectbox: make control white and text/arrow black for readability */
    section[data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
    }
    /* Keep selectbox value text black for readability on its white control */
    section[data-testid="stSidebar"] div[data-baseweb="select"] * { color: #000000 !important; }
    section[data-testid="stSidebar"] div[data-baseweb="select"] input { color: #000000 !important; }
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg { fill: #000000 !important; color: #000000 !important; }

    /* Header alignment */
    .mlcc-header { display:flex; align-items:center; gap:16px; margin-top: 8px; }
    .mlcc-header .mlcc-logo { width: 64px; height: auto; }
    .mlcc-header h1 { color: #009376 !important; }
    .mlcc-subtitle { color: #555; margin: 2px 0 14px 0; font-size: 1rem; }

    /* Remove default chat message card styling to avoid gray background */
    div[data-testid="stChatMessage"] { background: transparent !important; box-shadow: none !important; border: none !important; }
    div[data-testid="stChatMessage"] > div { background: transparent !important; box-shadow: none !important; border: none !important; }

    /* Compact inline action icons inside chat messages */
    div[data-testid="stChatMessage"] div[data-testid="stHorizontalBlock"] { gap: 6px !important; justify-content: flex-end; align-items: center; }
    div[data-testid="stChatMessage"] .stButton > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 4px 6px !important;
        min-width: 0 !important;
        color: #0a8f79 !important; /* unified green tone */
        font-size: 18px !important;
    }
    div[data-testid="stChatMessage"] .stButton > button:hover { background: rgba(10,143,121,0.08) !important; color: #0a8f79 !important; }

    /* Normalize Sources section typography to match message body */
    .sources-section { margin-top: 0.25rem; }
    .sources-heading { font-size: 1rem; font-weight: 600; color: #333; margin: 0.25rem 0 0.5rem 0; }
    .sources-section .stButton > button {
        font-size: 0.95rem !important;
        padding: 6px 10px !important;
        background: #0a8f79 !important;
        color: #fff !important;
        border-radius: 8px !important;
    }
    .sources-section .stButton > button:hover { background: #077966 !important; }
    .sources-section [data-testid="stExpander"] p,
    .sources-section [data-testid="stMarkdownContainer"] p,
    .sources-section [data-testid="stMarkdownContainer"] li { font-size: 0.95rem !important; }

    /* Make the download button dark-theme friendly in the sidebar */
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] > div > button {
        background-color: #0a8f79 !important;
        color: #ffffff !important;
        border: 1px solid #0a8f79 !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] > div > button:hover {
        background-color: #077966 !important;
        border-color: #077966 !important;
    }

    /* Chat History area in sidebar: force readable styles regardless of Streamlit wrapper structure */
    section[data-testid="stSidebar"] h3:has(span:contains("Chat History")),
    section[data-testid="stSidebar"] .chat-history-section h3 { 
        color: #ffffff !important;  /* Keep header white */
    }

    /* Download button - ensure white background and black text (even when disabled) */
    /* Remove any legacy download button styles (we use the HTML icon now) */
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] { display: none !important; }

    /* Q: sections - white border around each item in the sidebar */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 2px solid #ffffff !important;
        border-radius: 8px !important;
        padding: 0 !important;           /* reduce internal padding */
        margin: 6px 0 !important;        /* tighter vertical spacing */
        background: transparent !important;
    }
    /* Remove default details/summary marker that looks like a '>' */
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary::-webkit-details-marker { display: none !important; }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary::marker { content: '' !important; }

    /* Keep expander header text white */
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary { color: #ffffff !important; }
    /* Content inside expanders white */
    section[data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stMarkdownContainer"] { color: #ffffff !important; }

    /* Reduce vertical gaps just inside the Chat History area */
    section[data-testid="stSidebar"] .chat-history-section [data-testid="stVerticalBlock"] {
      gap: 6px !important;            /* default is ~16px */
    }
    /* Kill extra margins around each bordered container that wraps an expander */
    section[data-testid="stSidebar"] .chat-history-section [data-testid="stVerticalBlock"] > div:has([data-testid="stExpander"]) {
      margin: 4px 0 !important;       /* tighter stack */
      padding: 0 !important;
    }
    /* Compact the expander header + body padding */
    section[data-testid="stSidebar"] .chat-history-section [data-testid="stExpander"] > div {
      padding: 6px 8px !important;
    }
    section[data-testid="stSidebar"] .chat-history-section details > summary {
      padding: 6px 8px !important;    /* covers older markup */
    }

    /* Download icon fallback link styling */
    section[data-testid="stSidebar"] .dl-icon{
      display:inline-flex; align-items:center; justify-content:center;
      width:36px; height:36px; margin-top:4px;
      border:1px solid #ffffff; border-radius:8px; text-decoration:none;
      font-size:18px; line-height:1; user-select:none;
    }
    section[data-testid="stSidebar"] .dl-icon:hover{ background:#2f2f2f; }
    </style>
    """, unsafe_allow_html=True)
    
    # Additional favicon setting
    if TREE_ICON:
        st.markdown(f'''
            <link rel="icon" href="{TREE_ICON}" type="image/x-icon">
            <link rel="shortcut icon" href="{TREE_ICON}" type="image/x-icon">
        ''', unsafe_allow_html=True)

def load_responsive_css():
    """Mobile-first responsive CSS to improve usability on small screens."""
    st.markdown(
        """
        <style>
        /* Base typography and container */
        html { font-size: 16px; }
        .main .block-container { padding-top: 0 !important; margin-top: 0 !important; max-width: 100% !important; }

        /* Buttons – touch targets */
        .stButton > button { min-height: 44px; }

        /* Header responsiveness */
        .mlcc-header { display:flex; align-items:center; gap:16px; margin-top:8px; flex-wrap:wrap; }

        @media (max-width: 768px) {
          html { font-size: 14px; }
          .main .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
          .stButton > button { padding: 12px 20px; font-size: 0.95rem; width: 100%; }
          [data-testid="stChatMessage"] { padding: 0.5rem; }
          [data-testid="stChatMessage"] h1 {font-size: 1.25rem !important;}
          [data-testid="stChatMessage"] h2 {font-size: 1.1rem !important;}
          [data-testid="stChatMessage"] h3 {font-size: 1rem !important;}
          [data-testid="stChatMessage"] p  {font-size: 0.95rem !important;}
          .mlcc-header { gap: 12px; justify-content: center; text-align: center; }
          .mlcc-header h1 { font-size: 1.5rem !important; }
          .mlcc-header .mlcc-logo { width: 48px; }
        }

        /* Sidebar sizing for mobile */
        @media (max-width: 768px) {
          section[data-testid="stSidebar"] { width: 85% !important; max-width: 320px !important; }
          section[data-testid="stSidebar"] > div { padding: 1rem !important; }
        }

        /* Consent + FAQ modals responsive */
        @media (max-width: 768px) {
          div[data-testid="column"]:has(.consent-modal-marker) { width: 95vw !important; top: 2vh !important; padding: 16px !important; }
          div[data-testid="column"]:has(.consent-modal-marker) h1 { font-size: 1.5rem !important; }
          div[data-testid="column"]:has(.consent-modal-marker) h3 { font-size: 1rem !important; }
          div[data-testid="column"]:has(.consent-modal-marker) p,
          div[data-testid="column"]:has(.consent-modal-marker) li { font-size: 0.9rem !important; }

          div[data-testid="column"]:has(.faq-popup-marker) { width: 95vw !important; max-height: 90vh !important; padding: 12px !important; }
          div[data-testid="column"]:has(.faq-popup-marker) h1 { font-size: 1.3rem !important; }
          div[data-testid="column"]:has(.faq-popup-marker) h2 { font-size: 1.1rem !important; }
        }

        /* Touch-friendly expanders */
        @media (max-width: 768px) {
          [data-testid="stExpander"] summary { min-height: 44px; padding: 12px !important; }
        }

        /* Sources buttons smaller on mobile */
        @media (max-width: 768px) {
          .sources-section .stButton > button { font-size: 0.85rem !important; padding: 8px 12px !important; }
        }

        /* Hide custom sidebar toggle on mobile; use Streamlit native menu */
        @media (max-width: 768px) {
          #sb-toggle-anchor + div.stButton { display: none !important; }
        }

        /* User bubbles max width on mobile */
        @media (max-width: 768px) {
          div[style*="max-width:85%"] { max-width: 90% !important; }
        }

        /* Fix chat input on mobile */
        @media (max-width: 768px) {
          [data-testid="stChatInput"] {
            position: fixed; bottom: 0; left: 0; right: 0; padding: 8px;
            background: white; border-top: 1px solid #ddd; z-index: 100;
          }
          .main { padding-bottom: 80px !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
def generate_chat_history_text():
    """Convert chat history to downloadable text format."""
    history_text = "Chat History\n\n"
    for msg in st.session_state.chat_history:
        role = "User" if msg['role'] == 'user' else "Assistant"
        history_text += f"{role}: {msg['content']}\n\n"
        if msg.get('citations'):
            history_text += "Sources:\n"
            for citation in msg['citations']:
                details = get_citation_details(citation)
                history_text += f"- {details['title']}\n"
                if details['url']:
                    history_text += f"  URL: {details['url']}\n"
                if details['snippet']:
                    history_text += f"  Content: {details['snippet']}\n"
            history_text += "\n"
    return history_text

def format_message_for_copy(message_index: int) -> str:
    """Create a normalized plain-text snippet for one chat turn, similar to the download format.

    - If the message is an assistant reply, include the preceding user question (when available)
    - Include sources for assistant messages using titles and URLs
    """
    try:
        history = st.session_state.get('chat_history', [])
        if not history or message_index < 0 or message_index >= len(history):
            return ""

        msg = history[message_index]
        lines = []

        if msg.get('role') == 'assistant':
            # Preceding user question for context
            j = message_index - 1
            while j >= 0 and history[j].get('role') != 'user':
                j -= 1
            if j >= 0:
                lines.append(f"User: {history[j].get('content','')}")

        role = 'User' if msg.get('role') == 'user' else 'Assistant'
        lines.append(f"{role}: {msg.get('content','')}")

        # Add citations for assistant messages
        if msg.get('role') == 'assistant' and msg.get('citations'):
            lines.append("Sources:")
            for cit in msg['citations']:
                d = get_citation_details(cit)
                title = d.get('title', 'Untitled Source')
                url = d.get('url') or ''
                snippet = d.get('snippet') or ''
                lines.append(f"- {title}")
                if url:
                    lines.append(f"  URL: {url}")
                if snippet:
                    lines.append(f"  Content: {snippet}")

        return "\n".join(lines) + "\n"
    except Exception:
        # Fallback to raw content
        history = st.session_state.get('chat_history', [])
        msg = history[message_index] if 0 <= message_index < len(history) else {}
        return str(msg.get('content', ''))

def display_chat_history_section():
    msgs = st.session_state.get("chat_history", [])
    if not msgs:
        return

    import base64

    st.markdown('<div class="chat-history-section">', unsafe_allow_html=True)

    # Header row with title + icon
    text = generate_chat_history_text() or "Chat History is empty.\n"
    data_bytes = text.encode("utf-8")
    b64 = base64.b64encode(data_bytes).decode()

    hcol, icol = st.columns([5, 1])
    with hcol:
        st.markdown("### Chat History")
    with icol:
        st.markdown(
            f'''
            <a class="dl-icon" title="Download chat history"
               href="data:text/plain;charset=utf-8;base64,{b64}"
               download="chat_history.txt">📥</a>
            ''',
            unsafe_allow_html=True,
        )

    # Compact Q/A list
    for i in range(0, len(msgs), 2):
        if msgs[i].get('role') != 'user':
            continue
        q = msgs[i].get('content', '')
        a = msgs[i+1].get('content', '') if i+1 < len(msgs) and msgs[i+1].get('role') == 'assistant' else ''
        with st.expander(f"Q: {q[:60]}…", expanded=False):
            st.markdown("**Question:**"); st.write(q)
            st.markdown("**Response:**"); st.write(a)

    st.markdown('</div>', unsafe_allow_html=True)

def display_consent_form():
    """Display the consent form using Streamlit's native components."""
    # Move the form higher up with padding adjustments and apply an overlay modal style
    st.markdown(
        """
        <style>
        /* Custom padding to position the form higher on the page */
        .main .block-container { padding-top: 0 !important; margin-top: 0 !important; }

        /* Backdrop overlay */
        .consent-backdrop {
            position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 10000;
        }

        /* Style the centered consent modal container (cream box) */
        div[data-testid="column"]:has(.consent-modal-marker) {
            position: fixed; top: 6vh; left: 50%; transform: translateX(-50%);
            width: min(880px, 92vw);
            z-index: 10001;
            background-color: #FFF7E1; /* soft cream */
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Use columns to center the consent form but make it wider
    col1, col2, col3 = st.columns([1, 6, 1])  # Changed from [1, 4, 1] to make middle column even wider
    
    with col2:
        # Backdrop overlay sits behind the modal container
        st.markdown('<div class="consent-backdrop"></div>', unsafe_allow_html=True)
        # Marker for CSS targeting of the modal column
        st.markdown('<div class="consent-modal-marker"></div>', unsafe_allow_html=True)
        # Container for the consent form
        with st.container():
            # Header
            st.markdown("""
            <div style="text-align: center; padding-bottom: 20px; margin-bottom: 25px; border-bottom: 1px solid #eee;">
                <h1 style="margin: 0; color: #009376; font-size: 36px; font-weight: bold;">
                    MLCC Climate Chatbot
                </h1>
                <h3 style="margin: 10px 0 0 0; color: #666; font-size: 18px; font-weight: normal;">
                    Connecting Toronto Communities to Climate Knowledge
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <p style="text-align: center; margin-bottom: 30px; font-size: 16px;">
                Welcome! The purpose of this app is to educate people about climate change and build a community of informed citizens. 
                It provides clear, accurate info on climate impacts and encourages local action.
            </p>
            """, unsafe_allow_html=True)
            
            # Main consent checkbox - removed the border div that was here
            main_consent = st.checkbox(
                "By checking this box, you agree to the following:",
                value=st.session_state.get('main_consent', False),
                key="main_consent_checkbox",
                help="You must agree to continue"
            )
            st.session_state.main_consent = main_consent
            
            # Bullet points - directly added without border
            st.markdown(
                """
            <ul style="margin: 15px 0; font-size: 15px;">
                <li>I certify that I meet the age requirements <em>(13+ or with parental/guardian consent if under 18)</em></li>
                <li>I have read and agreed to the Privacy Policy</li>
                <li>I have read and agreed to the Terms of Use</li>
                <li>I have read and understood the Disclaimer</li>
            </ul>
            """,
                unsafe_allow_html=True
            )
            
            # Policy expanders - all three buttons in one row
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                with st.expander("📄 Privacy Policy"):
                    st.markdown("""
                    ### Privacy Policy
                    Last Updated: January 28, 2025

                    #### Information Collection
                    We are committed to protecting user privacy and minimizing data collection. Our practices include:

                    ##### What We Do Not Collect
                    - Personal identifying information (PII)
                    - User accounts or profiles
                    - Location data
                    - Device information
                    - Usage patterns

                    ##### What We Do Collect
                    - Anonymized questions (with all PII automatically redacted)
                    - Aggregate usage statistics
                    - Error reports and system performance data

                    #### Data Usage
                    Collected data is used exclusively for:
                    - Improving chatbot response accuracy
                    - Identifying common climate information needs
                    - Enhancing language processing capabilities
                    - System performance optimization

                    #### Data Protection
                    We protect user privacy through:
                    - Automatic PII redaction before caching
                    - Secure data storage practices
                    - Limited access controls

                    #### Third-Party Services
                    Our chatbot utilizes Cohere's language models. Users should note:
                    - No personal data is shared with Cohere
                    - Questions are processed without identifying information
                    - Cohere's privacy policies apply to their services

                    #### Changes to Privacy Policy
                    We reserve the right to update this privacy policy as needed. Users will be notified of significant changes through our website.

                    #### Contact Information
                    For privacy-related questions or concerns, contact us at info@crcgreen.com
                    """, unsafe_allow_html=True)
            
            with col_b:
                with st.expander("📄 Terms of Use"):
                    st.markdown("""
                    ### Terms of Use
                    Last Updated: January 28, 2025

                    #### Acceptance of Terms
                    By accessing and using the Climate Resilience Communities chatbot, you accept and agree to be bound by these Terms of Use and all applicable laws and regulations.

                    #### Acceptable Use
                    Users agree to use the chatbot in accordance with these terms and all applicable laws. Prohibited activities include but are not limited to:
                    - Spreading misinformation or deliberately providing false information
                    - Engaging in hate speech or discriminatory behavior
                    - Attempting to override or manipulate the chatbot's safety features
                    - Using the service for harassment or harmful purposes
                    - Attempting to extract personal information or private data

                    #### Open-Source License
                    Our chatbot's codebase is available under the MIT License. This means you can:
                    - Use the code for any purpose
                    - Modify and distribute the code
                    - Use it commercially
                    - Sublicense it
                    
                    Under the condition that:
                    - The original copyright notice and permission notice must be included
                    - The software is provided "as is" without warranty

                    #### Intellectual Property
                    While our code is open-source, the following remains the property of Climate Resilience Communities:
                    - Trademarks and branding
                    - Content created specifically for the chatbot
                    - Documentation and supporting materials

                    #### Liability Limitation
                    The chatbot and its services are provided "as is" and "as available" without any warranties, expressed or implied. Climate Resilience Communities is not liable for any damages arising from:
                    - Use or inability to use the service
                    - Reliance on information provided
                    - Decisions made based on chatbot interactions
                    - Technical issues or service interruptions
                    """, unsafe_allow_html=True)
            
            with col_c:
                with st.expander("📄 Disclaimer"):
                    st.markdown("""
                    ### Disclaimer
                    Last Updated: January 28, 2025

                    #### General Information
                    Climate Resilience Communities ("we," "our," or "us") provides this climate information chatbot as a public service to Toronto's communities. While we strive for accuracy and reliability, please note the following important limitations and disclaimers.

                    #### Scope of Information
                    The information provided through our chatbot is for general informational and educational purposes only. It does not constitute professional, legal, or scientific advice. Users should consult qualified experts and official channels for decisions regarding climate adaptation, mitigation, or response strategies.

                    #### Information Accuracy
                    While our chatbot uses Retrieval-Augmented Generation technology and cites verified sources, the field of climate science and related policies continues to evolve. We encourage users to:
                    - Verify time-sensitive information through official government channels
                    - Cross-reference critical information with current scientific publications
                    - Consult local authorities for community-specific guidance

                    #### Third-Party Content
                    Citations and references to third-party content are provided for transparency and verification. Climate Resilience Communities does not endorse and is not responsible for the accuracy, completeness, or reliability of third-party information.
                    """, unsafe_allow_html=True)
            
            # Divider
            st.markdown("---")
            
            # Get Started button - centered with updated text
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button(
                    "Start Chatting Now",
                    disabled=not st.session_state.get('main_consent', False),
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.consent_given = True
                    st.rerun()
            
            # Warning message
            if not st.session_state.get('main_consent', False):
                st.warning("⚠️ Please check the box above to continue.")


@st.dialog(" ", width="large")
def show_consent_dialog():
    """Consent modal shown as a native Streamlit dialog overlay."""
    # Cream styling for the dialog body
    st.markdown(
        """
        <style>
        /* Keeps dialog content pane creamy without relying on fragile data-testids */
        [data-testid="stDialog"] section div [data-testid="stVerticalBlock"] > div {
            background: #FFF7E1;
            border-radius: 12px;
            padding: 18px 18px 10px 18px;
        }
        
        /* Prevent closing the dialog by clicking on the backdrop/overlay */
        [data-testid="stDialogOverlay"],
        [data-testid="stModalOverlay"],
        [role="dialog"] ~ div {
            pointer-events: none !important;
        }

        /* Hide Streamlit's built-in dialog title text by making it white and zero-size */
        [data-testid="stDialog"] h2:not(.consent-title) {
            color: #ffffff !important; /* white text on white background */
            font-size: 0 !important;
            line-height: 0 !important;
            margin: 0 !important;
        }
        
        .consent-title {
            color: #009376 !important;
            font-size: 28px !important;
            font-weight: 700 !important;
            margin: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="text-align:center; margin-bottom: 8px;">
            <h2 class="consent-title">MLCC Climate Chatbot</h2>
            <p style="color:#666; margin:6px 0 0 0;">Connecting Toronto Communities to Climate Knowledge</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        "Welcome! This app shares clear info on climate impacts and local action. "
        "Please confirm you're good with the basics below."
    )

    agreed = st.checkbox(
        "By checking this box, you agree to the following:",
        value=st.session_state.get("main_consent", False),
        key="main_consent",
    )

    st.markdown(
        """
        - I meet the age requirements *(13+ or with guardian consent if under 18)*  
        - I read and agree to the **Privacy Policy**  
        - I read and agree to the **Terms of Use**  
        - I read and understand the **Disclaimer**
        """
    )

    with st.expander("📄 Privacy Policy"):
        st.markdown(
            """
            ### Privacy Policy
            Last Updated: January 28, 2025

            #### Information Collection
            We are committed to protecting user privacy and minimizing data collection. Our practices include:

            ##### What We Do Not Collect
            - Personal identifying information (PII)
            - User accounts or profiles
            - Location data
            - Device information
            - Usage patterns

            ##### What We Do Collect
            - Anonymized questions (with all PII automatically redacted)
            - Aggregate usage statistics
            - Error reports and system performance data

            #### Data Usage
            Collected data is used exclusively for:
            - Improving chatbot response accuracy
            - Identifying common climate information needs
            - Enhancing language processing capabilities
            - System performance optimization

            #### Data Protection
            We protect user privacy through:
            - Automatic PII redaction before caching
            - Secure data storage practices
            - Limited access controls

            #### Third-Party Services
            Our chatbot utilizes Cohere's language models. Users should note:
            - No personal data is shared with Cohere
            - Questions are processed without identifying information
            - Cohere's privacy policies apply to their services

            #### Changes to Privacy Policy
            We reserve the right to update this privacy policy as needed. Users will be notified of significant changes through our website.

            #### Contact Information
            For privacy-related questions or concerns, contact us at info@crcgreen.com
            """
        )
    with st.expander("📄 Terms of Use"):
        st.markdown(
            """
            ### Terms of Use
            Last Updated: January 28, 2025

            #### Acceptance of Terms
            By accessing and using the Climate Resilience Communities chatbot, you accept and agree to be bound by these Terms of Use and all applicable laws and regulations.

            #### Acceptable Use
            Users agree to use the chatbot in accordance with these terms and all applicable laws. Prohibited activities include but are not limited to:
            - Spreading misinformation or deliberately providing false information
            - Engaging in hate speech or discriminatory behavior
            - Attempting to override or manipulate the chatbot's safety features
            - Using the service for harassment or harmful purposes
            - Attempting to extract personal information or private data

            #### Open-Source License
            Our chatbot's codebase is available under the MIT License. This means you can:
            - Use the code for any purpose
            - Modify and distribute the code
            - Use it commercially
            - Sublicense it
            
            Under the condition that:
            - The original copyright notice and permission notice must be included
            - The software is provided "as is" without warranty

            #### Intellectual Property
            While our code is open-source, the following remains the property of Climate Resilience Communities:
            - Trademarks and branding
            - Content created specifically for the chatbot
            - Documentation and supporting materials

            #### Liability Limitation
            The chatbot and its services are provided "as is" and "as available" without any warranties, expressed or implied. Climate Resilience Communities is not liable for any damages arising from:
            - Use or inability to use the service
            - Reliance on information provided
            - Decisions made based on chatbot interactions
            - Technical issues or service interruptions
            """
        )
    with st.expander("📄 Disclaimer"):
        st.markdown(
            """
            ### Disclaimer
            Last Updated: January 28, 2025

            #### General Information
            Climate Resilience Communities ("we," "our," or "us") provides this climate information chatbot as a public service to Toronto's communities. While we strive for accuracy and reliability, please note the following important limitations and disclaimers.

            #### Scope of Information
            The information provided through our chatbot is for general informational and educational purposes only. It does not constitute professional, legal, or scientific advice. Users should consult qualified experts and official channels for decisions regarding climate adaptation, mitigation, or response strategies.

            #### Information Accuracy
            While our chatbot uses Retrieval-Augmented Generation technology and cites verified sources, the field of climate science and related policies continues to evolve. We encourage users to:
            - Verify time-sensitive information through official government channels
            - Cross-reference critical information with current scientific publications
            - Consult local authorities for community-specific guidance

            #### Third-Party Content
            Citations and references to third-party content are provided for transparency and verification. Climate Resilience Communities does not endorse and is not responsible for the accuracy, completeness, or reliability of third-party information.
            """
        )

    st.markdown("---")
    if st.button("Start Chatting Now", disabled=not agreed, type="primary", use_container_width=True):
        st.session_state.consent_given = True
        st.rerun()


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
        # Immediately rerun to apply page_config flip logic
        try:
            st.rerun()
        except Exception:
            pass

    # Load CSS
    load_custom_css()
    # Ensure client UI matches server-side sidebar state on each run
    try:
        st_html(
            f"""
<script>
setTimeout(() => {{
  const sidebar = document.querySelector('section[data-testid="stSidebar"]');
  if (!sidebar) return;
  {"sidebar.style.transform=''; sidebar.style.display='';" if st.session_state.get('_sb_open', True) else "sidebar.style.transform='translateX(-100%)';"}
}}, 60);
</script>
""",
            height=0,
        )
    except Exception:
        pass
    load_responsive_css()
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

        if st.session_state.get('_sb_open', True):
            with st.sidebar:
                # Add a close button at the top of the sidebar, wrapped in a unique div
                st.markdown('<div class="sb-close-button-container">', unsafe_allow_html=True)
                st.button("⬅️", on_click=toggle_sidebar, key="sb_close_btn", help="Close sidebar")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
                st.markdown('<div class="content">', unsafe_allow_html=True)
                
                st.title('Multilingual Climate Chatbot')
                
                # Language selection and confirmation
                st.write("**Please choose your preferred language to get started:**")
                languages = sorted(chatbot.LANGUAGE_NAME_TO_CODE.keys())
                default_index = languages.index(st.session_state.selected_language)
                selected_language = st.selectbox(
                    "Select your language",
                    options=languages,
                    index=default_index,
                    help="Choose your preferred language",
                )
                # Simplest visibility fix: make the select control background white in the dark sidebar
                st.markdown('<style>section[data-testid="stSidebar"] .stSelectbox > div > div {background: white !important;}</style>', unsafe_allow_html=True)
                # Robust selectbox visibility fix for dark sidebar
                st.markdown(
                    """
                    <style>
                    /* Fix language selectbox visibility in dark sidebar */
                    section[data-testid="stSidebar"] div[data-baseweb="select"] {
                        background-color: #ffffff !important;  /* White background for the dropdown */
                        border-radius: 8px !important;
                        border: 1px solid #cccccc !important;
                    }
                    
                    /* Make sure the text inside is black and visible on white background */
                    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
                        background-color: #ffffff !important;  /* Ensure white background for inner div */
                    }
                    
                    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
                        color: #000000 !important;  /* Black text */
                    }
                    
                    section[data-testid="stSidebar"] div[data-baseweb="select"] input {
                        color: #000000 !important;  /* Black text for input */
                        background-color: #ffffff !important;  /* White background */
                    }
                    
                    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
                        fill: #000000 !important;  /* Black arrow */
                    }
                    
                    /* Dropdown menu items */
                    div[data-baseweb="popover"] ul[role="listbox"] {
                        background-color: #ffffff !important;
                    }
                    
                    div[data-baseweb="popover"] ul[role="listbox"] li {
                        color: #000000 !important;
                        background-color: #ffffff !important;
                    }
                    
                    div[data-baseweb="popover"] ul[role="listbox"] li:hover {
                        background-color: #f0f0f0 !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                # Ensure white text in dark mode for the selectbox label and value
                st.markdown(
                    """
    <style>
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] div[role="combobox"] div[data-testid="stMarkdownContainer"] * {
      color: #ffffff !important;
    }
    section[data-testid="stSidebar"] div[role="combobox"] span{ color:#000000 !important; }
    /* Keep the dropdown options readable */
    section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="listbox"] * { color:#000000 !important; }
    </style>
                    """,
                    unsafe_allow_html=True,
                )
                # One-click confirm: when user clicks Confirm, flip flag and rerun immediately
                if not st.session_state.language_confirmed:
                    if st.button("Confirm", key="confirm_lang_btn"):
                        st.session_state.selected_language = selected_language
                        st.session_state.language_confirmed = True
                        # AUTO-CLOSE SIDEBAR ON MOBILE ONLY (robust param-based detection)
                        if _is_mobile_from_query_params():
                            st.session_state._sb_open = False
                            st.session_state._sb_rerun = True
                            _set_query_params_robust({"sb": "0"}, merge=True)
                            # Aid client-side collapse on next load
                            st_html('<script>try{sessionStorage.setItem("closeSidebarOnLoad","1");}catch(e){}</script>', height=0)
                        st.rerun()
                else:
                    st.session_state.selected_language = selected_language
                
                if len(st.session_state.chat_history) == 0:
                    st.markdown(
                        """
                        <div style="margin-top: 10px;">
                        <h3 style="color: #009376; font-size: 20px; margin-bottom: 10px;">How It Works</h3>
                        <ul style="padding-left: 20px; margin-bottom: 20px; font-size: 14px;">
                            <li style="margin-bottom: 8px;"><b>Choose Language</b>: Select from 200+ options.</li>
                            <li style="margin-bottom: 8px;"><b>Ask Questions</b>: <i>"What are the local impacts of climate change in Toronto?"</i> or <i>"Why is summer so hot now in Toronto?"</i></li>
                            <li style="margin-bottom: 8px;"><b>Act</b>: Ask about actionable steps such as <i>"What can I do about flooding in Toronto?"</i> or <i>"How to reduce my carbon footprint?"</i> and receive links to local resources (e.g., city programs, community groups).</li>
                        </ul>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                if len(st.session_state.chat_history) > 0:
                    # Tighten spacing before chat history to avoid large gaps
                    st.markdown('<div style="margin: 8px 0;"></div>', unsafe_allow_html=True)
                    display_chat_history_section()
                
                if 'show_faq_popup' not in st.session_state:
                    st.session_state.show_faq_popup = False
                if st.button("📚 Support & FAQs"):
                    st.session_state.show_faq_popup = True
                    # Auto-close sidebar on mobile if FAQ opened
                    if _is_mobile_from_query_params():
                        st.session_state._sb_open = False
                        st.session_state._sb_rerun = True
                        _set_query_params_robust({"sb": "0"}, merge=True)
                        st_html('<script>try{sessionStorage.setItem("closeSidebarOnLoad","1");}catch(e){}</script>', height=0)
                        st.rerun()
                    # Auto-close sidebar on mobile if FAQ opened
                    if _is_mobile_from_query_params():
                        st.session_state._sb_open = False
                        st.session_state._sb_rerun = True
                        _set_query_params_robust({"sb": "0"}, merge=True)
                        st_html('<script>try{sessionStorage.setItem("closeSidebarOnLoad","1");}catch(e){}</script>', height=0)
                        st.rerun()
                st.markdown('<div class="footer" style="margin-top: 20px; margin-bottom: 20px;">', unsafe_allow_html=True)
                st.markdown('<div>Made by:</div>', unsafe_allow_html=True)
                if TREE_ICON:
                    st.image(TREE_ICON, width=40)
                st.markdown('<div style="font-size: 18px; display:flex; align-items:center; gap:6px;">\
                    <a href="https://crc.place/" target="_blank" title="Climate Resilient Communities">Climate Resilient Communities</a>\
                    <span title="Trademark">™</span>\
                    </div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        # Sidebar toggle control in main content area (only shows when sidebar is closed)
        if not st.session_state.get('_sb_open', True):
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

        # Header
        if CCC_ICON_B64:
            st.markdown(
                f"""
                <div class="mlcc-header">
                    <img class="mlcc-logo" src="data:image/png;base64,{CCC_ICON_B64}" alt="Logo" />
                    <h1 style="margin:0;">Multilingual Climate Chatbot</h1>
                </div>
                <div class="mlcc-subtitle">Ask me anything about climate change!</div>
                """,
                unsafe_allow_html=True,
            )

        else:
            st.title("Multilingual Climate Chatbot")
            st.write("Ask me anything about climate change!")

        # Remove floating toggle; sidebar collapse is disabled and sidebar always visible via CSS

        # FAQ Popup Modal using Streamlit native components (restored)
        if st.session_state.show_faq_popup:
            st.markdown(
                """
            <style>
            .stApp > div > div > div > div > div > section > div { background-color: rgba(0, 0, 0, 0.7) !important; }
            div[data-testid="column"]:has(.faq-popup-marker) {
                background-color: white; border-radius: 10px; padding: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                max-height: 80vh; overflow-y: auto;
            }
            a.feedback-button { display: inline-block; padding: 6px 10px; border-radius: 6px; border: 1px solid #d0d7de; background: #f6f8fa; color: #24292f !important; text-decoration: none; font-size: 14px; }
            a.feedback-button:hover { background: #eef2f6; }
            </style>
            """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 6, 1])
            with col2:
                st.markdown('<div class="faq-popup-marker"></div>', unsafe_allow_html=True)
                header_col1, header_col2 = st.columns([11, 1])
                with header_col1:
                    st.markdown("# Support & FAQs")
                with header_col2:
                    if st.button("✕", key="close_faq_top", help="Close FAQ"):
                        st.session_state.show_faq_popup = False
                        st.rerun()
                st.markdown("---")

                # Info Accuracy
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

                # Privacy
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

                # Trust & Transparency
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
                        st.markdown(
                            '<a class="feedback-button" href="https://forms.gle/7mXRSc3JAF8ZSTmr9" target="_blank" title="Report bugs or share feedback (opens Google Form)">📝 Submit Feedback</a>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            'For technical support or to report issues, please visit our <a href="https://github.com/Climate-Resilient-Communities/climate-multilingual-chatbot" target="_blank">GitHub repository</a>.',
                            unsafe_allow_html=True,
                        )

                st.markdown("<br><br>", unsafe_allow_html=True)
            st.stop()

        # Chat area
        retry_req = st.session_state.get('retry_request') if isinstance(st.session_state.get('retry_request'), dict) else None
        injected_retry_placeholder = display_chat_messages(retry_req)
        if st.session_state.language_confirmed:
            query = st.chat_input("Ask Climate Change Bot", key="chat_input_main")
            if query:
                try:
                    from src.utils.logging_setup import ensure_file_logger
                    ensure_file_logger(os.getenv("PIPELINE_LOG_FILE", os.path.join(os.getcwd(), "logs", "pipeline_debug.log")))
                    logger.info("UI IN → raw_query repr=%r codepoints(first20)=%s", query, [ord(c) for c in query[:20]])
                except Exception:
                    pass
                st.session_state.chat_history.append({'role': 'user', 'content': query})
        else:
            st.markdown(
                """
                <div style="margin-top: 10px; margin-bottom: 30px; background-color: #009376; padding: 10px; border-radius: 5px; color: white; text-align: center;">
                Please select your language and click Confirm to start chatting.
                </div>
                """,
                unsafe_allow_html=True
            )
            query = None

        # Respect the needs_rerun flag; otherwise process query/retry
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

                # Enhanced handling of successful responses vs off-topic questions
                if result and result.get('success', False):
                    # Clean and prepare the response content
                    response_content = result['response']

                    # Ensure proper markdown formatting for headings
                    if response_content and isinstance(response_content, str):
                        # Strip any leading/trailing whitespace
                        response_content = response_content.strip()

                        # If content starts with a heading, ensure it's properly formatted
                        if response_content.startswith('#'):
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

            # Sidebar
            with st.sidebar:
                # Style the close button to match the sidebar panel color
                st.markdown('<div id="sb-close-anchor"></div>', unsafe_allow_html=True)
                st.markdown(
                    """
                    <style>
                    section[data-testid=\"stSidebar\"] #sb-close-anchor + div.stButton > button {
                        background-color: #303030 !important; /* same as sidebar */
                        color: #ffffff !important;
                        border: 1px solid #303030 !important;
                        border-radius: 8px !important;
                        padding: 4px 8px !important;
                        box-shadow: none !important;
                    }
                    section[data-testid=\"stSidebar\"] #sb-close-anchor + div.stButton > button:hover {
                        background-color: #2f2f2f !important; /* subtle hover */
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
                st.markdown('<div class="content">', unsafe_allow_html=True)

                st.title('Multilingual Climate Chatbot')

                # Language selection and confirmation
                st.write("**Please choose your preferred language to get started:**")
                languages = sorted(chatbot.LANGUAGE_NAME_TO_CODE.keys())
                default_index = languages.index(st.session_state.selected_language)
                selected_language = st.selectbox(
                    "Select your language",
                    options=languages,
                    index=default_index
                )

                # One-click confirm in second sidebar rendering path as well
                if not st.session_state.language_confirmed:
                    if st.button("Confirm", key="confirm_lang_btn_2"):
                        st.session_state.selected_language = selected_language
                        st.session_state.language_confirmed = True
                        # AUTO-CLOSE SIDEBAR ON MOBILE ONLY (robust param-based detection)
                        if _is_mobile_from_query_params():
                            st.session_state._sb_open = False
                            st.session_state._sb_rerun = True
                            _set_query_params_robust({"sb": "0"}, merge=True)
                            # Aid client-side collapse on next load
                            st_html('<script>try{sessionStorage.setItem("closeSidebarOnLoad","1");}catch(e){}</script>', height=0)
                        st.rerun()
                else:
                    st.session_state.selected_language = selected_language

                # Add "How It Works" section in the sidebar (moved from main area)
                # FIXED: Using chat_history length instead of has_asked_question
                if len(st.session_state.chat_history) == 0:
                    # Remove the green banner from sidebar - it will only be in main content area
                    st.markdown(
                        """
                        <div style=\"margin-top: 10px;\"> 
                        <h3 style=\"color: #009376; font-size: 20px; margin-bottom: 10px;\">How It Works</h3>

                        <ul style=\"padding-left: 20px; margin-bottom: 20px; font-size: 14px;\">
                            <li style=\"margin-bottom: 8px;\"><b>Choose Language</b>: Select from 200+ options.</li>
                            <li style=\"margin-bottom: 8px;\"><b>Ask Questions</b>: <i>\"What are the local impacts of climate change in Toronto?\"</i> or <i>\"Why is summer so hot now in Toronto?\"</i></li>
                            <li style=\"margin-bottom: 8px;\"><b>Act</b>: Ask about actionable steps such as <i>\"What can I do about flooding in Toronto?\"</i> or <i>\"How to reduce my carbon footprint?\"</i> and receive links to local resources (e.g., city programs, community groups).</li>
                        </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # FIXED: Show chat history if there are any messages
                if len(st.session_state.chat_history) > 0:
                    # This is the Chat History section that appears after asking questions
                    st.markdown("---")
                    display_chat_history_section()

                # Support and FAQs section with popup behavior
                if 'show_faq_popup' not in st.session_state:
                    st.session_state.show_faq_popup = False

                if st.button("📚 Support & FAQs"):
                    st.session_state.show_faq_popup = True

                # Move "Made by" section here
                st.markdown('<div class="footer" style="margin-top: 20px; margin-bottom: 20px;">', unsafe_allow_html=True)
                st.markdown('<div>Made by:</div>', unsafe_allow_html=True)
                if TREE_ICON:
                    st.image(TREE_ICON, width=40)
                st.markdown('<div style="font-size: 18px; display:flex; align-items:center; gap:6px;">\
                    <a href="https://crc.place/" target="_blank" title="Climate Resilient Communities">Climate Resilient Communities</a>\
                    <span title="Trademark">™</span>\
                    </div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Main header content with proper alignment
            if CCC_ICON_B64:
                st.markdown(
                    f"""
                    <div class="mlcc-header">
                        <img class="mlcc-logo" src="data:image/png;base64,{CCC_ICON_B64}" alt="Logo" />
                        <h1 style="margin:0;">Multilingual Climate Chatbot</h1>
                    </div>
                    <div class="mlcc-subtitle">Ask me anything about climate change!</div>
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
            st.error(f"Error initializing chatbot: {str(e)}")
            st.info("Make sure the .env file exists in the project root directory")

if __name__ == "__main__":
    main()