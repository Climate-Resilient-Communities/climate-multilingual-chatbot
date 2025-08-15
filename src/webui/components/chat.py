import re
import logging
import streamlit as st

from ..utils.helpers import (
    escape_html,
    get_citation_details,
    format_message_for_copy,
)

logger = logging.getLogger(__name__)


def is_rtl_language(language_code: str) -> bool:
    return language_code in {"fa", "ar", "he"}


def clean_html_content(content: str) -> str:
    if content is None:
        return ""
    # Remove stray closing tags sometimes produced by LLMs
    content = re.sub(r"</div>\s*$", "", content)
    content = re.sub(r"</?div[^>]*>\s*$", "", content)
    content = re.sub(r"</?span[^>]*>\s*$", "", content)
    content = re.sub(r"</?p[^>]*>\s*$", "", content)
    # Balance code blocks
    backtick_count = content.count("```")
    if backtick_count % 2 != 0:
        content += "\n```"
    return str(content)


def render_user_bubble(text: str, language_code: str = "en") -> str:
    direction = "rtl" if is_rtl_language(language_code) else "ltr"
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
    if "message_feedback" not in st.session_state:
        st.session_state.message_feedback = {}
    if "show_copy_panel" not in st.session_state or not isinstance(st.session_state.show_copy_panel, dict):
        st.session_state.show_copy_panel = {}
    _ = format_message_for_copy(message_index, st.session_state.get("chat_history", []))
    role = message.get("role", "assistant")
    is_assistant = role != "user"
    if not is_assistant:
        return
    col1, col2, col3, col4 = st.columns([0.5, 0.5, 0.5, 10])
    with col1:
        if st.button("👍", key=f"msg_up_{message_index}", help="Thumbs up", use_container_width=True):
            st.session_state.message_feedback[message_index] = "up"
            try:
                from ..app_nova import log_feedback_event  # legacy hook
                log_feedback_event(message_index, "up")
            except Exception:
                pass
    with col2:
        if st.button("👎", key=f"msg_down_{message_index}", help="Thumbs down", use_container_width=True):
            st.session_state.message_feedback[message_index] = "down"
            try:
                from ..app_nova import log_feedback_event
                log_feedback_event(message_index, "down")
            except Exception:
                pass
    with col3:
        if st.button("↻", key=f"msg_retry_{message_index}", help="Retry this answer", use_container_width=True):
            prior_query = ""
            user_index = -1
            j = message_index - 1
            hist = st.session_state.chat_history
            while j >= 0:
                if hist[j].get("role") == "user":
                    prior_query = hist[j].get("content", "")
                    user_index = j
                    break
                j -= 1
            try:
                if 0 <= message_index < len(st.session_state.chat_history):
                    st.session_state.chat_history.pop(message_index)
            except Exception as _e:
                logger.warning(f"Retry removal failed: {_e}")
            st.session_state.retry_request = {
                "assistant_index": message_index,
                "user_index": user_index,
                "query": prior_query,
            }
            st.rerun()


def display_source_citations(citations, base_idx: int = 0) -> None:
    if not citations:
        return
    st.markdown("---")
    st.markdown('<div class="sources-section">', unsafe_allow_html=True)
    st.markdown('<div class="sources-heading">Sources</div>', unsafe_allow_html=True)
    unique_sources = {}
    for citation in citations:
        details = get_citation_details(citation)
        if details["title"] not in unique_sources:
            unique_sources[details["title"]] = details
    for idx, (title, source) in enumerate(unique_sources.items()):
        with st.container():
            unique_key = f"source_{base_idx}_{idx}"
            url_str = str(source.get("url") or "")
            safe_title = (title or "").strip()
            btn_text = safe_title[:100] if safe_title and len(safe_title) >= 4 else "Content sourced from leading climate specialist"
            button_label = f"📄 {btn_text}..."
            if st.button(button_label, key=unique_key):
                st.session_state.selected_source = f"{base_idx}_{title}"
            if st.session_state.get("selected_source") == f"{base_idx}_{title}":
                with st.expander("Source Details", expanded=True):
                    if title:
                        st.markdown(f"**Title:** {title}")
                    url_val = source.get("url", "")
                    if url_val and url_val.strip():
                        st.markdown(f"**URL:** [{url_val}]({url_val})")
                    else:
                        st.markdown("**Source:** Verified climate research document")
                    if source.get("snippet"):
                        st.markdown("**Cited Content:**")
                        st.markdown(source["snippet"])
                    if source.get("content"):
                        st.markdown("**Full Content:**")
                        st.markdown(source["content"][:500] + "..." if len(source["content"]) > 500 else source["content"])


