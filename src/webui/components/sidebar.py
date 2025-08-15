import base64
import streamlit as st
from typing import Callable, Optional

from ..utils.helpers import generate_chat_history_text


def display_chat_history_in_sidebar() -> None:
    msgs = st.session_state.get("chat_history", [])
    if not msgs:
        return

    text = generate_chat_history_text(msgs) or "Chat History is empty.\n"
    data_bytes = text.encode("utf-8")
    b64 = base64.b64encode(data_bytes).decode()

    st.markdown('<div class="chat-history-section">', unsafe_allow_html=True)
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

    for i in range(0, len(msgs), 2):
        if msgs[i].get("role") != "user":
            continue
        q = msgs[i].get("content", "")
        a = (
            msgs[i + 1].get("content", "")
            if i + 1 < len(msgs) and msgs[i + 1].get("role") == "assistant"
            else ""
        )
        with st.expander(f"Q: {q[:60]}…", expanded=False):
            st.markdown("**Question:**"); st.write(q)
            st.markdown("**Response:**"); st.write(a)

    st.markdown('</div>', unsafe_allow_html=True)


def render_sidebar(
    chatbot,
    mobile_mode: bool,
    toggle_sidebar: Callable[[], None],
    set_query_params: Callable[[dict, bool], None],
    tree_icon_path: Optional[str] = None,
) -> None:
    if not st.session_state.get("_sb_open", True):
        return
    with st.sidebar:
        st.markdown('<div class="sb-close-button-container">', unsafe_allow_html=True)
        st.button("⬅️", on_click=toggle_sidebar, key="sb_close_btn", help="Close sidebar")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown('<div class="content">', unsafe_allow_html=True)

        st.title('Multilingual Climate Chatbot')

        st.write("**Please choose your preferred language to get started:**")
        languages = sorted(chatbot.LANGUAGE_NAME_TO_CODE.keys())
        default_index = languages.index(st.session_state.selected_language)
        selected_language = st.selectbox(
            "Select your language",
            options=languages,
            index=default_index,
            help="Choose your preferred language",
        )
        st.markdown('<style>section[data-testid="stSidebar"] .stSelectbox > div > div {background: white !important;}</style>', unsafe_allow_html=True)

        if not st.session_state.language_confirmed:
            if st.button("Confirm", key="confirm_lang_btn"):
                st.session_state.selected_language = selected_language
                st.session_state.language_confirmed = True
                if mobile_mode:
                    st.session_state._sb_open = False
                    st.session_state._sb_rerun = True
                    set_query_params({"sb": "0"}, merge=True)
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
                unsafe_allow_html=True,
            )

        if len(st.session_state.chat_history) > 0:
            st.markdown('<div style="margin: 8px 0;"></div>', unsafe_allow_html=True)
            display_chat_history_in_sidebar()

        if 'show_faq_popup' not in st.session_state:
            st.session_state.show_faq_popup = False
        if st.button("📚 Support & FAQs"):
            st.session_state.show_faq_popup = True
            if mobile_mode:
                st.session_state._sb_open = False
                st.session_state._sb_rerun = True
                set_query_params({"sb": "0"}, merge=True)
                st.rerun()

        st.markdown('<div class="footer" style="margin-top: 20px; margin-bottom: 20px;">', unsafe_allow_html=True)
        st.markdown('<div>Made by:</div>', unsafe_allow_html=True)
        if tree_icon_path:
            st.image(tree_icon_path, width=40)
        st.markdown('<div style="font-size: 18px; display:flex; align-items:center; gap:6px;">\
            <a href="https://crc.place/" target="_blank" title="Climate Resilient Communities">Climate Resilient Communities</a>\
            <span title="Trademark">™</span>\
            </div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


