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

# ======================================================
# Machine-specific paths (can be overridden by .env)
# ======================================================

# Helper function to validate paths
def _get_path(env_var, default_path, path_type="file"):
    """Get path from env or default, validate it exists"""
    path = os.getenv(env_var, default_path)
    
    # If env var is explicitly set but empty, raise error
    if env_var in os.environ and not path.strip():
        raise ValueError(
            f"\n{'='*70}\n"
            f"ERROR: {env_var} is set but empty in .env file!\n"
            f"Please provide a valid path or remove the line from .env\n"
            f"{'='*70}"
        )
    
    return path

def _get_path_required(env_var):
    """Get path from env, raise error if not set"""
    path = os.getenv(env_var)
    if not path or not path.strip():
        raise ValueError(
            f"\n{'='*70}\n"
            f"ERROR: {env_var} not set in .env file!\n"
            f"Please create a .env file and set all required paths.\n"
            f"Copy .env.example to .env and edit with your paths.\n"
            f"{'='*70}"
        )
    return path

DIAGNOSIS_PATH = _get_path_required("DIAGNOSIS_PATH")
CROSS_PATH = _get_path_required("CROSS_PATH")
ANNOTATIONS_PATH = _get_path_required("ANNOTATIONS_PATH")
IMAGE_BASE_PATH = _get_path_required("IMAGE_BASE_PATH")
ANONYMIZED_EHR_PATH = _get_path_required("NOTES_PATH")

# Backward compatibility
NOTES_PATH = ANONYMIZED_EHR_PATH


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

# Illumination technique (optional field; standard slit lamp techniques).
# Backward-compatible: labels created before this field simply omit it.
ILLUMINATION_NOT_SPECIFIED = "Not specified"
ILLUMINATION_OPTIONS = [
    "Direct",
    "Indirect",
    "Slit beam",
    "Diffuse",
    "Sclerotic scatter",
    "Retroillumination",
    "Specular reflection",
    "Tangential",
]

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
    "Unknown",
    "Bacterial",
    "Fungal",
    "Herpetic",
    "Acanthamoeba"
    
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
    "prelabel_first": "AI pre-labels first, then remaining images",
    "prelabel_first_third": "AI pre-labels only - First third (1-33%)",
    "prelabel_second_third": "AI pre-labels only - Second third (34-66%)",
    "prelabel_last_third": "AI pre-labels only - Last third (67-100%)",
    # Sixths: AI pre-labels split into 6 equal contiguous parts
    "prelabel_1_6": "AI pre-labels only - 1st sixth (0-16%)",
    "prelabel_2_6": "AI pre-labels only - 2nd sixth (17-33%)",
    "prelabel_3_6": "AI pre-labels only - 3rd sixth (34-50%)",
    "prelabel_4_6": "AI pre-labels only - 4th sixth (51-66%)",
    "prelabel_5_6": "AI pre-labels only - 5th sixth (67-83%)",
    "prelabel_6_6": "AI pre-labels only - 6th sixth (84-100%)",
    "forward": "Start from beginning",
    "backward": "Start from end",
    "middle_out": "Start from middle",
    "random": "Random order (seeded by user)"
}

# Set of all "sixth" strategy names, mapped to their part number (1-6)
PRELABEL_SIXTH_STRATEGIES = {f"prelabel_{k}_6": k for k in range(1, 7)}

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
    "NOTES_AND_ANNOTATIONS": "Only images with both notes and annotations",
    "WITH_AI_PRELABEL": "Only images with AI pre-labels"
}

DEFAULT_DATASET_FILTER = os.getenv(
    "DEFAULT_DATASET_FILTER",
    "WITH_AI_PRELABEL"
)

# ======================================================
# Date formats
# ======================================================

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
