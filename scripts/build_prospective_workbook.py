"""
Build the prospective data collection workbook.

Generates prospective/Prospective_AI_Image_Collection.xlsx from three sources so
the three stay aligned:

  * config/config.py      - the label taxonomy the retrospective app produces,
                            so prospective rows can train the same model
  * the Epic eye exam      - the structured pick-lists doctors already fill in
                            (Lids/Lashes, Conjunctiva/Sclera, Cornea, AC, Iris,
                            Lens), including Epic's own Trace/1+..4+ grading
  * the students' CSV      - the columns they had already decided they needed

Re-run this script to regenerate the blank workbook. It never touches a filled
copy: it refuses to overwrite an existing file unless --force is passed.
"""

import argparse
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.append(str(Path(__file__).parent.parent))

from config.config import (  # noqa: E402
    CATARACT_SEVERITY,
    ILLUMINATION_OPTIONS,
    TUMOR_LOCATION,
)

# ======================================================
# Controlled vocabularies
# ======================================================
# Each entry becomes a column on the Lists sheet and a dropdown wherever it is
# referenced. Keep option text identical to the app / Epic wording.

LISTS = {
    "YesNo": ["Yes", "No"],
    "YesNoUnk": ["Yes", "No", "Unknown"],
    "Sex": ["M", "F", "Other", "Unknown"],
    "Eye": ["OD", "OS"],
    # Epic grades severity as Trace/1+..4+; keep both variants so a column only
    # offers Trace where Epic does.
    "Grade": ["None", "Trace", "1+", "2+", "3+", "4+"],
    "GradeNoTrace": ["None", "1+", "2+", "3+", "4+"],
    "Smoking": ["Never", "Former", "Current", "Unknown"],
    "SunExposure": ["Low", "Moderate", "High", "Unknown"],
    "Certainty": ["Definite", "Probable", "Possible"],
    # Primary diagnosis: the app's five categories, expanded with the specific
    # entities already appearing in the students' sheet.
    "Diagnosis": [
        "Normal / no disease",
        "OSSN - CIN",
        "OSSN - invasive SCC",
        "OSSN - resolved / treated",
        "Conjunctival melanoma",
        "Primary acquired melanosis (PAM)",
        "Conjunctival nevus",
        "Conjunctival papilloma",
        "Conjunctival lymphoma",
        "Pterygium",
        "Pinguecula",
        "Infectious keratitis - bacterial",
        "Infectious keratitis - fungal",
        "Infectious keratitis - herpetic (HSV/VZV)",
        "Infectious keratitis - Acanthamoeba",
        "Infectious conjunctivitis",
        "Dry eye disease",
        "Meibomian gland dysfunction",
        "Rosacea keratitis",
        "Corneal scar / opacity",
        "Corneal dystrophy",
        "Corneal graft / post-keratoplasty",
        "Cataract",
        "Pseudophakia",
        "Subconjunctival hemorrhage",
        "Other (specify in notes)",
    ],
    "PastSurgery": [
        "None",
        "Cataract extraction",
        "Pterygium excision",
        "OSSN excision",
        "Keratoplasty - PKP",
        "Keratoplasty - DSAEK/DMEK",
        "Amniotic membrane graft",
        "Glaucoma surgery / tube",
        "Retina surgery",
        "Refractive surgery",
        "Other (specify)",
    ],
    "Treatment": ["None", "Medical", "Surgical", "Medical + Surgical"],
    "MedicalTx": [
        "None",
        "Topical interferon",
        "Topical 5-FU",
        "Topical mitomycin C",
        "Topical steroid",
        "Topical antibiotic",
        "Topical antiviral",
        "Topical antifungal",
        "Lubricants only",
        "Other (specify)",
    ],
    "LensStatus": ["Phakic", "PCIOL", "ACIOL", "Aphakic", "Not visible"],
    "Infiltrate": ["None", "Sterile", "Sub-epithelial", "Stromal"],
    "Hyphema": ["None", "Layered", "Total"],
    "ACDepth": ["Deep", "Shallow", "Flat", "Narrow"],
    "Opacity": ["None", "Central", "Peripheral", "Both"],
    "Keratoplasty": ["None", "PKP", "LKP", "DSAEK", "DMEK"],
    "Neoplasm": ["None", "Benign", "Malignant", "Indeterminate"],
    "Quadrant": TUMOR_LOCATION + ["Diffuse / circumferential"],
    "LesionAppearance": [
        "Gelatinous",
        "Leukoplakic",
        "Papilliform",
        "Nodular",
        "Diffuse / sheet-like",
        "Pigmented",
        "Cystic",
        "Opalescent",
    ],
    "Illumination": ILLUMINATION_OPTIONS,
    "Quality": ["Usable", "Non Usable"],
    "ImageLaterality": ["OD", "OS", "Both eyes visible"],
    "Stain": ["None", "Fluorescein", "Lissamine green", "Rose bengal"],
    "Severity": CATARACT_SEVERITY,
    "Pathology": [
        "Not done",
        "Pending",
        "Benign",
        "Dysplasia - mild",
        "Dysplasia - moderate",
        "Dysplasia - severe / CIS",
        "Invasive SCC",
        "Melanoma",
        "Other (specify)",
    ],
}

