from pathlib import Path
import streamlit as st
from src.webui.utils.helpers import get_base64_image


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_css_files() -> None:
    base_dir = Path(__file__).resolve().parent
    main_css = base_dir / "main.css"
    mobile_css = base_dir / "mobile.css"

    css_chunks: list[str] = []
    for p in (main_css, mobile_css):
        if p.exists():
            css_text = _read_text(p).strip()
            if css_text:
                css_chunks.append(css_text)

    if not css_chunks:
        return

    st.markdown(
        """
        <style>
        %s
        </style>
        """
        % ("\n\n".join(css_chunks)),
        unsafe_allow_html=True,
    )


def load_custom_css():
    """SIMPLIFIED CSS - removed problematic JavaScript and complex theme detection"""
    from src.webui.assets import WALLPAPER
    
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
    [data-testid="stChatMessage"] h4, [data-testid="stChatMessage"] h5, [data-testid="stChatMessage"] h6 {font-size: 1.0rem !important;}
    [data-testid="stChatMessage"] p {font-size: 16px !important; line-height: 1.6 !important;}
    [data-testid="stChatMessage"] ul, [data-testid="stChatMessage"] ol {font-size: 16px !important; line-height: 1.6 !important;}
    [data-testid="stChatMessage"] strong {font-weight: 600 !important;}
    
    .message-title {
        font-size: 16px !important;
        color: #333333 !important;
        margin-bottom: 8px !important;
        padding: 0 !important;
        font-weight: 600 !important;
    }
    
    /* Hide Streamlit default widgets + fix language selectbox */
    section[data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #cccccc !important;
    }
    
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: #000000 !important;
    }
    
    section[data-testid="stSidebar"] div[data-baseweb="select"] input {
        color: #000000 !important;
        background-color: #ffffff !important;
    }
    
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: #000000 !important;
    }
    
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
    
    /* Citations/sources section */
    .sources-section {
        margin: 20px 0;
        border-radius: 8px;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 20px;
    }
    
    .sources-heading {
        font-size: 18px;
        font-weight: 600;
        color: #333;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #009376;
    }
    
    /* Style source buttons with smaller size and subtle appearance */
    .sources-section .stButton > button {
        background-color: #ffffff !important;
        color: #495057 !important;
        border: 1px solid #ced4da !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin: 4px 0 !important;
        width: 100% !important;
        text-align: left !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
    }
    
    .sources-section .stButton > button:hover {
        background-color: #f8f9fa !important;
        border-color: #009376 !important;
        transform: none !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
    }
    
    .sources-section .stButton > button:active {
        background-color: #e9ecef !important;
        transform: translateY(1px) !important;
    }
    
    /* Expander in sources */
    .sources-section .streamlit-expanderHeader {
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 6px;
    }
    
    .sources-section .streamlit-expanderContent {
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-top: none;
        padding: 15px;
    }
    
    /* Chat input */
    .stChatInput > div > div > div > div {
        background-color: white;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
    }
    
    .stChatInput > div > div > div > div:focus-within {
        border-color: #009376;
        box-shadow: 0 0 0 1px #009376;
    }
    
    /* Success messages for green banner */
    .stAlert[data-baseweb="notification"] {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)


def load_mobile_css() -> None:
    """Mobile-specific CSS."""
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        /* Hide "Made by" text on mobile to save space */
        .mlcc-header.desktop {
            display: none !important;
        }
        .mlcc-header.mobile {
            display: block !important;
        }
        
        /* Add mobile-specific avatar hiding in chat */
        [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
        [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
            display: none !important;
        }
        
        /* Hide grey avatar boxes on mobile */
        [data-testid="stChatMessage"] > div:first-child {
            display: none !important;
        }
        [data-testid="stChatMessage"] {
            padding-left: 0 !important;
        }
        
        /* Style headers in FAQ popup for mobile */
        div[data-testid="column"]:has(.faq-popup-marker) h1 {
            font-size: 20px !important;
        }
        div[data-testid="column"]:has(.faq-popup-marker) h2 {
            font-size: 18px !important;
        }
        div[data-testid="column"]:has(.faq-popup-marker) h3 {
            font-size: 16px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def load_responsive_css():
    """Responsive layout CSS."""
    st.markdown("""
    <style>
    /* Desktop header styles */
    .mlcc-header.desktop {
        display: block;
    }
    .mlcc-header.mobile {
        display: none;
    }
    
    /* Mobile responsive styles */
    @media (max-width: 768px) {
        .mlcc-header.desktop {
            display: none !important;
        }
        .mlcc-header.mobile {
            display: block !important;
            text-align: center;
            margin: 10px 0;
            padding: 8px 12px;
        }
        
        /* Mobile header layout - use flexbox for better control */
        .mobile-header-container {
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 8px 12px !important;
            margin: 0 !important;
            min-height: 56px !important;
        }
        
        /* Language selector in mobile header */
        .mobile-header-container .stSelectbox {
            flex: 0 0 auto !important;
            min-width: 120px !important;
            max-width: 140px !important;
        }
        
        /* FAQ button positioning with fixed position for safety */
        #mobile-faq-wrap {
            position: fixed !important;
            top: env(safe-area-inset-top, 16px) !important;
            right: 16px !important;
            z-index: 1000 !important;
            pointer-events: auto !important;
        }
        
        /* Fallback for very small screens */
        @media (max-width: 400px) {
            #mobile-faq-wrap {
                right: 8px !important;
                top: calc(env(safe-area-inset-top, 8px) + 8px) !important;
            }
        }
        
        /* Remove default margins on mobile */
        .main .block-container {
            padding-top: 8px !important;
            padding-left: 12px !important;
            padding-right: 12px !important;
        }
        
        /* Adjust chat container spacing */
        .stChatInput {
            margin-top: 16px !important;
            margin-bottom: 16px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


