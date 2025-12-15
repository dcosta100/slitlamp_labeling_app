"""
Configuration file for Slitlamp Labeling Application
"""

from pathlib import Path
import os

# Base paths - UPDATE THESE WITH YOUR ACTUAL PATHS
DIAGNOSIS_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\studyinfo_laterality_diagnosis.dta"
# NOTES_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\ehrs_transformed.parquet"
NOTES_PATH = r"C:\Projects_Local\slitlamp_labeling_app\preprocessing\ehr_anonymized_all.parquet"
CROSS_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\slitlamp_crosswalk_complete_12082025.csv"
ANNOTATIONS_PATH = r"C:\Users\dxr1276\Box\PROJECTS\DOUGLAS\Files_code\Databases\_BPGR\BPGR_slexam_all.csv"
IMAGE_BASE_PATH = r"L:\SlitLamp" # Base directory for images
ANONYMIZED_EHR_PATH = r"C:\Projects_Local\slitlamp_labeling_app\preprocessing\ehr_anonymized_all.parquet"

# Preprocessed dataset path (RECOMMENDED for faster loading)
# Run preprocessing/create_preprocessed_dataset.py first to create this file
PREPROCESSED_PATH = r"C:\Projects_Local\slitlamp_labeling_app\data\preprocessed_dataset.parquet"  # Set to path of preprocessed file, or None to disable
# Example: PREPROCESSED_PATH = r"C:\Projects\slitlamp_labeling_app\data\preprocessed_dataset.parquet"

# Use preprocessed dataset if available (MUCH FASTER!)
USE_PREPROCESSED = True  # Set to False to always load from scratch


# Application paths
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

# Labeling options
LATERALITY_OPTIONS = ["Left", "Right"]
DIAGNOSIS_OPTIONS = [
    "Ulcer",
    "Hyposphagma",
    "Dry Eye",
    "Pterygium",
    "Pinguecula",
    "Other"
]
FLAG_OPTIONS = ["No", "Yes"]
QUALITY_OPTIONS = ["Usable", "Not Usable"]

# Admin credentials (default)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # CHANGE THIS IN PRODUCTION

# Labeling route strategies
ROUTE_STRATEGIES = {
    "forward": "Start from beginning",
    "backward": "Start from end",
    "middle_out": "Start from middle",
    "random": "Random order (seeded by user)"
}

# Application settings
MAX_NOTE_DAYS_DIFFERENCE = 365  # Maximum days to search for notes
MAX_ANNOTATION_DAYS_DIFFERENCE = 7  # Maximum days difference for annotation matching (1 week)
IMAGES_PER_SESSION = 50  # Number of images to load at once
AUTO_SAVE_INTERVAL = 5  # Save every N labels

# Dataset filtering options
DATASET_FILTER_OPTIONS = {
    "ALL": "Show all images (no filtering)",
    "NOTES": "Only images with matching clinical notes",
    "ANNOTATIONS": "Only images with matching annotations",
    "NOTES_AND_ANNOTATIONS": "Only images with both notes and annotations"
}

# Default filter (change this to filter your dataset)
DEFAULT_DATASET_FILTER = "NOTES_AND_ANNOTATIONS"  # Options: "ALL", "NOTES", "ANNOTATIONS", "NOTES_AND_ANNOTATIONS"

# Date format
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
