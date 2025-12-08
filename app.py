"""
Slitlamp Image Labeling Application
Main Streamlit application for medical image labeling
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from utils.auth import authenticate_user, initialize_session_state
from utils.data_loader import DataLoader
from pages import labeling_page, admin_page, login_page

# Page configuration
st.set_page_config(
    page_title="Slitlamp Image Labeling",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .label-section {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .warning-message {
        color: #ffc107;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    
    # Initialize session state
    initialize_session_state()
    
    # Check if user is logged in
    if not st.session_state.get('logged_in', False):
        login_page.show()
    else:
        # Sidebar navigation
        with st.sidebar:
            st.markdown("### 👤 User Information")
            st.write(f"**Username:** {st.session_state.username}")
            st.write(f"**Role:** {st.session_state.role}")
            st.markdown("---")
            
            # Navigation
            if st.session_state.role == "admin":
                page = st.radio(
                    "Navigation",
                    ["🏷️ Labeling", "📊 Admin Dashboard"],
                    key="navigation"
                )
            else:
                page = "🏷️ Labeling"
            
            st.markdown("---")
            
            # Dataset filter (admin only)
            if st.session_state.role == "admin":
                from config.config import DATASET_FILTER_OPTIONS, DEFAULT_DATASET_FILTER
                
                st.markdown("### 🔍 Dataset Filter")
                
                current_filter = st.session_state.get('dataset_filter', DEFAULT_DATASET_FILTER)
                
                filter_mode = st.selectbox(
                    "Show images with:",
                    options=list(DATASET_FILTER_OPTIONS.keys()),
                    index=list(DATASET_FILTER_OPTIONS.keys()).index(current_filter),
                    format_func=lambda x: DATASET_FILTER_OPTIONS[x],
                    key="filter_selector"
                )
                
                # If filter changed, update and reload
                if filter_mode != current_filter:
                    st.session_state.dataset_filter = filter_mode
                    # Force reload by deleting data_loader and route
                    if 'data_loader' in st.session_state:
                        del st.session_state.data_loader
                    if 'route_indices' in st.session_state:
                        del st.session_state.route_indices
                    if 'current_position' in st.session_state:
                        st.session_state.current_position = 0
                    st.rerun()
                
                st.caption(f"Current: {DATASET_FILTER_OPTIONS[filter_mode]}")
                st.markdown("---")
            
            # Logout button
            if st.button("🚪 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # Show selected page
        if page == "🏷️ Labeling":
            labeling_page.show()
        elif page == "📊 Admin Dashboard":
            admin_page.show()

if __name__ == "__main__":
    main()