def display_chat_messages(retry_request=None):
    st.markdown(
        """
        <style>
        [data-testid="stChatMessage"] h1{font-size:1.50rem!important;} [data-testid="stChatMessage"] h2{font-size:1.25rem!important;} [data-testid="stChatMessage"] h3{font-size:1.10rem!important;}
        [data-testid="stChatMessage"] h4,[data-testid="stChatMessage"] h5,[data-testid="stChatMessage"] h6{font-size:1rem!important;}
        @media (max-width:768px){
          div[data-testid="stChatMessage"] img,div[data-testid="stChatMessage"] svg{display:none!important;}
          div[data-testid="stChatMessage"],div[data-testid="stChatMessage"]>div{background:transparent!important;box-shadow:none!important;border:none!important;}
          div[data-testid="stChatMessage"]{padding:6px 8px!important;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    retry_user_index = retry_request.get("user_index") if isinstance(retry_request, dict) else None
    injected_retry_placeholder = None
    for i, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            user_msg = st.chat_message("user")
            user_code = message.get("language_code", "en")
            user_msg.markdown(render_user_bubble(message.get("content", ""), user_code), unsafe_allow_html=True)
            render_message_actions_ui(i, message)
            if retry_user_index is not None and retry_user_index == i and injected_retry_placeholder is None:
                retry_msg_container = st.chat_message("assistant")
                injected_retry_placeholder = retry_msg_container.empty()
        else:
            assistant_message = st.chat_message("assistant")
            content = clean_html_content(message.get("content", ""))
            language_code = message.get("language_code", "en")
            text_align = "right" if is_rtl_language(language_code) else "left"
            direction = "rtl" if is_rtl_language(language_code) else "ltr"
            try:
                if is_rtl_language(language_code):
                    assistant_message.markdown(
                        f"""<div style="direction: {direction}; text-align: {text_align}">{content}</div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    if content.strip().startswith("#"):
                        content = "\n" + content.strip()
                    assistant_message.markdown(content)
            except Exception as e:
                logger.error(f"Error rendering message: {str(e)}")
                assistant_message.text("Error displaying formatted message. Raw content:")
                assistant_message.text(content)
            if message.get("citations"):
                display_source_citations(message["citations"], base_idx=i)
            render_message_actions_ui(i, message)
    return injected_retry_placeholder


def handle_chat_turn(chatbot) -> None:
    """Handle a full user→assistant chat turn, including retries and progress UI."""
    import re
    import os
    import logging
    import streamlit as st
    from ..components.progress import run_query_with_interactive_progress
    from ..components.chat import display_source_citations
    from ..components.chat import is_rtl_language, clean_html_content, render_user_bubble
    from ..app_nova import render_message_actions_ui  # reuse existing action renderer
    from ..setup.logging_config import persist_interaction_record

    logger = logging.getLogger(__name__)

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
        query = None

    if st.session_state.get('needs_rerun', False):
        st.session_state.needs_rerun = False
        return

    if not (query or retry_req) or not chatbot:
        return

    # Display user message if present
    if query:
        st.chat_message("user").markdown(render_user_bubble(query), unsafe_allow_html=True)
        render_message_actions_ui(len(st.session_state.chat_history) - 1, st.session_state.chat_history[-1])

    # Placeholder for assistant typing/progress
    if retry_req and injected_retry_placeholder is not None:
        typing_message = injected_retry_placeholder
    else:
        response_placeholder = st.chat_message("assistant")
        typing_message = response_placeholder.empty()

    try:
        # Build conversation history
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
                    "timestamp": None,
                })
                i += 2
            else:
                i += 1

        retry_req = st.session_state.get('retry_request') if isinstance(st.session_state.get('retry_request'), dict) else None
        retry_query = retry_req.get('query') if retry_req else None
        effective_query = retry_query or query

        # Query with progress UI
        result = run_query_with_interactive_progress(
            chatbot=chatbot,
            query=effective_query,
            language_name=st.session_state.selected_language,
            conversation_history=conversation_history,
            response_placeholder=typing_message,
            skip_cache=bool(retry_req),
        )

        typing_message.empty()

        if result and result.get('success', False):
            response_content = result['response']
            if response_content and isinstance(response_content, str):
                response_content = response_content.strip()
                if response_content.startswith('#'):
                    response_content = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', response_content)

            final_response = {
                'role': 'assistant',
                'language_code': result.get('language_code', 'en'),
                'content': response_content,
                'citations': result.get('citations', []),
                'retrieval_source': result.get('retrieval_source'),
                'fallback_reason': result.get('fallback_reason'),
            }

            if retry_req and isinstance(retry_req.get('assistant_index'), int):
                insert_at = min(retry_req['assistant_index'], len(st.session_state.chat_history))
                st.session_state.chat_history.insert(insert_at, final_response)
                try:
                    persist_interaction_record(insert_at, "none")
                except Exception:
                    pass
            else:
                st.session_state.chat_history.append(final_response)
                try:
                    persist_interaction_record(len(st.session_state.chat_history) - 1, "none")
                except Exception:
                    pass

            language_code = final_response['language_code']
            text_align = 'right' if is_rtl_language(language_code) else 'left'
            direction = 'rtl' if is_rtl_language(language_code) else 'ltr'
            content = clean_html_content(final_response['content'])
            typing_message.markdown(
                f"""<div style="direction: {direction}; text-align: {text_align}">{content}</div>""",
                unsafe_allow_html=True,
            )

            try:
                if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                    st.session_state.copy_texts = {}
                st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = content or final_response['content'] or ''
            except Exception:
                pass

            if result.get('citations'):
                if retry_req and isinstance(retry_req.get('assistant_index'), int):
                    message_idx = min(retry_req['assistant_index'], len(st.session_state.chat_history) - 1)
                else:
                    message_idx = len(st.session_state.chat_history) - 1
                display_source_citations(result['citations'], base_idx=message_idx)
            if retry_req and isinstance(retry_req.get('assistant_index'), int):
                render_message_actions_ui(message_idx, final_response)
            else:
                render_message_actions_ui(len(st.session_state.chat_history) - 1, final_response)
        else:
            error_message = (
                result.get('message')
                or result.get('response')
                or 'An error occurred'
            )
            error_lower = error_message.lower() if isinstance(error_message, str) else ''
            if (
                "not about climate" in error_lower
                or "climate change" in error_lower
                or result.get('error_type') == "off_topic"
                or (result.get('validation_result', {}).get('reason') == "not_climate_related")
            ):
                off_topic = (
                    "I'm a climate change assistant and can only help with questions about climate, environment, and sustainability. "
                    "Please ask me about topics like climate change causes, effects, or solutions."
                )
                st.session_state.chat_history.append({'role': 'assistant','content': off_topic,'language_code': 'en'})
                try:
                    persist_interaction_record(len(st.session_state.chat_history) - 1, "none")
                except Exception:
                    pass
                typing_message.markdown(off_topic)
                try:
                    if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                        st.session_state.copy_texts = {}
                    st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = off_topic
                except Exception:
                    pass
            else:
                st.session_state.chat_history.append({'role': 'assistant','content': str(error_message),'language_code': 'en'})
                typing_message.error(str(error_message))
                try:
                    if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                        st.session_state.copy_texts = {}
                    st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = str(error_message)
                except Exception:
                    pass
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        st.session_state.chat_history.append({'role': 'assistant','content': error_msg,'language_code': 'en'})
        typing_message.error(error_msg)
        render_message_actions_ui(len(st.session_state.chat_history) - 1, st.session_state.chat_history[-1])
        try:
            if 'copy_texts' not in st.session_state or not isinstance(st.session_state.copy_texts, dict):
                st.session_state.copy_texts = {}
            st.session_state.copy_texts[len(st.session_state.chat_history) - 1] = error_msg
        except Exception:
            pass

    if retry_req:
        st.session_state.retry_request = None
        st.session_state.last_retry_applied = None
    st.session_state.needs_rerun = True
    st.rerun()



