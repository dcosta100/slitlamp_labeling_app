"""
Diagnostic script to verify all paths are configured correctly
Run this before starting the app to check configuration
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def check_path(name, path, should_exist=True, is_file=True):
    """Check if a path exists and print status"""
    path_obj = Path(path)
    exists = path_obj.exists()
    
    status = "✅" if exists else "❌"
    type_check = ""
    
    if exists:
        if is_file and not path_obj.is_file():
            status = "⚠️ "
            type_check = " (expected file, found directory)"
        elif not is_file and not path_obj.is_dir():
            status = "⚠️ "
            type_check = " (expected directory, found file)"
    elif not should_exist:
        status = "ℹ️ "
        type_check = " (optional - will be created)"
    
    print(f"{status} {name:30s}: {path}{type_check}")
    return exists or not should_exist

def main():
    print("="*70)
    print("SLITLAMP LABELING APP - PATH DIAGNOSTICS")
    print("="*70)
    print()
    
    # Import config
    try:
        from config.config import (
            DIAGNOSIS_PATH,
            ANONYMIZED_EHR_PATH,
            CROSS_PATH,
            ANNOTATIONS_PATH,
            IMAGE_BASE_PATH,
            USE_PREPROCESSED,
            PREPROCESSED_PATH,
            LABELS_DIR,
            DATA_DIR,
            DEFAULT_DATASET_FILTER
        )
    except Exception as e:
        print(f"❌ ERROR: Could not import config: {e}")
        print("\nMake sure you're running this from the project root directory")
        return
    
    all_ok = True
    
    print("── Required Data Files ────────────────────────────────────────")
    all_ok &= check_path("Diagnosis (.dta)", DIAGNOSIS_PATH, should_exist=True, is_file=True)
    all_ok &= check_path("EHR Notes (parquet)", ANONYMIZED_EHR_PATH, should_exist=True, is_file=True)
    all_ok &= check_path("Crosswalk (.csv)", CROSS_PATH, should_exist=True, is_file=True)
    all_ok &= check_path("Annotations (.csv)", ANNOTATIONS_PATH, should_exist=True, is_file=True)
    
    print()
    print("── Image Storage ──────────────────────────────────────────────")
    all_ok &= check_path("Image Base Path", IMAGE_BASE_PATH, should_exist=True, is_file=False)
    
    print()
    print("── Preprocessed Dataset ───────────────────────────────────────")
    print(f"   USE_PREPROCESSED: {USE_PREPROCESSED}")
    if USE_PREPROCESSED:
        all_ok &= check_path("Preprocessed (.parquet)", PREPROCESSED_PATH, should_exist=True, is_file=True)
    else:
        check_path("Preprocessed (.parquet)", PREPROCESSED_PATH, should_exist=False, is_file=True)
    
    print()
    print("── Application Directories ────────────────────────────────────")
    check_path("Data Directory", DATA_DIR, should_exist=False, is_file=False)
    check_path("Labels Directory", LABELS_DIR, should_exist=False, is_file=False)
    
    print()
    print("── AI Pre-Labels ──────────────────────────────────────────────")
    ai_prelabel_file = LABELS_DIR / "AI_prelabel_labels.json"
    has_prelabels = check_path("AI_prelabel_labels.json", ai_prelabel_file, should_exist=True, is_file=True)
    
    if has_prelabels:
        import json
        try:
            with open(ai_prelabel_file, 'r') as f:
                data = json.load(f)
            count = len(data.get('labels', {}))
            print(f"   ℹ️  AI pre-labels loaded: {count:,} images")
        except Exception as e:
            print(f"   ⚠️  Could not read AI pre-labels: {e}")
    
    print()
    print("── Configuration ──────────────────────────────────────────────")
    print(f"   Default filter: {DEFAULT_DATASET_FILTER}")
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print(f"   ✅ .env file found")
    else:
        print(f"   ℹ️  .env file not found (using defaults from config.py)")
        print(f"      To customize paths, copy .env.example to .env")
    
    print()
    print("="*70)
    if all_ok:
        print("✅ ALL REQUIRED PATHS ARE VALID")
        print("="*70)
        print("\nYou can start the app with: streamlit run app.py")
    else:
        print("❌ SOME PATHS ARE MISSING OR INVALID")
        print("="*70)
        print("\nPlease fix the paths above before starting the app")
        print("\nTo configure paths:")
        print("  1. Copy .env.example to .env")
        print("  2. Edit .env with correct paths for your machine")
        print("  3. Run this script again to verify")
    print()

if __name__ == "__main__":
    main()