# ======================================================
# Sheet definitions
# ======================================================
# (header, list_name or None, width, help text). list_name None = free entry.

VISIT_COLUMNS = [
    ("study_id", None, 12, "Study ID, e.g. ckai001. Must match the other sheets."),
    ("visit_date", None, 12, "Date of this visit (YYYY-MM-DD)."),
    ("age_at_visit", None, 12, "Age in years. Use this instead of date of birth."),
    ("sex", "Sex", 8, "Sex."),
    ("consent_obtained", "YesNo", 16, "Written consent obtained for imaging and research use."),
    ("consent_date", None, 13, "Date consent was signed."),
    ("clinician", None, 16, "Attending who performed the exam."),
    ("chief_complaint", None, 30, "Reason for the visit, in the patient's words."),
    ("clinical_diagnosis_text", None, 40, "Free-text impression, as written in the chart."),
    ("images_taken", "YesNo", 13, "Were slit lamp photographs taken at this visit?"),
    ("diabetes", "YesNoUnk", 10, "History of diabetes mellitus."),
    ("immunosuppressed", "YesNoUnk", 17, "On immunosuppression, or immunosuppressed for any reason."),
    ("hiv_status", "YesNoUnk", 12, "HIV positive. Strong risk factor for OSSN - ask actively."),
    ("cancer_history", "YesNoUnk", 15, "Any prior malignancy."),
    ("autoimmune_disease", "YesNoUnk", 18, "Rheumatoid arthritis, Sjogren, etc."),
    ("smoking", "Smoking", 11, "Smoking status."),
    ("sun_exposure", "SunExposure", 14, "Lifetime UV exposure. Ask: outdoor work, hours/day outdoors."),
    ("outdoor_occupation", "YesNoUnk", 18, "Works or worked mainly outdoors."),
    ("visit_notes", None, 40, "Anything else worth recording about this visit."),
]

