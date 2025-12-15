"""
Labeling page - main interface for image labeling with MULTILABEL support
"""

import streamlit as st
from PIL import Image
from pathlib import Path
from utils.data_loader import DataLoader
from utils.label_manager import LabelManager
from utils.auth import get_user_route_strategy
from config.config import (
    LATERALITY_OPTIONS,
    QUALITY_OPTIONS,
    DIAGNOSTIC_CATEGORIES,
    # Dry Eye Disease
    DRY_EYE_SEVERITY,
    DRY_EYE_SIGNS,
    # Cataract
    CATARACT_TYPE,
    CATARACT_SEVERITY,
    CATARACT_FEATURES,
    # Infectious
    INFECTIOUS_TYPE,
    INFECTIOUS_ETIOLOGY,
    KERATITIS_SIZE,
    KERATITIS_FEATURES,
    CONJUNCTIVITIS_FEATURES,
    # Tumor
    TUMOR_TYPE,
    TUMOR_MALIGNANCY,
    TUMOR_LOCATION,
    TUMOR_FEATURES,
    # Subconjunctival Hemorrhage
    SCH_PRESENCE,
    SCH_EXTENT,
    AUTO_SAVE_INTERVAL,
    DATASET_FILTER_OPTIONS,
    DEFAULT_DATASET_FILTER,
    ENABLE_AUTOFILL_SAME_STUDYID
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
    
    # If not labeled, check if we should auto-fill from same studyid
    if not existing_label and ENABLE_AUTOFILL_SAME_STUDYID:
        current_studyid = image_data.get('maskedid_studyid')
        if current_studyid:
            last_label = st.session_state.label_manager.get_last_label_for_studyid(current_studyid)
            if last_label:
                # Store the auto-filled label in session state with a special key
                autofill_key = f"autofill_{current_index}"
                if autofill_key not in st.session_state:
                    st.session_state[autofill_key] = last_label
                existing_label = st.session_state.get(autofill_key)
    
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

        # Labeling form
        st.markdown("### 🏷️ Label This Image")
        
        # Check if this is auto-filled
        autofill_key = f"autofill_{current_index}"
        is_autofilled = autofill_key in st.session_state and not st.session_state.label_manager.is_labeled(current_index)
        
        if existing_label:
            if st.session_state.label_manager.is_labeled(current_index):
                st.info(f"✏️ This image was previously labeled on {existing_label['labeled_at']}")
            elif is_autofilled:
                col_msg, col_clear = st.columns([3, 1])
                with col_msg:
                    st.success(f"💡 Auto-filled from Study ID: {image_data.get('maskedid_studyid')}")
                with col_clear:
                    if st.button("🗑️ Clear", key=f"clear_autofill_{current_index}"):
                        del st.session_state[autofill_key]
                        st.rerun()
        
        # Laterality (outside form for immediate feedback)
        default_lat_idx = 0
        if existing_label and existing_label['laterality'] in LATERALITY_OPTIONS:
            default_lat_idx = LATERALITY_OPTIONS.index(existing_label['laterality'])
        
        laterality = st.selectbox(
            "Laterality *",
            LATERALITY_OPTIONS,
            index=default_lat_idx,
            key=f"lat_{current_index}"
        )
        
        # Quality Assessment (PRIMARY CHOICE - outside form)
        default_quality_idx = 0
        if existing_label and existing_label['quality'] in QUALITY_OPTIONS:
            default_quality_idx = QUALITY_OPTIONS.index(existing_label['quality'])
        
        quality = st.selectbox(
            "Quality Assessment *",
            QUALITY_OPTIONS,
            index=default_quality_idx,
            key=f"quality_{current_index}"
        )
        
        st.markdown("---")
        
        # Initialize conditions dictionary
        conditions = {}
        
        # Only show diagnostic options if quality is "Usable"
        if quality == "Usable":
            st.markdown("#### 📋 Diagnostic Assessment (Select all that apply)")
            
            existing_conditions = existing_label.get('conditions', {}) if existing_label else {}
            
            # ===== 1) DRY EYE DISEASE =====
            has_dry_eye = st.checkbox(
                "**Dry Eye Disease**",
                value="Dry Eye Disease" in existing_conditions,
                key=f"has_dry_eye_{current_index}"
            )
            
            if has_dry_eye:
                with st.container():
                    st.markdown("##### 👁️ Dry Eye Disease Details")
                    
                    existing_dry_eye = existing_conditions.get("Dry Eye Disease", {})
                    
                    # Severity
                    default_severity_idx = 0
                    if existing_dry_eye.get('severity') in DRY_EYE_SEVERITY:
                        default_severity_idx = DRY_EYE_SEVERITY.index(existing_dry_eye['severity'])
                    
                    dry_eye_severity = st.selectbox(
                        "Severity *",
                        DRY_EYE_SEVERITY,
                        index=default_severity_idx,
                        key=f"dry_eye_severity_{current_index}"
                    )
                    
                    # Signs
                    default_signs = existing_dry_eye.get('signs', [])
                    dry_eye_signs = st.multiselect(
                        "Signs (check any if seen)",
                        DRY_EYE_SIGNS,
                        default=default_signs,
                        key=f"dry_eye_signs_{current_index}"
                    )
                    
                    conditions["Dry Eye Disease"] = {
                        "severity": dry_eye_severity,
                        "signs": dry_eye_signs
                    }
                    
                    st.markdown("---")
            
            # ===== 2) CATARACT =====
            has_cataract = st.checkbox(
                "**Cataract**",
                value="Cataract" in existing_conditions,
                key=f"has_cataract_{current_index}"
            )
            
            if has_cataract:
                with st.container():
                    st.markdown("##### 🔍 Cataract Details")
                    
                    existing_cataract = existing_conditions.get("Cataract", {})
                    
                    # Type
                    default_type_idx = 0
                    if existing_cataract.get('type') in CATARACT_TYPE:
                        default_type_idx = CATARACT_TYPE.index(existing_cataract['type'])
                    
                    cataract_type = st.selectbox(
                        "Type *",
                        CATARACT_TYPE,
                        index=default_type_idx,
                        key=f"cataract_type_{current_index}"
                    )
                    
                    cataract_data = {"type": cataract_type}
                    
                    # Severity (only for Nuclear/Cortical/PSC)
                    if cataract_type in ["Nuclear", "Cortical", "PSC"]:
                        default_severity_idx = 0
                        if existing_cataract.get('severity') in CATARACT_SEVERITY:
                            default_severity_idx = CATARACT_SEVERITY.index(existing_cataract['severity'])
                        
                        cataract_severity = st.selectbox(
                            "Severity *",
                            CATARACT_SEVERITY,
                            index=default_severity_idx,
                            key=f"cataract_severity_{current_index}"
                        )
                        cataract_data["severity"] = cataract_severity
                    
                    # Features (optional)
                    default_features = existing_cataract.get('features', [])
                    cataract_features = st.multiselect(
                        "Features (optional)",
                        CATARACT_FEATURES,
                        default=default_features,
                        key=f"cataract_features_{current_index}"
                    )
                    cataract_data["features"] = cataract_features
                    
                    conditions["Cataract"] = cataract_data
                    
                    st.markdown("---")
            
            # ===== 3) INFECTIOUS KERATITIS / CONJUNCTIVITIS =====
            has_infectious = st.checkbox(
                "**Infectious Keratitis / Conjunctivitis**",
                value="Infectious Keratitis / Conjunctivitis" in existing_conditions,
                key=f"has_infectious_{current_index}"
            )
            
            if has_infectious:
                with st.container():
                    st.markdown("##### 🦠 Infectious Keratitis / Conjunctivitis Details")
                    
                    existing_infectious = existing_conditions.get("Infectious Keratitis / Conjunctivitis", {})
                    
                    # Type
                    default_type_idx = 0
                    if existing_infectious.get('type') in INFECTIOUS_TYPE:
                        default_type_idx = INFECTIOUS_TYPE.index(existing_infectious['type'])
                    
                    infectious_type = st.selectbox(
                        "Type *",
                        INFECTIOUS_TYPE,
                        index=default_type_idx,
                        key=f"infectious_type_{current_index}"
                    )
                    
                    infectious_data = {"type": infectious_type}
                    
                    # Etiology (if infectious)
                    if infectious_type in ["Keratitis—Infectious", "Conjunctivitis—Infectious"]:
                        default_etiology_idx = 0
                        if existing_infectious.get('etiology') in INFECTIOUS_ETIOLOGY:
                            default_etiology_idx = INFECTIOUS_ETIOLOGY.index(existing_infectious['etiology'])
                        
                        infectious_etiology = st.selectbox(
                            "Etiology *",
                            INFECTIOUS_ETIOLOGY,
                            index=default_etiology_idx,
                            key=f"infectious_etiology_{current_index}"
                        )
                        infectious_data["etiology"] = infectious_etiology
                    
                    # Keratitis-specific options
                    if infectious_type == "Keratitis—Infectious":
                        # Size
                        default_size_idx = 0
                        if existing_infectious.get('keratitis_size') in KERATITIS_SIZE:
                            default_size_idx = KERATITIS_SIZE.index(existing_infectious['keratitis_size'])
                        
                        keratitis_size = st.selectbox(
                            "Keratitis Size *",
                            KERATITIS_SIZE,
                            index=default_size_idx,
                            key=f"keratitis_size_{current_index}"
                        )
                        infectious_data["keratitis_size"] = keratitis_size
                        
                        # Features
                        default_features = existing_infectious.get('keratitis_features', [])
                        keratitis_features = st.multiselect(
                            "Keratitis Features (check any)",
                            KERATITIS_FEATURES,
                            default=default_features,
                            key=f"keratitis_features_{current_index}"
                        )
                        infectious_data["keratitis_features"] = keratitis_features
                    
                    # Conjunctivitis-specific options
                    if infectious_type == "Conjunctivitis—Infectious":
                        default_features = existing_infectious.get('conjunctivitis_features', [])
                        conjunctivitis_features = st.multiselect(
                            "Conjunctivitis Features (check any)",
                            CONJUNCTIVITIS_FEATURES,
                            default=default_features,
                            key=f"conjunctivitis_features_{current_index}"
                        )
                        infectious_data["conjunctivitis_features"] = conjunctivitis_features
                    
                    conditions["Infectious Keratitis / Conjunctivitis"] = infectious_data
                    
                    st.markdown("---")
            
            # ===== 4) OCULAR SURFACE TUMORS =====
            has_tumor = st.checkbox(
                "**Ocular Surface Tumors**",
                value="Ocular Surface Tumors" in existing_conditions,
                key=f"has_tumor_{current_index}"
            )
            
            if has_tumor:
                with st.container():
                    st.markdown("##### 🔬 Ocular Surface Tumors Details")
                    
                    existing_tumor = existing_conditions.get("Ocular Surface Tumors", {})
                    
                    # Type
                    default_type_idx = 0
                    if existing_tumor.get('type') in TUMOR_TYPE:
                        default_type_idx = TUMOR_TYPE.index(existing_tumor['type'])
                    
                    tumor_type = st.selectbox(
                        "Lesion Type *",
                        TUMOR_TYPE,
                        index=default_type_idx,
                        key=f"tumor_type_{current_index}"
                    )
                    
                    tumor_data = {"type": tumor_type}
                    
                    # Only show additional fields if not "No lesion" or "Unclear"
                    if tumor_type not in ["No lesion", "Unclear"]:
                        # Malignancy
                        default_malignancy_idx = 0
                        if existing_tumor.get('malignancy') in TUMOR_MALIGNANCY:
                            default_malignancy_idx = TUMOR_MALIGNANCY.index(existing_tumor['malignancy'])
                        
                        tumor_malignancy = st.selectbox(
                            "Malignancy *",
                            TUMOR_MALIGNANCY,
                            index=default_malignancy_idx,
                            key=f"tumor_malignancy_{current_index}"
                        )
                        tumor_data["malignancy"] = tumor_malignancy
                        
                        # Location
                        default_location_idx = 0
                        if existing_tumor.get('location') in TUMOR_LOCATION:
                            default_location_idx = TUMOR_LOCATION.index(existing_tumor['location'])
                        
                        tumor_location = st.selectbox(
                            "Location *",
                            TUMOR_LOCATION,
                            index=default_location_idx,
                            key=f"tumor_location_{current_index}"
                        )
                        tumor_data["location"] = tumor_location
                        
                        # Features (optional)
                        default_features = existing_tumor.get('features', [])
                        tumor_features = st.multiselect(
                            "Features (optional)",
                            TUMOR_FEATURES,
                            default=default_features,
                            key=f"tumor_features_{current_index}"
                        )
                        tumor_data["features"] = tumor_features
                    
                    conditions["Ocular Surface Tumors"] = tumor_data
                    
                    st.markdown("---")
            
            # ===== 5) SUBCONJUNCTIVAL HEMORRHAGE =====
            has_sch = st.checkbox(
                "**Subconjunctival Hemorrhage**",
                value="Subconjunctival Hemorrhage" in existing_conditions,
                key=f"has_sch_{current_index}"
            )
            
            if has_sch:
                with st.container():
                    st.markdown("##### 🩸 Subconjunctival Hemorrhage Details")
                    
                    existing_sch = existing_conditions.get("Subconjunctival Hemorrhage", {})
                    
                    # Presence
                    default_presence_idx = 0
                    if existing_sch.get('presence') in SCH_PRESENCE:
                        default_presence_idx = SCH_PRESENCE.index(existing_sch['presence'])
                    
                    sch_presence = st.selectbox(
                        "Presence *",
                        SCH_PRESENCE,
                        index=default_presence_idx,
                        key=f"sch_presence_{current_index}"
                    )
                    
                    sch_data = {"presence": sch_presence}
                    
                    # Extent (only if present)
                    if sch_presence == "Present":
                        default_extent_idx = 0
                        if existing_sch.get('extent') in SCH_EXTENT:
                            default_extent_idx = SCH_EXTENT.index(existing_sch['extent'])
                        
                        sch_extent = st.selectbox(
                            "Extent *",
                            SCH_EXTENT,
                            index=default_extent_idx,
                            key=f"sch_extent_{current_index}"
                        )
                        sch_data["extent"] = sch_extent
                    
                    conditions["Subconjunctival Hemorrhage"] = sch_data
                    
                    st.markdown("---")
            
            # ===== 6) NONE OF THE ABOVE =====
            has_none = st.checkbox(
                "**None of the Above**",
                value="None of the Above" in existing_conditions,
                key=f"has_none_{current_index}"
            )
            
            if has_none:
                with st.container():
                    st.markdown("##### ℹ️ Other Findings")
                    
                    existing_none = existing_conditions.get("None of the Above", {})
                    default_other = existing_none.get('other_text', '')
                    
                    other_text = st.text_area(
                        "Please describe any findings (optional)",
                        value=default_other,
                        key=f"other_text_{current_index}",
                        height=100
                    )
                    
                    conditions["None of the Above"] = {"other_text": other_text}
                    
                    st.markdown("---")
        
        st.markdown("---")
        
        # Initialize button states
        save_button = False
        review_button = False
        
        # Action buttons - NOW WITH FORM
        with st.form("save_form"):
            col_save, col_review = st.columns(2)
            
            with col_save:
                save_button = st.form_submit_button("💾 Save Label", use_container_width=True)
            
            with col_review:
                review_button = st.form_submit_button("📌 Save & Mark for Review", use_container_width=True)
        
        # Handle form submission (OUTSIDE the form)
        if save_button or review_button:
            # Validation
            validation_error = None
            
            if quality == "Usable":
                # Check if at least one condition is selected
                if not conditions:
                    validation_error = "Please select at least one diagnostic category"
                else:
                    # Validate each condition
                    for condition_name, condition_data in conditions.items():
                        if condition_name == "Dry Eye Disease":
                            if not condition_data.get("severity"):
                                validation_error = "Please specify severity for Dry Eye Disease"
                                break
                        
                        elif condition_name == "Cataract":
                            if not condition_data.get("type"):
                                validation_error = "Please specify type for Cataract"
                                break
                            if condition_data.get("type") in ["Nuclear", "Cortical", "PSC"]:
                                if not condition_data.get("severity"):
                                    validation_error = "Please specify severity for this cataract type"
                                    break
                        
                        elif condition_name == "Infectious Keratitis / Conjunctivitis":
                            if not condition_data.get("type"):
                                validation_error = "Please specify type for Infectious condition"
                                break
                            if condition_data.get("type") in ["Keratitis—Infectious", "Conjunctivitis—Infectious"]:
                                if not condition_data.get("etiology"):
                                    validation_error = "Please specify etiology for infectious cases"
                                    break
                            if condition_data.get("type") == "Keratitis—Infectious":
                                if not condition_data.get("keratitis_size"):
                                    validation_error = "Please specify keratitis size"
                                    break
                        
                        elif condition_name == "Ocular Surface Tumors":
                            if not condition_data.get("type"):
                                validation_error = "Please specify lesion type for Tumors"
                                break
                            if condition_data.get("type") not in ["No lesion", "Unclear"]:
                                if not condition_data.get("malignancy"):
                                    validation_error = "Please specify malignancy for tumor"
                                    break
                                if not condition_data.get("location"):
                                    validation_error = "Please specify location for tumor"
                                    break
                        
                        elif condition_name == "Subconjunctival Hemorrhage":
                            if not condition_data.get("presence"):
                                validation_error = "Please specify presence for Subconjunctival Hemorrhage"
                                break
                            if condition_data.get("presence") == "Present":
                                if not condition_data.get("extent"):
                                    validation_error = "Please specify extent for hemorrhage"
                                    break
            
            if validation_error:
                st.error(validation_error)
            else:
                # Save the label
                st.session_state.label_manager.add_label(
                    image_index=current_index,
                    image_path=image_data['image_path'],
                    laterality=laterality,
                    quality=quality,
                    conditions=conditions,
                    metadata={
                        'maskedid_studyid': image_data.get('maskedid_studyid'),
                        'exam_date': str(image_data.get('exam_date')),
                        'pat_mrn': image_data.get('pat_mrn')
                    }
                )
                
                # Clear autofill from session state after saving
                autofill_key = f"autofill_{current_index}"
                if autofill_key in st.session_state:
                    del st.session_state[autofill_key]
                
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
    
    with col_info:
        st.markdown("### 📋 Clinical Information")
        
        # Patient and exam information
        with st.expander("🔍 Exam Details", expanded=True):
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.write(f"**Study ID:** {image_data.get('maskedid_studyid', 'N/A')}")
                st.write(f"**Main Diagnosis:** {image_data.get('main_diagnosis', 'N/A')}")
                st.write(f"**Order Diagnosis:** {image_data.get('order_diagnosis', 'N/A')}")
            with info_col2:
                st.write(f"**Exam Date:** {image_data.get('exam_date', 'N/A')}")
                st.write(f"**Laterality:** {image_data.get('laterality', 'N/A')}")
            
        
        # Annotations
        annotations = image_data.get('annotations', [])
        if annotations:
            with st.expander("🔬 Exam Description", expanded=True):
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
        
        st.markdown("---")
        
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
