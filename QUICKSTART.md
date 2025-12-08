# Quick Start Guide

## First Time Setup

### 1. Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Your Paths

Open `config/config.py` and update these lines:

```python
DIAGNOSIS_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\studyinfo_laterality_diagnosis.dta"
NOTES_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\ba746f39a1773233.parquet"
CROSS_PATH = r"C:\Users\dxr1276\OneDrive\Projects\Forevision\slitlamp_crosswalk_complete_12082025.csv"
IMAGE_BASE_PATH = r"L:\SlitLamp"
```

### 3. Run the Application
```bash
streamlit run app.py
```

### 4. First Login
- Username: `admin`
- Password: `admin123`

### 5. Create Labelers
As admin:
1. Go to Admin Dashboard
2. Click "User Management"
3. Create new users with different route strategies

## Route Strategy Recommendations

For 250,000 images with multiple labelers:

- **User 1**: Forward (starts at image 1)
- **User 2**: Backward (starts at image 250,000)
- **User 3**: Middle Out (starts at image 125,000)
- **User 4**: Random (seeded random order)
- **User 5**: Forward (different from User 1 due to continued labeling)

This ensures maximum coverage with minimal overlap.

## Tips for Efficient Labeling

1. **Use "Next Unlabeled"** button to skip already labeled images
2. **Mark for Review** when unsure - you can come back later
3. **Use Skip** for images you want to revisit
4. **Save frequently** - labels auto-save but it's good practice
5. **Check Progress** regularly via the progress bar

## Common Issues

### "Image not found"
- Check IMAGE_BASE_PATH in config
- Verify network drive is mounted (L:\ drive)
- Check file permissions

### "Data loading error"
- Verify all three file paths in config
- Ensure you have read permissions
- Check file formats are correct

### "Login failed"
- Use default credentials: admin/admin123
- Check data/users/users.json exists
- Try deleting users.json to reset (creates new admin)

## For Developers

### Adding Custom Diagnosis Options

Edit `config/config.py`:
```python
DIAGNOSIS_OPTIONS = [
    "Ulcer",
    "Hyposphagma",
    "Dry Eye",
    "Pterygium",
    "Pinguecula",
    "Your New Option",  # Add here
    "Other"
]
```

### Changing Auto-Save Interval

Edit `config/config.py`:
```python
AUTO_SAVE_INTERVAL = 5  # Save every N labels
```

### Customizing Date Search Window

Edit `config/config.py`:
```python
MAX_NOTE_DAYS_DIFFERENCE = 365  # Maximum days to search for notes
```

## Getting Help

- Read the full README.md
- Check inline code comments
- Review error messages carefully
- Contact your system administrator
