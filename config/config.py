"""
Configuration file for Slitlamp Labeling Application
"""

from pathlib import Path
import os

# Base paths - UPDATE THESE WITH YOUR ACTUAL PATHS
DIAGNOSIS_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\studyinfo_laterality_diagnosis.dta"
NOTES_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\ehrs_transformed.parquet"
CROSS_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\slitlamp_crosswalk_complete_12082025.csv"
IMAGE_BASE_PATH = r"L:\SlitLamp"

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
IMAGES_PER_SESSION = 50  # Number of images to load at once
AUTO_SAVE_INTERVAL = 5  # Save every N labels

# Date format
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
