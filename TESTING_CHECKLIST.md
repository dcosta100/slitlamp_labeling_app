# 🧪 Testing Checklist

Use this checklist to verify your installation is working correctly.

## ✅ Installation Testing

- [ ] Virtual environment created successfully
- [ ] All dependencies installed without errors
- [ ] `initialize.py` ran successfully
- [ ] `data/labels/` directory exists
- [ ] `data/users/` directory exists
- [ ] `data/users/users.json` exists and contains admin user

## ✅ Configuration Testing

- [ ] Opened `config/config.py`
- [ ] Updated `DIAGNOSIS_PATH` with correct path
- [ ] Updated `NOTES_PATH` with correct path
- [ ] Updated `CROSS_PATH` with correct path
- [ ] Updated `IMAGE_BASE_PATH` with correct path
- [ ] All data files exist at specified paths
- [ ] All data files are readable

## ✅ Application Startup

- [ ] Application starts without errors
- [ ] Browser opens automatically (or manually at localhost:8501)
- [ ] Login page displays correctly
- [ ] No error messages in terminal

## ✅ Authentication Testing

### Admin Login
- [ ] Can login with admin/admin123
- [ ] Redirected to labeling page after login
- [ ] Sidebar shows username and role
- [ ] Admin Dashboard option visible in sidebar
- [ ] Logout button works

### User Creation
- [ ] Navigate to Admin Dashboard
- [ ] Go to User Management tab
- [ ] Create a test labeler account
- [ ] New user appears in user list
- [ ] Logout and login with new user credentials
- [ ] New user does NOT see Admin Dashboard

## ✅ Data Loading Testing

- [ ] Application loads diagnosis data (.dta file)
- [ ] Application loads notes data (.parquet file)
- [ ] Application loads crosswalk data (.csv file)
- [ ] Total image count displays correctly
- [ ] No error messages about data loading

## ✅ Labeling Interface Testing

### Navigation
- [ ] "First" button works
- [ ] "Previous" button works
- [ ] "Next" button works
- [ ] "Next Unlabeled" button works
- [ ] "Go to position" number input works
- [ ] "Skip" button works

### Image Display
- [ ] Image loads and displays correctly
- [ ] Image path is shown
- [ ] Image filename is shown
- [ ] Image index is shown

### Clinical Information
- [ ] Exam Details expander shows correct data
- [ ] MRN displays correctly
- [ ] Study ID displays correctly
- [ ] Exam date displays correctly
- [ ] Laterality displays correctly
- [ ] Main diagnosis displays correctly
- [ ] Order diagnosis displays correctly

### Clinical Notes
- [ ] Clinical notes load for patients with notes
- [ ] Notes show days difference from exam date
- [ ] Notes marked as "before" or "after" correctly
- [ ] Both notes show when exam date is between two notes
- [ ] Long notes show in expandable section

### Labeling Form
- [ ] Laterality dropdown works (Left/Right)
- [ ] Diagnosis dropdown works
- [ ] "Other" diagnosis shows text input
- [ ] Flag dropdown works (Yes/No)
- [ ] Quality dropdown works (Usable/Not Usable)
- [ ] "Save Label" button saves successfully
- [ ] Success message displays after saving
- [ ] Auto-advances to next unlabeled image after save

### Special Features
- [ ] Can mark image for review
- [ ] Review queue counter updates
- [ ] Can edit previously labeled images
- [ ] Edit history is preserved
- [ ] Progress bar updates after labeling
- [ ] Label count increases correctly

## ✅ Route Strategy Testing

Create 4 test users with different strategies:

### User 1: Forward Strategy
- [ ] Starts at position 1
- [ ] Goes sequentially: 1, 2, 3, 4...

### User 2: Backward Strategy
- [ ] Starts at last position
- [ ] Goes backward: N, N-1, N-2...

### User 3: Middle-Out Strategy
- [ ] Starts near middle position
- [ ] Alternates outward from middle

### User 4: Random Strategy
- [ ] Order appears random
- [ ] Same order when user logs in again (seeded)
- [ ] Different from other users

## ✅ Label Persistence Testing

- [ ] Label an image
- [ ] Logout
- [ ] Login again
- [ ] Navigate to previously labeled image
- [ ] Form shows previous values
- [ ] "Previously labeled" message shows
- [ ] Can edit and save again
- [ ] Edit history is preserved