EYE_COLUMNS = [
    # --- identity -------------------------------------------------------
    ("study_id", None, 12, "Must match the Visit sheet."),
    ("visit_date", None, 12, "Must match the Visit sheet."),
    ("eye", "Eye", 7, "OD (right) or OS (left). One row per eye."),
    # --- headline -------------------------------------------------------
    ("eye_diseased", "YesNo", 13, "Does this eye have the condition under study?"),
    ("eye_diagnosis", "Diagnosis", 34, "Working diagnosis for THIS eye."),
    ("diagnosis_certainty", "Certainty", 18, "How confident is the clinician?"),
    ("exam_all_normal", "YesNo", 15, "Yes = whole slit lamp exam normal. Then leave the exam block blank."),
    # --- function -------------------------------------------------------
    ("va_cc", None, 9, "Best corrected visual acuity, e.g. 20/40."),
    ("va_sc", None, 9, "Uncorrected visual acuity."),
    ("iop_mmhg", None, 10, "Intraocular pressure in mmHg."),
    # --- history --------------------------------------------------------
    ("past_ocular_surgery", "PastSurgery", 24, "Most relevant previous surgery on this eye."),
    ("past_ocular_surgery_detail", None, 26, "Which procedure, and roughly when."),
    ("past_ocular_disease", None, 26, "Prior ocular disease in this eye."),
    ("current_medical_tx", "MedicalTx", 22, "Treatment this eye is on right now."),
    ("current_medical_tx_detail", None, 24, "Drug, concentration, schedule."),
    # --- lids / lashes ---------------------------------------------------
    ("lids_mgd", "GradeNoTrace", 11, "Meibomian gland dysfunction (Epic grading)."),
    ("lids_blepharitis", "GradeNoTrace", 16, "Blepharitis."),
    ("lids_telangiectasia", "YesNo", 19, "Lid margin telangiectasia."),
    ("lids_trichiasis", "YesNo", 15, "Lashes touching the globe."),
    ("lids_other", None, 20, "Any other lid finding."),
    # --- conjunctiva / sclera --------------------------------------------
    ("conj_injection", "Grade", 14, "Conjunctival injection."),
    ("conj_chemosis", "Grade", 13, "Chemosis."),
    ("conj_follicles", "GradeNoTrace", 14, "Follicles."),
    ("conj_papillae", "GradeNoTrace", 13, "Papillae."),
    ("conj_pinguecula", "YesNo", 15, "Pinguecula present."),
    ("conj_pterygium", "YesNo", 14, "Pterygium present."),
    ("conj_pterygium_extent_mm", None, 22, "How far it encroaches onto the cornea, in mm."),
    ("conj_neoplasm", "Neoplasm", 14, "Conjunctival neoplasm, as graded clinically."),
    ("conj_pigmentation", "YesNo", 17, "Pigmented conjunctival lesion or melanosis."),
    ("conj_subconj_hemorrhage", "GradeNoTrace", 22, "Subconjunctival hemorrhage."),
    ("conj_conjunctivochalasis", "YesNo", 22, "Redundant conjunctival folds."),
    ("conj_other", None, 20, "Any other conjunctival or scleral finding."),
    # --- cornea -----------------------------------------------------------
    ("cornea_pee", "GradeNoTrace", 12, "Punctate epithelial erosions / SPK."),
    ("cornea_epithelial_defect", "YesNo", 22, "Epithelial defect present."),
    ("cornea_epi_defect_size_mm", None, 22, "Largest diameter of the defect, in mm."),
    ("cornea_infiltrate", "Infiltrate", 17, "Infiltrate and its type."),
    ("cornea_ulcer", "YesNo", 13, "Corneal ulcer present."),
    ("cornea_ulcer_size_mm", None, 19, "Largest diameter of the ulcer, in mm."),
    ("cornea_dendrite", "YesNo", 15, "Dendritic or pseudodendritic lesion."),
    ("cornea_edema", "GradeNoTrace", 13, "Corneal edema."),
    ("cornea_guttata", "GradeNoTrace", 14, "Guttata."),
    ("cornea_kp", "GradeNoTrace", 11, "Keratic precipitates."),
    ("cornea_neovascularization", "YesNo", 23, "Corneal neovascularization."),
    ("cornea_opacity", "Opacity", 14, "Scar or opacity, and where."),
    ("cornea_keratoplasty", "Keratoplasty", 19, "Previous corneal graft in place."),
    ("cornea_other", None, 20, "Any other corneal finding."),
    # --- anterior chamber -------------------------------------------------
    ("ac_cell", "Grade", 9, "Anterior chamber cell."),
    ("ac_flare", "Grade", 10, "Anterior chamber flare."),
    ("ac_hypopyon_mm", None, 15, "Hypopyon height in mm. Leave blank if none."),
    ("ac_hyphema", "Hyphema", 12, "Hyphema."),
    ("ac_depth", "ACDepth", 10, "Chamber depth."),
    # --- iris / lens ------------------------------------------------------
    ("iris_findings", None, 22, "Nevus, atrophy, synechiae, NVI, transillumination defects..."),
    ("lens_status", "LensStatus", 13, "Phakic, pseudophakic (which IOL), or aphakic."),
    ("lens_nuclear_sclerosis", "Grade", 21, "Nuclear sclerosis."),
    ("lens_cortical", "GradeNoTrace", 14, "Cortical changes."),
    ("lens_psc", "GradeNoTrace", 11, "Posterior subcapsular cataract."),
    ("lens_pco", "GradeNoTrace", 11, "Posterior capsular opacification."),
    # --- lesion characterisation ------------------------------------------
    ("lesion_present", "YesNo", 15, "Is there a discrete lesion to characterise?"),
    ("lesion_clock_from", None, 18, "Start of the lesion in clock hours (1-12), as Epic records it."),
    ("lesion_clock_to", None, 16, "End of the lesion in clock hours (1-12)."),
    ("lesion_quadrant", "Quadrant", 22, "Main quadrant involved."),
    ("lesion_size_h_mm", None, 17, "Horizontal diameter in mm."),
    ("lesion_size_v_mm", None, 17, "Vertical diameter in mm."),
    ("lesion_limbal_involvement", "YesNo", 24, "Does it cross the limbus?"),
    ("lesion_corneal_involvement", "YesNo", 25, "Does it extend onto the cornea?"),
    ("lesion_appearance", "LesionAppearance", 22, "Dominant morphology."),
    ("lesion_feeder_vessels", "YesNo", 20, "Prominent feeder vessels."),
    # --- ancillary ---------------------------------------------------------
    ("slit_lamp_photo_taken", "YesNo", 20, "Photographs taken of this eye. If Yes, fill the Images sheet."),
    ("as_oct_done", "YesNo", 12, "Anterior segment OCT performed."),
    ("oct_done", "YesNo", 10, "Posterior OCT performed."),
    ("biopsy_done", "YesNo", 12, "Tissue taken."),
    ("pathology_result", "Pathology", 22, "Histopathology, once it comes back. The reference standard."),
    # --- plan ---------------------------------------------------------------
    ("treatment_plan", "Treatment", 17, "What was decided at this visit."),
    ("treatment_detail", None, 28, "Which drug or procedure."),
    ("eye_notes", None, 40, "Anything the columns above do not capture."),
]

