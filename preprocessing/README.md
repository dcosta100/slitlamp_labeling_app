# 🚀 Dataset Preprocessing Guide

## Why Preprocess?

Without preprocessing, the app needs to check **every single image** (250,000+) to see if it has matching notes and annotations. This takes **forever**!

Preprocessing calculates all matches **once** and saves the results, making the app **100x faster**.

## How It Works

The preprocessing script:
1. Loads all datasets
2. For each image, checks if it has matching notes (within date range)
3. For each image, checks if it has matching annotations (within 1 week)
4. Saves results with flags: `has_notes`, `has_annotations`
5. Creates a single `.parquet` file with everything

## Setup

### 1. Update Paths in config.py

Make sure these are correct:
```python
DIAGNOSIS_PATH = r"your\path\studyinfo_laterality_diagnosis.dta"
NOTES_PATH = r"your\path\ba746f39a1773233.parquet"
CROSS_PATH = r"your\path\slitlamp_crosswalk_complete_12082025.csv"
ANNOTATIONS_PATH = r"M:\DATASETS\_BPGR\BPGR_slexam_all.csv"
```

### 2. Run the Preprocessing Script

```bash
# Windows
cd preprocessing
python create_preprocessed_dataset.py

# Linux/Mac
cd preprocessing
python3 create_preprocessed_dataset.py
```

**This will take a while** (maybe 30 minutes to 2 hours depending on your data size), but you only run it **ONCE**.

### 3. Update config.py with Preprocessed Path

After the script finishes, it will create:
- `data/preprocessed_dataset.parquet` (the main file)
- `data/preprocessed_dataset_summary.txt` (statistics)

Update your `config/config.py`:
```python
PREPROCESSED_PATH = r"C:\Projects\slitlamp_labeling_app\data\preprocessed_dataset.parquet"
USE_PREPROCESSED = True
```

### 4. Run the App

Now when you run the app, it will load **instantly**! 🎉

```bash
streamlit run app.py
```

## When to Re-run Preprocessing

Re-run the preprocessing script if:
- ✅ You add new images to the dataset
- ✅ Clinical notes are updated
- ✅ Annotations are updated
- ✅ You change MAX_NOTE_DAYS_DIFFERENCE or MAX_ANNOTATION_DAYS_DIFFERENCE

Otherwise, use the preprocessed file!

## Statistics

After preprocessing, check `data/preprocessed_dataset_summary.txt`:

```
total_images: 250000
with_notes: 45000 (18.0%)
with_annotations: 125000 (50.0%)
with_both: 38000 (15.2%)
created_at: 2025-12-08T14:30:00
```

This shows how many images match each filter criteria.

## File Sizes

- **Original datasets**: ~10-20 GB total
- **Preprocessed file**: ~500 MB - 2 GB (compressed)
- **Loading time**: <5 seconds (vs 30+ minutes without preprocessing)

## Troubleshooting

### Script takes too long
- **Normal!** For 250K images, expect 30 min - 2 hours
- Progress is printed every 10,000 rows
- Run it overnight if needed

### Out of memory error
- Close other applications
- Use a machine with more RAM
- Or process in chunks (contact support)

### File not found after preprocessing
- Check the output path in the script's final message
- Make sure PREPROCESSED_PATH in config.py matches the output path
- Check file permissions

## Advanced: Manual Filtering

If you want to create custom filters without re-running preprocessing:

```python
import pandas as pd

# Load preprocessed data
df = pd.read_parquet('data/preprocessed_dataset.parquet')

# Filter for images with notes AND annotations
filtered = df[df['has_notes'] & df['has_annotations']]

print(f"Found {len(filtered)} images with both notes and annotations")
```

---

**Remember:** Preprocessing is a **one-time investment** that makes your app **dramatically faster**! 🚀
