"""
Create a comprehensive parquet file with all images that have both notes and annotations
This creates a wide-format dataset ready for analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
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
    IMAGE_BASE_PATH,
    MAX_NOTE_DAYS_DIFFERENCE,
    MAX_ANNOTATION_DAYS_DIFFERENCE,
    PREPROCESSED_PATH,
    USE_PREPROCESSED
)

def load_data():
    """Load all necessary datasets"""
    print("="*60)
    print("LOADING DATA")
    print("="*60)
    
    # Load diagnosis data
    print("\n1. Loading diagnosis data...")
    diagnosis_df = pd.read_stata(DIAGNOSIS_PATH)
    diagnosis_df['exam_date'] = pd.to_datetime(diagnosis_df['exam_date'])
    if 'pat_mrn' in diagnosis_df.columns:
        diagnosis_df['pat_mrn'] = diagnosis_df['pat_mrn'].astype(str).str.strip()
    print(f"   ✓ Loaded {len(diagnosis_df):,} diagnosis records")
    
    # Load notes data
    print("\n2. Loading notes data...")
    notes_df = pd.read_parquet(ANONYMIZED_EHR_PATH)
    notes_df['note_date'] = pd.to_datetime(notes_df['note_date'])
    if 'pat_mrn' in notes_df.columns:
        notes_df['pat_mrn'] = notes_df['pat_mrn'].astype(str).str.strip()
    
    # Filter for Progress Notes only
    if 'ip_note_type' in notes_df.columns:
        original_count = len(notes_df)
        notes_df = notes_df[notes_df['ip_note_type'] == 'Progress Notes'].copy()
        print(f"   ✓ Loaded {len(notes_df):,} Progress Notes (filtered from {original_count:,})")
    else:
        print(f"   ✓ Loaded {len(notes_df):,} notes")
    
    # Load crosswalk data
    print("\n3. Loading crosswalk data...")
    cross_df = pd.read_csv(CROSS_PATH)
    if 'maskedid' in cross_df.columns:
        cross_df['maskedid'] = cross_df['maskedid'].astype(str).str.strip()
    print(f"   ✓ Loaded {len(cross_df):,} image records")
    
    # Load annotations data
    print("\n4. Loading annotations data...")
    annotations_df = pd.read_csv(ANNOTATIONS_PATH)
    if 'studyid' in annotations_df.columns:
        annotations_df.rename(columns={'studyid': 'maskedid'}, inplace=True)
    if 'date' in annotations_df.columns:
        annotations_df['annotation_date'] = pd.to_datetime(annotations_df['date'])
    if 'maskedid' in annotations_df.columns:
        annotations_df['maskedid'] = annotations_df['maskedid'].astype(str).str.strip()
    print(f"   ✓ Loaded {len(annotations_df):,} annotation records")
    
    print("\n✅ All datasets loaded successfully!")
    return diagnosis_df, notes_df, cross_df, annotations_df

def merge_base_data(cross_df, diagnosis_df):
    """Merge crosswalk with diagnosis"""
    print("\n" + "="*60)
    print("MERGING BASE DATASETS")
    print("="*60)
    
    merged_df = cross_df.merge(
        diagnosis_df,
        on='maskedid_studyid',
        how='left',
        suffixes=('', '_diag')
    )
    
    # Handle duplicate columns
    for col in list(merged_df.columns):
        if col.endswith('_diag'):
            original_col = col.replace('_diag', '')
            if original_col in merged_df.columns:
                merged_df[original_col] = merged_df[original_col].fillna(merged_df[col])
            else:
                merged_df[original_col] = merged_df[col]
            merged_df.drop(col, axis=1, inplace=True)
    
    # Ensure pat_mrn and maskedid are strings
    if 'pat_mrn' in merged_df.columns:
        merged_df['pat_mrn'] = merged_df['pat_mrn'].astype(str).str.strip()
    if 'maskedid' in merged_df.columns:
        merged_df['maskedid'] = merged_df['maskedid'].astype(str).str.strip()
    
    # Add image path
    merged_df['image_path'] = merged_df.apply(
        lambda row: str(Path(IMAGE_BASE_PATH) / row['maskedid'] / row['maskedid_studyid'] / row['proc_name'] / row['photo_name']),
        axis=1
    )
    
    print(f"✓ Merged dataset has {len(merged_df):,} images")
    return merged_df

def filter_images_with_both(merged_df, notes_df, annotations_df):
    """Filter to only images that have both notes and annotations"""
    print("\n" + "="*60)
    print("FILTERING IMAGES WITH NOTES AND ANNOTATIONS")
    print("="*60)
    
    # Index notes and annotations for faster lookup
    print("\n1. Indexing notes by patient...")
    notes_by_patient = notes_df.groupby('pat_mrn')
    print(f"   ✓ Indexed {len(notes_by_patient):,} patients with notes")
    
    print("\n2. Indexing annotations by maskedid...")
    annotations_by_id = annotations_df.groupby('maskedid')
    print(f"   ✓ Indexed {len(annotations_by_id):,} patients with annotations")
    
    # Filter images
    print("\n3. Filtering images...")
    has_notes = []
    has_annotations = []
    
    for idx, row in tqdm(merged_df.iterrows(), total=len(merged_df), desc="   Checking images"):
        pat_mrn = row.get('pat_mrn')
        maskedid = row.get('maskedid')
        exam_date = row.get('exam_date')
        
        # Check notes
        notes_match = False
        if pd.notna(pat_mrn) and pd.notna(exam_date) and pat_mrn in notes_by_patient.groups:
            patient_notes = notes_by_patient.get_group(pat_mrn)
            days_diff = (patient_notes['note_date'] - exam_date).dt.days.abs()
            notes_match = (days_diff <= MAX_NOTE_DAYS_DIFFERENCE).any()
        
        # Check annotations
        annotations_match = False
        if pd.notna(maskedid) and pd.notna(exam_date) and maskedid in annotations_by_id.groups:
            patient_anns = annotations_by_id.get_group(maskedid)
            days_diff = (patient_anns['annotation_date'] - exam_date).dt.days.abs()
            annotations_match = (days_diff <= MAX_ANNOTATION_DAYS_DIFFERENCE).any()
        
        has_notes.append(notes_match)
        has_annotations.append(annotations_match)
    
    merged_df['has_notes'] = has_notes
    merged_df['has_annotations'] = has_annotations
    
    # Filter to only images with both
    filtered_df = merged_df[merged_df['has_notes'] & merged_df['has_annotations']].copy()
    
    print(f"\n✓ Filtering complete:")
    print(f"   Total images: {len(merged_df):,}")
    print(f"   With notes: {merged_df['has_notes'].sum():,} ({100*merged_df['has_notes'].sum()/len(merged_df):.1f}%)")
    print(f"   With annotations: {merged_df['has_annotations'].sum():,} ({100*merged_df['has_annotations'].sum()/len(merged_df):.1f}%)")
    print(f"   With BOTH: {len(filtered_df):,} ({100*len(filtered_df)/len(merged_df):.1f}%)")
    
    return filtered_df

def add_matched_data(filtered_df, notes_df, annotations_df, max_notes=5, max_annotations=5):
    """Add matched notes and annotations to each image"""
    print("\n" + "="*60)
    print("ADDING MATCHED NOTES AND ANNOTATIONS")
    print("="*60)
    
    # Index for faster lookup
    notes_by_patient = notes_df.groupby('pat_mrn')
    annotations_by_id = annotations_df.groupby('maskedid')
    
    # Prepare columns for notes
    note_columns = []
    for i in range(1, max_notes + 1):
        note_columns.extend([
            f'note_{i}_date',
            f'note_{i}_days_diff',
            f'note_{i}_type',
            f'note_{i}_text_preview',
            f'note_{i}_full_text'
        ])
    
    # Prepare columns for annotations
    ann_columns = []
    for i in range(1, max_annotations + 1):
        ann_columns.extend([
            f'annotation_{i}_date',
            f'annotation_{i}_days_diff'
        ])
    
    # Initialize all columns with None
    for col in note_columns + ann_columns:
        filtered_df[col] = None
    
    # Also track counts
    filtered_df['total_matching_notes'] = 0
    filtered_df['total_matching_annotations'] = 0
    
    print(f"\nProcessing {len(filtered_df):,} images...")
    
    for idx, row in tqdm(filtered_df.iterrows(), total=len(filtered_df), desc="Adding matched data"):
        pat_mrn = row.get('pat_mrn')
        maskedid = row.get('maskedid')
        exam_date = row.get('exam_date')
        
        # Get matching notes
        if pd.notna(pat_mrn) and pd.notna(exam_date) and pat_mrn in notes_by_patient.groups:
            patient_notes = notes_by_patient.get_group(pat_mrn).copy()
            patient_notes['days_difference'] = (patient_notes['note_date'] - exam_date).dt.days.abs()
            matching_notes = patient_notes[patient_notes['days_difference'] <= MAX_NOTE_DAYS_DIFFERENCE].copy()
            matching_notes = matching_notes.sort_values('days_difference').head(max_notes)
            
            filtered_df.at[idx, 'total_matching_notes'] = len(matching_notes)
            
            for i, (_, note) in enumerate(matching_notes.iterrows(), 1):
                if i <= max_notes:
                    filtered_df.at[idx, f'note_{i}_date'] = note.get('note_date')
                    filtered_df.at[idx, f'note_{i}_days_diff'] = int(note.get('days_difference', 0))
                    filtered_df.at[idx, f'note_{i}_type'] = note.get('ip_note_type', '')
                    note_text = str(note.get('note_text', ''))
                    filtered_df.at[idx, f'note_{i}_text_preview'] = note_text[:500] if note_text else ''
                    filtered_df.at[idx, f'note_{i}_full_text'] = note_text
        
        # Get matching annotations
        if pd.notna(maskedid) and pd.notna(exam_date) and maskedid in annotations_by_id.groups:
            patient_anns = annotations_by_id.get_group(maskedid).copy()
            patient_anns['days_difference'] = (patient_anns['annotation_date'] - exam_date).dt.days.abs()
            matching_anns = patient_anns[patient_anns['days_difference'] <= MAX_ANNOTATION_DAYS_DIFFERENCE].copy()
            matching_anns = matching_anns.sort_values('days_difference').head(max_annotations)
            
            filtered_df.at[idx, 'total_matching_annotations'] = len(matching_anns)
            
            for i, (_, ann) in enumerate(matching_anns.iterrows(), 1):
                if i <= max_annotations:
                    filtered_df.at[idx, f'annotation_{i}_date'] = ann.get('annotation_date')
                    filtered_df.at[idx, f'annotation_{i}_days_diff'] = int(ann.get('days_difference', 0))
                    
                    # Add all annotation fields dynamically
                    for col in ann.index:
                        if col not in ['maskedid', 'annotation_date', 'days_difference', 'date']:
                            filtered_df.at[idx, f'annotation_{i}_{col}'] = ann.get(col)
    
    print(f"\n✓ Added matched data successfully!")
    print(f"   Average notes per image: {filtered_df['total_matching_notes'].mean():.1f}")
    print(f"   Average annotations per image: {filtered_df['total_matching_annotations'].mean():.1f}")
    
    return filtered_df

def save_results(df, output_path):
    """Save the final dataset"""
    print("\n" + "="*60)
    print("SAVING RESULTS")
    print("="*60)
    
    print(f"\nSaving to: {output_path}")
    
    # Save as parquet
    df.to_parquet(output_path, index=False, compression='gzip')
    
    # Calculate file size
    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    
    # Save summary
    summary = {
        'created_at': datetime.now().isoformat(),
        'total_images': len(df),
        'total_columns': len(df.columns),
        'file_size_mb': file_size_mb,
        'avg_notes_per_image': df['total_matching_notes'].mean(),
        'avg_annotations_per_image': df['total_matching_annotations'].mean(),
        'max_note_days_diff': MAX_NOTE_DAYS_DIFFERENCE,
        'max_annotation_days_diff': MAX_ANNOTATION_DAYS_DIFFERENCE
    }
    
    summary_path = str(output_path).replace('.parquet', '_summary.txt')
    with open(summary_path, 'w') as f:
        for key, value in summary.items():
            f.write(f"{key}: {value}\n")
    
    print(f"\n✓ Saved successfully!")
    print(f"   File: {output_path}")
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"   Rows: {len(df):,}")
    print(f"   Columns: {len(df.columns):,}")
    print(f"   Summary: {summary_path}")
    
    return summary

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create comprehensive parquet with all images that have both notes and annotations'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='complete_dataset_with_notes_annotations.parquet',
        help='Output parquet file path'
    )
    parser.add_argument(
        '--max_notes',
        type=int,
        default=5,
        help='Maximum number of notes to include per image (default: 5)'
    )
    parser.add_argument(
        '--max_annotations',
        type=int,
        default=5,
        help='Maximum number of annotations to include per image (default: 5)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("COMPREHENSIVE DATASET GENERATOR")
    print("Images with BOTH Notes AND Annotations")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"   Max notes per image: {args.max_notes}")
    print(f"   Max annotations per image: {args.max_annotations}")
    print(f"   Note matching window: {MAX_NOTE_DAYS_DIFFERENCE} days")
    print(f"   Annotation matching window: {MAX_ANNOTATION_DAYS_DIFFERENCE} days")
    print(f"   Output file: {args.output}")
    
    # Load data
    diagnosis_df, notes_df, cross_df, annotations_df = load_data()
    
    # Merge base data
    merged_df = merge_base_data(cross_df, diagnosis_df)
    
    # Filter to images with both notes and annotations
    filtered_df = filter_images_with_both(merged_df, notes_df, annotations_df)
    
    if len(filtered_df) == 0:
        print("\n❌ ERROR: No images found with both notes and annotations!")
        print("   Check your filtering criteria and data.")
        return
    
    # Add matched notes and annotations
    result_df = add_matched_data(filtered_df, notes_df, annotations_df, args.max_notes, args.max_annotations)
    
    # Save results
    summary = save_results(result_df, args.output)
    
    print("\n" + "="*60)
    print("GENERATION COMPLETE!")
    print("="*60)
    print(f"\nDataset Summary:")
    print(f"   Total images: {summary['total_images']:,}")
    print(f"   Average notes/image: {summary['avg_notes_per_image']:.1f}")
    print(f"   Average annotations/image: {summary['avg_annotations_per_image']:.1f}")
    print(f"   File size: {summary['file_size_mb']:.1f} MB")
    print(f"\n✅ Ready to use!")
    print(f"\nLoad in Python with:")
    print(f"   df = pd.read_parquet('{args.output}')")

if __name__ == "__main__":
    main()