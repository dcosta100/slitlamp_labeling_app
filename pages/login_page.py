"""
Login page
"""

import streamlit as st
from utils.auth import authenticate_user
from utils.label_manager import LabelManager
from utils.session_logger import start_session

def show():
    """Show login page"""

    # Hide the sidebar. app.py already called st.set_page_config(), which may
    # only be called once per page, so the layout is set there and only the CSS
    # belongs here.
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<p class="main-header">🔬 Slitlamp Image Labeling</p>', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    success, role, message = authenticate_user(username, password)
                    
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = role

                        # Start the activity log for this session. The label
                        # count at login is the baseline used to work out how
                        # many labels the session actually produced.
                        st.session_state.labels_saved = 0
                        try:
                            labels_at_start = LabelManager(username).get_labeled_count()
                        except Exception:
                            labels_at_start = 0
                        start_session(st.session_state, username, labels_at_start)

                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown("---")
