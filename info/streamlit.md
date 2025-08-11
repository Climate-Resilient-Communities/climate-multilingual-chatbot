streamlit.md
1. Overview
This document provides a comprehensive analysis of the Streamlit application defined in app_nova.py. The application is a sophisticated, multilingual chatbot focused on climate change. It includes several advanced features, such as PII (Personally Identifiable Information) redaction, asynchronous operations, custom UI components, and detailed logging to local files and Azure Blob Storage.
The primary goal of this breakdown is to deconstruct the large codebase into logical, understandable sections. This will enable developers and LLMs to effectively navigate, understand, and modify the code.
This document is divided into two main parts:
Codebase Breakdown: A section-by-section analysis of the code with line numbers and descriptions.
Planning for Fixes: A detailed plan to address two critical UI bugs related to dark mode styling and sidebar controls.
Target Environment: streamlit>=1.40.1
2. Codebase Breakdown
The app_nova.py script can be broken down into the following logical sections:
Section 1: Pre-emptive Patches and Configuration (Lines 1-400)
This initial block of code is critical and runs before any other modules, including Streamlit itself. Its purpose is to configure the environment and apply patches to prevent common issues with libraries like PyTorch and Streamlit's file watcher.
Lines 5-20: Environment Variable Setup. Disables Streamlit's file watcher and live-reload features to prevent unexpected reruns and performance issues in a production environment. It also configures PyTorch and HuggingFace environment variables to disable JIT compilation and set a temporary cache directory.
Lines 22-58: PyTorch _classes Patch. Implements a sophisticated patch to prevent a known compatibility issue between PyTorch and Streamlit. It replaces torch._classes with a "safe" mock object that doesn't break Streamlit's module introspection when the app reruns. This is a crucial fix for stability.
Lines 60-80: Global Import Patching. The script hijacks Python's built-in __import__ function to apply the PyTorch patch automatically whenever torch or its submodules are imported anywhere in the application.
Lines 82-91: Warning Suppression & Logging Setup. Disables common UserWarning and FutureWarning messages from Streamlit and Transformers to keep the console clean. It then sets up a robust logging system, including a RotatingFileHandler for local log files (app.log) and defines a path for structured chat interaction logs (chat_interactions.jsonl).
Lines 93-299: Feedback and Interaction Logging.
log_feedback_event(): A function to log user feedback (thumbs up/down) on chat messages.
persist_interaction_record(): A core function that creates a detailed JSON record of a chat interaction (query, response, feedback, citations, etc.), redacts PII using the redact_pii function, and persists it.
_persist_record_to_blob(): A helper function that handles uploading the JSON interaction record to an Azure Append Blob if connection details are provided as environment variables. This is essential for data collection in a deployed environment.
Lines 301-310: Asyncio Event Loop Setup. Ensures a running asyncio event loop is available, which is necessary for running asynchronous functions from within Streamlit's synchronous execution model.
Lines 312-398: Streamlit Page Configuration and Sidebar Control.
This section calculates the favicon path and then calls st.set_page_config().
It contains a complex but robust mechanism to control the initial state of the sidebar (expanded or collapsed) based on a URL query parameter (sb=0 or sb=1). It uses session state (_sb_open, _sb_rerun) and a double-rerun trick to override Streamlit's default browser-based preference for the sidebar state.
It also includes a mechanism to clear the browser's localStorage and sessionStorage via a reset_ui=1 query parameter to force a completely fresh UI state for the user.
Lines 400-470: PII Redaction and Module Imports.
redact_pii(): A comprehensive function that uses regular expressions to find and replace various types of PII (emails, phone numbers, credit cards, SSNs, etc.) with placeholders like [EMAIL_REDACTED].
The script then adds the project's root directory to the Python path and imports the application's core custom modules, like MultilingualClimateChatbot.
Lines 472-500: Asset Loading and Utility Functions. Defines paths for static assets (icons, wallpaper) and includes a get_base64_image helper to encode images for embedding in CSS.
Section 2: Core Application Logic and Helpers (Lines 501-900)
This section contains the functions that drive the chatbot's backend processing and UI rendering logic.
Lines 502-545: Async Execution Helpers.
create_event_loop() and run_async(): Helper functions to manage the asyncio event loop and execute asynchronous coroutines from the main synchronous thread, which is essential for calling the chatbot's async methods.
Lines 547-568: Chatbot Initialization (init_chatbot). A cached function (@st.cache_resource) that initializes the MultilingualClimateChatbot class. Caching ensures the heavy model and index are loaded only once per session. It includes error handling for common issues like a missing Pinecone index.
Lines 570-658: Citation and Progress Display.
get_citation_details(): Safely extracts details (title, URL, content) from citation objects.
display_source_citations(): Renders a list of source citations below a chat message, deduplicating them and presenting them in an interactive, expandable format.
display_progress(), _render_loading_ui(): Functions to render an animated, multi-stage loading indicator while the chatbot is processing a query.
Lines 660-720: Background Query Execution.
_run_query_background(): A worker function designed to run in a separate thread. It calls the chatbot's asynchronous processing pipeline.
run_query_with_interactive_progress(): The orchestrator function that starts the background worker thread and, in the main thread, listens to a queue for progress updates to render the interactive loading UI. This provides a responsive user experience during long-running operations.
Lines 722-800: Message Rendering and Actions.
is_rtl_language(), clean_html_content(), escape_html(): Utility functions for handling right-to-left languages and sanitizing content for safe HTML rendering.
render_user_bubble(): Creates a custom-styled HTML bubble for user messages.
render_message_actions_ui(): Renders the action buttons (👍, 👎, ↻ for retry) next to an assistant's message. The retry logic is handled here by setting a retry_request in the session state and triggering a rerun.
Lines 802-870: Chat History Display (display_chat_messages). This function iterates through st.session_state.chat_history and renders each message. It uses custom rendering for user bubbles and handles RTL text alignment. Crucially, it can inject a temporary placeholder for a "retry" response, allowing the new response to be generated in the correct position in the chat log.
Section 3: UI Styling and Layout (Lines 872-1350)
This part of the code is dedicated to defining the application's visual appearance and layout through custom CSS and HTML.
Lines 872-1100: Custom CSS (load_custom_css). This large function injects a significant amount of CSS into the page to achieve a custom look and feel. Key responsibilities include:
Hiding the default Streamlit header and toolbar.
Applying a background wallpaper.
Styling buttons, chat messages, and the sidebar.
Crucially, it forces the sidebar to be dark (#303030) and makes all text within it white (color: #ffffff !important;), which is the source of the dark mode bug.
It also contains specific styles for the chat history section in the sidebar, download buttons, and other custom elements.
Lines 1102-1150: Chat History Export and Formatting.
generate_chat_history_text(): Converts the entire chat history into a plain text string for downloading.
format_message_for_copy(): Formats a single chat turn (user query + assistant response + sources) into a plain text string for the copy-to-clipboard functionality.
Lines 1152-1185: Sidebar Chat History (display_chat_history_section). Renders a compact, expandable list of past questions and answers in the sidebar, along with a download button for the full chat history.
Lines 1187-1580: Consent Form (display_consent_form, show_consent_dialog).
These functions are responsible for displaying a mandatory consent form before the user can access the main application.
The code uses st.dialog (a feature in Streamlit >= 1.31) to show the form as a modal overlay, which is a modern and clean approach. It includes expanders for Privacy Policy, Terms of Use, and a Disclaimer. The main chat interface is blocked until consent is given.
Section 4: Main Application Execution (main) (Lines 1583-end)
This is the entry point of the application, orchestrating the entire UI flow.
Lines 1585-1615: Session State Initialization. Sets up all necessary keys in st.session_state on the first run, such as chat_history, selected_language, and flags like consent_given.
Lines 1617-1622: Consent Gate. Checks if consent_given is True. If not, it calls show_consent_dialog() and immediately stops further execution with st.stop().
Lines 1624-1640: Chatbot Initialization Call. Calls the cached init_chatbot() function and handles any potential initialization errors by displaying a message to the user.
Lines 1642-1740: Sidebar Rendering. This block renders all the components inside the sidebar (st.sidebar), including:
The title and language selector (st.selectbox).
The "Confirm" button for the language.
The "How It Works" section (shown only before the first question).
The chat history section (shown after the first question).
The "Support & FAQs" button and the "Made by" footer.
Lines 1742-1990: Main Panel Rendering and Chat Logic. This is the core interactive loop of the app.
It renders the main header.
It handles the FAQ popup modal logic.
It calls display_chat_messages() to show the current conversation.
It displays the st.chat_input widget for the user to type their query.
Query/Retry Processing: If the user submits a query OR a retry is requested, this block executes the main logic:
It adds the user's message to the history.
It calls run_query_with_interactive_progress() to get the chatbot's response while showing a loading animation.
It handles the response, whether it's a successful answer, an off-topic rejection, or an error.
It appends the assistant's final response to the chat history.
It calls persist_interaction_record() to log the exchange.
Finally, it triggers a st.rerun() to ensure the UI is cleanly updated.
Lines 1992-end: Duplicate Logic for Consent Flow. This large, duplicated block of code appears to be a remnant or a fallback path for rendering the UI while the consent dialog is active. It largely mirrors the main application logic, which can be a source of confusion and bugs. It should ideally be refactored to avoid repetition.
Line 2291: Entry Point Guard. The standard if __name__ == "__main__": ensures the main() function is called when the script is executed.
3. Planning for Fixes
Here is a detailed plan to resolve the two issues you've identified.
Issue 1: Dark Mode Language Selector is Unreadable
Problem: In the sidebar, the st.selectbox for language selection has black text on a dark background, making the selected value ("english") invisible. This is caused by conflicting CSS rules. One rule makes all sidebar text white, but a more specific rule makes text inside select boxes black, assuming a light background which is not present in dark mode.
Goal: Make the language selector readable in both light and dark modes. The suggested solution is to give the selectbox a white background and ensure its text is black. This is a robust approach that avoids complex theme-dependent CSS.
Plan:
Locate the CSS: The relevant CSS is injected in the load_custom_css function (around lines 872-1100).
Identify the Target: The st.selectbox widget is rendered as an HTML element that can be targeted with div[data-baseweb="select"].
Modify the CSS: Add a new, specific CSS rule inside the <style> block of the load_custom_css function. This rule will override the default dark theme styling for this specific widget.
Proposed CSS Addition (to be placed around line 1000, within the main CSS string):
code
Css
/* FIX: Ensure the language selectbox in the sidebar is always readable */
section[data-testid="stSidebar"] div[data-baseweb="select"] {
    background-color: #ffffff !important;
    border-radius: 8px !important; /* Optional: adds rounded corners to match other elements */
}

/* Ensure the text inside the now-white box is black */
section[data-testid="stSidebar"] div[data-baseweb="select"] div {
    color: #000000 !important;
}

/* Ensure the dropdown arrow is also visible (it might be white) */
section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
    fill: #000000 !important;
}
This change will make the entire selectbox component have a white background, with black text and a black dropdown arrow, ensuring it is perfectly readable against the dark sidebar without affecting the light mode appearance.
Issue 2: Missing Sidebar Toggle Button on Azure
Problem: The default Streamlit sidebar collapse/expand arrow is not visible when the app is deployed on Azure. The app's custom CSS explicitly hides the default header, toolbar, and collapse controls, which is likely the cause.
Goal: Provide a visible, functional button for users to collapse and expand the sidebar.
Plan:
The best approach is to create a custom toggle button that hooks into the application's existing, sophisticated sidebar control logic (_sb_open and _sb_rerun session state variables). Placing this button in the main content area ensures it's always accessible, even when the sidebar is collapsed.
Location: Add the button at the very top of the main content area, right after the consent gate and chatbot initialization in the main function (around line 1641).
State Management: We will use the existing st.session_state._sb_open variable. No new state is needed.
Implementation:
Define a small callback function to handle the button click.
Use st.columns to create a small, unobtrusive button positioned at the top-left of the main panel.
Use an emoji for the button icon (⬅️ or ➡️) that changes based on the sidebar's current state.
Proposed Code Addition (to be placed in main() around line 1741, just before the header is rendered):
code
Python
# ... after chatbot initialization and error checking ...

