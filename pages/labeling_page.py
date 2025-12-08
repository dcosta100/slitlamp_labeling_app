"""
Labeling page - main interface for image labeling
"""

import streamlit as st
from PIL import Image
from pathlib import Path
from utils.data_loader import DataLoader
from utils.label_manager import LabelManager
from utils.auth import get_user_route_strategy
from config.config import (
    LATERALITY_OPTIONS,
    DIAGNOSIS_OPTIONS,
    FLAG_OPTIONS,
    QUALITY_OPTIONS,
    AUTO_SAVE_INTERVAL,
    DATASET_FILTER_OPTIONS,
    DEFAULT_DATASET_FILTER
)

def show():
    """Show labeling page"""
    
    st.markdown('<p class="main-header">🏷️ Image Labeling Interface</p>', unsafe_allow_html=True)
    
    # Initialize data loader and label manager
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DataLoader()
        # Set filter mode from session state or use default
        filter_mode = st.session_state.get('dataset_filter', DEFAULT_DATASET_FILTER)
        st.session_state.data_loader.filter_mode = filter_mode
        
        with st.spinner("Loading datasets..."):
            # merge_datasets will handle loading (either preprocessed or regular)
            success, message = st.session_state.data_loader.merge_datasets()
            if not success:
                st.error(message)
                return
            st.success(message)
    
    if 'label_manager' not in st.session_state:
        st.session_state.label_manager = LabelManager(st.session_state.username)
    
    # Get route strategy and indices
    if 'route_indices' not in st.session_state:
        total_images = st.session_state.data_loader.get_total_images()
        strategy = get_user_route_strategy(st.session_state.username)
        st.session_state.route_indices = st.session_state.data_loader.get_route_indices(
            strategy, st.session_state.username, total_images
        )
        
        # Find the next unlabeled image or continue from where left off
        last_labeled = st.session_state.label_manager.get_last_labeled_index(st.session_state.route_indices)
        if last_labeled >= 0:
            next_unlabeled = st.session_state.label_manager.get_next_unlabeled_index(
                st.session_state.route_indices, last_labeled + 1
            )
            if next_unlabeled is not None:
                st.session_state.current_position = next_unlabeled
            else:
                st.session_state.current_position = last_labeled + 1
        else:
            st.session_state.current_position = 0
    
    # Progress bar
    total_images = len(st.session_state.route_indices)
    labeled_count = st.session_state.label_manager.get_labeled_count()
    progress = labeled_count / total_images if total_images > 0 else 0
    
    st.progress(progress)
    st.markdown(f"**Progress:** {labeled_count} / {total_images} images labeled ({progress*100:.1f}%)")
    
    # Navigation controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("⏮️ First", use_container_width=True):
            st.session_state.current_position = 0
            st.rerun()
    
    with col2:
        if st.button("◀️ Previous", use_container_width=True):
            if st.session_state.current_position > 0:
                st.session_state.current_position -= 1
                st.rerun()
    
    with col3:
        position_input = st.number_input(
            "Go to position",
            min_value=1,
            max_value=total_images,
            value=st.session_state.current_position + 1,
            key="position_input"
        )
        if position_input - 1 != st.session_state.current_position:
            st.session_state.current_position = position_input - 1
            st.rerun()
    
    with col4:
        if st.button("▶️ Next", use_container_width=True):
            if st.session_state.current_position < total_images - 1:
                st.session_state.current_position += 1
                st.rerun()
    
    with col5:
        if st.button("⏭️ Next Unlabeled", use_container_width=True):
            next_unlabeled = st.session_state.label_manager.get_next_unlabeled_index(
                st.session_state.route_indices,
                st.session_state.current_position
            )
            if next_unlabeled is not None:
                st.session_state.current_position = next_unlabeled
                st.rerun()
            else:
                st.info("All images have been labeled!")
    
    st.markdown("---")
    
    # Get current image data
    current_index = st.session_state.route_indices[st.session_state.current_position]
    image_data, message = st.session_state.data_loader.get_image_data(current_index)
    
    if image_data is None:
        st.error(f"Error loading image data: {message}")
        return
    
    # Check if already labeled
    existing_label = st.session_state.label_manager.get_label(current_index)
    
    # Main layout - Image on left, Info and Labels on right
    col_img, col_info = st.columns([1, 1])
    
    with col_img:
        st.markdown("### 📸 Image")
        
        image_path = Path(image_data['image_path'])
        if image_path.exists():
            try:
                img = Image.open(image_path)
                st.image(img, use_container_width=True)
                
                # Image info
                st.caption(f"**File:** {image_data['photo_name']}")
                st.caption(f"**Index:** {current_index} | **Position:** {st.session_state.current_position + 1}/{total_images}")
            except Exception as e:
                st.error(f"Error loading image: {str(e)}")
                st.code(str(image_path))
        else:
            st.warning("⚠️ Image file not found")
            st.code(str(image_path))
            st.info("The image path may need to be updated in config/config.py")
    
    with col_info:
        st.markdown("### 📋 Clinical Information")
        
        # Patient and exam information
        with st.expander("🔍 Exam Details", expanded=True):
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.write(f"**MRN:** {image_data.get('pat_mrn', 'N/A')}")
                st.write(f"**Study ID:** {image_data.get('maskedid_studyid', 'N/A')}")
            with info_col2:
                st.write(f"**Exam Date:** {image_data.get('exam_date', 'N/A')}")
                st.write(f"**Laterality:** {image_data.get('laterality', 'N/A')}")
            
            st.write(f"**Main Diagnosis:** {image_data.get('main_diagnosis', 'N/A')}")
            st.write(f"**Order Diagnosis:** {image_data.get('order_diagnosis', 'N/A')}")
        
        # Clinical notes
        notes = image_data.get('notes', [])
        if notes:
            with st.expander("📝 Clinical Notes", expanded=True):
                for i, note in enumerate(notes):
                    days_diff = note['days_diff']
                    position = note['position']
                    
                    if position == 'before':
                        icon = "⬅️"
                        timing = f"{abs(days_diff)} days before exam"
                    elif position == 'after':
                        icon = "➡️"
                        timing = f"{days_diff} days after exam"
                    else:
                        icon = "🎯"
                        timing = "Same day as exam"
                    
                    st.markdown(f"**{icon} Note {i+1}** - {timing}")
                    st.caption(f"Date: {note['note_date'].strftime('%Y-%m-%d')}")
                    
                    note_text = note['note_text']
                    if len(note_text) > 500:
                        with st.expander("View full note"):
                            st.text(note_text)
                    else:
                        st.text(note_text)
                    
                    if i < len(notes) - 1:
                        st.markdown("---")
        else:
            st.info("No clinical notes found for this patient within the search window.")
        
        # Annotations
        annotations = image_data.get('annotations', [])
        if annotations:
            with st.expander("🔬 Exam Annotations", expanded=True):
                # Get the annotation date and days difference
                if annotations:
                    days_diff = annotations[0]['days_diff']
                    ann_date = annotations[0]['annotation_date']
                    
                    if days_diff == 0:
                        timing = "Same day as exam"
                        icon = "🎯"
                    elif days_diff < 0:
                        timing = f"{abs(days_diff)} days before exam"
                        icon = "⬅️"
                    else:
                        timing = f"{days_diff} days after exam"
                        icon = "➡️"
                    
                    st.markdown(f"**{icon} Annotations** - {timing}")
                    st.caption(f"Date: {ann_date.strftime('%Y-%m-%d')}")
                    
                    # Group annotations by laterality
                    laterality_groups = {}
                    for ann in annotations:
                        lat = ann.get('laterality', 'Unknown')
                        if lat not in laterality_groups:
                            laterality_groups[lat] = []
                        laterality_groups[lat].append(ann)
                    
                    # Display annotations grouped by laterality
                    for lat, anns in laterality_groups.items():
                        st.markdown(f"**{lat.upper()}:**")
                        ann_data = []
                        for ann in anns:
                            ann_data.append({
                                'Field': ann['examfield'],
                                'Value': ann['value']
                            })
                        
                        if ann_data:
                            import pandas as pd
                            df_anns = pd.DataFrame(ann_data)
                            st.dataframe(df_anns, use_container_width=True, hide_index=True)
        else:
            st.info("No exam annotations found for this image within 1 week.")
        
        st.markdown("---")
        
        # Labeling form
        st.markdown("### 🏷️ Label This Image")
        
        if existing_label:
            st.info(f"✏️ This image was previously labeled on {existing_label['labeled_at']}")
        
        with st.form("labeling_form"):
            # Laterality
            default_lat_idx = 0
            if existing_label and existing_label['laterality'] in LATERALITY_OPTIONS:
                default_lat_idx = LATERALITY_OPTIONS.index(existing_label['laterality'])
            
            laterality = st.selectbox(
                "Laterality *",
                LATERALITY_OPTIONS,
                index=default_lat_idx,
                key=f"lat_{current_index}"
            )
            
            # Diagnosis
            default_diag_idx = 0
            if existing_label and existing_label['diagnosis'] in DIAGNOSIS_OPTIONS:
                default_diag_idx = DIAGNOSIS_OPTIONS.index(existing_label['diagnosis'])
            
            diagnosis = st.selectbox(
                "Diagnosis *",
                DIAGNOSIS_OPTIONS,
                index=default_diag_idx,
                key=f"diag_{current_index}"
            )
            
            # Diagnosis Other
            diagnosis_other = None
            if diagnosis == "Other":
                default_other = existing_label.get('diagnosis_other', '') if existing_label else ''
                diagnosis_other = st.text_input(
                    "Specify diagnosis",
                    value=default_other,
                    key=f"diag_other_{current_index}"
                )
            
            # Flag
            default_flag_idx = 0
            if existing_label and existing_label['flag'] in FLAG_OPTIONS:
                default_flag_idx = FLAG_OPTIONS.index(existing_label['flag'])
            
            flag = st.selectbox(
                "Flag",
                FLAG_OPTIONS,
                index=default_flag_idx,
                key=f"flag_{current_index}"
            )
            
            # Quality
            default_quality_idx = 0
            if existing_label and existing_label['quality'] in QUALITY_OPTIONS:
                default_quality_idx = QUALITY_OPTIONS.index(existing_label['quality'])
            
            quality = st.selectbox(
                "Quality Assessment",
                QUALITY_OPTIONS,
                index=default_quality_idx,
                key=f"quality_{current_index}"
            )
            
            # Action buttons
            col_save, col_review = st.columns(2)
            
            with col_save:
                save_button = st.form_submit_button("💾 Save Label", use_container_width=True)
            
            with col_review:
                review_button = st.form_submit_button("📌 Save & Mark for Review", use_container_width=True)
            
            if save_button or review_button:
                if diagnosis == "Other" and not diagnosis_other:
                    st.error("Please specify the diagnosis when selecting 'Other'")
                else:
                    # Save the label
                    st.session_state.label_manager.add_label(
                        image_index=current_index,
                        image_path=image_data['image_path'],
                        laterality=laterality,
                        diagnosis=diagnosis,
                        diagnosis_other=diagnosis_other,
                        flag=flag,
                        quality=quality,
                        metadata={
                            'maskedid_studyid': image_data.get('maskedid_studyid'),
                            'exam_date': str(image_data.get('exam_date')),
                            'pat_mrn': image_data.get('pat_mrn')
                        }
                    )
                    
                    if review_button:
                        st.session_state.label_manager.add_to_review_queue(current_index)
                    
                    st.success("✅ Label saved successfully!")
                    
                    # Auto-advance to next unlabeled image
                    next_unlabeled = st.session_state.label_manager.get_next_unlabeled_index(
                        st.session_state.route_indices,
                        st.session_state.current_position + 1
                    )
                    if next_unlabeled is not None:
                        st.session_state.current_position = next_unlabeled
                        st.rerun()
                    elif st.session_state.current_position < total_images - 1:
                        st.session_state.current_position += 1
                        st.rerun()
        
        # Review queue
        review_queue = st.session_state.label_manager.get_review_queue()
        if review_queue:
            st.markdown("---")
            st.markdown(f"### 📌 Review Queue ({len(review_queue)} items)")
            
            if st.button("View Review Queue"):
                st.session_state.show_review_queue = True
        
        # Skip button (outside form)
        if st.button("⏭️ Skip This Image", use_container_width=True):
            if st.session_state.current_position < total_images - 1:
                st.session_state.current_position += 1
                st.rerun()
