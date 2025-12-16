"""
Configuration file for Slitlamp Labeling Application
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# ======================================================
# Load environment variables (.env)
# ======================================================
# This allows machine-specific configuration without
# changing the codebase. If .env is missing, defaults
# defined below are used.
load_dotenv()

# ======================================================
# Machine-specific paths (can be overridden by .env)
# ======================================================

DIAGNOSIS_PATH = os.getenv(
    "DIAGNOSIS_PATH",
    r"C:\Users\dxr1276\OneDrive\Projects\Forevision\studyinfo_laterality_diagnosis.dta"
)

NOTES_PATH = os.getenv(
    "NOTES_PATH",
    r"C:\Projects_Local\slitlamp_labeling_app\preprocessing\ehr_anonymized_all.parquet"
)

CROSS_PATH = os.getenv(
    "CROSS_PATH",
    r"C:\Users\dxr1276\OneDrive\Projects\Forevision\slitlamp_crosswalk_complete_12082025.csv"
)

ANNOTATIONS_PATH = os.getenv(
    "ANNOTATIONS_PATH",
    r"C:\Users\dxr1276\Box\PROJECTS\DOUGLAS\Files_code\Databases\_BPGR\BPGR_slexam_all.csv"
)

IMAGE_BASE_PATH = os.getenv(
    "IMAGE_BASE_PATH",
    r"L:\SlitLamp"
)

ANONYMIZED_EHR_PATH = os.getenv(
    "ANONYMIZED_EHR_PATH",
    r"C:\Projects_Local\slitlamp_labeling_app\preprocessing\ehr_anonymized_all.parquet"
)

# Preprocessed dataset path (recommended for faster loading)
PREPROCESSED_PATH = os.getenv(
    "PREPROCESSED_PATH",
    r"C:\Projects_Local\slitlamp_labeling_app\data\preprocessed_dataset.parquet"
)

USE_PREPROCESSED = os.getenv("USE_PREPROCESSED", "True").lower() == "true"

# ======================================================
# Application paths (project-relative, NOT in .env)
# ======================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
LABELS_DIR = DATA_DIR / "labels"
USERS_DIR = DATA_DIR / "users"

# Create directories if they don't exist
LABELS_DIR.mkdir(parents=True, exist_ok=True)
USERS_DIR.mkdir(parents=True, exist_ok=True)

# User configuration file
USERS_CONFIG_FILE = USERS_DIR / "users.json"

# ======================================================
# Labeling options - MULTILABEL HIERARCHICAL STRUCTURE
# ======================================================

LATERALITY_OPTIONS = ["Left", "Right", "Not Possible to Determine"]

# Quality options (first choice)
QUALITY_OPTIONS = ["Usable", "Non Usable"]

# Main diagnostic categories (MULTILABEL)
DIAGNOSTIC_CATEGORIES = [
    "Dry Eye Disease",
    "Cataract",
    "Infectious Keratitis / Conjunctivitis",
    "Ocular Surface Tumors",
    "Subconjunctival Hemorrhage",
    "None of the Above"
]

# ------------------------------------------------------
# 1) Dry Eye Disease
# ------------------------------------------------------
DRY_EYE_SEVERITY = ["None", "Mild", "Moderate", "Severe"]
DRY_EYE_SIGNS = [
    "MGD",
    "Lid telangiectasia",
    "Foamy tear film",
    "Conjunctival injection",
    "Filaments",
    "Exposure",
    "Conjunctivochalasis"
]

# ------------------------------------------------------
# 2) Cataract
# ------------------------------------------------------
CATARACT_TYPE = [
    "None",
    "Nuclear",
    "Cortical",
    "PSC",
    "Mature-White",
    "Pseudophakia",
    "Aphakia",
    "Other-Unclear"
]
CATARACT_SEVERITY = ["Mild", "Moderate", "Severe"]
CATARACT_FEATURES = [
    "Brunescent",
    "Cortical spokes",
    "Posterior plaque",
    "Phacodonesis"
]

# ------------------------------------------------------
# 3) Infectious Keratitis / Conjunctivitis
# ------------------------------------------------------
INFECTIOUS_TYPE = [
    "Keratitis—Infectious",
    "Conjunctivitis—Infectious",
    "No infection",
    "Unclear"
]
INFECTIOUS_ETIOLOGY = [
    "Bacterial",
    "Fungal",
    "Herpetic",
    "Acanthamoeba",
    "Unknown"
]
KERATITIS_SIZE = ["<2 mm", "2–5 mm", ">5 mm"]
KERATITIS_FEATURES = [
    "Epi defect",
    "Stromal infiltrate",
    "Ulcer",
    "Feathery edge",
    "Ring",
    "Satellite",
    "Hypopyon",
    "Dendrite",
    "Pseudodendrite"
]
CONJUNCTIVITIS_FEATURES = [
    "Papillae",
    "Follicles",
    "Membrane",
    "Pseudomembrane",
    "Mucus",
    "SEIs"
]

# ------------------------------------------------------
# 4) Ocular Surface Tumors
# ------------------------------------------------------
TUMOR_TYPE = [
    "OSSN",
    "Pterygium",
    "Pinguecula",
    "Conjunctival nevus",
    "Melanoma",
    "Papilloma",
    "No lesion",
    "Unclear"
]
TUMOR_MALIGNANCY = ["Benign", "Malignant", "Indeterminate"]
TUMOR_LOCATION = ["Nasal", "Temporal", "Superior", "Inferior", "Multifocal"]
TUMOR_FEATURES = [
    "Leukoplakia",
    "Gelatinous",
    "Feeder vessels",
    "Limbal involvement",
    "Pigmented",
    "Cystic spaces",
    "Diffuse sheet",
    "Keratin"
]

# ------------------------------------------------------
# 5) Subconjunctival Hemorrhage
# ------------------------------------------------------
SCH_PRESENCE = ["Present", "None", "Unclear"]
SCH_EXTENT = ["1 quadrant", "2 quadrants", "3 quadrants", "4 quadrants"]

# ======================================================
# Admin credentials (DO NOT hardcode in production)
# ======================================================

DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

# ======================================================
# Labeling route strategies
# ======================================================

ROUTE_STRATEGIES = {
    "forward": "Start from beginning",
    "backward": "Start from end",
    "middle_out": "Start from middle",
    "random": "Random order (seeded by user)"
}

# ======================================================
# Application settings
# ======================================================

MAX_NOTE_DAYS_DIFFERENCE = int(os.getenv("MAX_NOTE_DAYS_DIFFERENCE", 365))
MAX_ANNOTATION_DAYS_DIFFERENCE = int(os.getenv("MAX_ANNOTATION_DAYS_DIFFERENCE", 7))
IMAGES_PER_SESSION = int(os.getenv("IMAGES_PER_SESSION", 50))
AUTO_SAVE_INTERVAL = int(os.getenv("AUTO_SAVE_INTERVAL", 5))

ENABLE_AUTOFILL_SAME_STUDYID = (
    os.getenv("ENABLE_AUTOFILL_SAME_STUDYID", "True").lower() == "true"
)

# ======================================================
# Dataset filtering
# ======================================================

DATASET_FILTER_OPTIONS = {
    "ALL": "Show all images (no filtering)",
    "NOTES": "Only images with matching clinical notes",
    "ANNOTATIONS": "Only images with matching annotations",
    "NOTES_AND_ANNOTATIONS": "Only images with both notes and annotations"
}

DEFAULT_DATASET_FILTER = os.getenv(
    "DEFAULT_DATASET_FILTER",
    "NOTES_AND_ANNOTATIONS"
)

# ======================================================
# Date formats
# ======================================================

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
