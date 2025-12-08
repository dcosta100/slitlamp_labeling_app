# 🔬 Slitlamp Image Labeling Application

A professional Streamlit-based application for labeling slitlamp medical images with comprehensive clinical context and multi-user support.

## 📋 Features

### Core Functionality
- **Image Labeling Interface**: Intuitive interface for labeling medical images with laterality, diagnosis, quality assessment, and flags
- **Clinical Context**: Automatically displays relevant clinical notes and exam information alongside images
- **Smart Note Matching**: Finds and displays clinical notes closest to exam date (before, after, or both)
- **Multi-User Support**: Individual login system with personalized labeling progress
- **Route Strategies**: Different labeling sequences per user to maximize coverage
- **Progress Tracking**: Real-time progress bars and statistics
- **Label History**: Complete audit trail with timestamps and edit history
- **Review Queue**: Mark images for later review

### User Roles

#### Labeler
- Label images with full clinical context
- Track personal progress
- Navigate images (first, previous, next, last, skip, go-to)
- Mark images for review
- Edit previous labels

#### Admin
- All labeler features
- User management (create users, assign route strategies)
- Dashboard with comprehensive statistics
- View all users' progress
- Review all labels with filtering
- Export labels to CSV

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Windows OS (paths configured for Windows, but can be adapted)
- Access to the required data files (.dta, .parquet, .csv)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd slitlamp_labeling_app
```

2. **Create virtual environment**
```bash
python -m venv venv
```

3. **Activate virtual environment**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Configure paths**

Edit `config/config.py` and update the following paths with your actual data locations:

```python
DIAGNOSIS_PATH = r"C:\Users\YourUser\...\studyinfo_laterality_diagnosis.dta"
NOTES_PATH = r"C:\Users\YourUser\...\ba746f39a1773233.parquet"
CROSS_PATH = r"C:\Users\YourUser\...\slitlamp_crosswalk_complete_12082025.csv"
IMAGE_BASE_PATH = r"L:\SlitLamp"
```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Default Login

**Admin Account:**
- Username: `admin`
- Password: `admin123`

⚠️ **Important:** Change the default admin password after first login!

## 📁 Project Structure

```
slitlamp_labeling_app/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                 # Git ignore rules
│
├── config/                    # Configuration
│   ├── __init__.py
│   └── config.py              # Application settings and paths
│
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── auth.py                # Authentication and user management
│   ├── data_loader.py         # Data loading and merging
│   └── label_manager.py       # Label saving and statistics
│
├── pages/                     # Application pages
│   ├── __init__.py
│   ├── login_page.py          # Login interface
│   ├── labeling_page.py       # Main labeling interface
│   └── admin_page.py          # Admin dashboard
│
└── data/                      # Data directory (created automatically)
    ├── labels/                # User label files (JSON)
    └── users/                 # User configuration
```

## 🎯 Usage Guide

### For Labelers

1. **Login** with your credentials
2. **Navigate** through images using the control buttons
3. **Review** clinical information displayed on the right panel
4. **Label** each image with:
   - Laterality (Left/Right)
   - Diagnosis (predefined options + Other)
   - Flag (Yes/No) - for problematic images
   - Quality Assessment (Usable/Not Usable)
5. **Save** your label (automatically advances to next unlabeled image)
6. **Mark for Review** if you want to revisit later

### Navigation Options
- **⏮️ First**: Go to first image in your sequence
- **◀️ Previous**: Go to previous image
- **Go to position**: Jump to specific position
- **▶️ Next**: Go to next image
- **⏭️ Next Unlabeled**: Skip to next unlabeled image
- **⏭️ Skip**: Skip current image without labeling

### For Admins

1. **Login** with admin credentials
2. **Navigate** to Admin Dashboard from sidebar
3. **View Statistics**: 
   - Overall progress across all users
   - Per-user statistics and visualizations
   - Diagnosis and laterality distributions
4. **Manage Users**:
   - Create new labeler accounts
   - Assign route strategies
   - View all users and their roles
5. **Review Labels**:
   - View review queues for each user
   - Filter and search labels
   - Export labels to CSV

## 🛠️ Route Strategies

Different users are assigned different labeling sequences to maximize coverage:

- **Forward**: Start from image 1 → N
- **Backward**: Start from image N → 1
- **Middle Out**: Start from middle, alternate outward
- **Random**: Random sequence (seeded by username for reproducibility)

## 💾 Data Storage

### Label Files
Labels are stored as JSON files in `data/labels/` directory:
- One file per user: `{username}_labels.json`
- Contains all labels with full metadata
- Includes edit history and timestamps
- Review queue tracking

### User Configuration
User data stored in `data/users/users.json`:
- Hashed passwords (SHA-256)
- User roles
- Route strategies
- Account creation dates

## 🔒 Security Notes

- Passwords are hashed using SHA-256
- User sessions managed by Streamlit
- Local authentication only (no external auth)
- Change default admin password immediately
- Keep user data files secure

## 📊 Label Data Format

Each label contains:
```json
{
  "image_path": "path/to/image.jpg",
  "laterality": "Left",
  "diagnosis": "Ulcer",
  "diagnosis_other": null,
  "flag": "No",
  "quality": "Usable",
  "labeled_by": "username",
  "labeled_at": "2025-12-08 14:30:00",
  "is_edit": false,
  "metadata": {
    "maskedid_studyid": "123456",
    "exam_date": "2024-01-15",
    "pat_mrn": "MRN123"
  },
  "edit_history": []
}
```

## 🐛 Troubleshooting

### Images Not Loading
- Verify `IMAGE_BASE_PATH` in `config/config.py`
- Check image file permissions
- Ensure image paths in crosswalk CSV are correct

### Data Loading Errors
- Verify all three data file paths in config
- Check file permissions
- Ensure pandas can read .dta (Stata) files

### Login Issues
- Check `data/users/users.json` exists
- Verify default admin credentials
- Delete users.json to reset (will lose all users!)

## 📝 Development

### Adding New Features

1. Create feature in appropriate module (`utils/` or `pages/`)
2. Update `config/config.py` if new settings needed
3. Test thoroughly with multiple users
4. Update this README

### Testing

```bash
# Create test user
# Login as admin → User Management → Create User

# Test different route strategies
# Create users with different strategies and compare sequences
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit pull request with description

## 📄 License

[Add your license here]

## 👥 Authors

[Add your name/team here]

## 🙏 Acknowledgments

Built for medical image labeling workflows with clinical context integration.

## 📞 Support

For issues or questions:
1. Check this README
2. Review code comments
3. Contact the development team

---

**Version:** 1.0.0  
**Last Updated:** December 2025
