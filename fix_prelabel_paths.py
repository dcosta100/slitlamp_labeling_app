"""
Fix image paths in AI_prelabel_labels.json to match local configuration
Run this on each PC to update paths to local IMAGE_BASE_PATH
"""

import json
from pathlib import Path
import sys
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import IMAGE_BASE_PATH

def fix_prelabel_paths(labels_file, new_base_path):
    """
    Update all image paths in AI prelabels to use new base path
    
    Args:
        labels_file: Path to AI_prelabel_labels.json
        new_base_path: New IMAGE_BASE_PATH for this machine
    """
    
    print("="*70)
    print("FIX AI PRE-LABEL PATHS")
    print("="*70)
    print(f"\nLabels file: {labels_file}")
    print(f"New base path: {new_base_path}\n")
    
    # Load labels
    with open(labels_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    labels = data.get('labels', {})
    original_count = len(labels)
    
    print(f"Total labels: {original_count:,}")
    
    # Extract old base path from first label
    if labels:
        first_path = list(labels.keys())[0]
        # Find everything before "SlitLamp"
        match = re.search(r'(.+?)[/\\]SlitLamp[/\\]', first_path, re.IGNORECASE)
        if match:
            old_base = match.group(1)
            print(f"Detected old base path: {old_base}")
        else:
            print("Could not detect old base path")
            old_base = None
    
    # Convert paths
    new_labels = {}
    new_base = str(Path(new_base_path))
    
    for old_path, label_data in labels.items():
        # Extract from "SlitLamp" onwards
        match = re.search(r'SlitLamp[/\\](.+)', old_path, re.IGNORECASE)
        if match:
            relative_path = match.group(1)
            # Build new path
            new_path = str(Path(new_base) / "SlitLamp" / relative_path)
            
            # Update label data
            label_data['image_path'] = new_path
            new_labels[new_path] = label_data
        else:
            # Keep original if can't parse
            new_labels[old_path] = label_data
    
    # Update data
    data['labels'] = new_labels
    
    # Backup original
    backup_file = labels_file.parent / f"{labels_file.stem}_BACKUP.json"
    print(f"\n📁 Creating backup: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Save updated
    print(f"💾 Saving updated labels: {labels_file}")
    with open(labels_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Show samples
    print("\n" + "="*70)
    print("UPDATED PATHS (samples)")
    print("="*70)
    sample_keys = list(new_labels.keys())[:3]
    for i, path in enumerate(sample_keys, 1):
        print(f"{i}. {path}")
    
    print("\n" + "="*70)
    print("✅ DONE!")
    print("="*70)
    print(f"Updated {len(new_labels):,} label paths")
    print(f"Backup saved: {backup_file}")
    print("\nRestart the app to use updated paths")

def main():
    """Main function"""
    
    labels_file = Path("data/labels/AI_prelabel_labels.json")
    
    if not labels_file.exists():
        print(f"❌ ERROR: {labels_file} not found")
        print("\nMake sure you're running this from the project root")
        return
    
    print(f"Current IMAGE_BASE_PATH from config: {IMAGE_BASE_PATH}")
    print("\nThis will update all paths in AI_prelabel_labels.json")
    print("to use the IMAGE_BASE_PATH from your config/environment")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        fix_prelabel_paths(labels_file, IMAGE_BASE_PATH)
    else:
        print("Cancelled")

if __name__ == "__main__":
    main()