# --- BEGIN PROPOSED FIX FOR SIDEBAR TOGGLE ---

# Define a callback function to toggle the sidebar state
def toggle_sidebar():
    # Flip the boolean state
    st.session_state._sb_open = not st.session_state._sb_open
    # Set the rerun flag to trigger the page_config logic
    st.session_state._sb_rerun = True

# Use columns to create a small space for the button on the left
_left_main, _right_main = st.columns([1, 20]) # Adjust ratio as needed

with _left_main:
    # Determine the correct icon based on the sidebar state
    arrow_icon = "⬅️" if st.session_state._sb_open else "➡️"
    st.button(arrow_icon, on_click=toggle_sidebar, help="Toggle sidebar")

# Inject CSS to position the button correctly and make it look good
st.markdown("""
<style>
    /* Target the column containing our button */
    div[data-testid="stHorizontalBlock"] > div:has(button[kind="secondary"]:has(span:contains("⬅️"))) {
        position: fixed;
        top: 0.5rem;
        left: 1rem;
        z-index: 1000;
    }
    div[data-testid="stHorizontalBlock"] > div:has(button[kind="secondary"]:has(span:contains("➡️"))) {
        position: fixed;
        top: 0.5rem;
        left: 1rem;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# --- END PROPOSED FIX ---

with _right_main:
    # The rest of the main panel content starts here.
    # To prevent overlap, we can add a small spacer if needed,
    # but absolute positioning should handle it.
    pass # The existing header rendering will follow

# Header rendering code follows...
if CCC_ICON_B64:
    st.markdown(...)
Correction & Simplification: The CSS positioning above is complex and might be brittle. A simpler method is to just place the button without the complex positioning. It will appear at the top-left of the main content flow, which is acceptable and much more robust.
Revised, Simpler Plan:
code
Python
# In main(), around line 1741

# --- BEGIN REVISED FIX FOR SIDEBAR TOGGLE ---
def toggle_sidebar():
    st.session_state._sb_open = not st.session_state._sb_open
    st.session_state._sb_rerun = True

arrow_icon = "⬅️" if st.session_state._sb_open else "➡️"
st.button(arrow_icon, on_click=toggle_sidebar, help="Toggle sidebar")
# --- END REVISED FIX ---

# Header
if CCC_ICON_B64:
    st.markdown(...) # The rest of the main function continues
This simplified plan adds a functional button that leverages the app's existing sidebar logic. When clicked, it will trigger the double-rerun sequence defined at the top of the script, forcing the sidebar to either collapse or expand, effectively solving the problem on Azure.
89.0s
