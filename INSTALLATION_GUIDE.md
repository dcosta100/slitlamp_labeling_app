# 📦 Installation and Folder Structure Guide

## 📋 Complete Folder Structure

After installation, your project should look like this:

```
slitlamp_labeling_app/
│
├── 📄 app.py                          # Main application file - DO NOT MODIFY
├── 📄 initialize.py                   # Initialization script
├── 📄 requirements.txt                # Python dependencies
├── 📄 README.md                       # Full documentation
├── 📄 QUICKSTART.md                   # Quick start guide
├── 📄 CHANGELOG.md                    # Version history
├── 📄 LICENSE                         # License file
├── 📄 .gitignore                      # Git ignore rules
│
├── 🪟 install.bat                     # Windows installation script
├── 🪟 run_app.bat                     # Windows run script
├── 🐧 install.sh                      # Linux/Mac installation script
├── 🐧 run_app.sh                      # Linux/Mac run script
│
├── 📁 .streamlit/                     # Streamlit configuration
│   └── config.toml                    # Theme and server settings
│
├── 📁 config/                         # Application configuration
│   ├── __init__.py
│   └── 📝 config.py                   # ⚠️ EDIT THIS FILE WITH YOUR PATHS
│
├── 📁 utils/                          # Utility modules
│   ├── __init__.py
│   ├── auth.py                        # Authentication system
│   ├── data_loader.py                 # Data loading and merging
│   └── label_manager.py               # Label management
│
├── 📁 pages/                          # Application pages
│   ├── __init__.py
│   ├── login_page.py                  # Login interface
│   ├── labeling_page.py               # Main labeling interface
│   └── admin_page.py                  # Admin dashboard
│
├── 📁 data/                           # Data directory (auto-created)
│   ├── 📁 labels/                     # User label files (auto-created)
│   │   └── {username}_labels.json    # Individual user labels
│   └── 📁 users/                      # User configuration (auto-created)
│       └── users.json                 # User accounts database
│
└── 📁 venv/                           # Virtual environment (created during install)
```

## 🚀 Step-by-Step Installation

### For Windows Users

1. **Download/Clone the repository**
   ```
   Place all files in a folder, e.g., C:\Projects\slitlamp_labeling_app\
   ```

2. **Run the installation script**
   - Double-click `install.bat`
   - OR open Command Prompt in the folder and run:
   ```cmd
   install.bat
   ```

3. **Configure your data paths**
   - Open `config\config.py` in a text editor
   - Update these lines with YOUR actual paths:
   ```python
   DIAGNOSIS_PATH = r"C:\Users\YourUser\...\studyinfo_laterality_diagnosis.dta"
   NOTES_PATH = r"C:\Users\YourUser\...\ba746f39a1773233.parquet"
   CROSS_PATH = r"C:\Users\YourUser\...\slitlamp_crosswalk_complete_12082025.csv"
   IMAGE_BASE_PATH = r"L:\SlitLamp"
   ```

4. **Run the application**
   - Double-click `run_app.bat`
   - OR open Command Prompt and run:
   ```cmd
   run_app.bat
   ```

5. **Access the application**
   - Your browser will open automatically
   - Or go to: http://localhost:8501

6. **First login**
   - Username: `admin`
   - Password: `admin123`
   - ⚠️ Change this password immediately!

### For Linux/Mac Users

1. **Download/Clone the repository**
   ```bash
   cd ~
   # Place all files in a folder
   cd slitlamp_labeling_app
   ```

2. **Run the installation script**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Configure your data paths**
   - Open `config/config.py` in a text editor
   - Update the paths (use forward slashes):
   ```python
   DIAGNOSIS_PATH = "/path/to/studyinfo_laterality_diagnosis.dta"
   NOTES_PATH = "/path/to/ba746f39a1773233.parquet"
   CROSS_PATH = "/path/to/slitlamp_crosswalk_complete_12082025.csv"
   IMAGE_BASE_PATH = "/mnt/slitlamp"
   ```

4. **Run the application**
   ```bash
   chmod +x run_app.sh
   ./run_app.sh
   ```

5. **Access and login** (same as Windows)

## 📝 Files You Should EDIT

### Must Edit:
- **config/config.py** - Update data paths with your actual file locations

### Optional Edit:
- **config/config.py** - Change diagnosis options, quality options, etc.
- **LICENSE** - Add your name/organization
- **README.md** - Add your contact information

## 📝 Files You Should NOT Edit

Unless you know what you're doing:
- app.py
- All files in utils/
- All files in pages/
- initialize.py
- requirements.txt

## 🔧 Manual Installation (if scripts fail)

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize application
python initialize.py

# 5. Edit config/config.py with your paths

# 6. Run application
streamlit run app.py
```

## 🗂️ Where Your Data is Stored

### Label Files
Location: `data/labels/`
- One JSON file per user
- Format: `{username}_labels.json`
- Contains all labels with metadata
- **Backup these files regularly!**

### User Accounts
Location: `data/users/users.json`
- Contains all user accounts
- Passwords are hashed
- **Backup this file!**

### Application Logs
Location: Root directory
- Streamlit creates `.streamlit/` folder
- Contains cache and session data

## 🔒 Security Best Practices

1. **Change default admin password immediately**
2. **Backup data/labels/ and data/users/ regularly**
3. **Don't commit sensitive data to Git** (.gitignore configured)
4. **Keep the application on a secure network**
5. **Use strong passwords for all users**

## 🐛 Common Issues and Solutions

### Issue: "Module not found"
**Solution:** Make sure virtual environment is activated
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Issue: "Permission denied" on scripts
**Solution (Linux/Mac):**
```bash
chmod +x install.sh run_app.sh
```

### Issue: Images not loading
**Solution:** 
1. Check IMAGE_BASE_PATH in config/config.py
2. Verify network drive is mounted
3. Check file permissions

### Issue: Data loading error
**Solution:**
1. Verify all three data file paths in config/config.py
2. Ensure files exist and are readable
3. Check you have required packages installed

## 📦 Updating the Application

To update to a new version:

1. **Backup your data**
   ```
   Copy data/labels/ and data/users/ to a safe location
   ```

2. **Download new version**
   ```
   Replace all files EXCEPT config/config.py and data/ folder
   ```

3. **Update dependencies if needed**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **Restart the application**

## 🎯 Next Steps After Installation

1. ✅ Login as admin
2. ✅ Change admin password
3. ✅ Create labeler accounts (Admin Dashboard → User Management)
4. ✅ Assign different route strategies to each labeler
5. ✅ Start labeling!
6. ✅ Monitor progress in Admin Dashboard

## 📞 Getting Help

If you encounter issues:

1. Read this guide completely
2. Check README.md
3. Check QUICKSTART.md
4. Review error messages carefully
5. Verify all paths in config/config.py
6. Contact your system administrator

---

**Remember:** This is a local application. All data stays on your machine!