IMAGE_COLUMNS = [
    ("image_filename", None, 38, "Exact file name as saved by the camera. This is the key that links the image to its label."),
    ("study_id", None, 12, "Must match the Visit sheet."),
    ("visit_date", None, 12, "Must match the Visit sheet."),
    ("eye", "Eye", 7, "Which eye this photograph shows."),
    ("image_laterality", "ImageLaterality", 20, "What is actually visible in the frame. 'Both eyes visible' matters for training."),
    ("capture_time", None, 13, "Time the photo was taken (HH:MM)."),
    ("device", None, 18, "Camera / slit lamp model."),
    ("illumination", "Illumination", 20, "Slit lamp illumination technique. Same list as the labeling app."),
    ("magnification", None, 14, "Magnification used, e.g. 10x."),
    ("stain", "Stain", 16, "Any stain applied before this photo."),
    ("quality", "Quality", 12, "Would you use this image to train a model?"),
    ("quality_problem", None, 24, "If Non Usable: blurred, over-exposed, lashes in the way, ..."),
    ("ground_truth_diagnosis", "Diagnosis", 34, "What this image shows. This is the training label."),
    ("photographer", None, 16, "Who took the photograph."),
    ("image_notes", None, 34, "Anything unusual about this image."),
]

PHI_COLUMNS = [
    ("study_id", None, 12, "Links to every other sheet."),
    ("mrn", None, 14, "Medical record number."),
    ("first_name", None, 18, ""),
    ("last_name", None, 20, ""),
    ("date_of_birth", None, 14, "Keep here only. Use age_at_visit on the Visit sheet."),
    ("enrolled_date", None, 14, ""),
    ("linkage_notes", None, 30, ""),
]

# Collapsible sections on the wide exam sheet, given as the first and last
# column NAME of each block. Deriving the letters keeps the groups correct when
# a column is inserted, which hardcoded letters silently would not.
EYE_GROUPS = [
    ("va_cc", "current_medical_tx_detail", "function + history"),
    ("lids_mgd", "lids_other", "lids"),
    ("conj_injection", "conj_other", "conjunctiva"),
    ("cornea_pee", "cornea_other", "cornea"),
    ("ac_cell", "ac_depth", "anterior chamber"),
    ("iris_findings", "lens_pco", "iris + lens"),
    ("lesion_present", "lesion_feeder_vessels", "lesion"),
    ("slit_lamp_photo_taken", "pathology_result", "ancillary"),
]


def column_letter_for(columns, name):
    """Spreadsheet letter of a named column."""
    for index, (column_name, *_rest) in enumerate(columns, start=1):
        if column_name == name:
            return get_column_letter(index)
    raise KeyError(f"{name} is not a column on this sheet")

# ======================================================
# Styling
# ======================================================

HEADER_FILL = PatternFill("solid", fgColor="1F77B4")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
PHI_FILL = PatternFill("solid", fgColor="C00000")
TITLE_FONT = Font(bold=True, size=14, color="1F77B4")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(bottom=THIN)


def write_header(ws, columns, fill=HEADER_FILL):
    """Header row + comments + widths + freeze panes."""
    for index, (name, list_name, width, help_text) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=index, value=name)
        cell.fill = fill
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(index)].width = width

        # The help text goes in row 2 so it is always visible while typing,
        # rather than hidden in a comment nobody hovers over.
        note = ws.cell(row=2, column=index, value=help_text)
        note.font = Font(italic=True, size=8, color="808080")
        note.alignment = Alignment(vertical="top", wrap_text=True)

    ws.row_dimensions[1].height = 32
    ws.row_dimensions[2].height = 46
    ws.freeze_panes = "D3"


