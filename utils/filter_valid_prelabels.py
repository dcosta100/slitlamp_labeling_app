"""
Filter and recreate AI_prelabel_labels.json with only valid labels
Removes labels that don't match config options
"""

import json
from pathlib import Path
from datetime import datetime
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

def is_valid_value(value, valid_options):
    """Check if a value is in the valid options"""
    if value is None:
        return True
    return value in valid_options

def is_valid_list(values, valid_options):
    """Check if all values in a list are valid"""
    if not values:
        return True
    return all(val in valid_options for val in values)

def validate_and_filter_label(label):
    """
    Validate a single label and return filtered version or None if invalid
    
    Returns:
        (is_valid: bool, filtered_label: dict or None, issues: list)
    """
    issues = []
    
    # Check laterality
    lat = label.get('laterality')
    if not is_valid_value(lat, LATERALITY_OPTIONS):
        issues.append(f"Invalid laterality: {lat}")
        return False, None, issues
    
    # Check quality
    qual = label.get('quality')
    if not is_valid_value(qual, QUALITY_OPTIONS):
        issues.append(f"Invalid quality: {qual}")
        return False, None, issues
    
    # Filter conditions
    conditions = label.get('conditions', {})
    filtered_conditions = {}
    
    # Dry Eye Disease
    if 'Dry Eye Disease' in conditions:
        dry_eye = conditions['Dry Eye Disease']
        severity = dry_eye.get('severity')
        signs = dry_eye.get('signs', [])
        
        # Validate severity
        if not is_valid_value(severity, DRY_EYE_SEVERITY):
            issues.append(f"Invalid dry eye severity: {severity}")
        else:
            # Filter signs
            valid_signs = [s for s in signs if s in DRY_EYE_SIGNS]
            if len(valid_signs) < len(signs):
                invalid_signs = [s for s in signs if s not in DRY_EYE_SIGNS]
                issues.append(f"Removed invalid dry eye signs: {invalid_signs}")
            
            # Keep condition if severity is valid
            filtered_conditions['Dry Eye Disease'] = {
                'severity': severity,
                'signs': valid_signs
            }
    
    # Cataract
    if 'Cataract' in conditions:
        cataract = conditions['Cataract']
        cat_type = cataract.get('type')
        cat_severity = cataract.get('severity')
        features = cataract.get('features', [])
        
        # Validate type
        if not is_valid_value(cat_type, CATARACT_TYPE):
            issues.append(f"Invalid cataract type: {cat_type}")
        else:
            # Validate severity if present
            if cat_severity and not is_valid_value(cat_severity, CATARACT_SEVERITY):
                issues.append(f"Invalid cataract severity: {cat_severity}")
                cat_severity = None
            
            # Filter features
            valid_features = [f for f in features if f in CATARACT_FEATURES]
            if len(valid_features) < len(features):
                invalid_features = [f for f in features if f not in CATARACT_FEATURES]
                issues.append(f"Removed invalid cataract features: {invalid_features}")
            
            filtered_conditions['Cataract'] = {
                'type': cat_type,
                'severity': cat_severity,
                'features': valid_features
            }
    
    # Infectious Keratitis / Conjunctivitis
    if 'Infectious Keratitis / Conjunctivitis' in conditions:
        infectious = conditions['Infectious Keratitis / Conjunctivitis']
        inf_type = infectious.get('type')
        etiology = infectious.get('etiology')
        ker_size = infectious.get('keratitis_size')
        ker_features = infectious.get('keratitis_features', [])
        conj_features = infectious.get('conjunctivitis_features', [])
        
        # Validate type
        if not is_valid_value(inf_type, INFECTIOUS_TYPE):
            issues.append(f"Invalid infectious type: {inf_type}")
        else:
            inf_data = {'type': inf_type}
            
            # Validate etiology if present
            if etiology:
                if is_valid_value(etiology, INFECTIOUS_ETIOLOGY):
                    inf_data['etiology'] = etiology
                else:
                    issues.append(f"Invalid infectious etiology: {etiology}")
            
            # Validate keratitis size if present
            if ker_size:
                if is_valid_value(ker_size, KERATITIS_SIZE):
                    inf_data['keratitis_size'] = ker_size
                else:
                    issues.append(f"Invalid keratitis size: {ker_size}")
            
            # Filter keratitis features
            valid_ker_features = [f for f in ker_features if f in KERATITIS_FEATURES]
            if len(valid_ker_features) < len(ker_features):
                invalid = [f for f in ker_features if f not in KERATITIS_FEATURES]
                issues.append(f"Removed invalid keratitis features: {invalid}")
            if valid_ker_features:
                inf_data['keratitis_features'] = valid_ker_features
            
            # Filter conjunctivitis features
            valid_conj_features = [f for f in conj_features if f in CONJUNCTIVITIS_FEATURES]
            if len(valid_conj_features) < len(conj_features):
                invalid = [f for f in conj_features if f not in CONJUNCTIVITIS_FEATURES]
                issues.append(f"Removed invalid conjunctivitis features: {invalid}")
            if valid_conj_features:
                inf_data['conjunctivitis_features'] = valid_conj_features
            
            filtered_conditions['Infectious Keratitis / Conjunctivitis'] = inf_data
    
    # Ocular Surface Tumors
    if 'Ocular Surface Tumors' in conditions:
        tumor = conditions['Ocular Surface Tumors']
        tumor_type = tumor.get('type')
        malignancy = tumor.get('malignancy')
        location = tumor.get('location')
        features = tumor.get('features', [])
        
        # Validate type
        if not is_valid_value(tumor_type, TUMOR_TYPE):
            issues.append(f"Invalid tumor type: {tumor_type}")
        else:
            tumor_data = {'type': tumor_type}
            
            # Validate malignancy if present
            if malignancy:
                if is_valid_value(malignancy, TUMOR_MALIGNANCY):
                    tumor_data['malignancy'] = malignancy
                else:
                    issues.append(f"Invalid tumor malignancy: {malignancy}")
            
            # Validate location if present
            if location:
                if is_valid_value(location, TUMOR_LOCATION):
                    tumor_data['location'] = location
                else:
                    issues.append(f"Invalid tumor location: {location}")
            
            # Filter features
            valid_features = [f for f in features if f in TUMOR_FEATURES]
            if len(valid_features) < len(features):
                invalid = [f for f in features if f not in TUMOR_FEATURES]
                issues.append(f"Removed invalid tumor features: {invalid}")
            if valid_features:
                tumor_data['features'] = valid_features
            
            filtered_conditions['Ocular Surface Tumors'] = tumor_data
    
    # Subconjunctival Hemorrhage
    if 'Subconjunctival Hemorrhage' in conditions:
        sch = conditions['Subconjunctival Hemorrhage']
        presence = sch.get('presence')
        extent = sch.get('extent')
        
        # Validate presence
        if not is_valid_value(presence, SCH_PRESENCE):
            issues.append(f"Invalid SCH presence: {presence}")
        else:
            sch_data = {'presence': presence}
            
            # Validate extent if present
            if extent:
                if is_valid_value(extent, SCH_EXTENT):
                    sch_data['extent'] = extent
                else:
                    issues.append(f"Invalid SCH extent: {extent}")
            
            filtered_conditions['Subconjunctival Hemorrhage'] = sch_data
    
    # Create filtered label
    filtered_label = {
        'image_path': label['image_path'],
        'laterality': lat,
        'quality': qual,
        'conditions': filtered_conditions,
        'labeled_by': label.get('labeled_by', 'AI_prelabel'),
        'labeled_at': label.get('labeled_at'),
        'is_edit': label.get('is_edit', False),
        'metadata': label.get('metadata', {})
    }
    
    # Consider valid if no critical issues
    is_valid = len(issues) == 0 or all('Removed invalid' in issue for issue in issues)
    
    return is_valid, filtered_label, issues

