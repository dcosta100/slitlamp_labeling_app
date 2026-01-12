"""
Script to extract matching notes and annotations for a given image path
Usage: python get_image_matches.py --image_path "path/to/image.jpg" --output results.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys
from datetime import datetime

# Add parent directory to path if needed
sys.path.append(str(Path(__file__).parent))

from config import (
    DIAGNOSIS_PATH,
    ANONYMIZED_EHR_PATH,
    CROSS_PATH,
    ANNOTATIONS_PATH,
    MAX_NOTE_DAYS_DIFFERENCE,
    MAX_ANNOTATION_DAYS_DIFFERENCE,
    PREPROCESSED_PATH,
    USE_PREPROCESSED
)

def load_data():
    """Load all necessary datasets"""
    print("Loading datasets...")
    
    # Load diagnosis data
    print("  - Loading diagnosis data...")
    diagnosis_df = pd.read_stata(DIAGNOSIS_PATH)
    diagnosis_df['exam_date'] = pd.to_datetime(diagnosis_df['exam_date'])
    if 'pat_mrn' in diagnosis_df.columns:
        diagnosis_df['pat_mrn'] = diagnosis_df['pat_mrn'].astype(str).str.strip()
    
    # Load notes data
    print("  - Loading notes data...")
    notes_df = pd.read_parquet(ANONYMIZED_EHR_PATH)
    notes_df['note_date'] = pd.to_datetime(notes_df['note_date'])
    if 'pat_mrn' in notes_df.columns:
        notes_df['pat_mrn'] = notes_df['pat_mrn'].astype(str).str.strip()
    
    # Filter for Progress Notes only
    if 'ip_note_type' in notes_df.columns:
        notes_df = notes_df[notes_df['ip_note_type'] == 'Progress Notes'].copy()
        print(f"     Filtered to Progress Notes: {len(notes_df):,}")
    
    # Load crosswalk data
    print("  - Loading crosswalk data...")
    cross_df = pd.read_csv(CROSS_PATH)
    if 'maskedid' in cross_df.columns:
        cross_df['maskedid'] = cross_df['maskedid'].astype(str).str.strip()
    
    # Load annotations data
    print("  - Loading annotations data...")
    annotations_df = pd.read_csv(ANNOTATIONS_PATH)
    if 'studyid' in annotations_df.columns:
        annotations_df.rename(columns={'studyid': 'maskedid'}, inplace=True)
    if 'date' in annotations_df.columns:
        annotations_df['annotation_date'] = pd.to_datetime(annotations_df['date'])
    if 'maskedid' in annotations_df.columns:
        annotations_df['maskedid'] = annotations_df['maskedid'].astype(str).str.strip()
    
    print("All datasets loaded successfully!")
    return diagnosis_df, notes_df, cross_df, annotations_df

def find_image_info(image_path, cross_df, diagnosis_df):
    """Find image information from crosswalk and diagnosis data"""
    print(f"\nSearching for image: {image_path}")
    
    # Parse the image path structure
    # Expected: BASE_PATH / maskedid / maskedid_studyid / proc_name / photo_name
    path_obj = Path(image_path)
    photo_name = path_obj.name
    proc_name = path_obj.parent.name
    maskedid_studyid = path_obj.parent.parent.name
    maskedid = path_obj.parent.parent.parent.name
    
    print(f"  Parsed path components:")
    print(f"    maskedid: {maskedid}")
    print(f"    maskedid_studyid: {maskedid_studyid}")
    print(f"    proc_name: {proc_name}")
    print(f"    photo_name: {photo_name}")
    
    # Search in crosswalk using multiple criteria for best match
    image_row = None
    
    # Try matching by maskedid_studyid and photo_name (most specific)
    if 'maskedid_studyid' in cross_df.columns and 'photo_name' in cross_df.columns:
        mask = (cross_df['maskedid_studyid'] == maskedid_studyid) & (cross_df['photo_name'] == photo_name)
        if mask.any():
            image_row = cross_df[mask].iloc[0]
            print(f"  ✓ Found exact match using maskedid_studyid + photo_name")
    
    # If not found, try just photo_name (less specific but may work)
    if image_row is None and 'photo_name' in cross_df.columns:
        mask = cross_df['photo_name'] == photo_name
        if mask.any():
            image_row = cross_df[mask].iloc[0]
            print(f"  ✓ Found match using photo_name only")
            print(f"    WARNING: Multiple images may have same photo_name!")
    
    # If still not found, try partial matching on photo_name
    if image_row is None and 'photo_name' in cross_df.columns:
        mask = cross_df['photo_name'].astype(str).str.contains(photo_name, case=False, na=False, regex=False)
        if mask.any():
            image_row = cross_df[mask].iloc[0]
            print(f"  ✓ Found match using partial photo_name matching")
    
    if image_row is None:
        print(f"  ✗ ERROR: Image not found in crosswalk!")
        print(f"  Available columns in crosswalk: {list(cross_df.columns)}")
        print(f"  Trying to match:")
        print(f"    maskedid_studyid: {maskedid_studyid}")
        print(f"    photo_name: {photo_name}")
        return None
    
    # Get maskedid_studyid and merge with diagnosis
    maskedid_studyid = image_row.get('maskedid_studyid')
    if pd.isna(maskedid_studyid):
        print(f"  ERROR: No maskedid_studyid found for this image!")
        return None
    
    # Find diagnosis info
    diag_row = diagnosis_df[diagnosis_df['maskedid_studyid'] == maskedid_studyid]
    if len(diag_row) == 0:
        print(f"  WARNING: No diagnosis info found for maskedid_studyid: {maskedid_studyid}")
        # Use crosswalk data only
        result = image_row.to_dict()
    else:
        # Merge crosswalk and diagnosis
        result = {**image_row.to_dict(), **diag_row.iloc[0].to_dict()}
    
    print(f"  Image info found:")
    print(f"    maskedid_studyid: {maskedid_studyid}")
    print(f"    maskedid: {result.get('maskedid', 'N/A')}")
    print(f"    pat_mrn: {result.get('pat_mrn', 'N/A')}")
    print(f"    exam_date: {result.get('exam_date', 'N/A')}")
    
    return result

def find_matching_notes(image_info, notes_df):
    """Find all notes matching the image"""
    print("\nSearching for matching notes...")
    
    pat_mrn = image_info.get('pat_mrn')
    exam_date = image_info.get('exam_date')
    
    if pd.isna(pat_mrn) or pd.isna(exam_date):
        print("  ERROR: Missing pat_mrn or exam_date!")
        return pd.DataFrame()
    
    # Filter notes by patient
    patient_notes = notes_df[notes_df['pat_mrn'] == str(pat_mrn)].copy()
    
    if len(patient_notes) == 0:
        print(f"  No notes found for pat_mrn: {pat_mrn}")
        return pd.DataFrame()
    
    print(f"  Found {len(patient_notes):,} total notes for this patient")
    
    # Calculate days difference
    patient_notes['days_difference'] = (patient_notes['note_date'] - pd.to_datetime(exam_date)).dt.days.abs()
    
    # Filter by threshold
    matching_notes = patient_notes[patient_notes['days_difference'] <= MAX_NOTE_DAYS_DIFFERENCE].copy()
    
    # Sort by date difference (closest first)
    matching_notes = matching_notes.sort_values('days_difference')
    
    print(f"  Found {len(matching_notes)} notes within {MAX_NOTE_DAYS_DIFFERENCE} days")
    
    return matching_notes

def find_matching_annotations(image_info, annotations_df):
    """Find all annotations matching the image"""
    print("\nSearching for matching annotations...")
    
    maskedid = image_info.get('maskedid')
    exam_date = image_info.get('exam_date')
    
    if pd.isna(maskedid) or pd.isna(exam_date):
        print("  ERROR: Missing maskedid or exam_date!")
        return pd.DataFrame()
    
    # Filter annotations by maskedid
    patient_anns = annotations_df[annotations_df['maskedid'] == str(maskedid)].copy()
    
    if len(patient_anns) == 0:
        print(f"  No annotations found for maskedid: {maskedid}")
        return pd.DataFrame()
    
    print(f"  Found {len(patient_anns):,} total annotations for this patient")
    
    # Calculate days difference
    patient_anns['days_difference'] = (patient_anns['annotation_date'] - pd.to_datetime(exam_date)).dt.days.abs()
    
    # Filter by threshold
    matching_anns = patient_anns[patient_anns['days_difference'] <= MAX_ANNOTATION_DAYS_DIFFERENCE].copy()
    
    # Sort by date difference (closest first)
    matching_anns = matching_anns.sort_values('days_difference')
    
    print(f"  Found {len(matching_anns)} annotations within {MAX_ANNOTATION_DAYS_DIFFERENCE} days")
    
    return matching_anns

def create_wide_format(image_info, matching_notes, matching_anns, max_cols=5):
    """Create a wide-format dataframe with separate columns for each note/annotation"""
    print("\nCreating output dataframe...")
    
    result = {}
    
    # Add image info
    result['image_path'] = image_info.get('image_path', '')
    result['maskedid_studyid'] = image_info.get('maskedid_studyid', '')
    result['maskedid'] = image_info.get('maskedid', '')
    result['pat_mrn'] = image_info.get('pat_mrn', '')
    result['exam_date'] = image_info.get('exam_date', '')
    result['laterality'] = image_info.get('laterality', '')
    
    # Add notes (up to max_cols)
    result['total_matching_notes'] = len(matching_notes)
    for i in range(max_cols):
        if i < len(matching_notes):
            note = matching_notes.iloc[i]
            result[f'note_{i+1}_date'] = note.get('note_date', '')
            result[f'note_{i+1}_days_diff'] = note.get('days_difference', '')
            result[f'note_{i+1}_type'] = note.get('ip_note_type', '')
            result[f'note_{i+1}_text'] = note.get('note_text', '')[:500] if 'note_text' in note else ''  # Truncate for preview
            result[f'note_{i+1}_full_text'] = note.get('note_text', '')  # Full text
        else:
            result[f'note_{i+1}_date'] = None
            result[f'note_{i+1}_days_diff'] = None
            result[f'note_{i+1}_type'] = None
            result[f'note_{i+1}_text'] = None
            result[f'note_{i+1}_full_text'] = None
    
    # Add annotations (up to max_cols)
    result['total_matching_annotations'] = len(matching_anns)
    for i in range(max_cols):
        if i < len(matching_anns):
            ann = matching_anns.iloc[i]
            result[f'annotation_{i+1}_date'] = ann.get('annotation_date', '')
            result[f'annotation_{i+1}_days_diff'] = ann.get('days_difference', '')
            # Add all annotation columns with prefix
            for col in ann.index:
                if col not in ['maskedid', 'annotation_date', 'days_difference', 'date']:
                    result[f'annotation_{i+1}_{col}'] = ann.get(col, '')
        else:
            result[f'annotation_{i+1}_date'] = None
            result[f'annotation_{i+1}_days_diff'] = None
    
    return pd.DataFrame([result])

def save_results(df, output_path, format='csv'):
    """Save results to file"""
    print(f"\nSaving results to {output_path}...")
    
    if format == 'csv':
        df.to_csv(output_path, index=False)
    elif format == 'parquet':
        df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    print(f"Results saved successfully!")
    print(f"  Total columns: {len(df.columns)}")
    print(f"  File size: {Path(output_path).stat().st_size / 1024:.1f} KB")

def main():
    parser = argparse.ArgumentParser(
        description='Extract matching notes and annotations for a given image'
    )
    parser.add_argument(
        '--image_path',
        type=str,
        required=True,
        help='Path to the image file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='image_matches.csv',
        help='Output file path (default: image_matches.csv)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'parquet'],
        default='csv',
        help='Output format (default: csv)'
    )
    parser.add_argument(
        '--max_cols',
        type=int,
        default=5,
        help='Maximum number of note/annotation columns (default: 5)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("IMAGE MATCHES EXTRACTOR")
    print("="*60)
    
    # Load data
    diagnosis_df, notes_df, cross_df, annotations_df = load_data()
    
    # Find image info
    image_info = find_image_info(args.image_path, cross_df, diagnosis_df)
    if image_info is None:
        print("\nERROR: Could not find image information. Exiting.")
        return
    
    # Find matching notes
    matching_notes = find_matching_notes(image_info, notes_df)
    
    # Find matching annotations
    matching_anns = find_matching_annotations(image_info, annotations_df)
    
    # Create output dataframe
    result_df = create_wide_format(image_info, matching_notes, matching_anns, args.max_cols)
    
    # Save results
    save_results(result_df, args.output, args.format)
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE!")
    print("="*60)
    print(f"\nSummary:")
    print(f"  Image: {args.image_path}")
    print(f"  Matching notes: {len(matching_notes)}")
    print(f"  Matching annotations: {len(matching_anns)}")
    print(f"  Output file: {args.output}")

if __name__ == "__main__":
    main()