def add_validations(ws, columns, n_rows):
    """Attach a dropdown to every column that has a controlled vocabulary."""
    for index, (name, list_name, _width, _help) in enumerate(columns, start=1):
        if not list_name:
            continue
        letter = get_column_letter(index)
        column_index = list(LISTS).index(list_name) + 1
        list_letter = get_column_letter(column_index)
        size = len(LISTS[list_name])
        validation = DataValidation(
            type="list",
            formula1=f"=Lists!${list_letter}$2:${list_letter}${size + 1}",
            allow_blank=True,
            showDropDown=False,          # False = show the dropdown arrow
            errorTitle="Not in the list",
            error=f"Pick one of the {size} allowed values for {name}.",
            promptTitle=name,
            prompt=_help_for(columns, name),
        )
        ws.add_data_validation(validation)
        validation.add(f"{letter}3:{letter}{n_rows + 2}")


def _help_for(columns, name):
    for column_name, _list, _width, help_text in columns:
        if column_name == name:
            return help_text
    return ""


def build_lists_sheet(wb):
    ws = wb.create_sheet("Lists")
    for column_index, (list_name, values) in enumerate(LISTS.items(), start=1):
        header = ws.cell(row=1, column=column_index, value=list_name)
        header.fill = HEADER_FILL
        header.font = HEADER_FONT
        ws.column_dimensions[get_column_letter(column_index)].width = max(14, len(list_name) + 4)
        for row_index, value in enumerate(values, start=2):
            ws.cell(row=row_index, column=column_index, value=value)
    ws.freeze_panes = "A2"
    ws.sheet_properties.tabColor = "808080"
    return ws


def build_readme(wb):
    ws = wb.create_sheet("README", 0)
    ws.column_dimensions["A"].width = 118
    lines = [
        ("Prospective AI Image Collection", "title"),
        ("", None),
        ("What this workbook is for", "h"),
        ("Every patient photographed in clinic is recorded here. The rows feed two things at once:", None),
        ("  1. training data for the slit lamp AI model, and", None),
        ("  2. the clinical study itself.", None),
        ("The vocabulary matches the retrospective labeling app and the Epic eye exam, so prospective", None),
        ("and retrospective data can be pooled without re-mapping anything.", None),
        ("", None),
        ("How to fill it in", "h"),
        ("Sheet 1 - Visit       one row per patient visit.", None),
        ("Sheet 2 - Eye_Exam    one row per EYE per visit, so normally two rows per visit (OD and OS).", None),
        ("Sheet 3 - Images      one row per photograph. This is what links a picture to its label.", None),
        ("Sheet 4 - PHI_Linkage study_id to MRN and name. See the warning below.", None),
        ("Lists                 the allowed values behind every dropdown. Edit here to change a dropdown.", None),
        ("", None),
        ("Row 1 is the column name. Row 2 explains the column - leave it in place, start typing on row 3.", None),
        ("Grey cells with a dropdown arrow only accept values from the list. Everything else is free text.", None),
        ("Blank means 'not assessed'. It does not mean normal - use exam_all_normal = Yes for that.", None),
        ("", None),
        ("Filling it fast", "h"),
        ("If the slit lamp exam is unremarkable, set exam_all_normal = Yes and leave the whole exam block", None),
        ("blank. Only fill the detail columns when there is something to record.", None),
        ("The exam columns are grouped by anatomical section (lids, conjunctiva, cornea, anterior chamber,", None),
        ("iris/lens, lesion, ancillary). Use the +/- buttons above the column letters to collapse the", None),
        ("sections you are not using.", None),
        ("", None),
        ("Grading", "h"),
        ("Severity uses Epic's own scale - Trace, 1+, 2+, 3+, 4+ - so numbers can be compared directly", None),
        ("against what is already in the chart. Sizes are in millimetres. Lesion position uses clock hours", None),
        ("(1-12), which is how Epic records it.", None),
        ("", None),
        ("Linking images to labels", "h"),
        ("image_filename on the Images sheet must be the exact file name from the camera. That is the only", None),
        ("thing tying a photograph to its ground truth, so a typo there costs you the image.", None),
        ("Keep study_id, visit_date and eye identical across all three sheets.", None),
        ("", None),
        ("PATIENT PRIVACY - READ THIS", "warn"),
        ("The PHI_Linkage sheet holds names, MRNs and dates of birth. The other sheets deliberately do not:", None),
        ("they carry study_id and age only.", None),
        ("  - Keep this workbook on hospital-managed storage. Do not put it in Dropbox, personal email,", None),
        ("    or the code repository.", None),
        ("  - Before sharing data with anyone outside the study, delete the PHI_Linkage sheet and save", None),
        ("    under a new name.", None),
        ("  - Better still, keep PHI_Linkage as a separate password-protected file from day one.", None),
        ("", None),
        ("Questions the first draft left open", "h"),
        ("date of birth      -> replaced by age_at_visit. DOB lives only on PHI_Linkage.", None),
        ("how granular       -> as granular as Epic already is, and no more. Every graded column mirrors an", None),
        ("                      Epic field, so the doctor is not being asked to think in a new scale.", None),
        ("which surgeries    -> past_ocular_surgery dropdown, with a free-text detail column beside it.", None),
        ("how to code disease-> eye_diagnosis dropdown. Add new entries on the Lists sheet, never free-type", None),
        ("                      into the column, or the categories will drift apart.", None),
        ("consent / flow     -> consent_obtained and consent_date on the Visit sheet. Suggested order in", None),
        ("                      clinic: consent first, then photograph, then fill Visit + Eye_Exam from the", None),
        ("                      chart, then Images from the camera's file list at the end of the session.", None),
    ]
    row = 1
    for text, kind in lines:
        cell = ws.cell(row=row, column=1, value=text)
        if kind == "title":
            cell.font = TITLE_FONT
        elif kind == "h":
            cell.font = Font(bold=True, size=11, color="1F77B4")
        elif kind == "warn":
            cell.font = Font(bold=True, size=11, color="C00000")
        else:
            cell.font = Font(size=10)
        cell.alignment = Alignment(vertical="center")
        row += 1
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = "1F77B4"
    return ws


