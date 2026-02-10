"""
Labeling page with AI suggestion auto-fill support
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
    DRY_EYE_SEVERITY,
    DRY_EYE_SIGNS,
    CATARACT_TYPE,
    CATARACT_SEVERITY,
    CATARACT_FEATURES,
    INFECTIOUS_TYPE,
    INFECTIOUS_ETIOLOGY,
    KERATITIS_SIZE,
    KERATITIS_FEATURES,
    CONJUNCTIVITIS_FEATURES,
    TUMOR_TYPE,
    TUMOR_MALIGNANCY,
    TUMOR_LOCATION,
    TUMOR_FEATURES,
    SCH_PRESENCE,
    SCH_EXTENT,
    ENABLE_AUTOFILL_SAME_STUDYID
)

def show():
    """Show labeling page with AI suggestion support"""
    
    st.markdown('<p class="main-header">🏷️ Image Labeling Interface</p>', unsafe_allow_html=True)
    
    # Initialize data loader and label manager
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DataLoader()
        # Set filter mode from session state or use default
        from config.config import DEFAULT_DATASET_FILTER
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
    
    # Also load AI_prelabel manager for suggestions
    if 'ai_label_manager' not in st.session_state:
        st.session_state.ai_label_manager = LabelManager("AI_prelabel")
    
    data_loader = st.session_state.data_loader
    label_manager = st.session_state.label_manager
    ai_label_manager = st.session_state.ai_label_manager
    
    # Initialize route if needed
    if 'route_indices' not in st.session_state:
        total_images = data_loader.get_total_images()
        route_strategy = get_user_route_strategy(st.session_state.username)
        st.session_state.route_indices = data_loader.create_route(total_images, route_strategy, st.session_state.username)
        st.session_state.current_position = 0
    
    route_indices = st.session_state.route_indices
    current_position = st.session_state.current_position
    
    if current_position >= len(route_indices):
        st.success("🎉 You have reached the end of your route!")
        return
    
    current_index = route_indices[current_position]
    
    # Get image data
    image_data, message = data_loader.get_image_data(current_index)
    if image_data is None:
        st.error(f"Error loading image: {message}")
        return
    
    # Check for existing label from current user
    existing_label = label_manager.get_label(current_index)
    
    # Check for AI suggestion by image_path (only if user hasn't labeled yet)
    ai_suggestion = None
    if not existing_label:
        ai_suggestion = ai_label_manager.get_label_by_path(image_data['image_path'])
    
    # Display interface
    col_image, col_info = st.columns([1.2, 1])
    
    with col_image:
        st.markdown("### 📷 Image")
        
        # Show studyid counter if available
        if image_data.get('studyid_counter'):
            st.caption(f"**Study Images:** {image_data['studyid_counter']}")
        
        # Display image
        image_path = Path(image_data['image_path'])
        if image_path.exists():
            try:
                img = Image.open(image_path)
                st.image(img, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading image: {str(e)}")
                st.code(str(image_path))
        else:
            st.warning("⚠️ Image file not found")
            st.code(str(image_path))
    
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
        
        # Clinical Notes
        notes = image_data.get('notes', [])
        if notes:
            with st.expander(f"📝 Clinical Notes ({len(notes)} found)", expanded=False):
                for i, note in enumerate(notes):
                    note_date = note.get('note_date', 'N/A')
                    days_diff = note.get('days_diff', 0)
                    position = note.get('position', '')
                    
                    # Format days difference
                    if days_diff == 0:
                        timing = "📅 Same day as exam"
                    elif days_diff < 0:
                        timing = f"📅 {abs(days_diff)} days before exam"
                    else:
                        timing = f"📅 {days_diff} days after exam"
                    
                    st.markdown(f"**Note {i+1}** - {note_date}")
                    st.caption(timing)
                    
                    # Show note text in scrollable container
                    note_text = note.get('note_text', 'No text available')
                    st.text_area(
                        f"Note {i+1} Content",
                        value=note_text,
                        height=200,
                        disabled=True,
                        key=f"note_{current_index}_{i}",
                        label_visibility="collapsed"
                    )
                    
                    if i < len(notes) - 1:
                        st.markdown("---")
        
        # Exam Annotations
        annotations = image_data.get('annotations', [])
        if annotations:
            with st.expander(f"🔬 Exam Annotations ({len(annotations)} found)", expanded=False):
                # Group by laterality
                annotations_by_lat = {}
                for ann in annotations:
                    lat = ann.get('laterality', 'Unknown')
                    if lat not in annotations_by_lat:
                        annotations_by_lat[lat] = []
                    annotations_by_lat[lat].append(ann)
                
                for laterality, anns in annotations_by_lat.items():
                    st.markdown(f"**{laterality} Eye:**")
                    
                    # Create dataframe for display
                    ann_data = []
                    for ann in anns:
                        ann_data.append({
                            'Field': ann.get('examfield', 'N/A'),
                            'Value': ann.get('value', 'N/A'),
                            'Date': str(ann.get('annotation_date', 'N/A')),
                            'Days Diff': ann.get('days_diff', 'N/A')
                        })
                    
                    if ann_data:
                        import pandas as pd
                        ann_df = pd.DataFrame(ann_data)
                        st.dataframe(ann_df, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
        
        # Show AI suggestion indicator
        if ai_suggestion and not existing_label:
            st.info("💡 **AI Suggestion Available** - Review and save if correct")
        
        if existing_label:
            st.info(f"✏️ **Previously Labeled** on {existing_label['labeled_at']}")
        
        st.markdown("---")
        
        # Labeling form
        st.markdown("### 🏷️ Label This Image")
        
        with st.form("labeling_form"):
            # Determine source for default values
            source_label = existing_label or ai_suggestion
            
            # Laterality
            default_lat_idx = 0
            if source_label and source_label['laterality'] in LATERALITY_OPTIONS:
                default_lat_idx = LATERALITY_OPTIONS.index(source_label['laterality'])
            
            laterality = st.selectbox(
                "Laterality *",
                LATERALITY_OPTIONS,
                index=default_lat_idx,
                help="Which eye is shown in this image"
            )
            
            # Quality
            default_quality_idx = 0
            if source_label and source_label['quality'] in QUALITY_OPTIONS:
                default_quality_idx = QUALITY_OPTIONS.index(source_label['quality'])
            
            quality = st.selectbox(
                "Image Quality *",
                QUALITY_OPTIONS,
                index=default_quality_idx,
                help="Is this image usable for diagnosis?"
            )
            
            # Conditions (only if Usable)
            conditions_data = {}
            
            if quality == "Usable":
                st.markdown("#### 🔬 Conditions")
                
                # Get existing conditions
                existing_conditions = source_label.get('conditions', {}) if source_label else {}
                
                # Dry Eye Disease
                with st.expander("👁️ Dry Eye Disease", expanded="Dry Eye Disease" in existing_conditions):
                    severity_idx = 0
                    if "Dry Eye Disease" in existing_conditions:
                        sev = existing_conditions["Dry Eye Disease"].get("severity", "None")
                        if sev in DRY_EYE_SEVERITY:
                            severity_idx = DRY_EYE_SEVERITY.index(sev)
                    
                    dry_eye_severity = st.selectbox("Severity", DRY_EYE_SEVERITY, index=severity_idx, key="dry_eye_sev")
                    
                    default_signs = []
                    if "Dry Eye Disease" in existing_conditions:
                        default_signs = existing_conditions["Dry Eye Disease"].get("signs", [])
                    
                    dry_eye_signs = st.multiselect("Signs", DRY_EYE_SIGNS, default=default_signs, key="dry_eye_signs")
                    
                    if dry_eye_severity != "None":
                        conditions_data["Dry Eye Disease"] = {
                            "severity": dry_eye_severity,
                            "signs": dry_eye_signs
                        }
                
                # Cataract
                with st.expander("🔍 Cataract", expanded="Cataract" in existing_conditions):
                    cat_type_idx = 0
                    if "Cataract" in existing_conditions:
                        ctype = existing_conditions["Cataract"].get("type", "None")
                        if ctype in CATARACT_TYPE:
                            cat_type_idx = CATARACT_TYPE.index(ctype)
                    
                    cataract_type = st.selectbox("Type", CATARACT_TYPE, index=cat_type_idx, key="cat_type")
                    
                    cataract_severity = None
                    cataract_features = []
                    
                    if cataract_type not in ["None", "Pseudophakia", "Aphakia"]:
                        sev_idx = 0
                        if "Cataract" in existing_conditions:
                            csev = existing_conditions["Cataract"].get("severity", "Mild")
                            if csev in CATARACT_SEVERITY:
                                sev_idx = CATARACT_SEVERITY.index(csev)
                        
                        cataract_severity = st.selectbox("Severity", CATARACT_SEVERITY, index=sev_idx, key="cat_sev")
                        
                        default_features = []
                        if "Cataract" in existing_conditions:
                            default_features = existing_conditions["Cataract"].get("features", [])
                        
                        cataract_features = st.multiselect("Features", CATARACT_FEATURES, default=default_features, key="cat_feat")
                    
                    if cataract_type != "None":
                        conditions_data["Cataract"] = {
                            "type": cataract_type,
                            "severity": cataract_severity,
                            "features": cataract_features
                        }
                
                # Infectious Keratitis / Conjunctivitis
                with st.expander("🦠 Infectious Keratitis / Conjunctivitis", expanded="Infectious Keratitis / Conjunctivitis" in existing_conditions):
                    inf_type_idx = 2  # Default: No infection
                    if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                        itype = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("type", "No infection")
                        if itype in INFECTIOUS_TYPE:
                            inf_type_idx = INFECTIOUS_TYPE.index(itype)
                    
                    infectious_type = st.selectbox("Type", INFECTIOUS_TYPE, index=inf_type_idx, key="inf_type")
                    
                    if infectious_type not in ["No infection", "Unclear"]:
                        etiol_idx = 0
                        if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                            etiol = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("etiology")
                            if etiol and etiol in INFECTIOUS_ETIOLOGY:
                                etiol_idx = INFECTIOUS_ETIOLOGY.index(etiol)
                        
                        etiology = st.selectbox("Etiology", INFECTIOUS_ETIOLOGY, index=etiol_idx, key="inf_etiol")
                        
                        inf_data = {"type": infectious_type, "etiology": etiology}
                        
                        if "Keratitis" in infectious_type:
                            size_idx = 0
                            if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                                ksize = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("keratitis_size")
                                if ksize and ksize in KERATITIS_SIZE:
                                    size_idx = KERATITIS_SIZE.index(ksize)
                            
                            keratitis_size = st.selectbox("Keratitis Size", KERATITIS_SIZE, index=size_idx, key="ker_size")
                            
                            default_ker_feat = []
                            if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                                default_ker_feat = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("keratitis_features", [])
                            
                            keratitis_features = st.multiselect("Keratitis Features", KERATITIS_FEATURES, default=default_ker_feat, key="ker_feat")
                            
                            inf_data["keratitis_size"] = keratitis_size
                            inf_data["keratitis_features"] = keratitis_features
                        
                        if "Conjunctivitis" in infectious_type:
                            default_conj_feat = []
                            if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                                default_conj_feat = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("conjunctivitis_features", [])
                            
                            conjunctivitis_features = st.multiselect("Conjunctivitis Features", CONJUNCTIVITIS_FEATURES, default=default_conj_feat, key="conj_feat")
                            inf_data["conjunctivitis_features"] = conjunctivitis_features
                        
                        conditions_data["Infectious Keratitis / Conjunctivitis"] = inf_data
                    elif infectious_type != "No infection":
                        conditions_data["Infectious Keratitis / Conjunctivitis"] = {"type": infectious_type}
                
                # Ocular Surface Tumors
                with st.expander("🔬 Ocular Surface Tumors", expanded="Ocular Surface Tumors" in existing_conditions):
                    tumor_type_idx = 6  # Default: No lesion
                    if "Ocular Surface Tumors" in existing_conditions:
                        ttype = existing_conditions["Ocular Surface Tumors"].get("type", "No lesion")
                        if ttype in TUMOR_TYPE:
                            tumor_type_idx = TUMOR_TYPE.index(ttype)
                    
                    tumor_type = st.selectbox("Type", TUMOR_TYPE, index=tumor_type_idx, key="tumor_type")
                    
                    if tumor_type not in ["No lesion", "Unclear"]:
                        mal_idx = 0
                        if "Ocular Surface Tumors" in existing_conditions:
                            mal = existing_conditions["Ocular Surface Tumors"].get("malignancy")
                            if mal and mal in TUMOR_MALIGNANCY:
                                mal_idx = TUMOR_MALIGNANCY.index(mal)
                        
                        malignancy = st.selectbox("Malignancy", TUMOR_MALIGNANCY, index=mal_idx, key="tumor_mal")
                        
                        loc_idx = 0
                        if "Ocular Surface Tumors" in existing_conditions:
                            loc = existing_conditions["Ocular Surface Tumors"].get("location")
                            if loc and loc in TUMOR_LOCATION:
                                loc_idx = TUMOR_LOCATION.index(loc)
                        
                        location = st.selectbox("Location", TUMOR_LOCATION, index=loc_idx, key="tumor_loc")
                        
                        default_tumor_feat = []
                        if "Ocular Surface Tumors" in existing_conditions:
                            default_tumor_feat = existing_conditions["Ocular Surface Tumors"].get("features", [])
                        
                        tumor_features = st.multiselect("Features", TUMOR_FEATURES, default=default_tumor_feat, key="tumor_feat")
                        
                        conditions_data["Ocular Surface Tumors"] = {
                            "type": tumor_type,
                            "malignancy": malignancy,
                            "location": location,
                            "features": tumor_features
                        }
                    elif tumor_type != "No lesion":
                        conditions_data["Ocular Surface Tumors"] = {"type": tumor_type}
                
                # Subconjunctival Hemorrhage
                with st.expander("🩸 Subconjunctival Hemorrhage", expanded="Subconjunctival Hemorrhage" in existing_conditions):
                    sch_pres_idx = 1  # Default: None
                    if "Subconjunctival Hemorrhage" in existing_conditions:
                        pres = existing_conditions["Subconjunctival Hemorrhage"].get("presence", "None")
                        if pres in SCH_PRESENCE:
                            sch_pres_idx = SCH_PRESENCE.index(pres)
                    
                    sch_presence = st.selectbox("Presence", SCH_PRESENCE, index=sch_pres_idx, key="sch_pres")
                    
                    if sch_presence == "Present":
                        ext_idx = 0
                        if "Subconjunctival Hemorrhage" in existing_conditions:
                            ext = existing_conditions["Subconjunctival Hemorrhage"].get("extent")
                            if ext and ext in SCH_EXTENT:
                                ext_idx = SCH_EXTENT.index(ext)
                        
                        sch_extent = st.selectbox("Extent", SCH_EXTENT, index=ext_idx, key="sch_ext")
                        
                        conditions_data["Subconjunctival Hemorrhage"] = {
                            "presence": sch_presence,
                            "extent": sch_extent
                        }
                    elif sch_presence != "None":
                        conditions_data["Subconjunctival Hemorrhage"] = {"presence": sch_presence}
            
            # Submit button
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("💾 Save Label", use_container_width=True)
            with col2:
                skip = st.form_submit_button("⏭️ Skip", use_container_width=True)
            
            if submitted:
                # Save label
                metadata = {
                    'maskedid_studyid': image_data.get('maskedid_studyid'),
                    'exam_date': str(image_data.get('exam_date')),
                    'pat_mrn': image_data.get('pat_mrn')
                }
                
                label_manager.add_label(
                    image_index=current_index,
                    image_path=image_data['image_path'],
                    laterality=laterality,
                    quality=quality,
                    conditions=conditions_data,
                    metadata=metadata
                )
                
                st.success("✅ Label saved successfully!")
                st.session_state.labels_saved += 1
                
                # Move to next
                st.session_state.current_position += 1
                st.rerun()
            
            if skip:
                st.session_state.current_position += 1
                st.rerun()
        
        # Navigation
        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        
        nav_col1, nav_col2, nav_col3 = st.columns(3)
        
        with nav_col1:
            if st.button("⏮️ First", use_container_width=True):
                st.session_state.current_position = 0
                st.rerun()
        
        with nav_col2:
            if st.button("⬅️ Previous", use_container_width=True) and current_position > 0:
                st.session_state.current_position -= 1
                st.rerun()
        
        with nav_col3:
            if st.button("➡️ Next", use_container_width=True):
                st.session_state.current_position += 1
                st.rerun()
        
        # Progress
        progress = (current_position + 1) / len(route_indices)
        st.progress(progress)
        st.caption(f"Position: {current_position + 1} / {len(route_indices)} | Labeled: {label_manager.get_labeled_count()}")
