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
    col1, col2, col3 = st.columns(3)
    
    total_labeled = sum(stats['statistics']['total'] for stats in all_stats.values())
    total_usable = sum(stats['statistics']['by_quality'].get('Usable', 0) for stats in all_stats.values())
    total_not_usable = sum(stats['statistics']['by_quality'].get('Non Usable', 0) for stats in all_stats.values())
    
    with col1:
        st.metric("Total Labels", total_labeled)
    with col2:
        st.metric("Usable", total_usable)
    with col3:
        st.metric("Non Usable", total_not_usable)
    
    st.markdown("---")
    
    # Per-user statistics
    st.markdown("### 👥 Per-User Statistics")
    
    user_data = []
    for username, data in all_stats.items():
        stats = data['statistics']
        user_data.append({
            'Username': username,
            'Total Labels': stats['total'],
            'Usable': stats['by_quality'].get('Usable', 0),
            'Non Usable': stats['by_quality'].get('Non Usable', 0),
            'Last Modified': data['last_modified']
        })
    
    df_users = pd.DataFrame(user_data)
    st.dataframe(df_users, use_container_width=True, hide_index=True)
    
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
        fig.add_trace(go.Bar(name='Usable', x=df_users['Username'], y=df_users['Usable']))
        fig.add_trace(go.Bar(name='Non Usable', x=df_users['Username'], y=df_users['Non Usable']))
        fig.update_layout(title='Quality Distribution per User', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    # Condition distribution (multilabel)
    st.markdown("---")
    st.markdown("### 🏥 Diagnostic Conditions Distribution (All Users)")
    
    all_conditions = {}
    for username, data in all_stats.items():
        by_condition = data['statistics']['by_condition']
        for condition, count in by_condition.items():
            all_conditions[condition] = all_conditions.get(condition, 0) + count
    
    if all_conditions:
        df_cond = pd.DataFrame(list(all_conditions.items()), columns=['Condition', 'Count'])
        df_cond = df_cond.sort_values('Count', ascending=False)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.dataframe(df_cond, use_container_width=True, hide_index=True)
        
        with col2:
            fig = px.bar(
                df_cond,
                x='Condition',
                y='Count',
                title='Distribution of Diagnostic Conditions',
                color='Count',
                color_continuous_scale='Viridis'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed statistics by condition
    st.markdown("---")
    st.markdown("### 🔬 Detailed Condition Statistics")
    
    # Get detailed stats from one user (they should all have same structure)
    sample_username = list(all_stats.keys())[0]
    label_manager = LabelManager(sample_username)
    detailed_stats = label_manager.get_detailed_statistics()
    
    # Create tabs for each condition
    condition_tabs = st.tabs([
        "👁️ Dry Eye",
        "🔍 Cataract",
        "🦠 Infectious",
        "🔬 Tumors",
        "🩸 Hemorrhage"
    ])
    
    with condition_tabs[0]:
        # Dry Eye statistics
        dry_eye_severity = {}
        dry_eye_signs = {}
        
        for username, data in all_stats.items():
            lm = LabelManager(username)
            det_stats = lm.get_detailed_statistics()
            
            for sev, count in det_stats['detailed']['dry_eye']['by_severity'].items():
                dry_eye_severity[sev] = dry_eye_severity.get(sev, 0) + count
            
            for sign, count in det_stats['detailed']['dry_eye']['by_signs'].items():
                dry_eye_signs[sign] = dry_eye_signs.get(sign, 0) + count
        
        if dry_eye_severity:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Severity Distribution**")
                df_sev = pd.DataFrame(list(dry_eye_severity.items()), columns=['Severity', 'Count'])
                fig = px.pie(df_sev, values='Count', names='Severity', title='Dry Eye Severity')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Signs Distribution**")
                if dry_eye_signs:
                    df_signs = pd.DataFrame(list(dry_eye_signs.items()), columns=['Sign', 'Count'])
                    df_signs = df_signs.sort_values('Count', ascending=True)
                    fig = px.bar(df_signs, x='Count', y='Sign', orientation='h', title='Dry Eye Signs')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Dry Eye Disease labels yet")
    
    with condition_tabs[1]:
        # Cataract statistics
        cataract_type = {}
        cataract_severity = {}
        cataract_features = {}
        
        for username, data in all_stats.items():
            lm = LabelManager(username)
            det_stats = lm.get_detailed_statistics()
            
            for cat_type, count in det_stats['detailed']['cataract']['by_type'].items():
                cataract_type[cat_type] = cataract_type.get(cat_type, 0) + count
            
            for sev, count in det_stats['detailed']['cataract']['by_severity'].items():
                cataract_severity[sev] = cataract_severity.get(sev, 0) + count
            
            for feat, count in det_stats['detailed']['cataract']['by_features'].items():
                cataract_features[feat] = cataract_features.get(feat, 0) + count
        
        if cataract_type:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Type Distribution**")
                df_type = pd.DataFrame(list(cataract_type.items()), columns=['Type', 'Count'])
                fig = px.pie(df_type, values='Count', names='Type', title='Cataract Types')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Severity Distribution**")
                if cataract_severity:
                    df_sev = pd.DataFrame(list(cataract_severity.items()), columns=['Severity', 'Count'])
                    fig = px.bar(df_sev, x='Severity', y='Count', title='Cataract Severity')
                    st.plotly_chart(fig, use_container_width=True)
            
            if cataract_features:
                st.markdown("**Features Distribution**")
                df_feat = pd.DataFrame(list(cataract_features.items()), columns=['Feature', 'Count'])
                st.dataframe(df_feat, use_container_width=True, hide_index=True)
        else:
            st.info("No Cataract labels yet")
    
    with condition_tabs[2]:
        # Infectious statistics
        infectious_type = {}
        infectious_etiology = {}
        
        for username, data in all_stats.items():
            lm = LabelManager(username)
            det_stats = lm.get_detailed_statistics()
            
            for inf_type, count in det_stats['detailed']['infectious']['by_type'].items():
                infectious_type[inf_type] = infectious_type.get(inf_type, 0) + count
            
            for etiology, count in det_stats['detailed']['infectious']['by_etiology'].items():
                infectious_etiology[etiology] = infectious_etiology.get(etiology, 0) + count
        
        if infectious_type:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Type Distribution**")
                df_type = pd.DataFrame(list(infectious_type.items()), columns=['Type', 'Count'])
                fig = px.bar(df_type, x='Type', y='Count', title='Infectious Type')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Etiology Distribution**")
                if infectious_etiology:
                    df_etio = pd.DataFrame(list(infectious_etiology.items()), columns=['Etiology', 'Count'])
                    fig = px.pie(df_etio, values='Count', names='Etiology', title='Infectious Etiology')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Infectious Keratitis/Conjunctivitis labels yet")
    
    with condition_tabs[3]:
        # Tumor statistics
        tumor_type = {}
        tumor_malignancy = {}
        tumor_location = {}
        
        for username, data in all_stats.items():
            lm = LabelManager(username)
            det_stats = lm.get_detailed_statistics()
            
            for ttype, count in det_stats['detailed']['tumor']['by_type'].items():
                tumor_type[ttype] = tumor_type.get(ttype, 0) + count
            
            for malig, count in det_stats['detailed']['tumor']['by_malignancy'].items():
                tumor_malignancy[malig] = tumor_malignancy.get(malig, 0) + count
            
            for loc, count in det_stats['detailed']['tumor']['by_location'].items():
                tumor_location[loc] = tumor_location.get(loc, 0) + count
        
        if tumor_type:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Type Distribution**")
                df_type = pd.DataFrame(list(tumor_type.items()), columns=['Type', 'Count'])
                fig = px.bar(df_type, x='Type', y='Count', title='Tumor Types')
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Malignancy Distribution**")
                if tumor_malignancy:
                    df_malig = pd.DataFrame(list(tumor_malignancy.items()), columns=['Malignancy', 'Count'])
                    fig = px.pie(df_malig, values='Count', names='Malignancy', title='Tumor Malignancy')
                    st.plotly_chart(fig, use_container_width=True)
            
            if tumor_location:
                st.markdown("**Location Distribution**")
                df_loc = pd.DataFrame(list(tumor_location.items()), columns=['Location', 'Count'])
                fig = px.bar(df_loc, x='Location', y='Count', title='Tumor Location')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Ocular Surface Tumor labels yet")
    
    with condition_tabs[4]:
        # Hemorrhage statistics
        sch_presence = {}
        sch_extent = {}
        
        for username, data in all_stats.items():
            lm = LabelManager(username)
            det_stats = lm.get_detailed_statistics()
            
            for pres, count in det_stats['detailed']['sch']['by_presence'].items():
                sch_presence[pres] = sch_presence.get(pres, 0) + count
            
            for ext, count in det_stats['detailed']['sch']['by_extent'].items():
                sch_extent[ext] = sch_extent.get(ext, 0) + count
        
        if sch_presence:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Presence Distribution**")
                df_pres = pd.DataFrame(list(sch_presence.items()), columns=['Presence', 'Count'])
                fig = px.pie(df_pres, values='Count', names='Presence', title='Hemorrhage Presence')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Extent Distribution**")
                if sch_extent:
                    df_ext = pd.DataFrame(list(sch_extent.items()), columns=['Extent', 'Count'])
                    fig = px.bar(df_ext, x='Extent', y='Count', title='Hemorrhage Extent')
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Subconjunctival Hemorrhage labels yet")
    
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
            st.dataframe(df_lat, use_container_width=True, hide_index=True)
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
    st.dataframe(df_users, use_container_width=True, hide_index=True)
    
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
                    conditions = label.get('conditions', {})
                    condition_names = ', '.join(conditions.keys()) if conditions else 'No conditions'
                    
                    with st.expander(f"Image {idx_str} - {label['laterality']} - {condition_names}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Laterality:** {label['laterality']}")
                            st.write(f"**Quality:** {label['quality']}")
                            st.write(f"**Labeled at:** {label['labeled_at']}")
                        
                        with col2:
                            st.write(f"**Study ID:** {label.get('metadata', {}).get('maskedid_studyid', 'N/A')}")
                        
                        # Show conditions
                        if conditions:
                            st.markdown("**Conditions:**")
                            for condition_name, condition_data in conditions.items():
                                st.markdown(f"- **{condition_name}**")
                                for key, value in condition_data.items():
                                    if value:  # Only show non-empty values
                                        st.write(f"  - {key}: {value}")
                        
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
                conditions = label.get('conditions', {})
                condition_names = ', '.join(conditions.keys()) if conditions else 'None'
                
                label_data.append({
                    'Index': idx,
                    'Study ID': label.get('metadata', {}).get('maskedid_studyid', 'N/A'),
                    'Laterality': label['laterality'],
                    'Quality': label['quality'],
                    'Conditions': condition_names,
                    'Labeled At': label['labeled_at'],
                    'Edited': '✓' if label.get('is_edit', False) else ''
                })
            
            df_labels = pd.DataFrame(label_data)
            
            # Add filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_laterality = st.multiselect(
                    "Filter by Laterality",
                    options=df_labels['Laterality'].unique()
                )
            
            with col2:
                filter_quality = st.multiselect(
                    "Filter by Quality",
                    options=df_labels['Quality'].unique()
                )
            
            with col3:
                # Get all unique conditions
                all_conditions = set()
                for conditions_str in df_labels['Conditions']:
                    if conditions_str != 'None':
                        all_conditions.update([c.strip() for c in conditions_str.split(',')])
                
                filter_condition = st.multiselect(
                    "Filter by Condition",
                    options=sorted(all_conditions)
                )
            
            # Apply filters
            if filter_laterality:
                df_labels = df_labels[df_labels['Laterality'].isin(filter_laterality)]
            if filter_quality:
                df_labels = df_labels[df_labels['Quality'].isin(filter_quality)]
            if filter_condition:
                # Filter rows that contain at least one of the selected conditions
                mask = df_labels['Conditions'].apply(
                    lambda x: any(cond in x for cond in filter_condition)
                )
                df_labels = df_labels[mask]
            
            st.dataframe(df_labels, use_container_width=True, hide_index=True)
            
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