"""
Labeling page with dynamic fields using session state (NO FORM)
Fields appear/disappear instantly based on selections
"""

import streamlit as st
from PIL import Image
from pathlib import Path
from utils.data_loader import DataLoader
from utils.label_manager import LabelManager
from utils.auth import get_user_route_strategy
from config.config import (
    LATERALITY_OPTIONS, QUALITY_OPTIONS,
    DRY_EYE_SEVERITY, DRY_EYE_SIGNS,
    CATARACT_TYPE, CATARACT_SEVERITY, CATARACT_FEATURES,
    INFECTIOUS_TYPE, INFECTIOUS_ETIOLOGY,
    KERATITIS_SIZE, KERATITIS_FEATURES, CONJUNCTIVITIS_FEATURES,
    TUMOR_TYPE, TUMOR_MALIGNANCY, TUMOR_LOCATION, TUMOR_FEATURES,
    SCH_PRESENCE, SCH_EXTENT,
)

# Keyboard shortcuts
KEYBOARD_JS = """
<script>
document.addEventListener('keydown', function(e) {
    const tag = document.activeElement.tagName.toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag)) return;
    if (e.key === 'ArrowRight' || e.key === 'd') {
        const btns = window.parent.document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.innerText.trim().startsWith('Next')) { btn.click(); break; }
        }
    }
    if (e.key === 'ArrowLeft' || e.key === 'a') {
        const btns = window.parent.document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.innerText.trim().startsWith('Prev')) { btn.click(); break; }
        }
    }
});
</script>
"""

def initialize_label_state(source_label):
    """Initialize session state from existing/AI label"""
    if 'label_laterality' not in st.session_state or st.session_state.get('_reset_labels'):
        st.session_state.label_laterality = source_label.get('laterality', LATERALITY_OPTIONS[0]) if source_label else LATERALITY_OPTIONS[0]
        st.session_state.label_quality = source_label.get('quality', QUALITY_OPTIONS[0]) if source_label else QUALITY_OPTIONS[0]
        
        conditions = source_label.get('conditions', {}) if source_label else {}
        
        # Dry Eye
        st.session_state.dry_eye_severity = conditions.get('Dry Eye Disease', {}).get('severity', 'None')
        st.session_state.dry_eye_signs = conditions.get('Dry Eye Disease', {}).get('signs', [])
        
        # Cataract
        st.session_state.cataract_type = conditions.get('Cataract', {}).get('type', 'None')
        st.session_state.cataract_severity = conditions.get('Cataract', {}).get('severity', 'Mild')
        st.session_state.cataract_features = conditions.get('Cataract', {}).get('features', [])
        
        # Infectious
        st.session_state.infectious_type = conditions.get('Infectious Keratitis / Conjunctivitis', {}).get('type', 'No infection')
        st.session_state.infectious_etiology = conditions.get('Infectious Keratitis / Conjunctivitis', {}).get('etiology', INFECTIOUS_ETIOLOGY[0])
        st.session_state.keratitis_size = conditions.get('Infectious Keratitis / Conjunctivitis', {}).get('keratitis_size', KERATITIS_SIZE[0])
        st.session_state.keratitis_features = conditions.get('Infectious Keratitis / Conjunctivitis', {}).get('keratitis_features', [])
        st.session_state.conjunctivitis_features = conditions.get('Infectious Keratitis / Conjunctivitis', {}).get('conjunctivitis_features', [])
        
        # Tumor
        st.session_state.tumor_type = conditions.get('Ocular Surface Tumors', {}).get('type', 'No lesion')
        st.session_state.tumor_malignancy = conditions.get('Ocular Surface Tumors', {}).get('malignancy', TUMOR_MALIGNANCY[0])
        st.session_state.tumor_location = conditions.get('Ocular Surface Tumors', {}).get('location', TUMOR_LOCATION[0])
        st.session_state.tumor_features = conditions.get('Ocular Surface Tumors', {}).get('features', [])
        
        # SCH
        st.session_state.sch_presence = conditions.get('Subconjunctival Hemorrhage', {}).get('presence', 'None')
        st.session_state.sch_extent = conditions.get('Subconjunctival Hemorrhage', {}).get('extent', SCH_EXTENT[0])
        
        st.session_state._reset_labels = False

