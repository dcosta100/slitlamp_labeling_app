"""
Validate AI pre-labels against config options
Identifies labels with values that don't match the official config
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import (
    LATERALITY_OPTIONS,
    QUALITY_OPTIONS,
    DRY_EYE_SEVERITY,
    DRY_EYE_SIGNS,
    CATARACT_TYPE,
    CATARACT_SEVERITY,
    CATARACT_FEATURES,
    INFECTIOUS_TYPE,
    INFECTIOUS_ETIOLOGY,
    KERATITIS_SIZE,
    KERATITIS_FEATURES,
    CONJUNCTIVITIS_FEATURES,
    TUMOR_TYPE,
    TUMOR_MALIGNANCY,
    TUMOR_LOCATION,
    TUMOR_FEATURES,
    SCH_PRESENCE,
    SCH_EXTENT
)

def validate_labels(labels_file):
    """Validate all labels in a JSON file"""
    
    print("="*70)
    print("AI PRE-LABELS VALIDATION")
    print("="*70)
    print(f"\nValidating: {labels_file}")
    
    # Load labels
    with open(labels_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    labels = data.get('labels', {})
    total_labels = len(labels)
    
    print(f"Total labels: {total_labels:,}\n")
    
    # Track invalid values
    invalid_values = defaultdict(lambda: defaultdict(set))
    images_with_issues = set()
    issue_count = 0
    
    # Validation mappings
    validations = {
        'laterality': LATERALITY_OPTIONS,
        'quality': QUALITY_OPTIONS,
        'dry_eye_severity': DRY_EYE_SEVERITY,
        'dry_eye_signs': DRY_EYE_SIGNS,
        'cataract_type': CATARACT_TYPE,
        'cataract_severity': CATARACT_SEVERITY,
        'cataract_features': CATARACT_FEATURES,
        'infectious_type': INFECTIOUS_TYPE,
        'infectious_etiology': INFECTIOUS_ETIOLOGY,
        'keratitis_size': KERATITIS_SIZE,
        'keratitis_features': KERATITIS_FEATURES,
        'conjunctivitis_features': CONJUNCTIVITIS_FEATURES,
        'tumor_type': TUMOR_TYPE,
        'tumor_malignancy': TUMOR_MALIGNANCY,
        'tumor_location': TUMOR_LOCATION,
        'tumor_features': TUMOR_FEATURES,
        'sch_presence': SCH_PRESENCE,
        'sch_extent': SCH_EXTENT
    }
    
    print("Validating labels...")
    for image_path, label in labels.items():
        has_issue = False
        
        # Check laterality
        lat = label.get('laterality')
        if lat and lat not in LATERALITY_OPTIONS:
            invalid_values['laterality'][lat].add(image_path)
            has_issue = True
            issue_count += 1
        
        # Check quality
        qual = label.get('quality')
        if qual and qual not in QUALITY_OPTIONS:
            invalid_values['quality'][qual].add(image_path)
            has_issue = True
            issue_count += 1
        
        # Check conditions
        conditions = label.get('conditions', {})
        
        # Dry Eye Disease
        if 'Dry Eye Disease' in conditions:
            dry_eye = conditions['Dry Eye Disease']
            
            severity = dry_eye.get('severity')
            if severity and severity not in DRY_EYE_SEVERITY:
                invalid_values['dry_eye_severity'][severity].add(image_path)
                has_issue = True
                issue_count += 1
            
            signs = dry_eye.get('signs', [])
            for sign in signs:
                if sign not in DRY_EYE_SIGNS:
                    invalid_values['dry_eye_signs'][sign].add(image_path)
                    has_issue = True
                    issue_count += 1
        
        # Cataract
        if 'Cataract' in conditions:
            cataract = conditions['Cataract']
            
            cat_type = cataract.get('type')
            if cat_type and cat_type not in CATARACT_TYPE:
                invalid_values['cataract_type'][cat_type].add(image_path)
                has_issue = True
                issue_count += 1
            
            cat_severity = cataract.get('severity')
            if cat_severity and cat_severity not in CATARACT_SEVERITY:
                invalid_values['cataract_severity'][cat_severity].add(image_path)
                has_issue = True
                issue_count += 1
            
            features = cataract.get('features', [])
            for feature in features:
                if feature not in CATARACT_FEATURES:
                    invalid_values['cataract_features'][feature].add(image_path)
                    has_issue = True
                    issue_count += 1
        
        # Infectious Keratitis / Conjunctivitis
        if 'Infectious Keratitis / Conjunctivitis' in conditions:
            infectious = conditions['Infectious Keratitis / Conjunctivitis']
            
            inf_type = infectious.get('type')
            if inf_type and inf_type not in INFECTIOUS_TYPE:
                invalid_values['infectious_type'][inf_type].add(image_path)
                has_issue = True
                issue_count += 1
            
            etiology = infectious.get('etiology')
            if etiology and etiology not in INFECTIOUS_ETIOLOGY:
                invalid_values['infectious_etiology'][etiology].add(image_path)
                has_issue = True
                issue_count += 1
            
            ker_size = infectious.get('keratitis_size')
            if ker_size and ker_size not in KERATITIS_SIZE:
                invalid_values['keratitis_size'][ker_size].add(image_path)
                has_issue = True
                issue_count += 1
            
            ker_features = infectious.get('keratitis_features', [])
            for feature in ker_features:
                if feature not in KERATITIS_FEATURES:
                    invalid_values['keratitis_features'][feature].add(image_path)
                    has_issue = True
                    issue_count += 1
            
            conj_features = infectious.get('conjunctivitis_features', [])
            for feature in conj_features:
                if feature not in CONJUNCTIVITIS_FEATURES:
                    invalid_values['conjunctivitis_features'][feature].add(image_path)
                    has_issue = True
                    issue_count += 1
        
        # Ocular Surface Tumors
        if 'Ocular Surface Tumors' in conditions:
            tumor = conditions['Ocular Surface Tumors']
            
            tumor_type = tumor.get('type')
            if tumor_type and tumor_type not in TUMOR_TYPE:
                invalid_values['tumor_type'][tumor_type].add(image_path)
                has_issue = True
                issue_count += 1
            
            malignancy = tumor.get('malignancy')
            if malignancy and malignancy not in TUMOR_MALIGNANCY:
                invalid_values['tumor_malignancy'][malignancy].add(image_path)
                has_issue = True
                issue_count += 1
            
            location = tumor.get('location')
            if location and location not in TUMOR_LOCATION:
                invalid_values['tumor_location'][location].add(image_path)
                has_issue = True
                issue_count += 1
            
            features = tumor.get('features', [])
            for feature in features:
                if feature not in TUMOR_FEATURES:
                    invalid_values['tumor_features'][feature].add(image_path)
                    has_issue = True
                    issue_count += 1
        
        # Subconjunctival Hemorrhage
        if 'Subconjunctival Hemorrhage' in conditions:
            sch = conditions['Subconjunctival Hemorrhage']
            
            presence = sch.get('presence')
            if presence and presence not in SCH_PRESENCE:
                invalid_values['sch_presence'][presence].add(image_path)
                has_issue = True
                issue_count += 1
            
            extent = sch.get('extent')
            if extent and extent not in SCH_EXTENT:
                invalid_values['sch_extent'][extent].add(image_path)
                has_issue = True
                issue_count += 1
        
        if has_issue:
            images_with_issues.add(image_path)
    
    # Print results
    print("\n" + "="*70)
    print("VALIDATION RESULTS")
    print("="*70)
    
    if not invalid_values:
        print("\n✅ ALL LABELS ARE VALID! No issues found.")
        return
    
    print(f"\n⚠️  Found {issue_count:,} invalid values in {len(images_with_issues):,} images")
    print(f"   ({100*len(images_with_issues)/total_labels:.1f}% of images have issues)\n")
    
    # Group by field
    for field_name, invalid_vals in sorted(invalid_values.items()):
        print(f"\n{'='*70}")
        print(f"Field: {field_name.upper()}")
        print(f"{'='*70}")
        
        for invalid_val, image_paths in sorted(invalid_vals.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(image_paths)
            print(f"\n  ❌ '{invalid_val}' (found in {count:,} images)")
            
            # Show valid options
            field_key = field_name.replace('_', ' ').title().replace(' ', '_').upper()
            if field_name == 'laterality':
                print(f"     Valid options: {LATERALITY_OPTIONS}")
            elif field_name == 'quality':
                print(f"     Valid options: {QUALITY_OPTIONS}")
            elif 'dry_eye_severity' in field_name:
                print(f"     Valid options: {DRY_EYE_SEVERITY}")
            elif 'dry_eye_signs' in field_name:
                print(f"     Valid options: {DRY_EYE_SIGNS}")
            elif 'cataract_type' in field_name:
                print(f"     Valid options: {CATARACT_TYPE}")
            elif 'cataract_severity' in field_name:
                print(f"     Valid options: {CATARACT_SEVERITY}")
            elif 'cataract_features' in field_name:
                print(f"     Valid options: {CATARACT_FEATURES}")
            elif 'infectious_type' in field_name:
                print(f"     Valid options: {INFECTIOUS_TYPE}")
            elif 'infectious_etiology' in field_name:
                print(f"     Valid options: {INFECTIOUS_ETIOLOGY}")
            elif 'keratitis_size' in field_name:
                print(f"     Valid options: {KERATITIS_SIZE}")
            elif 'keratitis_features' in field_name:
                print(f"     Valid options: {KERATITIS_FEATURES}")
            elif 'conjunctivitis_features' in field_name:
                print(f"     Valid options: {CONJUNCTIVITIS_FEATURES}")
            elif 'tumor_type' in field_name:
                print(f"     Valid options: {TUMOR_TYPE}")
            elif 'tumor_malignancy' in field_name:
                print(f"     Valid options: {TUMOR_MALIGNANCY}")
            elif 'tumor_location' in field_name:
                print(f"     Valid options: {TUMOR_LOCATION}")
            elif 'tumor_features' in field_name:
                print(f"     Valid options: {TUMOR_FEATURES}")
            elif 'sch_presence' in field_name:
                print(f"     Valid options: {SCH_PRESENCE}")
            elif 'sch_extent' in field_name:
                print(f"     Valid options: {SCH_EXTENT}")
            
            # Show first few affected images
            if count <= 3:
                print(f"     Affected images:")
                for img in list(image_paths)[:3]:
                    print(f"       - {img}")
            else:
                print(f"     Sample affected images (first 3):")
                for img in list(image_paths)[:3]:
                    print(f"       - {img}")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total labels validated: {total_labels:,}")
    print(f"Labels with issues: {len(images_with_issues):,} ({100*len(images_with_issues)/total_labels:.1f}%)")
    print(f"Labels without issues: {total_labels - len(images_with_issues):,} ({100*(total_labels - len(images_with_issues))/total_labels:.1f}%)")
    print(f"Total invalid values found: {issue_count:,}")
    
    # Save detailed report
    report_file = labels_file.parent / "validation_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("AI PRE-LABELS VALIDATION REPORT\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total labels: {total_labels:,}\n")
        f.write(f"Labels with issues: {len(images_with_issues):,}\n")
        f.write(f"Total invalid values: {issue_count:,}\n\n")
        
        for field_name, invalid_vals in sorted(invalid_values.items()):
            f.write(f"\n{'='*70}\n")
            f.write(f"{field_name.upper()}\n")
            f.write(f"{'='*70}\n")
            
            for invalid_val, image_paths in sorted(invalid_vals.items(), key=lambda x: len(x[1]), reverse=True):
                f.write(f"\nInvalid value: '{invalid_val}' (found in {len(image_paths):,} images)\n")
                f.write("Affected images:\n")
                for img in image_paths:
                    f.write(f"  - {img}\n")
    
    print(f"\n📁 Detailed report saved to: {report_file}")

def main():
    """Main validation function"""
    
    # Path to AI_prelabel labels
    labels_file = Path("C:\\Projects_Local\\slitlamp_labeling_app\\data\\labels\\AI_prelabel_labels.json")
    
    if not labels_file.exists():
        print(f"❌ ERROR: File not found: {labels_file}")
        print("\nPlease run create_prelabels_from_xlsx.py first")
        return
    
    validate_labels(labels_file)
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print("1. Review the invalid values above")
    print("2. Decide which values should be:")
    print("   a) Added to config.py as new valid options")
    print("   b) Mapped to existing options (e.g., 'Artificial tears' → ignore)")
    print("   c) Removed from pre-labels (invalid data)")
    print("\n3. Update config.py or re-prompt the AI with correct options")

if __name__ == "__main__":
    main()
