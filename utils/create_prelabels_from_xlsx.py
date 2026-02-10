"""
Script to convert AI labels from XLSX to pre-label JSON files
Creates label files that can be loaded by the labeling app
"""

import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def extract_json_from_ai_diagnosis(ai_text):
    """
    Extract JSON from AI_Diagnosis text that contains ```json ... ```
    
    Args:
        ai_text: String containing ```json\n{...}\n```
    
    Returns:
        dict or None
    """
    if pd.isna(ai_text) or not ai_text:
        return None
    
    # Find JSON between ```json and ```
    pattern = r'```json\s*\n(.*?)\n```'
    match = re.search(pattern, ai_text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print(f"JSON string: {json_str[:200]}...")
            return None
    else:
        # Try without the markdown wrapper (in case it's just pure JSON)
        try:
            return json.loads(ai_text)
        except:
            return None

def create_label_entry(row, index):
    """
    Create a single label entry in the format expected by the app
    
    Args:
        row: DataFrame row with AI_Diagnosis, image_path, etc
        index: Index/position for this label
    
    Returns:
        dict with label data
    """
    # Extract AI diagnosis JSON
    ai_diagnosis = extract_json_from_ai_diagnosis(row.get('AI_Diagnosis'))
    
    if not ai_diagnosis:
        return None
    
    # Get metadata from row
    image_path = row.get('image_path', '')
    maskedid_studyid = row.get('maskedid_studyid', '')
    exam_date = row.get('exam_date', '')
    pat_mrn = str(row.get('pat_mrn', '')) if pd.notna(row.get('pat_mrn')) else ''
    
    # Format exam_date
    if pd.notna(exam_date):
        if isinstance(exam_date, str):
            exam_date_str = exam_date
        else:
            exam_date_str = exam_date.strftime('%Y-%m-%d %H:%M:%S')
    else:
        exam_date_str = ''
    
    # Create label entry
    label_entry = {
        "image_path": image_path,
        "laterality": ai_diagnosis.get('laterality', 'Not Possible to Determine'),
        "quality": ai_diagnosis.get('quality', 'Usable'),
        "conditions": ai_diagnosis.get('conditions', {}),
        "labeled_by": "AI_prelabel",
        "labeled_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "is_edit": False,
        "metadata": {
            "maskedid_studyid": maskedid_studyid,
            "exam_date": exam_date_str,
            "pat_mrn": pat_mrn
        }
    }
    
    return label_entry

def create_prelabel_json(df, output_dir, username="AI_prelabel"):
    """
    Create pre-label JSON file from DataFrame with AI_Diagnosis
    
    Args:
        df: DataFrame with columns: AI_Diagnosis, image_path, maskedid_studyid, exam_date, pat_mrn
        output_dir: Directory to save the JSON file
        username: Username for the labels (default: AI_prelabel)
    
    Returns:
        Path to created file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create labels dict - use image_path as key for easier lookup
    labels = {}
    successful_count = 0
    failed_count = 0
    
    print(f"\nProcessing {len(df)} rows...")
    
    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"  Processing row {idx}/{len(df)}...")
        
        label_entry = create_label_entry(row, idx)
        
        if label_entry:
            # Use image_path as key for easier matching
            image_path = label_entry['image_path']
            labels[image_path] = label_entry
            successful_count += 1
        else:
            failed_count += 1
    
    # Create final JSON structure
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    final_json = {
        "user": username,
        "created_at": now,
        "last_modified": now,
        "labels": labels
    }
    
    # Save to file in data/labels (not data/pre_labels!)
    output_file = output_dir / f"{username}_labels.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"PRELABEL CREATION COMPLETE!")
    print(f"{'='*60}")
    print(f"✅ Successful: {successful_count} labels")
    print(f"❌ Failed: {failed_count} labels")
    print(f"📁 Output: {output_file}")
    print(f"\nFile size: {output_file.stat().st_size / 1024:.1f} KB")
    
    return output_file

def main():
    """
    Main function - edit this to point to your XLSX file
    """
    print("="*60)
    print("AI DIAGNOSIS (XLSX) TO PRE-LABEL CONVERTER")
    print("="*60)
    
    # ==================== EDIT THIS PATH ====================
    
    # Path to your XLSX file
    input_file = Path("C:\\Projects_Local\\slitlamp_labeling_app\\data\\grading_results_slitlamp.xlsx")
    
    # Where to save the pre-label JSON
    output_dir = Path("C:\\Projects_Local\\slitlamp_labeling_app\\data\\labels")
    
    # Username for these labels
    username = "AI_prelabel"
    
    # ==========================================================
    
    if not input_file.exists():
        print(f"\n❌ ERROR: File not found: {input_file}")
        print("Please place grading_results_slitlamp.xlsx in the utils/ folder")
        return
    
    print(f"\nLoading data from: {input_file}")
    
    # Load Excel file
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"❌ ERROR loading Excel: {e}")
        return
    
    print(f"Loaded {len(df):,} rows")
    
    # Check required columns
    required_cols = ['AI_Diagnosis', 'image_path', 'maskedid_studyid', 'exam_date']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"\n❌ ERROR: Missing required columns: {missing_cols}")
        print(f"Available columns: {df.columns.tolist()}")
        return
    
    # Check how many rows have AI_Diagnosis
    has_ai_diagnosis = df['AI_Diagnosis'].notna().sum()
    print(f"\nRows with AI_Diagnosis: {has_ai_diagnosis:,} / {len(df):,}")
    
    if has_ai_diagnosis == 0:
        print("\n⚠️  WARNING: No rows have AI_Diagnosis!")
        return
    
    # Filter to only rows with AI_Diagnosis
    df_with_ai = df[df['AI_Diagnosis'].notna()].copy()
    
    # Sort by maskedid_studyid to keep images from same study together
    df_with_ai = df_with_ai.sort_values('maskedid_studyid').reset_index(drop=True)
    
    print(f"\nProcessing {len(df_with_ai):,} rows with AI labels...")
    
    # Create pre-labels
    output_file = create_prelabel_json(df_with_ai, output_dir, username)
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print(f"1. File saved to: {output_file}")
    print(f"2. Copy it to your app's data/labels/ folder")
    print(f"3. The app will automatically load these labels")
    print(f"4. Users can review and edit AI pre-labels")
    print("\nDone! 🎉")

if __name__ == "__main__":
    main()
