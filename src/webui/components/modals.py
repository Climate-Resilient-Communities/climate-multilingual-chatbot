import streamlit as st


def show_consent_dialog() -> None:
    """Consent modal shown as a compatibility overlay that works across Streamlit versions."""
    # Try using st.dialog if available (Streamlit 1.30+)
    dlg = getattr(st, "dialog", None)
    if callable(dlg):
        with dlg(" ", width="large"):
            _render_consent_content()
    else:
        # Fallback: create a modal-like overlay with CSS
        st.markdown(
            """
            <style>
            .consent-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.7);
                z-index: 9999;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .consent-modal-content {
                background: #FFF7E1;
                border-radius: 12px;
                padding: 18px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }
            .consent-title { 
                color: #009376 !important; 
                font-size: 28px !important; 
                font-weight: 700 !important; 
                margin: 0 !important; 
                text-align: center;
            }
            .consent-subtitle {
                color: #666;
                margin: 6px 0 20px 0;
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        # Render the modal content inline with the overlay styling
        st.markdown('<div class="consent-modal-overlay">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown('<div class="consent-modal-content">', unsafe_allow_html=True)
            _render_consent_content()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def _render_consent_content():
    """Render the actual consent form content."""
    st.markdown(
        """
        <div style="text-align:center; margin-bottom: 8px;">
            <h2 class="consent-title">MLCC Climate Chatbot</h2>
            <p class="consent-subtitle">Connecting Toronto Communities to Climate Knowledge</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        "Welcome! This app shares clear info on climate impacts and local action. Please confirm you're good with the basics below."
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

    if st.button("Start Chatting Now", disabled=not agreed, type="primary", use_container_width=True):
        st.session_state.consent_given = True
        st.rerun()


def render_faq_modal() -> None:
    """Render the FAQ popup modal UI and stop after showing it."""
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
        @media (max-width: 768px) {
            div[data-testid="column"]:has(.faq-popup-marker) { padding: 12px !important; max-height: 85vh !important; }
            div[data-testid="column"]:has(.faq-popup-marker) h1 { font-size: 1.2rem !important; margin-bottom: 8px !important; }
            div[data-testid="column"]:has(.faq-popup-marker) h2 { font-size: 1.05rem !important; margin: 12px 0 6px 0 !important; }
            div[data-testid="column"]:has(.faq-popup-marker) h3 { font-size: 0.95rem !important; margin: 8px 0 4px 0 !important; }
            div[data-testid="column"]:has(.faq-popup-marker) p,
            div[data-testid="column"]:has(.faq-popup-marker) div,
            div[data-testid="column"]:has(.faq-popup-marker) li { font-size: 0.9rem !important; line-height: 1.4 !important; }
            div[data-testid="column"]:has(.faq-popup-marker) .stExpander > div > div > div { font-size: 0.9rem !important; }
            div[data-testid="column"]:has(.faq-popup-marker) [data-testid="stMarkdownContainer"] { font-size: 0.9rem !important; }
        }
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


def render_language_confirmation_banner() -> None:
    """Show the green language confirmation guidance banner."""
    st.markdown(
        """
        <div style="margin-top: 10px; margin-bottom: 30px; background-color: #009376; padding: 10px; border-radius: 5px; color: white; text-align: center;">Please select your language and click Confirm to start chatting.</div>
        """,
        unsafe_allow_html=True,
    )
