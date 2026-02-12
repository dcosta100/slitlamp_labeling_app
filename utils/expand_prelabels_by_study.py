"""
Expand AI pre-labels by maskedid_studyid
Uses preprocessed dataset and existing labels
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import PREPROCESSED_PATH, IMAGE_BASE_PATH

def build_image_path(row):
    """Build image path from row data"""
    base_path = Path(IMAGE_BASE_PATH)
    
    maskedid = str(row.get('maskedid', ''))
    maskedid_studyid = str(row.get('maskedid_studyid', ''))
    proc_name = str(row.get('proc_name', ''))
    photo_name = str(row.get('photo_name', ''))
    
    path = base_path / maskedid / maskedid_studyid / proc_name / photo_name
    return str(path)

def expand_prelabels_by_study(labels_file, preprocessed_file, output_file):
    """
    Expand pre-labels to all images with same maskedid_studyid
    
    Logic:
    - If maskedid_studyid has ANY pre-label → ALL images in that study get the label
    - Keeps same laterality, quality, conditions for all images in the study
    
    Args:
        labels_file: Path to AI_prelabel_labels.json
        preprocessed_file: Path to preprocessed_dataset.parquet
        output_file: Path to save expanded labels
    
    Returns:
        Number of original labels, number of expanded labels
    """
    
    print("="*70)
    print("EXPANDING PRE-LABELS BY MASKEDID_STUDYID")
    print("="*70)
    print(f"\nOriginal labels: {labels_file}")
    print(f"Preprocessed data: {preprocessed_file}")
    print(f"Output: {output_file}\n")
    
    # Load original labels
    print("Loading original labels...")
    with open(labels_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    original_labels = original_data.get('labels', {})
    original_count = len(original_labels)
    
    print(f"  Original labels: {original_count:,}")
    
    # Index labels by maskedid_studyid
    print("\nIndexing labels by maskedid_studyid...")
    labels_by_study = {}
    
    for image_path, label_data in original_labels.items():
        maskedid_studyid = label_data.get('metadata', {}).get('maskedid_studyid', '')
        
        if maskedid_studyid:
            # Store first label found for this study (we'll use it for all images)
            if maskedid_studyid not in labels_by_study:
                labels_by_study[maskedid_studyid] = {
                    'original_path': image_path,
                    'label_data': label_data
                }
    
    print(f"  Unique maskedid_studyid with labels: {len(labels_by_study):,}")
    
    # Load preprocessed dataset
    print("\nLoading preprocessed dataset...")
    df = pd.read_parquet(preprocessed_file)
    
    # Convert to string
    if 'maskedid_studyid' in df.columns:
        df['maskedid_studyid'] = df['maskedid_studyid'].astype(str).str.strip()
    
    print(f"  Total images in preprocessed: {len(df):,}")
    
    # Build image paths
    print("\nBuilding image paths...")
    df['image_path'] = df.apply(build_image_path, axis=1)
    
    # Expand labels
    print("\nExpanding labels to all images in same study...")
    expanded_labels = {}
    expansion_stats = {
        'studies_with_labels': len(labels_by_study),
        'original_kept': 0,
        'new_expanded': 0
    }
    
    processed_studies = 0
    
    for maskedid_studyid, label_info in labels_by_study.items():
        processed_studies += 1
        if processed_studies % 100 == 0:
            print(f"  Processing study {processed_studies}/{len(labels_by_study)}...")
        
        original_label = label_info['label_data']
        original_path = label_info['original_path']
        
        # Get ALL images for this maskedid_studyid
        study_images = df[df['maskedid_studyid'] == maskedid_studyid]
        
        if study_images.empty:
            continue
        
        # Apply label to ALL images in this study
        for _, row in study_images.iterrows():
            image_path = row['image_path']
            
            # Create label with updated metadata
            new_label = original_label.copy()
            new_label['metadata'] = original_label.get('metadata', {}).copy()
            new_label['metadata']['maskedid_studyid'] = str(row.get('maskedid_studyid', ''))
            new_label['metadata']['exam_date'] = str(row.get('exam_date', ''))
            new_label['metadata']['pat_mrn'] = str(row.get('pat_mrn', ''))
            
            # Mark if this is the original or expanded
            if image_path == original_path:
                new_label['metadata']['is_original'] = True
                expansion_stats['original_kept'] += 1
            else:
                new_label['metadata']['is_original'] = False
                new_label['metadata']['expanded_from'] = original_path
                expansion_stats['new_expanded'] += 1
            
            expanded_labels[image_path] = new_label
    
    # Create final JSON
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    expanded_data = {
        "user": "AI_prelabel",
        "created_at": now,
        "last_modified": now,
        "labels": expanded_labels,
        "metadata": {
            "expanded_from": str(labels_file),
            "expansion_method": "by_maskedid_studyid",
            "original_count": original_count,
            "expanded_count": len(expanded_labels),
            "expansion_stats": expansion_stats
        }
    }
    
    # Save expanded labels
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(expanded_data, f, indent=2, ensure_ascii=False)
    
    # Print results
    print("\n" + "="*70)
    print("EXPANSION COMPLETE")
    print("="*70)
    print(f"\n📊 STATISTICS:")
    print(f"  Studies with labels: {expansion_stats['studies_with_labels']:,}")
    print(f"  Original labels kept: {expansion_stats['original_kept']:,}")
    print(f"  New expanded labels: {expansion_stats['new_expanded']:,}")
    print(f"  Total labels: {len(expanded_labels):,}")
    print(f"\n📈 Expansion ratio: {len(expanded_labels)/original_count:.1f}x")
    print(f"\n📁 Saved to: {output_file}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    
    # Print sample
    print(f"\n📋 SAMPLE EXPANSION:")
    sample_study = list(labels_by_study.keys())[0] if labels_by_study else None
    if sample_study:
        study_labels = [p for p, l in expanded_labels.items() 
                       if l.get('metadata', {}).get('maskedid_studyid') == sample_study]
        print(f"  Study: {sample_study}")
        print(f"  Total images with this label: {len(study_labels)}")
        print(f"  Sample paths:")
        for path in study_labels[:3]:
            is_orig = expanded_labels[path].get('metadata', {}).get('is_original', False)
            marker = "★ ORIGINAL" if is_orig else "  EXPANDED"
            print(f"    {marker}: {Path(path).name}")
    
    return original_count, len(expanded_labels)

def main():
    """Main expansion function"""
    
    # Paths
    labels_file = Path("../data/labels/AI_prelabel_labels.json")
    preprocessed_file = Path(PREPROCESSED_PATH)
    output_file = Path("../data/labels/AI_prelabel_labels_expanded.json")
    
    if not labels_file.exists():
        print(f"❌ ERROR: Labels file not found: {labels_file}")
        print("   Run create_prelabels_from_xlsx.py first")
        return
    
    if not preprocessed_file.exists():
        print(f"❌ ERROR: Preprocessed file not found: {preprocessed_file}")
        print("   Run preprocessing/create_preprocessed_dataset.py first")
        return
    
    # Expand labels
    original_count, expanded_count = expand_prelabels_by_study(
        labels_file=labels_file,
        preprocessed_file=preprocessed_file,
        output_file=output_file
    )
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Review the expanded labels file")
    print("2. Backup and replace:")
    print("   cd data/labels")
    print("   mv AI_prelabel_labels.json AI_prelabel_labels_ORIGINAL.json")
    print("   mv AI_prelabel_labels_expanded.json AI_prelabel_labels.json")
    print("\n3. Restart app to use expanded labels")
    print("4. All users will see pre-labeled images first (prelabel_first strategy)")
    print(f"\n5. Expected: ~{expanded_count:,} images will have pre-labels")

if __name__ == "__main__":
    main()
