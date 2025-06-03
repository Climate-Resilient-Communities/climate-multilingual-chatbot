# Configure environment first
import os
import sys
import logging
from pathlib import Path

# Suppress the StreamlitAPIWarning about missing ScriptRunContext
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Initialize event loop properly at the very beginning
import asyncio
try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Set environment variables for Streamlit
# scrap the old key
os.environ.pop("STREAMLIT_WATCHER_TYPE", None)   
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
os.environ["HF_HOME"] = os.environ.get("TEMP", "/tmp") + "/huggingface"  # Replace deprecated TRANSFORMERS_CACHE

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

# Update asset paths using Path for cross-platform compatibility
ASSETS_DIR = Path(__file__).parent / "assets"
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

# Load favicon
favicon = None
if TREE_ICON and Path(TREE_ICON).exists():
    try:
        import base64
        with open(TREE_ICON, "rb") as f:
            favicon_data = base64.b64encode(f.read()).decode()
            # Create a data URL for the favicon
            favicon = f"data:image/x-icon;base64,{favicon_data}"
    except Exception as e:
        logger.warning(f"Could not load favicon: {e}")
        favicon = "🌳"  # Fallback to emoji
else:
    favicon = "🌳"  # Default emoji if no icon file

# Must be the first Streamlit command
import streamlit as st
st.set_page_config(
    layout="wide", 
    page_title="Multilingual Climate Chatbot",
    page_icon=favicon  # This sets the favicon
)

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
    """Initialize the chatbot with proper error handling."""
    try:
        # Use a valid Pinecone index name or one that actually exists in your environment
        # For local development, using a production index is recommended
        index_name = os.environ.get("PINECONE_INDEX_NAME", "climate-change-adaptation-index-10-24-prod")
        
        chatbot = MultilingualClimateChatbot(index_name)
        return {"success": True, "chatbot": chatbot, "error": None}
    except Exception as e:
        error_message = str(e)
        # Check if the error is specifically related to climatebert_tokenizer
        if "climatebert_tokenizer" in error_message:
            return {
                "success": False,
                "chatbot": None,
                "error": f"Failed to initialize chatbot: 'MultilingualClimateChatbot' object has no attribute 'climatebert_tokenizer'"
            }
        # For other errors, provide a more general message
        elif "404" in error_message and "Resource" in error_message and "not found" in error_message:
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
def clean_html_content(content):
    """Clean content from stray HTML tags that might break rendering."""
    import re
    
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

