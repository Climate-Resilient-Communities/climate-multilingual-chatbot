def display_consent_form():
    """Display the consent form as a modal overlay with cream-colored box."""
    
    # Create the modal overlay styling
    st.markdown(
        """
        <style>
        /* Hide main content padding temporarily */
        .main .block-container { 
            padding-top: 0 !important; 
            margin-top: 0 !important; 
        }
        
        /* Dark backdrop overlay that covers entire screen */
        .consent-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.65);
            z-index: 9999;
            pointer-events: none; /* Allow clicks to pass through backdrop */
        }
        
        /* Modal container - the cream colored box */
        .consent-modal {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: min(900px, 90vw);
            max-height: 85vh;
            background-color: #FFF7E1; /* Cream color */
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            overflow-y: auto;
        }
        
        /* Modal header styling */
        .consent-modal-header {
            text-align: center;
            padding-bottom: 20px;
            margin-bottom: 25px;
            border-bottom: 2px solid #f0e5d3;
        }
        
        .consent-modal-header h1 {
            margin: 0;
            color: #009376;
            font-size: 36px;
            font-weight: bold;
        }
        
        .consent-modal-header h3 {
            margin: 10px 0 0 0;
            color: #666;
            font-size: 18px;
            font-weight: normal;
        }
        
        /* Welcome message */
        .consent-welcome {
            text-align: center;
            margin-bottom: 30px;
            font-size: 16px;
            color: #444;
            padding: 0 20px;
        }
        
        /* Checkbox container */
        .consent-checkbox-container {
            background: rgba(255, 255, 255, 0.7);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }
        
        /* Bullet points */
        .consent-requirements {
            margin: 15px 0;
            font-size: 15px;
            color: #333;
        }
        
        .consent-requirements li {
            margin-bottom: 8px;
        }
        
        /* Policy buttons row */
        .consent-policies {
            margin: 20px 0;
        }
        
        /* Start button container */
        .consent-button-container {
            text-align: center;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid #f0e5d3;
        }
        
        /* Warning message */
        .consent-warning {
            text-align: center;
            margin-top: 15px;
            color: #d8000c;
            background-color: #ffbaba;
            padding: 10px;
            border-radius: 5px;
        }
        
        /* Ensure the modal content is properly contained */
        .consent-modal .stButton > button {
            background-color: #009376;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 12px 30px;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 250px;
        }
        
        .consent-modal .stButton > button:hover:not(:disabled) {
            background-color: #007e65;
            transform: translateY(-2px);
        }
        
        .consent-modal .stButton > button:disabled {
            background-color: #cccccc !important;
            color: #666666 !important;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Hide scrollbar but keep functionality */
        .consent-modal::-webkit-scrollbar {
            width: 8px;
        }
        
        .consent-modal::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .consent-modal::-webkit-scrollbar-thumb {
            background: rgba(0, 147, 118, 0.3);
            border-radius: 4px;
        }
        
        .consent-modal::-webkit-scrollbar-thumb:hover {
            background: rgba(0, 147, 118, 0.5);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Create the backdrop
    st.markdown('<div class="consent-backdrop"></div>', unsafe_allow_html=True)
    
    # Create the modal container
    st.markdown('<div class="consent-modal">', unsafe_allow_html=True)
    
    # Use a container to group all consent form elements
    with st.container():
        # Header
        st.markdown(
            """
            <div class="consent-modal-header">
                <h1>MLCC Climate Chatbot</h1>
                <h3>Connecting Toronto Communities to Climate Knowledge</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Welcome message
        st.markdown(
            """
            <div class="consent-welcome">
                Welcome! The purpose of this app is to educate people about climate change 
                and build a community of informed citizens. It provides clear, accurate info 
                on climate impacts and encourages local action.
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Main consent checkbox in a styled container
        st.markdown('<div class="consent-checkbox-container">', unsafe_allow_html=True)
        
        main_consent = st.checkbox(
            "**By checking this box, you agree to the following:**",
            value=st.session_state.get('main_consent', False),
            key="main_consent_checkbox",
            help="You must agree to continue"
        )
        st.session_state.main_consent = main_consent
        
        # Requirements list
        st.markdown(
            """
            <ul class="consent-requirements">
                <li>I certify that I meet the age requirements <em>(13+ or with parental/guardian consent if under 18)</em></li>
                <li>I have read and agreed to the Privacy Policy</li>
                <li>I have read and agreed to the Terms of Use</li>
                <li>I have read and understood the Disclaimer</li>
            </ul>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Policy expanders in a row
        st.markdown('<div class="consent-policies">', unsafe_allow_html=True)
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Start button container
        st.markdown('<div class="consent-button-container">', unsafe_allow_html=True)
        
        # Center the button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Start Chatting Now",
                disabled=not st.session_state.get('main_consent', False),
                use_container_width=True,
                type="primary"
            ):
                st.session_state.consent_given = True
                st.rerun()
        
        # Warning message if not consented
        if not st.session_state.get('main_consent', False):
            st.markdown(
                """
                <div class="consent-warning">
                    ⚠️ Please check the box above to continue
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Close the modal container
    st.markdown('</div>', unsafe_allow_html=True)
