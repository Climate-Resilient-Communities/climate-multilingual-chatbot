from __future__ import annotations

from typing import Tuple, Dict
import streamlit as st

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


def detect_device_info(get_param_fn) -> Tuple[bool, Dict]:
    """Return (is_mobile_like, info_dict) using multiple strategies.

    get_param_fn: function to read a single query param (name)->str|None
    info_dict keys: method, device_type, width, ua
    """
    info: Dict = {"method": "unknown", "device_type": None, "width": None, "ua": None}

    # 1) streamlit-user-device
    try:
        device_type = _user_device() if _user_device else None
        if isinstance(device_type, str) and device_type:
            info.update({"method": "user_device", "device_type": device_type})
            is_mobile_like = device_type.lower() in ("mobile", "phone", "tablet")
            return bool(is_mobile_like), info
    except Exception:
        pass

    # 2) st_screen_stats viewport width
    try:
        screen_data = _ScreenData(setTimeout=0) if _ScreenData else None
        data = screen_data.st_screen_data() if screen_data else None
        if isinstance(data, dict) and data.get("width") is not None:
            info.update({"method": "screen_stats", "width": data.get("width")})
            return bool(int(data.get("width", 9999)) <= 768), info
    except Exception:
        pass

    # 3) userAgent parsing via streamlit-javascript
    try:
        ua_string = _st_javascript("window.navigator.userAgent;") if _st_javascript else None
        info["ua"] = ua_string if isinstance(ua_string, str) else None
        if isinstance(ua_string, str) and ua_string:
            ua = _parse_user_agent(ua_string) if _parse_user_agent else None
            info["method"] = "user_agent"
            if ua is not None:
                info["device_type"] = (
                    "mobile" if getattr(ua, "is_mobile", False) else ("tablet" if getattr(ua, "is_tablet", False) else "desktop")
                )
                return bool(getattr(ua, "is_mobile", False) or getattr(ua, "is_tablet", False)), info
    except Exception:
        pass

    # 4) Query param fallback
    try:
        raw = get_param_fn("mobile") or get_param_fn("m")
        is_m = isinstance(raw, str) and raw.lower() in ("1", "true", "yes", "y")
        info.update({"method": "query_param", "device_type": "mobile" if is_m else "desktop"})
        return is_m, info
    except Exception:
        return False, info


def is_mobile_device(get_param_fn) -> bool:
    """Best-effort mobile detection for server-driven decisions with caching and debug info."""
    force_probe = False
    try:
        raw = get_param_fn("mobiledebug") or get_param_fn("dev")
        if isinstance(raw, str) and raw.lower() in ("1", "true", "yes", "y"):
            force_probe = True
    except Exception:
        pass

    if not force_probe and isinstance(st.session_state.get("is_mobile_detected"), bool):
        return bool(st.session_state.get("is_mobile_detected"))

    is_m, info = detect_device_info(get_param_fn)
    st.session_state.is_mobile_detected = bool(is_m)
    st.session_state.device_detection_info = info
    return st.session_state.is_mobile_detected


