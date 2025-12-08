"""
Admin dashboard page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.auth import create_user, get_all_users
from utils.label_manager import LabelManager
from config.config import ROUTE_STRATEGIES

def show():
    """Show admin dashboard"""
    
    st.markdown('<p class="main-header">📊 Admin Dashboard</p>', unsafe_allow_html=True)
    
    # Tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["📈 Statistics", "👥 User Management", "🔍 Label Review"])
    
    with tab1:
        show_statistics()
    
    with tab2:
        show_user_management()
    
    with tab3:
        show_label_review()

def show_statistics():
    """Show labeling statistics"""
    
    st.markdown("## 📊 Labeling Progress Overview")
    
    # Get all user stats
    all_stats = LabelManager.get_all_user_stats()
    
    if not all_stats:
        st.info("No labeling data available yet.")
        return
    
    # Overall statistics
    col1, col2, col3, col4 = st.columns(4)
    
    total_labeled = sum(stats['statistics']['total'] for stats in all_stats.values())
    total_flagged = sum(stats['statistics']['flagged'] for stats in all_stats.values())
    total_not_usable = sum(stats['statistics']['not_usable'] for stats in all_stats.values())
    total_edited = sum(stats['statistics']['edited'] for stats in all_stats.values())
    
    with col1:
        st.metric("Total Labels", total_labeled)
    with col2:
        st.metric("Flagged", total_flagged)
    with col3:
        st.metric("Not Usable", total_not_usable)
    with col4:
        st.metric("Edited", total_edited)
    
    st.markdown("---")
    
    # Per-user statistics
    st.markdown("### 👥 Per-User Statistics")
    
    user_data = []
    for username, data in all_stats.items():
        stats = data['statistics']
        user_data.append({
            'Username': username,
            'Total Labels': stats['total'],
            'Flagged': stats['flagged'],
            'Not Usable': stats['not_usable'],
            'Edited': stats['edited'],
            'Last Modified': data['last_modified']
        })
    
    df_users = pd.DataFrame(user_data)
    st.dataframe(df_users, use_container_width=True)
    
    # Visualizations
    st.markdown("---")
    st.markdown("### 📊 Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Labels per user
        fig = px.bar(
            df_users,
            x='Username',
            y='Total Labels',
            title='Labels per User',
            color='Total Labels',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Quality metrics per user
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Flagged', x=df_users['Username'], y=df_users['Flagged']))
        fig.add_trace(go.Bar(name='Not Usable', x=df_users['Username'], y=df_users['Not Usable']))
        fig.add_trace(go.Bar(name='Edited', x=df_users['Username'], y=df_users['Edited']))
        fig.update_layout(title='Quality Metrics per User', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    # Diagnosis distribution
    st.markdown("---")
    st.markdown("### 🏥 Diagnosis Distribution (All Users)")
    
    all_diagnoses = {}
    for username, data in all_stats.items():
        by_diagnosis = data['statistics']['by_diagnosis']
        for diag, count in by_diagnosis.items():
            all_diagnoses[diag] = all_diagnoses.get(diag, 0) + count
    
    if all_diagnoses:
        df_diag = pd.DataFrame(list(all_diagnoses.items()), columns=['Diagnosis', 'Count'])
        df_diag = df_diag.sort_values('Count', ascending=False)
        
        fig = px.pie(
            df_diag,
            values='Count',
            names='Diagnosis',
            title='Distribution of Diagnoses'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Laterality distribution
    st.markdown("---")
    st.markdown("### 👁️ Laterality Distribution (All Users)")
    
    all_laterality = {}
    for username, data in all_stats.items():
        by_laterality = data['statistics']['by_laterality']
        for lat, count in by_laterality.items():
            all_laterality[lat] = all_laterality.get(lat, 0) + count
    
    if all_laterality:
        df_lat = pd.DataFrame(list(all_laterality.items()), columns=['Laterality', 'Count'])
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(df_lat, use_container_width=True)
        with col2:
            fig = px.bar(
                df_lat,
                x='Laterality',
                y='Count',
                title='Distribution by Laterality',
                color='Laterality'
            )
            st.plotly_chart(fig, use_container_width=True)

def show_user_management():
    """Show user management interface"""
    
    st.markdown("## 👥 User Management")
    
    # Display existing users
    st.markdown("### Current Users")
    users = get_all_users()
    
    user_list = []
    for username, info in users.items():
        user_list.append({
            'Username': username,
            'Role': info['role'],
            'Created': info['created_at'],
            'Route Strategy': info.get('route_strategy', 'forward')
        })
    
    df_users = pd.DataFrame(user_list)
    st.dataframe(df_users, use_container_width=True)
    
    st.markdown("---")
    
    # Create new user
    st.markdown("### ➕ Create New User")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
        
        with col2:
            new_role = st.selectbox("Role", ["labeler", "admin"])
            new_strategy = st.selectbox(
                "Route Strategy",
                list(ROUTE_STRATEGIES.keys()),
                format_func=lambda x: f"{x}: {ROUTE_STRATEGIES[x]}"
            )
        
        submit = st.form_submit_button("Create User", use_container_width=True)
        
        if submit:
            if not new_username or not new_password:
                st.error("Please provide both username and password")
            else:
                success, message = create_user(
                    new_username,
                    new_password,
                    new_role,
                    new_strategy
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

def show_label_review():
    """Show label review interface"""
    
    st.markdown("## 🔍 Label Review")
    
    # Get all user stats
    all_stats = LabelManager.get_all_user_stats()
    
    if not all_stats:
        st.info("No labeling data available yet.")
        return
    
    # Select user to review
    usernames = list(all_stats.keys())
    selected_user = st.selectbox("Select user to review", usernames)
    
    if selected_user:
        label_manager = LabelManager(selected_user)
        
        # Show review queue
        review_queue = label_manager.get_review_queue()
        
        st.markdown(f"### 📌 Review Queue for {selected_user}")
        
        if review_queue:
            st.info(f"There are {len(review_queue)} images marked for review")
            
            # Display review queue items
            for idx_str in review_queue:
                label = label_manager.get_label(int(idx_str))
                if label:
                    with st.expander(f"Image {idx_str} - {label['diagnosis']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Laterality:** {label['laterality']}")
                            st.write(f"**Diagnosis:** {label['diagnosis']}")
                            if label['diagnosis_other']:
                                st.write(f"**Other Diagnosis:** {label['diagnosis_other']}")
                        
                        with col2:
                            st.write(f"**Flag:** {label['flag']}")
                            st.write(f"**Quality:** {label['quality']}")
                            st.write(f"**Labeled at:** {label['labeled_at']}")
                        
                        if st.button(f"Remove from review queue", key=f"remove_{idx_str}"):
                            label_manager.remove_from_review_queue(int(idx_str))
                            st.rerun()
        else:
            st.success("No images in review queue")
        
        st.markdown("---")
        
        # Show all labels for selected user
        st.markdown(f"### 📋 All Labels from {selected_user}")
        
        labels = label_manager.labels.get('labels', {})
        if labels:
            label_data = []
            for idx, label in labels.items():
                label_data.append({
                    'Index': idx,
                    'Laterality': label['laterality'],
                    'Diagnosis': label['diagnosis'],
                    'Other': label.get('diagnosis_other', ''),
                    'Flag': label['flag'],
                    'Quality': label['quality'],
                    'Labeled At': label['labeled_at'],
                    'Edited': '✓' if label.get('is_edit', False) else ''
                })
            
            df_labels = pd.DataFrame(label_data)
            
            # Add filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_diagnosis = st.multiselect(
                    "Filter by Diagnosis",
                    options=df_labels['Diagnosis'].unique()
                )
            
            with col2:
                filter_flag = st.multiselect(
                    "Filter by Flag",
                    options=df_labels['Flag'].unique()
                )
            
            with col3:
                filter_quality = st.multiselect(
                    "Filter by Quality",
                    options=df_labels['Quality'].unique()
                )
            
            # Apply filters
            if filter_diagnosis:
                df_labels = df_labels[df_labels['Diagnosis'].isin(filter_diagnosis)]
            if filter_flag:
                df_labels = df_labels[df_labels['Flag'].isin(filter_flag)]
            if filter_quality:
                df_labels = df_labels[df_labels['Quality'].isin(filter_quality)]
            
            st.dataframe(df_labels, use_container_width=True)
            
            # Export option
            csv = df_labels.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"{selected_user}_labels.csv",
                mime="text/csv"
            )
        else:
            st.info("No labels found for this user")
