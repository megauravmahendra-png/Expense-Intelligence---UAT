def login_page():
    """Beautiful login page"""
    
    # Custom CSS for login page
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 50px auto;
        padding: 50px 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .login-title {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        color: white;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .login-subtitle {
        text-align: center;
        color: rgba(255,255,255,0.9);
        margin-bottom: 40px;
        font-size: 1rem;
    }
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.2);
        border: 2px solid rgba(255,255,255,0.3);
        border-radius: 12px;
        color: white;
        font-size: 1rem;
        padding: 12px 16px;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(255,255,255,0.8);
        box-shadow: 0 0 0 3px rgba(255,255,255,0.1);
    }
    .stTextInput > label {
        color: white !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .login-button > button {
        width: 100%;
        background: white;
        color: #667eea;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 14px;
        border-radius: 12px;
        border: none;
        margin-top: 20px;
        transition: all 0.3s;
    }
    .login-button > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    .creator-text {
        text-align: center;
        color: rgba(255,255,255,0.8);
        margin-top: 30px;
        font-size: 0.9rem;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">💳 Expense Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Designed for awareness, not anxiety</div>', unsafe_allow_html=True)
        
        # Create a form to handle Enter key behavior
        with st.form(key="login_form"):
            username = st.text_input("Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            
            st.markdown('<div class="login-button">', unsafe_allow_html=True)
            login_btn = st.form_submit_button("🔐 Login", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if login_btn:
            if username and password:
                credentials = load_credentials()
                
                if credentials is not None:
                    # Check credentials
                    user_match = credentials[
                        (credentials['User Name'].str.strip() == username.strip()) & 
                        (credentials['Password'].astype(str).str.strip() == password.strip())
                    ]
                    
                    if not user_match.empty:
                        # Get the Google Drive link for this user
                        drive_link = user_match.iloc[0].get('Google Drive Data Link', '')
                        
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['user_drive_link'] = str(drive_link).strip() if pd.notna(drive_link) else ''
                        st.rerun()
                    else:
                        st.error("❌ Incorrect username or password")
            else:
                st.warning("⚠️ Please enter both username and password")
        
        st.markdown('<div class="creator-text">Created by Gaurav Mahendra</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