## ✅ Admin Dashboard Testing

### Statistics Tab
- [ ] Total labels metric shows correct count
- [ ] Flagged metric shows correct count
- [ ] Not Usable metric shows correct count
- [ ] Edited metric shows correct count
- [ ] Per-user statistics table displays
- [ ] "Labels per User" chart displays
- [ ] "Quality Metrics" chart displays
- [ ] Diagnosis distribution pie chart displays
- [ ] Laterality distribution chart displays

### User Management Tab
- [ ] Current users table displays
- [ ] Can create new labeler account
- [ ] Can create new admin account
- [ ] Can assign route strategies
- [ ] New users appear in table immediately

### Label Review Tab
- [ ] Can select user to review
- [ ] Review queue shows marked images
- [ ] Can remove items from review queue
- [ ] All labels table displays
- [ ] Can filter by diagnosis
- [ ] Can filter by flag
- [ ] Can filter by quality
- [ ] Can download labels as CSV
- [ ] CSV contains all correct data

## ✅ Multi-User Testing

### Concurrent Usage
- [ ] Open two browsers/tabs
- [ ] Login as different users
- [ ] Label different images
- [ ] Each user maintains separate session
- [ ] Labels don't conflict
- [ ] Each user has independent progress

### Label Overlap
- [ ] User 1 labels image X
- [ ] User 2 labels same image X
- [ ] Both labels are saved separately
- [ ] Each user's label file contains their version

## ✅ Error Handling Testing

### Missing Files
- [ ] Temporarily rename data file
- [ ] Start application
- [ ] Appropriate error message displays
- [ ] Application doesn't crash
- [ ] Can recover after fixing path

### Missing Images
- [ ] Navigate to image that doesn't exist
- [ ] "Image not found" warning displays
- [ ] Image path is shown for debugging
- [ ] Can continue labeling other images

### Invalid Login
- [ ] Try wrong password
- [ ] Error message displays
- [ ] Can try again
- [ ] Try non-existent username
- [ ] Appropriate error message displays

## ✅ Performance Testing

### Large Dataset
- [ ] Application loads with 250K+ images
- [ ] Navigation is responsive
- [ ] Progress bar updates smoothly
- [ ] No significant lag when labeling
- [ ] Memory usage is reasonable

### Long Sessions
- [ ] Label 50+ images in one session
- [ ] No performance degradation
- [ ] No memory leaks
- [ ] Auto-save works throughout

## ✅ Data Integrity Testing

### Label Files
- [ ] Open `data/labels/{username}_labels.json`
- [ ] JSON is valid and formatted
- [ ] Contains expected fields
- [ ] Timestamps are correct
- [ ] Metadata is complete

### User Files
- [ ] Open `data/users/users.json`
- [ ] JSON is valid
- [ ] Passwords are hashed (not plain text)
- [ ] User roles are correct
- [ ] Route strategies are saved

### Edit History
- [ ] Label an image
- [ ] Edit the same image
- [ ] Open label JSON file
- [ ] `edit_history` array exists
- [ ] Previous version is saved
- [ ] Edit timestamp is recorded

## ✅ Edge Cases Testing

- [ ] Label first image in dataset
- [ ] Label last image in dataset
- [ ] Navigate when at first image (Previous disabled)
- [ ] Navigate when at last image (Next disabled)
- [ ] Patient with no notes (displays message)
- [ ] Patient with >2 notes (shows closest)
- [ ] Exam date exactly matches note date
- [ ] Very old notes (>365 days) are excluded

## ✅ Export Testing

- [ ] Export labels as CSV from admin panel
- [ ] CSV file downloads successfully
- [ ] CSV contains all expected columns
- [ ] CSV can be opened in Excel
- [ ] Data is formatted correctly
- [ ] Special characters are handled correctly

## 🐛 Issues Found

Document any issues you find:

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| 1       |             |          |        |
| 2       |             |          |        |
| 3       |             |          |        |

## ✅ Final Approval

- [ ] All critical tests passed
- [ ] All users can login
- [ ] Labeling workflow works end-to-end
- [ ] Data is saved correctly
- [ ] Admin dashboard shows accurate statistics
- [ ] No major bugs found
- [ ] Application is ready for production use

---

**Testing completed by:** _______________  
**Date:** _______________  
**Version:** 1.0.0  
**Notes:**
