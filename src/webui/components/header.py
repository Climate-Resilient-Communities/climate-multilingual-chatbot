import streamlit as st


def render_mobile_header(chatbot, CCC_ICON_B64: str | None) -> None:
    """Render the compact mobile header and FAQ button.

    For now we keep the exact structure used in app_nova to avoid behavior changes.
    This can be further refined to remove inline CSS once styles are centralized.
    """
    faq_container = st.container()
    with faq_container:
        col1, col2, col3 = st.columns([8, 1, 1])
        with col3:
            st.markdown('<div id="mobile-faq-wrap"></div>', unsafe_allow_html=True)
            if st.button("?", key="mobile_faq_btn", help="Support and Faq"):
                st.session_state.show_faq_popup = True
                st.rerun()

    with st.container():
        if CCC_ICON_B64:
            st.markdown(
                f"""
                <div style="text-align:center; margin: 0 0 4px 0;">
                  <img src="data:image/png;base64,{CCC_ICON_B64}" alt="Logo"
                       style="width:20px;height:20px;vertical-align:middle;margin-right:6px;">
                  <span style="color:#009376;font-size:13px;">Made by
                    <a href="https://crc.place/" target="_blank" style="color:#009376;text-decoration:none;">
                      Climate Resilient Communities
                    </a>
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        try:
            languages = sorted(chatbot.LANGUAGE_NAME_TO_CODE.keys())
        except Exception:
            languages = [st.session_state.get("selected_language", "english")]

        current = st.session_state.get("selected_language", "english")
        idx = languages.index(current) if current in languages else 0

        st.selectbox(
            "Language",
            options=languages,
            index=idx,
            key="mobile_language_select",
            label_visibility="collapsed",
            on_change=lambda: st.session_state.update({
                "selected_language": st.session_state.get("mobile_language_select"),
                "language_confirmed": True,
            }),
        )
    # CSS kept in app scope; we rely on existing global CSS for sticky bar and wrap



def activate_mobile_mode(chatbot, CCC_ICON_B64: str | None) -> None:
    """Enable mobile UX behaviors and render the compact mobile header."""
    from src.webui.utils.helpers import set_query_params_robust  # local import to avoid cycles

    st.session_state.MOBILE_MODE = True
    if not st.session_state.get("language_confirmed"):
        st.session_state.selected_language = st.session_state.get("selected_language", "english") or "english"
        st.session_state.language_confirmed = True
    try:
        st.session_state._sb_open = False
        st.session_state._sb_rerun = True
        set_query_params_robust({"sb": "0"}, merge=True)
    except Exception:
        pass

    render_mobile_header(chatbot, CCC_ICON_B64)


def render_desktop_header(CCC_ICON_B64: str | None) -> None:
    """Render the desktop header with logo when available; fallback to title."""
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

