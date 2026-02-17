"""
Labeling page with AI suggestion auto-fill support
Layout:
  - Left column:  Image (top) + Clinical Info / Notes / Annotations (below)
  - Right column: Navigation (top) + Labels form (below)
Keyboard shortcuts:
  - ArrowRight / d : Next image
  - ArrowLeft  / a : Previous image
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
)

# ─────────────────────────────────────────────────────────────
# Keyboard shortcut: ArrowRight/d → next, ArrowLeft/a → prev
# Targets Streamlit buttons by their key attribute
# ─────────────────────────────────────────────────────────────
KEYBOARD_JS = """
<script>
document.addEventListener('keydown', function(e) {
    const tag = document.activeElement.tagName.toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag)) return;

    if (e.key === 'ArrowRight' || e.key === 'd') {
        // find button whose aria-label or text contains "Next"
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

def _inject_keyboard():
    st.components.v1.html(KEYBOARD_JS, height=0)


def show():
    """Show labeling page with AI suggestion support"""

    st.markdown('<p class="main-header">🏷️ Image Labeling Interface</p>', unsafe_allow_html=True)

    _inject_keyboard()

    # Force black text inside expanders
    st.markdown("""
        <style>
        .streamlit-expanderContent p,
        .streamlit-expanderContent span,
        .streamlit-expanderContent div,
        .streamlit-expanderContent label,
        .streamlit-expanderContent textarea {
            color: #000000 !important;
        }
        .exam-detail { color: #000000 !important; font-size: 0.9rem; margin: 2px 0; }
        </style>
    """, unsafe_allow_html=True)

    # ── Data loader ───────────────────────────────────────────
    if 'data_loader' not in st.session_state:
        st.session_state.data_loader = DataLoader()
        from config.config import DEFAULT_DATASET_FILTER
        filter_mode = st.session_state.get('dataset_filter', DEFAULT_DATASET_FILTER)
        st.session_state.data_loader.filter_mode = filter_mode
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

    data_loader      = st.session_state.data_loader
    label_manager    = st.session_state.label_manager
    ai_label_manager = st.session_state.ai_label_manager

    # ── Route ─────────────────────────────────────────────────
    if 'route_indices' not in st.session_state:
        total_images   = data_loader.get_total_images()
        route_strategy = get_user_route_strategy(st.session_state.username)
        st.session_state.route_indices    = data_loader.create_route(total_images, route_strategy, st.session_state.username)
        st.session_state.current_position = 0

    route_indices    = st.session_state.route_indices
    current_position = st.session_state.current_position

    if current_position >= len(route_indices):
        st.success("🎉 You have reached the end of your route!")
        return

    current_index = route_indices[current_position]

    # ── Image data ────────────────────────────────────────────
    image_data, message = data_loader.get_image_data(current_index)
    if image_data is None:
        st.error(f"Error loading image: {message}")
        return

    existing_label = label_manager.get_label(current_index)
    ai_suggestion  = None
    if not existing_label:
        ai_suggestion = ai_label_manager.get_label_by_path(image_data['image_path'])

    source_label        = existing_label or ai_suggestion
    existing_conditions = source_label.get('conditions', {}) if source_label else {}

    # ═════════════════════════════════════════════════════════
    # LAYOUT
    # ═════════════════════════════════════════════════════════
    col_left, col_right = st.columns([1.2, 1])

    # ─────────────────────────────────────────────────────────
    # LEFT: Image  +  Clinical info below
    # ─────────────────────────────────────────────────────────
    with col_left:

        st.markdown("### 📷 Image")
        if image_data.get('studyid_counter'):
            st.caption(f"**Study:** {image_data['studyid_counter']}")

        image_path = Path(image_data['image_path'])
        if image_path.exists():
            try:
                st.image(Image.open(image_path), use_container_width=True)
            except Exception as e:
                st.error(f"Error loading image: {e}")
                st.code(str(image_path))
        else:
            st.warning("⚠️ Image file not found")
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

        # EHR Notes
        notes = image_data.get('notes', [])
        if notes:
            with st.expander(f"📝 EHR Notes ({len(notes)} found)", expanded=False):
                for i, note in enumerate(notes):
                    days_diff = note.get('days_diff', 0)
                    if days_diff == 0:
                        timing = "Same day as exam"
                    elif days_diff < 0:
                        timing = f"{abs(days_diff)} days before exam"
                    else:
                        timing = f"{days_diff} days after exam"

                    st.markdown(
                        f'<p class="exam-detail"><b>Note {i+1}</b> &nbsp;|&nbsp;'
                        f' {note.get("note_date","N/A")} &nbsp;|&nbsp; {timing}</p>',
                        unsafe_allow_html=True
                    )
                    st.text_area(
                        f"note_{i}",
                        value=note.get('note_text', 'No text available'),
                        height=200,
                        disabled=True,
                        key=f"note_{current_index}_{i}",
                        label_visibility="collapsed"
                    )
                    if i < len(notes) - 1:
                        st.markdown("---")
        else:
            st.caption("No EHR notes found for this image.")

        # Annotations
        annotations = image_data.get('annotations', [])
        if annotations:
            with st.expander(f"🔬 Annotations ({len(annotations)} found)", expanded=False):
                import pandas as pd
                ann_by_lat = {}
                for ann in annotations:
                    ann_by_lat.setdefault(ann.get('laterality', 'Unknown'), []).append(ann)
                for lat, anns in ann_by_lat.items():
                    st.markdown(f'<p class="exam-detail"><b>{lat} Eye:</b></p>', unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame([{
                        'Field': a.get('examfield', 'N/A'),
                        'Value': a.get('value', 'N/A'),
                        'Date':  str(a.get('annotation_date', 'N/A')),
                        'Days Diff': a.get('days_diff', 'N/A')
                    } for a in anns]), use_container_width=True, hide_index=True)
        else:
            st.caption("No annotations found for this image.")

    # ─────────────────────────────────────────────────────────
    # RIGHT: Navigation (top)  +  Labels form
    # ─────────────────────────────────────────────────────────
    with col_right:

        # ── Navigation ────────────────────────────────────────
        progress = (current_position + 1) / len(route_indices)
        st.progress(progress)
        st.caption(
            f"Position: **{current_position + 1}** / {len(route_indices)} &nbsp;|&nbsp; "
            f"Labeled: **{label_manager.get_labeled_count()}**"
        )

        n1, n2, n3, n4 = st.columns(4)
        with n1:
            if st.button("⏮️ First", use_container_width=True):
                st.session_state.current_position = 0
                st.rerun()
        with n2:
            if st.button("◀ Prev", use_container_width=True, help="← or A"):
                if current_position > 0:
                    st.session_state.current_position -= 1
                    st.rerun()
        with n3:
            if st.button("Next ▶", use_container_width=True, help="→ or D"):
                st.session_state.current_position += 1
                st.rerun()
        with n4:
            if st.button("Last ⏭️", use_container_width=True):
                st.session_state.current_position = len(route_indices) - 1
                st.rerun()

        st.markdown("---")

        # ── AI / existing label indicator ─────────────────────
        if ai_suggestion and not existing_label:
            st.info("💡 **AI Suggestion** — review and save if correct")
        if existing_label:
            st.info(f"✏️ **Previously Labeled** on {existing_label.get('labeled_at','')}")

        # ── Label form ────────────────────────────────────────
        st.markdown("### 🏷️ Label This Image")

        with st.form("labeling_form"):

            # Laterality
            lat_idx = 0
            if source_label and source_label.get('laterality') in LATERALITY_OPTIONS:
                lat_idx = LATERALITY_OPTIONS.index(source_label['laterality'])
            laterality = st.selectbox("Laterality *", LATERALITY_OPTIONS, index=lat_idx)

            # Quality
            qual_idx = 0
            if source_label and source_label.get('quality') in QUALITY_OPTIONS:
                qual_idx = QUALITY_OPTIONS.index(source_label['quality'])
            quality = st.selectbox("Image Quality *", QUALITY_OPTIONS, index=qual_idx)

            conditions_data = {}

            if quality == "Usable":
                st.markdown("#### 🔬 Conditions")

                # Dry Eye
                with st.expander("👁️ Dry Eye Disease",
                                  expanded="Dry Eye Disease" in existing_conditions):
                    sev_idx = 0
                    if "Dry Eye Disease" in existing_conditions:
                        s = existing_conditions["Dry Eye Disease"].get("severity","None")
                        if s in DRY_EYE_SEVERITY: sev_idx = DRY_EYE_SEVERITY.index(s)
                    dry_sev = st.selectbox("Severity", DRY_EYE_SEVERITY, index=sev_idx, key="dry_sev")
                    default_signs = [s for s in existing_conditions.get("Dry Eye Disease",{}).get("signs",[]) if s in DRY_EYE_SIGNS]
                    dry_signs = st.multiselect("Signs", DRY_EYE_SIGNS, default=default_signs, key="dry_signs")
                    if dry_sev != "None":
                        conditions_data["Dry Eye Disease"] = {"severity": dry_sev, "signs": dry_signs}

                # Cataract
                with st.expander("🔍 Cataract", expanded="Cataract" in existing_conditions):
                    ct_idx = 0
                    if "Cataract" in existing_conditions:
                        ct = existing_conditions["Cataract"].get("type","None")
                        if ct in CATARACT_TYPE: ct_idx = CATARACT_TYPE.index(ct)
                    cat_type = st.selectbox("Type", CATARACT_TYPE, index=ct_idx, key="cat_type")
                    if cat_type not in ["None","Pseudophakia","Aphakia"]:
                        cs_idx = 0
                        if "Cataract" in existing_conditions:
                            cs = existing_conditions["Cataract"].get("severity","Mild")
                            if cs in CATARACT_SEVERITY: cs_idx = CATARACT_SEVERITY.index(cs)
                        cat_sev  = st.selectbox("Severity", CATARACT_SEVERITY, index=cs_idx, key="cat_sev")
                        def_feat = [f for f in existing_conditions.get("Cataract",{}).get("features",[]) if f in CATARACT_FEATURES]
                        cat_feat = st.multiselect("Features", CATARACT_FEATURES, default=def_feat, key="cat_feat")
                        if cat_type != "None":
                            conditions_data["Cataract"] = {"type": cat_type, "severity": cat_sev, "features": cat_feat}
                    elif cat_type != "None":
                        conditions_data["Cataract"] = {"type": cat_type, "severity": None, "features": []}

                # Infectious
                with st.expander("🦠 Infectious Keratitis / Conjunctivitis",
                                  expanded="Infectious Keratitis / Conjunctivitis" in existing_conditions):
                    ni_idx = INFECTIOUS_TYPE.index("No infection") if "No infection" in INFECTIOUS_TYPE else 0
                    if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                        it = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("type","No infection")
                        if it in INFECTIOUS_TYPE: ni_idx = INFECTIOUS_TYPE.index(it)
                    inf_type = st.selectbox("Type", INFECTIOUS_TYPE, index=ni_idx, key="inf_type")
                    if inf_type not in ["No infection","Unclear"]:
                        et_idx = 0
                        if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                            et = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("etiology")
                            if et and et in INFECTIOUS_ETIOLOGY: et_idx = INFECTIOUS_ETIOLOGY.index(et)
                        etiology  = st.selectbox("Etiology", INFECTIOUS_ETIOLOGY, index=et_idx, key="inf_etiol")
                        inf_data  = {"type": inf_type, "etiology": etiology}
                        if "Keratitis" in inf_type:
                            ks_idx = 0
                            if "Infectious Keratitis / Conjunctivitis" in existing_conditions:
                                ks = existing_conditions["Infectious Keratitis / Conjunctivitis"].get("keratitis_size")
                                if ks and ks in KERATITIS_SIZE: ks_idx = KERATITIS_SIZE.index(ks)
                            inf_data["keratitis_size"] = st.selectbox("Keratitis Size", KERATITIS_SIZE, index=ks_idx, key="ker_size")
                            def_kf = [f for f in existing_conditions.get("Infectious Keratitis / Conjunctivitis",{}).get("keratitis_features",[]) if f in KERATITIS_FEATURES]
                            inf_data["keratitis_features"] = st.multiselect("Keratitis Features", KERATITIS_FEATURES, default=def_kf, key="ker_feat")
                        if "Conjunctivitis" in inf_type:
                            def_cf = [f for f in existing_conditions.get("Infectious Keratitis / Conjunctivitis",{}).get("conjunctivitis_features",[]) if f in CONJUNCTIVITIS_FEATURES]
                            inf_data["conjunctivitis_features"] = st.multiselect("Conjunctivitis Features", CONJUNCTIVITIS_FEATURES, default=def_cf, key="conj_feat")
                        conditions_data["Infectious Keratitis / Conjunctivitis"] = inf_data
                    elif inf_type != "No infection":
                        conditions_data["Infectious Keratitis / Conjunctivitis"] = {"type": inf_type}

                # Tumors
                with st.expander("🔬 Ocular Surface Tumors",
                                  expanded="Ocular Surface Tumors" in existing_conditions):
                    nl_idx = TUMOR_TYPE.index("No lesion") if "No lesion" in TUMOR_TYPE else 0
                    if "Ocular Surface Tumors" in existing_conditions:
                        tt = existing_conditions["Ocular Surface Tumors"].get("type","No lesion")
                        if tt in TUMOR_TYPE: nl_idx = TUMOR_TYPE.index(tt)
                    tumor_type = st.selectbox("Type", TUMOR_TYPE, index=nl_idx, key="tumor_type")
                    if tumor_type not in ["No lesion","Unclear"]:
                        mal_idx = 0
                        if "Ocular Surface Tumors" in existing_conditions:
                            mal = existing_conditions["Ocular Surface Tumors"].get("malignancy")
                            if mal and mal in TUMOR_MALIGNANCY: mal_idx = TUMOR_MALIGNANCY.index(mal)
                        malignancy = st.selectbox("Malignancy", TUMOR_MALIGNANCY, index=mal_idx, key="tumor_mal")
                        loc_idx = 0
                        if "Ocular Surface Tumors" in existing_conditions:
                            loc = existing_conditions["Ocular Surface Tumors"].get("location")
                            if loc and loc in TUMOR_LOCATION: loc_idx = TUMOR_LOCATION.index(loc)
                        location = st.selectbox("Location", TUMOR_LOCATION, index=loc_idx, key="tumor_loc")
                        def_tf = [f for f in existing_conditions.get("Ocular Surface Tumors",{}).get("features",[]) if f in TUMOR_FEATURES]
                        tumor_feat = st.multiselect("Features", TUMOR_FEATURES, default=def_tf, key="tumor_feat")
                        conditions_data["Ocular Surface Tumors"] = {
                            "type": tumor_type, "malignancy": malignancy,
                            "location": location, "features": tumor_feat}
                    elif tumor_type != "No lesion":
                        conditions_data["Ocular Surface Tumors"] = {"type": tumor_type}

                # SCH
                with st.expander("🩸 Subconjunctival Hemorrhage",
                                  expanded="Subconjunctival Hemorrhage" in existing_conditions):
                    none_idx = SCH_PRESENCE.index("None") if "None" in SCH_PRESENCE else 0
                    if "Subconjunctival Hemorrhage" in existing_conditions:
                        pr = existing_conditions["Subconjunctival Hemorrhage"].get("presence","None")
                        if pr in SCH_PRESENCE: none_idx = SCH_PRESENCE.index(pr)
                    sch_pres = st.selectbox("Presence", SCH_PRESENCE, index=none_idx, key="sch_pres")
                    if sch_pres == "Present":
                        ext_idx = 0
                        if "Subconjunctival Hemorrhage" in existing_conditions:
                            ext = existing_conditions["Subconjunctival Hemorrhage"].get("extent")
                            if ext and ext in SCH_EXTENT: ext_idx = SCH_EXTENT.index(ext)
                        sch_ext = st.selectbox("Extent", SCH_EXTENT, index=ext_idx, key="sch_ext")
                        conditions_data["Subconjunctival Hemorrhage"] = {"presence": sch_pres, "extent": sch_ext}
                    elif sch_pres != "None":
                        conditions_data["Subconjunctival Hemorrhage"] = {"presence": sch_pres}

            # ── Buttons ───────────────────────────────────────
            b1, b2 = st.columns(2)
            with b1:
                submitted = st.form_submit_button("💾 Save Label", use_container_width=True)
            with b2:
                skip = st.form_submit_button("⏭️ Skip", use_container_width=True)

            if submitted:
                label_manager.add_label(
                    image_index=current_index,
                    image_path=image_data['image_path'],
                    laterality=laterality,
                    quality=quality,
                    conditions=conditions_data,
                    metadata={
                        'maskedid_studyid': image_data.get('maskedid_studyid'),
                        'exam_date':        str(image_data.get('exam_date')),
                        'pat_mrn':          image_data.get('pat_mrn')
                    }
                )
                st.success("✅ Label saved!")
                st.session_state.labels_saved = st.session_state.get('labels_saved', 0) + 1
                st.session_state.current_position += 1
                st.rerun()

            if skip:
                st.session_state.current_position += 1
                st.rerun()
