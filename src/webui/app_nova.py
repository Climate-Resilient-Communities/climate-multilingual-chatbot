# Configure environment first
import os
import sys
import logging
from pathlib import Path

# Configure torch environment variables before any imports
os.environ["PYTORCH_JIT"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_USE_CUDA_DSA"] = "0"
os.environ["TORCH_USE_RTLD_GLOBAL"] = "YES"  # Add this to prevent _path issues

# Configure logging
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Must be the first Streamlit command
import streamlit as st
st.set_page_config(layout="wide", page_title="Multilingual Climate Chatbot")

# Now configure torch after environment setup
import torch
torch.set_num_threads(1)
if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True

# Prevent torch path issues with Streamlit's file watcher
torch.utils.data._utils.MP_STATUS_CHECK_INTERVAL = 0

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import after environment setup
from src.utils.env_loader import load_environment
from src.main_nova import MultilingualClimateChatbot

# Load environment variables before initializing chatbot
load_environment()

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
            
        loop.set_debug(False)  # Disable debug to reduce overhead
        return loop
    except Exception as e:
        st.error(f"Failed to create event loop: {str(e)}")
        raise

def run_async(coro):
    """Helper function to run coroutines in a dedicated event loop"""
    loop = None
    try:
        loop = create_event_loop()
        
        # Run in executor to prevent blocking
        with ThreadPoolExecutor() as pool:
            future = pool.submit(lambda: loop.run_until_complete(coro))
            return future.result()
    except Exception as e:
        st.error(f"Async execution error: {str(e)}")
        raise
    finally:
        if loop and not loop.is_closed():
            try:
                # Clean up any remaining tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Use a timeout to prevent hanging
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
    try:
        # First attempt - try to initialize with full functionality
        chatbot = MultilingualClimateChatbot(
            index_name="climate-change-adaptation-index-10-24-prod"
        )
        return chatbot
    except Exception as e:
        st.error(f"Failed to initialize chatbot: {str(e)}")
        
        # Check if the error is related to git not being found
        if "[Errno 2] No such file or directory: 'git'" in str(e):
            st.warning("Git not found in Azure environment. Attempting to initialize with limited functionality.")
            try:
                # Try to modify environment to handle missing git
                os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
                os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
                
                # Retry initialization
                chatbot = MultilingualClimateChatbot(
                    index_name="climate-change-adaptation-index-10-24-prod"
                )
                return chatbot
            except Exception as retry_error:
                st.error(f"Second initialization attempt failed: {str(retry_error)}")
                return None
        return None

# Update asset paths using Path for cross-platform compatibility
ASSETS_DIR = Path(__file__).parent / "assets"
TREE_ICON = str(ASSETS_DIR / "tree.ico")
CCC_ICON = str(ASSETS_DIR / "CCCicon.png")

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
    st.markdown("### Sources")

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
            if st.button(f"📄 {title[:100]}...", key=unique_key):
                st.session_state.selected_source = f"{base_idx}_{title}"

            # Show details if selected
            if st.session_state.get('selected_source') == f"{base_idx}_{title}":
                with st.expander("Source Details", expanded=True):
                    if title:
                        st.markdown(f"**Title:** {title}")
                    if source.get('url'):
                        st.markdown(f"**URL:** [{source['url']}]({source['url']})")
                    if source.get('snippet'):
                        st.markdown("**Cited Content:**")
                        st.markdown(source['snippet'])
                    if source.get('content'):
                        st.markdown("**Full Content:**")
                        st.markdown(source['content'][:500] + '...' if len(source['content']) > 500 else source['content'])

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

def is_rtl_language(language_code):
        return language_code in {'fa', 'ar', 'he'}

def display_chat_messages():
    """Display chat messages in a custom format."""
    for i, message in enumerate(st.session_state.chat_history):
        if message['role'] == 'user':
            st.chat_message("user").markdown(message['content'])
        else:
            assistant_message = st.chat_message("assistant")

            language_code = message.get('language_code', 'en')
            text_align = 'right' if is_rtl_language(language_code) else 'left'
            direction = 'rtl' if is_rtl_language(language_code) else 'ltr'

            # Display the response without markdown header formatting
            assistant_message.markdown(
                f"""<div style="direction: {direction}; text-align: {text_align}">
                {message['content']}
                </div>""",
                unsafe_allow_html=True
            )
            
            if message.get('citations'):
                display_source_citations(message['citations'], base_idx=i)

def load_custom_css():
    st.markdown("""
    <style>
    /* Previous CSS styles remain the same */

    /* Add styles for the download button */
    .download-button {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        background-color: #4CAF50;
        color: white;
        border-radius: 4px;
        text-decoration: none;
        margin-left: 10px;
    }
    .download-button:hover {
        background-color: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)

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

def display_chat_history_section():
    """Display chat history with download button."""
    if st.session_state.chat_history:
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown("### Chat History")
        with col2:
            # Create download button for chat history
            chat_history_text = generate_chat_history_text()
            st.download_button(
                label="📥",
                data=chat_history_text,
                file_name="chat_history.txt",
                mime="text/plain",
                help="Download chat history"
            )

        messages = st.session_state.chat_history
        for idx in range(0, len(messages), 2):
            if messages[idx]['role'] == 'user':
                q = messages[idx]['content']
                if idx + 1 < len(messages) and messages[idx + 1]['role'] == 'assistant':
                    r = messages[idx + 1]['content']
                else:
                    r = ''
                with st.expander(f"Q: {q[:50]}...", expanded=False):
                    st.write("**Question:**")
                    st.write(q)
                    st.write("**Response:**")
                    st.write(r)

def main():
    load_custom_css()

    # Initialize session state
    if 'selected_source' not in st.session_state:
        st.session_state.selected_source = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'has_asked_question' not in st.session_state:
        st.session_state.has_asked_question = False
    if 'language_confirmed' not in st.session_state:
        st.session_state.language_confirmed = False
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = 'english'
    if 'event_loop' not in st.session_state:
        st.session_state.event_loop = create_event_loop()

    try:
        chatbot = init_chatbot()

        if chatbot is None:
            st.error("Failed to initialize chatbot. Please check your configuration.")
            st.info("Make sure all required API keys are properly configured in your environment")
            return

        # Sidebar
        with st.sidebar:
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

            if not st.session_state.language_confirmed:
                if st.button("Confirm"):
                    st.session_state.language_confirmed = True
                    st.session_state.selected_language = selected_language
            else:
                st.session_state.selected_language = selected_language

            # Display About section or Chat History
            if not st.session_state.has_asked_question:
                st.markdown("## About")
                st.markdown('''
                    The purpose of this app is to educate individuals about climate change and foster a community of informed citizens. It provides accurate information and resources about climate change and its impacts, and encourages users to take action in their own communities.
                ''')
            else:
                st.markdown("---")
                display_chat_history_section()

            # Footer
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="footer">', unsafe_allow_html=True)
            st.markdown('<div>Made by:</div>', unsafe_allow_html=True)
            st.image(TREE_ICON, width=40)
            st.markdown('<div style="font-size: 18px;">Climate Resilient Communities</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Main content
        col1, col2 = st.columns([1, 8])
        with col1:
            st.image(CCC_ICON, width=80)
        with col2:
            st.title("Multilingual Climate Chatbot")
            st.write("Ask me anything about climate change!")

        # Display chat messages
        display_chat_messages()

        if st.session_state.language_confirmed:
            query = st.chat_input("Ask Climate Change Bot")
        else:
            st.info("Please select your language and click Confirm to start chatting.")
            query = None

        if query and chatbot:
            # Handle user input and generate response
            st.session_state.chat_history.append({'role': 'user', 'content': query})
            st.session_state.has_asked_question = True
            st.chat_message("user").markdown(query)

            response_placeholder = st.chat_message("assistant")
            typing_message = response_placeholder.empty()
            typing_message.markdown("_Assistant is thinking..._")
            
            try:
                # Process query
                result = run_async(chatbot.process_query(
                    query=query, 
                    language_name=st.session_state.selected_language
                ))
                
                typing_message.empty()
                
                if result and result.get('success', False):
                    # Update response without header formatting
                    final_response = {
                        'role': 'assistant',
                        'language_code': result.get('language_code', 'en'),
                        'content': result['response'],
                        'citations': result.get('citations', [])
                    }
                    st.session_state.chat_history.append(final_response)
                    
                    # Display final response without markdown header formatting
                    language_code = final_response['language_code']
                    text_align = 'right' if is_rtl_language(language_code) else 'left'
                    direction = 'rtl' if is_rtl_language(language_code) else 'ltr'
                    
                    response_placeholder.markdown(
                        f"""<div style="direction: {direction}; text-align: {text_align}">
                        {final_response['content']}
                        </div>""",
                        unsafe_allow_html=True
                    )
                    
                    # Display citations if available
                    if result.get('citations'):
                        message_idx = len(st.session_state.chat_history) - 1
                        display_source_citations(result['citations'], base_idx=message_idx)
                else:
                    st.error(result.get('message', 'An error occurred'))
            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
        elif chatbot:
            # Clean up resources when chat session ends
            run_async(chatbot.cleanup())
    except Exception as e:
        st.error(f"Error initializing chatbot: {str(e)}")
        st.info("Make sure the .env file exists in the project root directory")

if __name__ == "__main__":
    main()