def filter_labels(input_file, output_file):
    """Filter labels file and create new one with only valid labels"""
    
    print("="*70)
    print("AI PRE-LABELS FILTERING")
    print("="*70)
    print(f"\nInput:  {input_file}")
    print(f"Output: {output_file}")
    
    # Load original labels
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_labels = data.get('labels', {})
    total_original = len(original_labels)
    
    print(f"\nOriginal labels: {total_original:,}")
    
    # Filter labels
    filtered_labels = {}
    valid_count = 0
    invalid_count = 0
    modified_count = 0
    
    print("\nFiltering labels...")
    for image_path, label in original_labels.items():
        is_valid, filtered_label, issues = validate_and_filter_label(label)
        
        if is_valid:
            filtered_labels[image_path] = filtered_label
            valid_count += 1
            
            if issues:  # Had issues but was fixable
                modified_count += 1
        else:
            invalid_count += 1
    
    # Create new labels file
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_data = {
        "user": "AI_prelabel",
        "created_at": now,
        "last_modified": now,
        "labels": filtered_labels,
        "metadata": {
            "filtered_from": str(input_file),
            "original_count": total_original,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "modified_count": modified_count
        }
    }
    
    # Save filtered labels
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    
    # Print results
    print("\n" + "="*70)
    print("FILTERING RESULTS")
    print("="*70)
    print(f"\n✅ Valid labels kept: {valid_count:,} ({100*valid_count/total_original:.1f}%)")
    print(f"   - Kept as-is: {valid_count - modified_count:,}")
    print(f"   - Modified (removed invalid fields): {modified_count:,}")
    print(f"\n❌ Invalid labels removed: {invalid_count:,} ({100*invalid_count/total_original:.1f}%)")
    print(f"\n📁 Filtered labels saved to: {output_file}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    
    return valid_count, invalid_count

def main():
    """Main filtering function"""
    
    # Paths
    input_file = Path("../data/labels/AI_prelabel_labels.json")
    output_file = Path("../data/labels/AI_prelabel_labels_filtered.json")
    
    if not input_file.exists():
        print(f"❌ ERROR: File not found: {input_file}")
        print("\nPlease run create_prelabels_from_xlsx.py first")
        return
    
    # Filter labels
    valid_count, invalid_count = filter_labels(input_file, output_file)
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Review the filtered labels file")
    print("2. Rename it to replace the original:")
    print(f"   mv {output_file.name} AI_prelabel_labels.json")
    print("\n3. Or keep both files for comparison")
    print("\n4. Restart the app to use filtered labels")

if __name__ == "__main__":
    main()