def build(output_path, n_rows=400):
    wb = Workbook()
    wb.remove(wb.active)

    build_readme(wb)

    for title, columns, colour in [
        ("1_Visit", VISIT_COLUMNS, "2CA02C"),
        ("2_Eye_Exam", EYE_COLUMNS, "FF7F0E"),
        ("3_Images", IMAGE_COLUMNS, "9467BD"),
    ]:
        ws = wb.create_sheet(title)
        write_header(ws, columns)
        ws.sheet_properties.tabColor = colour
        ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}1"

    ws_phi = wb.create_sheet("PHI_Linkage")
    write_header(ws_phi, PHI_COLUMNS, fill=PHI_FILL)
    ws_phi.sheet_properties.tabColor = "C00000"
    warning = ws_phi.cell(row=1, column=len(PHI_COLUMNS) + 2,
                          value="CONTAINS PATIENT IDENTIFIERS - delete this sheet before sharing")
    warning.font = Font(bold=True, color="C00000", size=11)

    build_lists_sheet(wb)

    # Validations must come after the Lists sheet exists.
    add_validations(wb["1_Visit"], VISIT_COLUMNS, n_rows)
    add_validations(wb["2_Eye_Exam"], EYE_COLUMNS, n_rows)
    add_validations(wb["3_Images"], IMAGE_COLUMNS, n_rows)

    # Collapsible anatomical sections on the wide exam sheet.
    exam = wb["2_Eye_Exam"]
    for first_name, last_name, _label in EYE_GROUPS:
        exam.column_dimensions.group(
            column_letter_for(EYE_COLUMNS, first_name),
            column_letter_for(EYE_COLUMNS, last_name),
            outline_level=1,
            hidden=False,
        )

    wb.save(output_path)
    return wb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(
        Path(__file__).parent.parent / "prospective" / "Prospective_AI_Image_Collection.xlsx"))
    parser.add_argument("--rows", type=int, default=400,
                        help="How many rows get dropdowns (default 400).")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite an existing workbook. Refuses by default.")
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() and not args.force:
        print(f"❌ {output} already exists. Pass --force only if it holds no data yet.")
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    build(output, args.rows)
    print(f"✅ wrote {output}")
    print(f"   sheets      : README, 1_Visit, 2_Eye_Exam, 3_Images, PHI_Linkage, Lists")
    print(f"   columns     : {len(VISIT_COLUMNS)} visit / {len(EYE_COLUMNS)} eye / {len(IMAGE_COLUMNS)} image")
    print(f"   vocabularies: {len(LISTS)} lists, {sum(len(v) for v in LISTS.values())} values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
