"""
Preprocessing script to create a single file with all matches pre-calculated
Run this ONCE to create the preprocessed dataset, then use it in the main app
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import (
    DIAGNOSIS_PATH,
    ANONYMIZED_EHR_PATH,
    CROSS_PATH,
    ANNOTATIONS_PATH,
    MAX_NOTE_DAYS_DIFFERENCE,
    MAX_ANNOTATION_DAYS_DIFFERENCE
)

def load_all_data():
    """Load all datasets"""
    print("Loading datasets...")
    
    # Load diagnosis data
    print("  - Loading diagnosis data...")
    diagnosis_df = pd.read_stata(DIAGNOSIS_PATH)
    diagnosis_df['exam_date'] = pd.to_datetime(diagnosis_df['exam_date'])
    
    # Convert pat_mrn to string for consistent matching
    if 'pat_mrn' in diagnosis_df.columns:
        diagnosis_df['pat_mrn'] = diagnosis_df['pat_mrn'].astype(str).str.strip()
    
    # Load notes data
    print("  - Loading notes data...")
    notes_df = pd.read_parquet(ANONYMIZED_EHR_PATH)
    notes_df['note_date'] = pd.to_datetime(notes_df['note_date'])
    
    # Convert pat_mrn to string for consistent matching
    if 'pat_mrn' in notes_df.columns:
        notes_df['pat_mrn'] = notes_df['pat_mrn'].astype(str).str.strip()
    
    # Filter for Progress Notes only
    if 'ip_note_type' in notes_df.columns:
        original_count = len(notes_df)
        notes_df = notes_df[notes_df['ip_note_type'] == 'Progress Notes'].copy()
        print(f"     Filtered to Progress Notes: {len(notes_df):,} / {original_count:,} ({100*len(notes_df)/original_count:.1f}%)")
    else:
        print("     Warning: 'ip_note_type' column not found - using all notes")
    
    # Load crosswalk data
    print("  - Loading crosswalk data...")
    cross_df = pd.read_csv(CROSS_PATH)
    
    # Load annotations data
    print("  - Loading annotations data...")
    annotations_df = pd.read_csv(ANNOTATIONS_PATH)
    if 'studyid' in annotations_df.columns:
        annotations_df.rename(columns={'studyid': 'maskedid'}, inplace=True)
    if 'date' in annotations_df.columns:
        annotations_df['annotation_date'] = pd.to_datetime(annotations_df['date'])
    
    # Convert maskedid to string for consistent matching
    if 'maskedid' in annotations_df.columns:
        annotations_df['maskedid'] = annotations_df['maskedid'].astype(str).str.strip()
    if 'maskedid' in cross_df.columns:
        cross_df['maskedid'] = cross_df['maskedid'].astype(str).str.strip()
    
    print("All datasets loaded successfully!")
    return diagnosis_df, notes_df, cross_df, annotations_df

def merge_base_data(cross_df, diagnosis_df):
    """Merge crosswalk with diagnosis"""
    print("\nMerging base datasets...")
    
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
    
    print(f"Merged dataset has {len(merged_df)} rows")
    return merged_df

def add_notes_flags(merged_df, notes_df):
    """Add flag indicating if patient has matching notes"""
    print("\nCalculating notes matches...")
    
    # Ensure pat_mrn is string in merged_df too
    if 'pat_mrn' in merged_df.columns:
        merged_df['pat_mrn'] = merged_df['pat_mrn'].astype(str).str.strip()
    
    merged_df['has_notes'] = False
    merged_df['notes_count'] = 0
    
    # Debug: Check unique values
    unique_mrns_merged = merged_df['pat_mrn'].dropna().nunique()
    unique_mrns_notes = notes_df['pat_mrn'].dropna().nunique()
    print(f"  Debug: Unique MRNs in merged: {unique_mrns_merged:,}")
    print(f"  Debug: Unique MRNs in notes: {unique_mrns_notes:,}")
    
    # Find overlap
    mrns_in_both = set(merged_df['pat_mrn'].dropna()) & set(notes_df['pat_mrn'].dropna())
    print(f"  Debug: MRNs in both datasets: {len(mrns_in_both):,}")
    
    # Group notes by patient
    notes_by_patient = notes_df.groupby('pat_mrn')
    
    total = len(merged_df)
    matches_found = 0
    
    for idx, row in merged_df.iterrows():
        if idx % 10000 == 0:
            print(f"  Processing row {idx:,}/{total:,} ({100*idx/total:.1f}%) - Matches so far: {matches_found:,}")
        
        pat_mrn = row.get('pat_mrn')
        exam_date = row.get('exam_date')
        
        if pd.notna(pat_mrn) and pd.notna(exam_date) and pat_mrn in notes_by_patient.groups:
            patient_notes = notes_by_patient.get_group(pat_mrn)
            
            # Calculate days difference
            days_diff = (patient_notes['note_date'] - exam_date).dt.days.abs()
            
            # Check if any notes within threshold
            matching_notes = (days_diff <= MAX_NOTE_DAYS_DIFFERENCE).sum()
            
            if matching_notes > 0:
                merged_df.at[idx, 'has_notes'] = True
                merged_df.at[idx, 'notes_count'] = matching_notes
                matches_found += 1
    
    print(f"Found {merged_df['has_notes'].sum():,} images with matching notes ({100*merged_df['has_notes'].sum()/len(merged_df):.2f}%)")
    return merged_df

def add_annotations_flags(merged_df, annotations_df):
    """Add flag indicating if image has matching annotations"""
    print("\nCalculating annotations matches...")
    
    # Ensure maskedid is string in merged_df too
    if 'maskedid' in merged_df.columns:
        merged_df['maskedid'] = merged_df['maskedid'].astype(str).str.strip()
    
    merged_df['has_annotations'] = False
    merged_df['annotations_count'] = 0
    
    # Debug: Check unique values
    unique_ids_merged = merged_df['maskedid'].dropna().nunique()
    unique_ids_annotations = annotations_df['maskedid'].dropna().nunique()
    print(f"  Debug: Unique maskedids in merged: {unique_ids_merged:,}")
    print(f"  Debug: Unique maskedids in annotations: {unique_ids_annotations:,}")
    
    # Find overlap
    ids_in_both = set(merged_df['maskedid'].dropna()) & set(annotations_df['maskedid'].dropna())
    print(f"  Debug: maskedids in both datasets: {len(ids_in_both):,}")
    
    # Group annotations by maskedid
    annotations_by_id = annotations_df.groupby('maskedid')
    
    total = len(merged_df)
    matches_found = 0
    
    for idx, row in merged_df.iterrows():
        if idx % 10000 == 0:
            print(f"  Processing row {idx:,}/{total:,} ({100*idx/total:.1f}%) - Matches so far: {matches_found:,}")
        
        maskedid = row.get('maskedid')
        exam_date = row.get('exam_date')
        
        if pd.notna(maskedid) and pd.notna(exam_date) and maskedid in annotations_by_id.groups:
            patient_anns = annotations_by_id.get_group(maskedid)
            
            # Calculate days difference
            days_diff = (patient_anns['annotation_date'] - exam_date).dt.days.abs()
            
            # Check if any annotations within threshold
            matching_anns = (days_diff <= MAX_ANNOTATION_DAYS_DIFFERENCE).sum()
            
            if matching_anns > 0:
                merged_df.at[idx, 'has_annotations'] = True
                merged_df.at[idx, 'annotations_count'] = matching_anns
                matches_found += 1
    
    print(f"Found {merged_df['has_annotations'].sum():,} images with matching annotations ({100*merged_df['has_annotations'].sum()/len(merged_df):.2f}%)")
    return merged_df

def save_preprocessed_data(merged_df, output_path):
    """Save preprocessed dataset"""
    print(f"\nSaving preprocessed dataset to {output_path}...")
    
    # Save as parquet for efficiency
    merged_df.to_parquet(output_path, index=False, compression='gzip')
    
    # Also save summary statistics
    summary = {
        'total_images': len(merged_df),
        'with_notes': merged_df['has_notes'].sum(),
        'with_annotations': merged_df['has_annotations'].sum(),
        'with_both': (merged_df['has_notes'] & merged_df['has_annotations']).sum(),
        'created_at': datetime.now().isoformat()
    }
    
    summary_path = output_path.replace('.parquet', '_summary.txt')
    with open(summary_path, 'w') as f:
        for key, value in summary.items():
            f.write(f"{key}: {value}\n")
    
    print(f"Preprocessed dataset saved successfully!")
    print(f"Summary saved to {summary_path}")
    return summary

def main():
    """Main preprocessing function"""
    print("="*60)
    print("SLITLAMP DATASET PREPROCESSING")
    print("="*60)
    
    # Load data
    diagnosis_df, notes_df, cross_df, annotations_df = load_all_data()
    
    # Merge base data
    merged_df = merge_base_data(cross_df, diagnosis_df)
    
    # Add notes flags
    merged_df = add_notes_flags(merged_df, notes_df)
    
    # Add annotations flags
    merged_df = add_annotations_flags(merged_df, annotations_df)
    
    # Save preprocessed data
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / 'preprocessed_dataset.parquet'
    
    summary = save_preprocessed_data(merged_df, str(output_path))
    
    print("\n" + "="*60)
    print("PREPROCESSING COMPLETE!")
    print("="*60)
    print(f"\nSummary:")
    print(f"  Total images: {summary['total_images']:,}")
    print(f"  With notes: {summary['with_notes']:,} ({100*summary['with_notes']/summary['total_images']:.1f}%)")
    print(f"  With annotations: {summary['with_annotations']:,} ({100*summary['with_annotations']/summary['total_images']:.1f}%)")
    print(f"  With both: {summary['with_both']:,} ({100*summary['with_both']/summary['total_images']:.1f}%)")
    print(f"\nPreprocessed file: {output_path}")
    print(f"File size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    print("\nYou can now use this preprocessed file in the main app!")

if __name__ == "__main__":
    main()