def show():
    """Show labeling page"""
    
    st.markdown('<p class="main-header">🏷️ Image Labeling Interface</p>', unsafe_allow_html=True)
    st.components.v1.html(KEYBOARD_JS, height=0)
    
    st.markdown("""
        <style>
        .streamlit-expanderContent p, .streamlit-expanderContent span,
        .streamlit-expanderContent div, .streamlit-expanderContent label,
        .streamlit-expanderContent textarea { color: #000000 !important; }
        .exam-detail { color: #000000 !important; font-size: 0.9rem; margin: 2px 0; }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DataLoader()
        from config.config import DEFAULT_DATASET_FILTER
        st.session_state.data_loader.filter_mode = st.session_state.get('dataset_filter', DEFAULT_DATASET_FILTER)
        with st.spinner("Loading datasets..."):
            success, message = st.session_state.data_loader.merge_datasets()
            if not success:
                st.error(message)
                return
            st.success(message)
    
    if 'label_manager' not in st.session_state:
        st.session_state.label_manager = LabelManager(st.session_state.username)
    if 'ai_label_manager' not in st.session_state:
        st.session_state.ai_label_manager = LabelManager("AI_prelabel")
    
    data_loader = st.session_state.data_loader
    label_manager = st.session_state.label_manager
    ai_label_manager = st.session_state.ai_label_manager
    
    # Route
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
    image_data, message = data_loader.get_image_data(current_index)
    if not image_data:
        st.error(f"Error loading image: {message}")
        return
    
    existing_label = label_manager.get_label(current_index)
    ai_suggestion = None
    if not existing_label:
        ai_suggestion = ai_label_manager.get_label_by_path(image_data['image_path'])
    
    source_label = existing_label or ai_suggestion
    
    # Initialize state for this image
    initialize_label_state(source_label)
    
    # Layout
    col_left, col_right = st.columns([1.2, 1])
    
    # LEFT COLUMN
    with col_left:
        st.markdown("### 📷 Image")
        if image_data.get('studyid_counter'):
            st.caption(f"**Study:** {image_data['studyid_counter']}")
        
        image_path = Path(image_data['image_path'])
        if image_path.exists():
            try:
                st.image(Image.open(image_path), use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")
                st.code(str(image_path))
        else:
            st.warning("⚠️ Image not found")
            st.code(str(image_path))
        
        st.markdown("---")
        
        # Exam Details
        with st.expander("🔍 Exam Details", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<p class="exam-detail"><b>MRN:</b> {image_data.get("pat_mrn","N/A")}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="exam-detail"><b>Study ID:</b> {image_data.get("maskedid_studyid","N/A")}</p>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<p class="exam-detail"><b>Exam Date:</b> {image_data.get("exam_date","N/A")}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="exam-detail"><b>Laterality:</b> {image_data.get("laterality","N/A")}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="exam-detail"><b>Main Diagnosis:</b> {image_data.get("main_diagnosis","N/A")}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="exam-detail"><b>Order Diagnosis:</b> {image_data.get("order_diagnosis","N/A")}</p>', unsafe_allow_html=True)
        
        # Notes
        notes = image_data.get('notes', [])
        if notes:
            with st.expander(f"📝 EHR Notes ({len(notes)} found)", expanded=True):
                for i, note in enumerate(notes):
                    days_diff = note.get('days_diff', 0)
                    timing = "Same day" if days_diff == 0 else f"{abs(days_diff)} days {'before' if days_diff < 0 else 'after'}"
                    st.markdown(f'<p class="exam-detail"><b>Note {i+1}</b> | {note.get("note_date","N/A")} | {timing}</p>', unsafe_allow_html=True)
                    st.text_area(f"note_{i}", value=note.get('note_text', 'N/A'), height=200, disabled=True, key=f"note_{current_index}_{i}", label_visibility="collapsed")
                    if i < len(notes) - 1:
                        st.markdown("---")
        else:
            st.caption("No EHR notes found")
        
        # Annotations
        annotations = image_data.get('annotations', [])
        if annotations:
            with st.expander(f"🔬 Annotations ({len(annotations)} found)", expanded=True):
                import pandas as pd
                ann_by_lat = {}
                for ann in annotations:
                    ann_by_lat.setdefault(ann.get('laterality', 'Unknown'), []).append(ann)
                for lat, anns in ann_by_lat.items():
                    st.markdown(f'<p class="exam-detail"><b>{lat} Eye:</b></p>', unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame([{
                        'Field': a.get('examfield', 'N/A'),
                        'Value': a.get('value', 'N/A'),
                        'Date': str(a.get('annotation_date', 'N/A')),
                        'Days Diff': a.get('days_diff', 'N/A')
                    } for a in anns]), use_container_width=True, hide_index=True)
        else:
            st.caption("No annotations found")
    
    # RIGHT COLUMN
    with col_right:
        # Navigation
        progress = (current_position + 1) / len(route_indices)
        st.progress(progress)
        st.caption(f"Position: **{current_position + 1}** / {len(route_indices)} | Labeled: **{label_manager.get_labeled_count()}**")
        
        n1, n2, n3, n4 = st.columns(4)
        with n1:
            if st.button("⏮️ First", use_container_width=True):
                st.session_state.current_position = 0
                st.session_state._reset_labels = True
                st.rerun()
        with n2:
            if st.button("◀ Prev", use_container_width=True, help="← or A"):
                if current_position > 0:
                    st.session_state.current_position -= 1
                    st.session_state._reset_labels = True
                    st.rerun()
        with n3:
            if st.button("Next ▶", use_container_width=True, help="→ or D"):
                st.session_state.current_position += 1
                st.session_state._reset_labels = True
                st.rerun()
        with n4:
            if st.button("Last ⏭️", use_container_width=True):
                st.session_state.current_position = len(route_indices) - 1
                st.session_state._reset_labels = True
                st.rerun()
        
        st.markdown("---")
        
        if ai_suggestion and not existing_label:
            st.info("💡 **AI Suggestion** — review and save if correct")
        if existing_label:
            st.info(f"✏️ **Previously Labeled** on {existing_label.get('labeled_at','')}")
        
        # Labels (NO FORM - direct widgets)
        st.markdown("### 🏷️ Label This Image")
        
        laterality = st.selectbox("Laterality *", LATERALITY_OPTIONS, 
                                  index=LATERALITY_OPTIONS.index(st.session_state.label_laterality), key="lat_select")
        st.session_state.label_laterality = laterality
        
        quality = st.selectbox("Image Quality *", QUALITY_OPTIONS,
                              index=QUALITY_OPTIONS.index(st.session_state.label_quality), key="qual_select")
        st.session_state.label_quality = quality
        
        conditions_data = {}
        
        if quality == "Usable":
            st.markdown("#### 🔬 Conditions")
            
            # Dry Eye
            with st.expander("👁️ Dry Eye Disease", expanded=True):
                dry_sev = st.selectbox("Severity", DRY_EYE_SEVERITY,
                                      index=DRY_EYE_SEVERITY.index(st.session_state.dry_eye_severity), key="dry_sev_select")
                st.session_state.dry_eye_severity = dry_sev
                
                dry_signs = st.multiselect("Signs", DRY_EYE_SIGNS, default=st.session_state.dry_eye_signs, key="dry_signs_select")
                st.session_state.dry_eye_signs = dry_signs
                
                if dry_sev != "None":
                    conditions_data["Dry Eye Disease"] = {"severity": dry_sev, "signs": dry_signs}
            
            # Cataract
            with st.expander("🔍 Cataract", expanded=True):
                cat_type = st.selectbox("Type", CATARACT_TYPE,
                                       index=CATARACT_TYPE.index(st.session_state.cataract_type), key="cat_type_select")
                st.session_state.cataract_type = cat_type
                
                if cat_type not in ["None", "Pseudophakia", "Aphakia"]:
                    cat_sev = st.selectbox("Severity", CATARACT_SEVERITY,
                                          index=CATARACT_SEVERITY.index(st.session_state.cataract_severity), key="cat_sev_select")
                    st.session_state.cataract_severity = cat_sev
                    
                    cat_feat = st.multiselect("Features", CATARACT_FEATURES, default=st.session_state.cataract_features, key="cat_feat_select")
                    st.session_state.cataract_features = cat_feat
                    
                    conditions_data["Cataract"] = {"type": cat_type, "severity": cat_sev, "features": cat_feat}
                elif cat_type != "None":
                    conditions_data["Cataract"] = {"type": cat_type, "severity": None, "features": []}
            
            # Infectious
            with st.expander("🦠 Infectious", expanded=True):
                inf_type = st.selectbox("Type", INFECTIOUS_TYPE,
                                       index=INFECTIOUS_TYPE.index(st.session_state.infectious_type), key="inf_type_select")
                st.session_state.infectious_type = inf_type
                
                if inf_type not in ["No infection", "Unclear"]:
                    etiology = st.selectbox("Etiology", INFECTIOUS_ETIOLOGY,
                                           index=INFECTIOUS_ETIOLOGY.index(st.session_state.infectious_etiology), key="etiol_select")
                    st.session_state.infectious_etiology = etiology
                    
                    inf_data = {"type": inf_type, "etiology": etiology}
                    
                    if "Keratitis" in inf_type:
                        ker_size = st.selectbox("Keratitis Size", KERATITIS_SIZE,
                                               index=KERATITIS_SIZE.index(st.session_state.keratitis_size), key="ker_size_select")
                        st.session_state.keratitis_size = ker_size
                        
                        ker_feat = st.multiselect("Keratitis Features", KERATITIS_FEATURES, default=st.session_state.keratitis_features, key="ker_feat_select")
                        st.session_state.keratitis_features = ker_feat
                        
                        inf_data["keratitis_size"] = ker_size
                        inf_data["keratitis_features"] = ker_feat
                    
                    if "Conjunctivitis" in inf_type:
                        conj_feat = st.multiselect("Conjunctivitis Features", CONJUNCTIVITIS_FEATURES, default=st.session_state.conjunctivitis_features, key="conj_feat_select")
                        st.session_state.conjunctivitis_features = conj_feat
                        inf_data["conjunctivitis_features"] = conj_feat
                    
                    conditions_data["Infectious Keratitis / Conjunctivitis"] = inf_data
                elif inf_type != "No infection":
                    conditions_data["Infectious Keratitis / Conjunctivitis"] = {"type": inf_type}
            
            # Tumor
            with st.expander("🔬 Tumor", expanded=True):
                tumor_type = st.selectbox("Type", TUMOR_TYPE,
                                         index=TUMOR_TYPE.index(st.session_state.tumor_type), key="tumor_type_select")
                st.session_state.tumor_type = tumor_type
                
                if tumor_type not in ["No lesion", "Unclear"]:
                    mal = st.selectbox("Malignancy", TUMOR_MALIGNANCY,
                                      index=TUMOR_MALIGNANCY.index(st.session_state.tumor_malignancy), key="mal_select")
                    st.session_state.tumor_malignancy = mal
                    
                    loc = st.selectbox("Location", TUMOR_LOCATION,
                                      index=TUMOR_LOCATION.index(st.session_state.tumor_location), key="loc_select")
                    st.session_state.tumor_location = loc
                    
                    feat = st.multiselect("Features", TUMOR_FEATURES, default=st.session_state.tumor_features, key="tumor_feat_select")
                    st.session_state.tumor_features = feat
                    
                    conditions_data["Ocular Surface Tumors"] = {"type": tumor_type, "malignancy": mal, "location": loc, "features": feat}
                elif tumor_type != "No lesion":
                    conditions_data["Ocular Surface Tumors"] = {"type": tumor_type}
            
            # SCH
            with st.expander("🩸 SCH", expanded=True):
                sch_pres = st.selectbox("Presence", SCH_PRESENCE,
                                       index=SCH_PRESENCE.index(st.session_state.sch_presence), key="sch_pres_select")
                st.session_state.sch_presence = sch_pres
                
                if sch_pres == "Present":
                    sch_ext = st.selectbox("Extent", SCH_EXTENT,
                                          index=SCH_EXTENT.index(st.session_state.sch_extent), key="sch_ext_select")
                    st.session_state.sch_extent = sch_ext
                    conditions_data["Subconjunctival Hemorrhage"] = {"presence": sch_pres, "extent": sch_ext}
                elif sch_pres != "None":
                    conditions_data["Subconjunctival Hemorrhage"] = {"presence": sch_pres}
        
        # Buttons
        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Save Label", use_container_width=True, type="primary"):
                label_manager.add_label(
                    image_index=current_index,
                    image_path=image_data['image_path'],
                    laterality=laterality,
                    quality=quality,
                    conditions=conditions_data,
                    metadata={
                        'maskedid_studyid': image_data.get('maskedid_studyid'),
                        'exam_date': str(image_data.get('exam_date')),
                        'pat_mrn': image_data.get('pat_mrn')
                    }
                )
                st.success("✅ Saved!")
                st.session_state.labels_saved = st.session_state.get('labels_saved', 0) + 1
                st.session_state.current_position += 1
                st.session_state._reset_labels = True
                st.rerun()
        with b2:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.current_position += 1
                st.session_state._reset_labels = True
                st.rerun()
