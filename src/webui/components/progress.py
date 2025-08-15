"""Progress and loading UI components."""

import time
import queue
import threading
import streamlit as st
from src.webui.utils.async_helpers import run_async


def _render_loading_ui(container, stage_text: str, progress_value: float) -> None:
    """Render a loading animation with progress bar and stage text."""
    with container.container():
        st.markdown(
            f"""
            <div style="text-align: center; padding: 20px; margin: 40px 0; border-radius: 12px; 
                        background-color: #f8f9fa; border: 1px solid #e9ecef;">
                <div style="font-size: 18px; color: #495057; margin-bottom: 15px;">
                    🔄 {stage_text}
                </div>
                <div style="width: 100%; background-color: #e9ecef; border-radius: 8px; height: 8px; margin: 0 auto;">
                    <div style="background-color: #009376; height: 100%; border-radius: 8px; 
                                width: {progress_value * 100:.1f}%; transition: width 0.3s ease;"></div>
                </div>
                <div style="font-size: 14px; color: #6c757d; margin-top: 10px;">
                    {progress_value * 100:.0f}% complete
                </div>
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


def display_progress(progress_placeholder):
    """Display a basic progress indicator.
    
    This function was likely used for simple progress display.
    For advanced progress with stages, use run_query_with_interactive_progress instead.
    """
    _render_loading_ui(progress_placeholder, "Processing...", 0.5)