def display_chat_messages():
    """Display chat messages in a custom format."""
    # Add CSS to control heading sizes inside chat messages
    st.markdown(
        """
        <style>
        /* Shrink headings that appear *inside* any chat message */
        [data-testid="stChatMessage"] h1     {font-size: 1.50rem !important;}  /* ≈24 px */
        [data-testid="stChatMessage"] h2     {font-size: 1.25rem !important;}  /* ≈20 px */
        [data-testid="stChatMessage"] h3     {font-size: 1.10rem !important;}  /* ≈18 px */
        [data-testid="stChatMessage"] h4,
        [data-testid="stChatMessage"] h5,
        [data-testid="stChatMessage"] h6     {font-size: 1rem    !important;}  /* ≈16 px */
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    for i, message in enumerate(st.session_state.chat_history):
        if message['role'] == 'user':
            st.chat_message("user").markdown(message['content'])
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

def load_custom_css():
    # Get wallpaper CSS if available
    wallpaper_css = ""
    wallpaper_base64 = None
    if WALLPAPER and Path(WALLPAPER).exists():
        wallpaper_base64 = get_base64_image(WALLPAPER)
    
    # Theme detection and application
    st.markdown("""
    <script>
    (function() {
        // Detect theme from multiple sources
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const hasDarkReader = document.documentElement.getAttribute('data-darkreader-mode') !== null;
        const hasExtension = hasDarkReader || document.documentElement.classList.contains('night-eye-active');
        
        // Apply theme
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-has-extension', hasExtension ? 'true' : 'false');
        
        // Listen for theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
        });
        
        // Prevent flash of unstyled content
        document.documentElement.style.visibility = 'hidden';
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                document.documentElement.style.visibility = 'visible';
            }, 100);
        });
    })();
    </script>
    """, unsafe_allow_html=True)
    
    # Hide Streamlit header
    hide_streamlit_header = """
    <style>
        header[data-testid="stHeader"] {
            display: none;
        }
        .stToolbar {
            display: none;
        }
        button[kind="header"] {
            display: none;
        }
    </style>
    """
    st.markdown(hide_streamlit_header, unsafe_allow_html=True)
    
    # Wallpaper CSS - separate implementation for better rendering
    if wallpaper_base64:
        st.markdown(f"""
        <style>
        /* Make sure the stApp background is transparent to show wallpaper */
        html, body {{
            background-color: var(--background-secondary);
        }}

        .stApp {{
            background-color: transparent !important;  /* This is important! */
            position: relative;
        }}

        /* Wallpaper layer */
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
            opacity: var(--wallpaper-opacity);
            pointer-events: none;
            z-index: -1;  /* Changed from 0 to -1 to ensure it's behind */
        }}

        /* Main container needs relative positioning */
        .main {{
            position: relative;
            z-index: 1;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Main CSS with theme variables
    st.markdown(f"""
    <style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&family=Open+Sans:wght@300;400;600;700&display=swap');
    
    /* Font families */
    :root {{
        --primary-font: 'Rocca Two', Merriweather, serif;
        --secondary-font: 'Poppins', 'Open Sans', sans-serif;
    }}
    
    /* Light theme colors (your current colors - unchanged) */
    :root {{
        --primary-color: #009376;
        --primary-hover: #007e65;
        --background-primary: #ffffff;
        --background-secondary: #f8fafa;
        --background-chat: #ffffff;
        --background-user-message: #DCF8C6;
        --background-consent: rgba(255, 255, 255, 0.95);
        --text-primary: #333333;
        --text-secondary: #666666;
        --text-on-primary: #ffffff;
        --border-color: #e0e0e0;
        --shadow-light: rgba(0, 0, 0, 0.05);
        --shadow-medium: rgba(0, 0, 0, 0.1);
        --shadow-heavy: rgba(0, 0, 0, 0.3);
        --overlay-color: rgba(0, 0, 0, 0.7);
        --button-disabled-bg: #cccccc;
        --button-disabled-text: #666666;
        --warning-bg: #fff3cd;
        --warning-text: #856404;
        --warning-border: #ffeeba;
        --success-bg: #d4edda;
        --success-text: #155724;
        --footer-border: #eeeeee;
        --expander-bg: #f9f9f9;
        --wallpaper-opacity: 0.15;
    }}
    
    /* Dark theme colors */
    [data-theme="dark"] {{
        --primary-color: #00c896;
        --primary-hover: #00b384;
        --background-primary: #1a1a1a;
        --background-secondary: #242424;
        --background-chat: #2d2d2d;
        --background-user-message: #1a4d1a;
        --background-consent: rgba(42, 42, 42, 0.95);
        --text-primary: #e8e8e8;
        --text-secondary: #b0b0b0;
        --text-on-primary: #ffffff;
        --border-color: #3a3a3a;
        --shadow-light: rgba(0, 0, 0, 0.2);
        --shadow-medium: rgba(0, 0, 0, 0.4);
        --shadow-heavy: rgba(0, 0, 0, 0.6);
        --overlay-color: rgba(0, 0, 0, 0.85);
        --button-disabled-bg: #4a4a4a;
        --button-disabled-text: #888888;
        --warning-bg: #523d0f;
        --warning-text: #fff3cd;
        --warning-border: #6b5810;
        --success-bg: #1e4620;
        --success-text: #a3d9a5;
        --footer-border: #333333;
        --expander-bg: #2a2a2a;
        --wallpaper-opacity: 0.05;
    }}
    
    /* Smooth transitions */
    * {{
        transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
    }}
    
    /* Prevent transition flash on load */
    html[style*="visibility: hidden"] * {{
        transition: none !important;
    }}
    
    /* Apply fonts */
    body {{
        font-family: var(--secondary-font);
        color: var(--text-primary);
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--primary-font);
        color: var(--primary-color);
    }}
    
    /* Remove padding */
    .main .block-container {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] > div {{
        padding-top: 0 !important;
    }}
    
    section[data-testid="stSidebar"] .element-container:first-child {{
        display: none;
    }}
    
    /* Button styling with theme support */
    .stButton > button {{
        background-color: var(--primary-color);
        color: var(--text-on-primary);
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px var(--shadow-medium);
        font-family: var(--secondary-font);
    }}
    
    .stButton > button:hover:not(:disabled) {{
        background-color: var(--primary-hover);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px var(--shadow-medium);
    }}
    
    .stButton > button:active:not(:disabled) {{
        transform: translateY(0px);
    }}
    
    .stButton > button:disabled {{
        background-color: var(--button-disabled-bg) !important;
        color: var(--button-disabled-text) !important;
        cursor: not-allowed;
        box-shadow: none;
        opacity: 1;
    }}
    
    /* Download button */
    .download-button {{
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        background-color: var(--primary-color);
        color: var(--text-on-primary);
        border-radius: 4px;
        text-decoration: none;
        margin-left: 10px;
        box-shadow: 0 2px 5px var(--shadow-medium);
        transition: all 0.3s ease;
        font-family: var(--secondary-font);
    }}
    
    .download-button:hover {{
        background-color: var(--primary-hover);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px var(--shadow-medium);
    }}
    
    /* Consent form container */
    .consent-form-container {{
        background-color: var(--background-consent);
        color: var(--text-primary);
        padding: 40px;
        margin: 20px auto;
        max-width: 800px;
        font-family: var(--secondary-font);
        border-radius: 10px;
        box-shadow: 0 4px 6px var(--shadow-light);
    }}
    
    /* Checkbox styling */
    .consent-checkbox label {{
        font-weight: bold;
        font-size: 16px;
        color: var(--primary-color);
        font-family: var(--secondary-font);
    }}
    
    /* Expander styling */
    .streamlit-expanderHeader {{
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-color);
        font-family: var(--primary-font);
    }}
    
    [data-testid="stExpander"] > div:last-child {{
        max-height: 400px;
        overflow-y: auto;
        font-family: var(--secondary-font);
    }}
    
    /* Sidebar content */
    .sidebar-content {{
        background-color: var(--background-primary);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px var(--shadow-light);
        font-family: var(--secondary-font);
    }}
    
    .sidebar-content h1 {{
        color: var(--primary-color);
        font-size: 24px;
        margin-bottom: 20px;
        font-family: var(--primary-font);
    }}
    
    .sidebar-content h2 {{
        color: var(--primary-color);
        font-size: 20px;
        margin-top: 30px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--border-color);
        font-family: var(--primary-font);
    }}
    
    /* Features list */
    .features-benefits ul {{
        list-style-type: disc;
        color: var(--text-primary);
    }}
    
    .features-benefits li {{
        margin-bottom: 10px;
        font-size: 14px;
        line-height: 1.6;
        font-family: var(--secondary-font);
    }}
    
    .features-benefits {{
        font-size: 14px;
        line-height: 1.4;
        font-family: var(--secondary-font);
    }}
    
    /* Chat messages */
    [data-testid="stChatMessageContent"] {{
        background-color: var(--background-chat);
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 5px var(--shadow-light);
        font-family: var(--secondary-font);
    }}
    
    /* User message styling - more modern bubble style */
    [data-testid="stChatMessage"] [data-testid="stChatMessageContent"]:has(> div.user-message) {{
        background-color: var(--background-user-message) !important;
        border-radius: 18px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13);
    }}
    
    /* Bot message styling - more modern bubble style */
    [data-testid="stChatMessage"] [data-testid="stChatMessageContent"]:has(> div.bot-message) {{
        background-color: var(--background-chat) !important;
        border-radius: 18px !important;
        padding: 12px 16px !important;
        box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13);
    }}
    
    /* Chat input */
    .stChatInputContainer {{
        padding: 10px;
        background-color: var(--background-primary);
        border-radius: 20px;
        box-shadow: 0 2px 10px var(--shadow-light);
        font-family: var(--secondary-font);
    }}
    
    /* Source citations */
    [data-testid="stExpander"] {{
        background-color: var(--expander-bg);
        border-left: 3px solid var(--primary-color);
        padding: 10px;
        margin-top: 15px;
        border-radius: 5px;
    }}
    
    /* Footer */
    .footer {{
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid var(--footer-border);
        text-align: center;
        font-size: 14px;
        color: var(--text-secondary);
        font-family: var(--secondary-font);
    }}
    
    /* Warning/Alert styling */
    .stAlert, [data-baseweb="notification"] {{
        background-color: var(--warning-bg) !important;
        color: var(--warning-text) !important;
        border: 1px solid var(--warning-border) !important;
    }}
    
    /* FAQ popup */
    .faq-popup {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: var(--overlay-color);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }}
    
    .faq-popup-content {{
        background-color: var(--background-primary);
        color: var(--text-primary);
        padding: 30px;
        border-radius: 10px;
        width: 80%;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        position: relative;
        box-shadow: 0 5px 15px var(--shadow-heavy);
    }}
    
    .faq-close-btn {{
        position: absolute;
        top: 10px;
        right: 15px;
        font-size: 24px;
        cursor: pointer;
        background: none;
        border: none;
        color: var(--primary-color);
    }}
    
    /* Headings in chat messages */
    [data-testid="stChatMessage"] h1 {{font-size: 1.50rem !important;}}
    [data-testid="stChatMessage"] h2 {{font-size: 1.25rem !important;}}
    [data-testid="stChatMessage"] h3 {{font-size: 1.10rem !important;}}
    [data-testid="stChatMessage"] h4,
    [data-testid="stChatMessage"] h5,
    [data-testid="stChatMessage"] h6 {{font-size: 1rem !important;}}
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {{
        :root {{
            --primary-color: #00ff00;
            --border-color: currentColor;
        }}
    }}
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {{
        * {{
            transition: none !important;
            animation: none !important;
        }}
    }}
    
    /* Handle extension overrides gracefully */
    [data-has-extension="true"] {{
        /* Don't fight the extension, just ensure readability */
        --primary-color: #00c896;
    }}
    
    /* Ensure critical elements remain visible */
    .stButton > button,
    .consent-form-container,
    .stAlert {{
        isolation: isolate;
        contain: paint;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Additional favicon setting
    if TREE_ICON:
        st.markdown(f'''
            <link rel="icon" href="{TREE_ICON}" type="image/x-icon">
            <link rel="shortcut icon" href="{TREE_ICON}" type="image/x-icon">
        ''', unsafe_allow_html=True)

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
        st.markdown("### Chat History")
        
        # Create download button for chat history on its own line with full width
        chat_history_text = generate_chat_history_text()
        st.download_button(
            label="📥 Download Chat History",
            data=chat_history_text,
            file_name="chat_history.txt",
            mime="text/plain",
            help="Download chat history",
            use_container_width=True
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

def display_consent_form():
    """Display the consent form using Streamlit's native components."""
    # Move the form higher up with padding adjustments
    st.markdown("""
        <style>
        /* Custom padding to position the form higher on the page */
        .main .block-container {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Use columns to center the consent form but make it wider
    col1, col2, col3 = st.columns([1, 6, 1])  # Changed from [1, 4, 1] to make middle column even wider
    
    with col2:
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
            st.markdown("""
            <ul style="margin: 15px 0; font-size: 15px;">
                <li>I certify that I meet the age requirements <em>(13+ or with parental/guardian consent if under 18)</em></li>
                <li>I have read and agreed to the Privacy Policy</li>
                <li>I have read and agreed to the Terms of Use</li>
                <li>I have read and understood the Disclaimer</li>
            </ul>
            """, unsafe_allow_html=True)
            
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
                    """)
            
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
                    """)
            
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
                    """)
            
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

def main():
    # Initialize session state first
    if 'selected_source' not in st.session_state:
        st.session_state.selected_source = None
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
    
    # Load CSS
    load_custom_css()
    
    # Start chatbot initialization immediately (runs in background due to @st.cache_resource)
    if st.session_state.chatbot_init is None:
        # This will run in the background while the consent form is shown
        st.session_state.chatbot_init = init_chatbot()
    
    # Check consent status and display consent form if needed
    if not st.session_state.consent_given:
        display_consent_form()
    else:
        # Main app content (only shown after consent)
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

                # Add "How It Works" section in the sidebar (moved from main area)
                # FIXED: Using chat_history length instead of has_asked_question
                if len(st.session_state.chat_history) == 0:
                    # Remove the green banner from sidebar - it will only be in main content area
                    st.markdown("""
                    <div style="margin-top: 10px;">
                    <h3 style="color: #009376; font-size: 20px; margin-bottom: 10px;">How It Works</h3>
                    
                    <ul style="padding-left: 20px; margin-bottom: 20px; font-size: 14px;">
                        <li style="margin-bottom: 8px;"><b>Choose Language</b>: Select from 200+ options.</li>
                        <li style="margin-bottom: 8px;"><b>Ask Questions</b>: <i>"What are the local impacts of climate change in Toronto?"</i> or <i>"Why is summer so hot now in Toronto?"</i></li>
                        <li style="margin-bottom: 8px;"><b>Act</b>: Ask about actionable steps such as <i>"What can I do about flooding in Toronto?"</i> or <i>"How to reduce my carbon footprint?"</i> and receive links to local resources (e.g., city programs, community groups).</li>
                    </ul>
                    </div>
                    """, unsafe_allow_html=True)

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
                st.markdown('<div style="font-size: 18px;">Climate Resilient Communities</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Main content
            col1, col2 = st.columns([1, 8])
            with col1:
                if CCC_ICON:
                    st.image(CCC_ICON, width=80)
            with col2:
                st.title("Multilingual Climate Chatbot")
                st.write("Ask me anything about climate change!")

            # FAQ Popup Modal using Streamlit native components
            if st.session_state.show_faq_popup:
                # Create a full-screen overlay effect using CSS
                st.markdown("""
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
                </style>
                """, unsafe_allow_html=True)
                
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
                            st.write("""
                            Our chatbot uses Retrieval-Augmented Generation (RAG) technology to provide verified information exclusively 
                            from government reports, academic research, and established non-profit organizations' publications. Every 
                            response includes citations to original sources, allowing you to verify the information directly. The system 
                            matches your questions with relevant, verified information rather than generating content independently.
                            """)
                        
                        with st.expander("What sources does the chatbot use?", expanded=True):
                            st.write("""
                            All information comes from three verified source types: government climate reports, peer-reviewed academic 
                            research, and established non-profit organization publications. Each response includes citations linking 
                            directly to these sources.
                            """)
                    
                    st.markdown("---")
                    
                    # Privacy Protection Section
                    with st.container():
                        st.markdown("## 🔒 Privacy Protection")
                        
                        with st.expander("What information does the chatbot collect?", expanded=True):
                            st.write("We maintain a strict privacy-first approach:")
                            st.markdown("""
                            - No personal identifying information (PII) is collected
                            - Questions are automatically screened to remove any personal details
                            - Only anonymized questions are cached to improve service quality
                            - No user accounts or profiles are created
                            """)
                        
                        with st.expander("How is the cached data used?", expanded=True):
                            st.write("""
                            Cached questions, stripped of all identifying information, help us improve response accuracy and identify 
                            common climate information needs. We regularly delete cached questions after analysis.
                            """)
                    
                    st.markdown("---")
                    
                    # Trust & Transparency Section
                    with st.container():
                        st.markdown("## 🤝 Trust & Transparency")
                        
                        with st.expander("How can I trust this tool?", expanded=True):
                            st.write("Our commitment to trustworthy information rests on:")
                            st.markdown("""
                            - Citations for every piece of information, linking to authoritative sources
                            - Open-source code available for public review  
                            - Community co-design ensuring real-world relevance
                            - Regular updates based on user feedback and new research
                            """)
                        
                        with st.expander("How can I provide feedback or report issues?", expanded=True):
                            st.write("We welcome your input through:")
                            st.markdown("""
                            - The feedback button within the chat interface
                            - Our GitHub repository for technical contributions
                            - Community feedback sessions
                            """)
                            st.write("For technical support or to report issues, please visit our GitHub repository.")
                    
                    # Add some space at the bottom
                    st.markdown("<br><br>", unsafe_allow_html=True)
                
                # Stop rendering anything else while popup is shown
                st.stop()

            # Display chat messages
            display_chat_messages()

            if st.session_state.language_confirmed:
                query = st.chat_input("Ask Climate Change Bot")
                # Append user question immediately after input
                if query:
                    st.session_state.chat_history.append({'role': 'user', 'content': query})
                    # REMOVED: has_asked_question update - not needed anymore
            else:
                # Just show a language selection banner under the main title
                # No extra welcome message, just the green banner
                st.markdown("""
                <div style="margin-top: 10px; margin-bottom: 30px; background-color: #009376; padding: 10px; border-radius: 5px; color: white; text-align: center;">
                Please select your language and click Confirm to start chatting.
                </div>
                """, unsafe_allow_html=True)
                query = None

            # Check for needs_rerun flag first and reset it to prevent loops
            if st.session_state.get('needs_rerun', False):
                st.session_state.needs_rerun = False
                # Don't process any queries on this run, as we're just updating the UI
                pass
            elif query and chatbot:
                # User message is already added to chat history above
                # Display the user message
                st.chat_message("user").markdown(query)

                response_placeholder = st.chat_message("assistant")
                typing_message = response_placeholder.empty()
                typing_message.markdown("_Assistant is thinking..._")
                
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
                    # Process query with conversation history
                    result = run_async(chatbot.process_query(
                        query=query, 
                        language_name=st.session_state.selected_language,
                        conversation_history=conversation_history
                    ))
                    
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
                                import re
                                response_content = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', response_content)
                        
                        # Update response without header formatting
                        final_response = {
                            'role': 'assistant',
                            'language_code': result.get('language_code', 'en'),
                            'content': response_content,  # Use the cleaned content
                            'citations': result.get('citations', [])
                        }
                        st.session_state.chat_history.append(final_response)
                        
                        # Display final response without markdown header formatting
                        language_code = final_response['language_code']
                        text_align = 'right' if is_rtl_language(language_code) else 'left'
                        direction = 'rtl' if is_rtl_language(language_code) else 'ltr'
                        
                        content = clean_html_content(final_response['content'])

                        response_placeholder.markdown(
                            f"""<div style="direction: {direction}; text-align: {text_align}">
                            {content}
                            </div>""",
                            unsafe_allow_html=True
                        )
                        
                        # Display citations if available
                        if result.get('citations'):
                            message_idx = len(st.session_state.chat_history) - 1
                            display_source_citations(result['citations'], base_idx=message_idx)
                    else:
                        # FIXED: Handle off-topic questions and other errors more comprehensively
                        error_message = result.get('message', 'An error occurred')
                        
                        # Check if it's an off-topic message about climate change
                        if ("not about climate" in error_message.lower() or 
                            "climate change" in error_message.lower() or 
                            result.get('error_type') == "off_topic" or
                            (result.get('validation_result', {}).get('reason') == "not_climate_related")):
                            
                            # This is an off-topic climate question
                            off_topic_response = "Oops! Looks like your question isn't about climate change. But I'm here to help if you've got a climate topic in mind!"
                            
                            # Add the response to chat history
                            st.session_state.chat_history.append({
                                'role': 'assistant', 
                                'content': off_topic_response,
                                'language_code': 'en'
                            })
                            
                            # Display the off-topic message
                            response_placeholder.markdown(off_topic_response)
                        else:
                            # Handle other types of errors
                            st.session_state.chat_history.append({
                                'role': 'assistant', 
                                'content': error_message,
                                'language_code': 'en'
                            })
                            response_placeholder.error(error_message)
                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    st.session_state.chat_history.append({
                        'role': 'assistant', 
                        'content': error_msg,
                        'language_code': 'en'
                    })
                    response_placeholder.error(error_msg)
                
                # Set flag to rerun and update UI with new chat history
                st.session_state.needs_rerun = True
                st.rerun()
            
            # Don't run cleanup after every message - only when the app is closing
            # This would be handled by st.cache_resource's cleanup mechanism
            
        except Exception as e:
            st.error(f"Error initializing chatbot: {str(e)}")
            st.info("Make sure the .env file exists in the project root directory")

if __name__ == "__main__":
    main()