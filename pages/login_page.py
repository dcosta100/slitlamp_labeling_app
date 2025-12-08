"""
Login page
"""

import streamlit as st
from utils.auth import authenticate_user

def show():
    """Show login page"""
    
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
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown("---")
        st.info("""
        **Default Admin Credentials:**
        - Username: `admin`
        - Password: `admin123`
        
        ⚠️ Please change the default password after first login!
        """)
