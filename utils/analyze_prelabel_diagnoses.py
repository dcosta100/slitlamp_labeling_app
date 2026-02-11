"""
Visualize distribution of conditions/diagnoses in AI pre-labels
Creates plots and statistics for main diagnostic categories
"""

import json
from pathlib import Path
from collections import Counter
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def analyze_conditions(labels_file):
    """Analyze and visualize condition distribution"""
    
    print("="*70)
    print("AI PRE-LABELS DIAGNOSTIC ANALYSIS")
    print("="*70)
    print(f"\nAnalyzing: {labels_file}\n")
    
    # Load labels
    with open(labels_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    labels = data.get('labels', {})
    total_labels = len(labels)
    
    print(f"Total images: {total_labels:,}\n")
    
    # Count conditions
    condition_counts = Counter()
    quality_counts = Counter()
    laterality_counts = Counter()
    
    # Detailed condition data
    dry_eye_severity = Counter()
    dry_eye_signs = Counter()
    
    cataract_type = Counter()
    cataract_severity = Counter()
    
    infectious_type = Counter()
    infectious_etiology = Counter()
    
    tumor_type = Counter()
    tumor_malignancy = Counter()
    
    sch_presence = Counter()
    
    for label in labels.values():
        # Count quality
        quality = label.get('quality', 'Unknown')
        quality_counts[quality] += 1
        
        # Count laterality
        laterality = label.get('laterality', 'Unknown')
        laterality_counts[laterality] += 1
        
        # Count conditions (only if Usable)
        if quality == 'Usable':
            conditions = label.get('conditions', {})
            
            for condition_name in conditions.keys():
                condition_counts[condition_name] += 1
            
            # Dry Eye Disease details
            if 'Dry Eye Disease' in conditions:
                dry_eye = conditions['Dry Eye Disease']
                severity = dry_eye.get('severity', 'Unknown')
                dry_eye_severity[severity] += 1
                
                for sign in dry_eye.get('signs', []):
                    dry_eye_signs[sign] += 1
            
            # Cataract details
            if 'Cataract' in conditions:
                cataract = conditions['Cataract']
                cat_type = cataract.get('type', 'Unknown')
                cataract_type[cat_type] += 1
                
                cat_sev = cataract.get('severity')
                if cat_sev:
                    cataract_severity[cat_sev] += 1
            
            # Infectious details
            if 'Infectious Keratitis / Conjunctivitis' in conditions:
                infectious = conditions['Infectious Keratitis / Conjunctivitis']
                inf_type = infectious.get('type', 'Unknown')
                infectious_type[inf_type] += 1
                
                etiology = infectious.get('etiology')
                if etiology:
                    infectious_etiology[etiology] += 1
            
            # Tumor details
            if 'Ocular Surface Tumors' in conditions:
                tumor = conditions['Ocular Surface Tumors']
                t_type = tumor.get('type', 'Unknown')
                tumor_type[t_type] += 1
                
                malignancy = tumor.get('malignancy')
                if malignancy:
                    tumor_malignancy[malignancy] += 1
            
            # SCH details
            if 'Subconjunctival Hemorrhage' in conditions:
                sch = conditions['Subconjunctival Hemorrhage']
                presence = sch.get('presence', 'Unknown')
                sch_presence[presence] += 1
    
    # Print results
    print("="*70)
    print("IMAGE QUALITY")
    print("="*70)
    for quality, count in quality_counts.most_common():
        pct = 100 * count / total_labels
        print(f"{quality:20s}: {count:5,} ({pct:5.1f}%)")
    
    print("\n" + "="*70)
    print("LATERALITY")
    print("="*70)
    for lat, count in laterality_counts.most_common():
        pct = 100 * count / total_labels
        print(f"{lat:20s}: {count:5,} ({pct:5.1f}%)")
    
    usable_count = quality_counts.get('Usable', 0)
    
    print("\n" + "="*70)
    print("MAIN CONDITIONS (from Usable images only)")
    print("="*70)
    for condition, count in condition_counts.most_common():
        pct = 100 * count / usable_count if usable_count > 0 else 0
        print(f"{condition:40s}: {count:5,} ({pct:5.1f}%)")
    
    # Detailed breakdowns
    if dry_eye_severity:
        print("\n" + "="*70)
        print("DRY EYE DISEASE - Severity")
        print("="*70)
        for severity, count in dry_eye_severity.most_common():
            pct = 100 * count / condition_counts.get('Dry Eye Disease', 1)
            print(f"{severity:20s}: {count:5,} ({pct:5.1f}%)")
    
    if dry_eye_signs:
        print("\n" + "="*70)
        print("DRY EYE DISEASE - Signs (Top 10)")
        print("="*70)
        for sign, count in dry_eye_signs.most_common(10):
            pct = 100 * count / condition_counts.get('Dry Eye Disease', 1)
            print(f"{sign:30s}: {count:5,} ({pct:5.1f}%)")
    
    if cataract_type:
        print("\n" + "="*70)
        print("CATARACT - Type")
        print("="*70)
        for cat_type, count in cataract_type.most_common():
            pct = 100 * count / condition_counts.get('Cataract', 1)
            print(f"{cat_type:20s}: {count:5,} ({pct:5.1f}%)")
    
    if cataract_severity:
        print("\n" + "="*70)
        print("CATARACT - Severity")
        print("="*70)
        for severity, count in cataract_severity.most_common():
            pct = 100 * count / condition_counts.get('Cataract', 1)
            print(f"{severity:20s}: {count:5,} ({pct:5.1f}%)")
    
    if infectious_type:
        print("\n" + "="*70)
        print("INFECTIOUS KERATITIS / CONJUNCTIVITIS - Type")
        print("="*70)
        for inf_type, count in infectious_type.most_common():
            pct = 100 * count / condition_counts.get('Infectious Keratitis / Conjunctivitis', 1)
            print(f"{str(inf_type):30s}: {count:5,} ({pct:5.1f}%)")
    
    if infectious_etiology:
        print("\n" + "="*70)
        print("INFECTIOUS KERATITIS / CONJUNCTIVITIS - Etiology")
        print("="*70)
        for etiology, count in infectious_etiology.most_common():
            pct = 100 * count / condition_counts.get('Infectious Keratitis / Conjunctivitis', 1)
            print(f"{str(etiology):20s}: {count:5,} ({pct:5.1f}%)")
    
    if tumor_type:
        print("\n" + "="*70)
        print("OCULAR SURFACE TUMORS - Type")
        print("="*70)
        for t_type, count in tumor_type.most_common():
            pct = 100 * count / condition_counts.get('Ocular Surface Tumors', 1)
            print(f"{str(t_type):20s}: {count:5,} ({pct:5.1f}%)")
    
    if tumor_malignancy:
        print("\n" + "="*70)
        print("OCULAR SURFACE TUMORS - Malignancy")
        print("="*70)
        for malignancy, count in tumor_malignancy.most_common():
            pct = 100 * count / condition_counts.get('Ocular Surface Tumors', 1)
            print(f"{str(malignancy):20s}: {count:5,} ({pct:5.1f}%)")
    
    if sch_presence:
        print("\n" + "="*70)
        print("SUBCONJUNCTIVAL HEMORRHAGE - Presence")
        print("="*70)
        for presence, count in sch_presence.most_common():
            pct = 100 * count / condition_counts.get('Subconjunctival Hemorrhage', 1)
            print(f"{str(presence):20s}: {count:5,} ({pct:5.1f}%)")
    
    # Try to create plots if matplotlib available
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        
        print("\n" + "="*70)
        print("CREATING PLOTS...")
        print("="*70)
        
        # Create output directory
        output_dir = labels_file.parent / "analysis_plots"
        output_dir.mkdir(exist_ok=True)
        
        # Plot 1: Main Conditions
        if condition_counts:
            fig, ax = plt.subplots(figsize=(12, 6))
            conditions = [c for c, _ in condition_counts.most_common()]
            counts = [c for _, c in condition_counts.most_common()]
            
            ax.barh(conditions, counts, color='steelblue')
            ax.set_xlabel('Number of Images', fontsize=12)
            ax.set_title('Distribution of Main Conditions', fontsize=14, fontweight='bold')
            ax.invert_yaxis()
            
            # Add count labels
            for i, (condition, count) in enumerate(zip(conditions, counts)):
                pct = 100 * count / usable_count if usable_count > 0 else 0
                ax.text(count, i, f' {count:,} ({pct:.1f}%)', va='center', fontsize=10)
            
            plt.tight_layout()
            plot_file = output_dir / "1_main_conditions.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {plot_file}")
        
        # Plot 2: Quality Distribution
        if quality_counts:
            fig, ax = plt.subplots(figsize=(8, 6))
            qualities = list(quality_counts.keys())
            counts = list(quality_counts.values())
            colors = ['#2ecc71' if q == 'Usable' else '#e74c3c' for q in qualities]
            
            ax.pie(counts, labels=qualities, autopct='%1.1f%%', startangle=90, colors=colors)
            ax.set_title('Image Quality Distribution', fontsize=14, fontweight='bold')
            
            plot_file = output_dir / "2_quality_distribution.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {plot_file}")
        
        # Plot 3: Laterality Distribution
        if laterality_counts:
            fig, ax = plt.subplots(figsize=(8, 6))
            lats = list(laterality_counts.keys())
            counts = list(laterality_counts.values())
            
            ax.bar(lats, counts, color='coral')
            ax.set_ylabel('Number of Images', fontsize=12)
            ax.set_title('Laterality Distribution', fontsize=14, fontweight='bold')
            
            # Add count labels
            for lat, count in zip(lats, counts):
                pct = 100 * count / total_labels
                ax.text(lat, count, f'{count:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            plot_file = output_dir / "3_laterality_distribution.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {plot_file}")
        
        # Plot 4: Dry Eye Severity
        if dry_eye_severity:
            fig, ax = plt.subplots(figsize=(8, 6))
            severities = [s for s, _ in dry_eye_severity.most_common()]
            counts = [c for _, c in dry_eye_severity.most_common()]
            
            ax.bar(severities, counts, color='lightblue')
            ax.set_ylabel('Number of Cases', fontsize=12)
            ax.set_title('Dry Eye Disease - Severity Distribution', fontsize=14, fontweight='bold')
            
            for sev, count in zip(severities, counts):
                ax.text(sev, count, f'{count:,}', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            plot_file = output_dir / "4_dry_eye_severity.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {plot_file}")
        
        # Plot 5: Cataract Types
        if cataract_type:
            fig, ax = plt.subplots(figsize=(10, 6))
            types = [t for t, _ in cataract_type.most_common()]
            counts = [c for _, c in cataract_type.most_common()]
            
            ax.barh(types, counts, color='gold')
            ax.set_xlabel('Number of Cases', fontsize=12)
            ax.set_title('Cataract Type Distribution', fontsize=14, fontweight='bold')
            ax.invert_yaxis()
            
            for i, (t, count) in enumerate(zip(types, counts)):
                ax.text(count, i, f' {count:,}', va='center', fontsize=10)
            
            plt.tight_layout()
            plot_file = output_dir / "5_cataract_types.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {plot_file}")
        
        # Plot 6: Infectious Types
        if infectious_type:
            fig, ax = plt.subplots(figsize=(10, 6))
            types = [t for t, _ in infectious_type.most_common()]
            counts = [c for _, c in infectious_type.most_common()]
            
            ax.barh(types, counts, color='salmon')
            ax.set_xlabel('Number of Cases', fontsize=12)
            ax.set_title('Infectious Keratitis/Conjunctivitis Type Distribution', fontsize=14, fontweight='bold')
            ax.invert_yaxis()
            
            for i, (t, count) in enumerate(zip(types, counts)):
                ax.text(count, i, f' {count:,}', va='center', fontsize=10)
            
            plt.tight_layout()
            plot_file = output_dir / "6_infectious_types.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {plot_file}")
        
        print(f"\n📁 All plots saved to: {output_dir}")
        
    except ImportError:
        print("\n⚠️  matplotlib not installed - skipping plot generation")
        print("   Install with: pip install matplotlib")
    except Exception as e:
        print(f"\n⚠️  Error creating plots: {e}")
    
    # Save summary to file
    summary_file = labels_file.parent / "diagnostic_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("AI PRE-LABELS DIAGNOSTIC SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total images: {total_labels:,}\n")
        f.write(f"Usable images: {usable_count:,}\n\n")
        
        f.write("MAIN CONDITIONS:\n")
        for condition, count in condition_counts.most_common():
            pct = 100 * count / usable_count if usable_count > 0 else 0
            f.write(f"  {condition}: {count:,} ({pct:.1f}%)\n")
    
    print(f"\n📄 Summary saved to: {summary_file}")

def main():
    """Main analysis function"""
    
    # Path to AI_prelabel labels
    labels_file = Path("../data/labels/AI_prelabel_labels.json")
    
    if not labels_file.exists():
        print(f"❌ ERROR: File not found: {labels_file}")
        print("\nPlease run create_prelabels_from_xlsx.py first")
        return
    
    analyze_conditions(labels_file)

if __name__ == "__main__":
    main()
