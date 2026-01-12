"""
Batch script to extract matching notes and annotations for multiple images
Usage: python batch_get_image_matches.py --image_list images.txt --output results.csv
       python batch_get_image_matches.py --image_paths "path1.jpg" "path2.jpg" --output results.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import sys
from datetime import datetime
from tqdm import tqdm

# Add parent directory to path if needed
sys.path.append(str(Path(__file__).parent))

from config import (
    DIAGNOSIS_PATH,
    ANONYMIZED_EHR_PATH,
    CROSS_PATH,
    ANNOTATIONS_PATH,
    MAX_NOTE_DAYS_DIFFERENCE,
    MAX_ANNOTATION_DAYS_DIFFERENCE,
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

def process_single_image(image_path, cross_df, diagnosis_df, notes_df, annotations_df, max_cols=5):
    """Process a single image and return results"""
    
    # Parse the image path structure
    # Expected: BASE_PATH / maskedid / maskedid_studyid / proc_name / photo_name
    path_obj = Path(image_path)
    photo_name = path_obj.name
    proc_name = path_obj.parent.name
    maskedid_studyid = path_obj.parent.parent.name
    maskedid = path_obj.parent.parent.parent.name
    
    # Search in crosswalk using multiple criteria for best match
    image_row = None
    
    # Try matching by maskedid_studyid and photo_name (most specific)
    if 'maskedid_studyid' in cross_df.columns and 'photo_name' in cross_df.columns:
        mask = (cross_df['maskedid_studyid'] == maskedid_studyid) & (cross_df['photo_name'] == photo_name)
        if mask.any():
            image_row = cross_df[mask].iloc[0]
    
    # If not found, try just photo_name (less specific but may work)
    if image_row is None and 'photo_name' in cross_df.columns:
        mask = cross_df['photo_name'] == photo_name
        if mask.any():
            image_row = cross_df[mask].iloc[0]
    
    # If still not found, try partial matching on photo_name
    if image_row is None and 'photo_name' in cross_df.columns:
        mask = cross_df['photo_name'].astype(str).str.contains(photo_name, case=False, na=False, regex=False)
        if mask.any():
            image_row = cross_df[mask].iloc[0]
    
    if image_row is None:
        return {
            'image_path': image_path,
            'error': 'Image not found in crosswalk',
            'total_matching_notes': 0,
            'total_matching_annotations': 0
        }
    
    # Get image info
    maskedid_studyid = image_row.get('maskedid_studyid')
    if pd.isna(maskedid_studyid):
        return {
            'image_path': image_path,
            'error': 'No maskedid_studyid found',
            'total_matching_notes': 0,
            'total_matching_annotations': 0
        }
    
    # Find diagnosis info
    diag_row = diagnosis_df[diagnosis_df['maskedid_studyid'] == maskedid_studyid]
    if len(diag_row) == 0:
        image_info = image_row.to_dict()
    else:
        image_info = {**image_row.to_dict(), **diag_row.iloc[0].to_dict()}
    
    # Find matching notes
    pat_mrn = image_info.get('pat_mrn')
    exam_date = image_info.get('exam_date')
    
    matching_notes = pd.DataFrame()
    if pd.notna(pat_mrn) and pd.notna(exam_date):
        patient_notes = notes_df[notes_df['pat_mrn'] == str(pat_mrn)].copy()
        if len(patient_notes) > 0:
            patient_notes['days_difference'] = (patient_notes['note_date'] - pd.to_datetime(exam_date)).dt.days.abs()
            matching_notes = patient_notes[patient_notes['days_difference'] <= MAX_NOTE_DAYS_DIFFERENCE].copy()
            matching_notes = matching_notes.sort_values('days_difference')
    
    # Find matching annotations
    maskedid = image_info.get('maskedid')
    
    matching_anns = pd.DataFrame()
    if pd.notna(maskedid) and pd.notna(exam_date):
        patient_anns = annotations_df[annotations_df['maskedid'] == str(maskedid)].copy()
        if len(patient_anns) > 0:
            patient_anns['days_difference'] = (patient_anns['annotation_date'] - pd.to_datetime(exam_date)).dt.days.abs()
            matching_anns = patient_anns[patient_anns['days_difference'] <= MAX_ANNOTATION_DAYS_DIFFERENCE].copy()
            matching_anns = matching_anns.sort_values('days_difference')
    
    # Create result dictionary
    result = {
        'image_path': image_path,
        'maskedid_studyid': image_info.get('maskedid_studyid', ''),
        'maskedid': image_info.get('maskedid', ''),
        'pat_mrn': image_info.get('pat_mrn', ''),
        'exam_date': image_info.get('exam_date', ''),
        'laterality': image_info.get('laterality', ''),
        'total_matching_notes': len(matching_notes),
        'total_matching_annotations': len(matching_anns)
    }
    
    # Add notes (up to max_cols)
    for i in range(max_cols):
        if i < len(matching_notes):
            note = matching_notes.iloc[i]
            result[f'note_{i+1}_date'] = note.get('note_date', '')
            result[f'note_{i+1}_days_diff'] = note.get('days_difference', '')
            result[f'note_{i+1}_type'] = note.get('ip_note_type', '')
            result[f'note_{i+1}_text_preview'] = str(note.get('note_text', ''))[:500] if 'note_text' in note else ''
            result[f'note_{i+1}_full_text'] = note.get('note_text', '')
        else:
            result[f'note_{i+1}_date'] = None
            result[f'note_{i+1}_days_diff'] = None
            result[f'note_{i+1}_type'] = None
            result[f'note_{i+1}_text_preview'] = None
            result[f'note_{i+1}_full_text'] = None
    
    # Add annotations (up to max_cols)
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
    
    return result

def main():
    parser = argparse.ArgumentParser(
        description='Extract matching notes and annotations for multiple images'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--image_list',
        type=str,
        help='Path to text file with one image path per line'
    )
    group.add_argument(
        '--image_paths',
        type=str,
        nargs='+',
        help='List of image paths'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='batch_image_matches.csv',
        help='Output file path (default: batch_image_matches.csv)'
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
        help='Maximum number of note/annotation columns per image (default: 5)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("BATCH IMAGE MATCHES EXTRACTOR")
    print("="*60)
    
    # Get list of image paths
    if args.image_list:
        print(f"\nReading image paths from: {args.image_list}")
        with open(args.image_list, 'r') as f:
            image_paths = [line.strip() for line in f if line.strip()]
    else:
        image_paths = args.image_paths
    
    print(f"Processing {len(image_paths)} images...")
    
    # Load data
    diagnosis_df, notes_df, cross_df, annotations_df = load_data()
    
    # Process all images
    results = []
    for image_path in tqdm(image_paths, desc="Processing images"):
        result = process_single_image(
            image_path, cross_df, diagnosis_df, notes_df, annotations_df, args.max_cols
        )
        results.append(result)
    
    # Create dataframe
    result_df = pd.DataFrame(results)
    
    # Save results
    print(f"\nSaving results to {args.output}...")
    if args.format == 'csv':
        result_df.to_csv(args.output, index=False)
    elif args.format == 'parquet':
        result_df.to_parquet(args.output, index=False)
    
    print(f"Results saved successfully!")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE!")
    print("="*60)
    print(f"\nSummary:")
    print(f"  Total images processed: {len(result_df)}")
    print(f"  Images with notes: {(result_df['total_matching_notes'] > 0).sum()}")
    print(f"  Images with annotations: {(result_df['total_matching_annotations'] > 0).sum()}")
    print(f"  Images with both: {((result_df['total_matching_notes'] > 0) & (result_df['total_matching_annotations'] > 0)).sum()}")
    print(f"  Average notes per image: {result_df['total_matching_notes'].mean():.1f}")
    print(f"  Average annotations per image: {result_df['total_matching_annotations'].mean():.1f}")
    print(f"  Output file: {args.output}")
    print(f"  File size: {Path(args.output).stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()