# 🏗️ Application Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Web Browser                        │
│                   (localhost:8501)                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ HTTP
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Streamlit Server                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Login Page  │  │ Labeling Page│  │  Admin Page  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Session State Management                  │    │
│  │  (user, role, position, labels, etc.)              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │     Auth     │  │ Data Loader  │  │Label Manager │     │
│  │   Module     │  │    Module    │  │    Module    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────┬─────────────┬────────────────┬────────────────┘
             │             │                │
             │             │                │
┌────────────▼─────────────▼────────────────▼────────────────┐
│                    File System                              │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  User Data       │  │  Medical Data    │               │
│  │  - users.json    │  │  - .dta (Stata)  │               │
│  │  - labels JSON   │  │  - .parquet      │               │
│  └──────────────────┘  │  - .csv          │               │
│                        │  - .jpg images   │               │
│                        └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Login Flow
```
User → Login Page → Auth Module → users.json
                                      ↓
                              Verify Password Hash
                                      ↓
                              Create Session State
                                      ↓
                              Redirect to Main Page
```

### 2. Image Labeling Flow
```
User Navigates → DataLoader → Load Medical Data → Merge Datasets
                                                        ↓
                                               Get Current Image
                                                        ↓
                                          Find Closest Clinical Notes
                                                        ↓
                                            Display Image + Context
                                                        ↓
User Labels → LabelManager → Save to JSON → Update Statistics
                                                        ↓
                                             Auto-advance to Next
```

### 3. Admin Dashboard Flow
```
Admin User → Admin Page → LabelManager.get_all_user_stats()
                                           ↓
                              Read All Label JSON Files
                                           ↓
                              Aggregate Statistics
                                           ↓
                              Generate Visualizations
                                           ↓
                              Display Dashboard
```

## Component Architecture

### Frontend (Streamlit Pages)
```
pages/
├── login_page.py
│   └── Handles user authentication
│
├── labeling_page.py
│   ├── Image display
│   ├── Clinical information panel
│   ├── Labeling form
│   └── Navigation controls
│
└── admin_page.py
    ├── Statistics visualization
    ├── User management
    └── Label review interface
```

### Backend (Utils)
```
utils/
├── auth.py
│   ├── User authentication
│   ├── Password hashing
│   ├── User creation
│   └── Session management
│
├── data_loader.py
│   ├── Load medical data files
│   ├── Merge datasets
│   ├── Find closest notes
│   ├── Route strategy implementation
│   └── Image path construction
│
└── label_manager.py
    ├── Save labels
    ├── Load labels
    ├── Track edit history
    ├── Manage review queue
    └── Generate statistics
```

### Configuration
```
config/
└── config.py
    ├── File paths
    ├── Labeling options
    ├── User defaults
    └── Application settings
```

## Data Models

### User Model (users.json)
```json
{
  "users": {
    "username": {
      "password": "hashed_password_sha256",
      "role": "admin|labeler",
      "created_at": "ISO timestamp",
      "route_strategy": "forward|backward|middle_out|random"
    }
  }
}
```

### Label Model (username_labels.json)
```json
{
  "user": "username",
  "created_at": "timestamp",
  "last_modified": "timestamp",
  "labels": {
    "image_index": {
      "image_path": "full/path/to/image.jpg",
      "laterality": "Left|Right",
      "diagnosis": "option",
      "diagnosis_other": "text|null",
      "flag": "Yes|No",
      "quality": "Usable|Not Usable",
      "labeled_by": "username",
      "labeled_at": "timestamp",
      "is_edit": true|false,
      "metadata": {
        "maskedid_studyid": "id",
        "exam_date": "date",
        "pat_mrn": "mrn"
      },
      "edit_history": [
        {previous_versions}
      ]
    }
  },
  "review_queue": ["index1", "index2"]
}
```

## Route Strategies

### Forward Strategy
```
User Path: [0] → [1] → [2] → ... → [N]
Best for: Standard sequential processing
```

### Backward Strategy
```
User Path: [N] → [N-1] → [N-2] → ... → [0]
Best for: Working from end of dataset
```

### Middle-Out Strategy
```
Middle = N/2
User Path: [N/2] → [N/2+1] → [N/2-1] → [N/2+2] → [N/2-2] → ...
Best for: Prioritizing middle sections
```

### Random Strategy
```
Seed = hash(username)
User Path: Random permutation based on seed
Best for: Ensuring variety and even distribution
```

## Security Architecture

```
Password Input → SHA-256 Hash → Compare with Stored Hash
                                         ↓
                                   Grant/Deny Access
                                         ↓
                              Create Session Cookie
                                         ↓
                              Session-based Authorization
```

## File Organization

```
Application Root
├── Code Files (Python)
│   ├── Immutable (don't edit)
│   └── Config (edit paths only)
│
├── Data Files (JSON)
│   ├── Auto-generated
│   ├── User-specific
│   └── Backed up regularly
│
└── External Data (Medical)
    ├── Referenced by path
    ├── Read-only access
    └── Not copied locally
```

## Scalability Considerations

### Current Implementation (Local)
- Single machine deployment
- Local file system storage
- Session state in memory
- No database required

### Future Scaling Options
- Add PostgreSQL for labels
- Implement Redis for sessions
- Deploy to cloud (AWS/Azure)
- Add load balancing
- Implement real-time sync

## Technology Stack

```
┌─────────────────────────────────────┐
│         Frontend Layer               │
│         Streamlit UI                 │
│         HTML/CSS/JavaScript          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│      Application Layer               │
│      Python 3.8+                     │
│      Streamlit Framework             │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│      Data Processing Layer           │
│      Pandas, NumPy                   │
│      PIL (Images)                    │
│      Plotly (Visualization)          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│      Storage Layer                   │
│      JSON (Labels & Users)           │
│      File System (Images)            │
│      Stata/Parquet/CSV (Medical)     │
└─────────────────────────────────────┘
```

## Performance Optimization

### Data Loading
- Pandas caching (@st.cache_data)
- Lazy loading of images
- Efficient dataset merging

### Session Management
- Minimal session state
- Strategic rerun() calls
- Efficient navigation

### File I/O
- JSON for fast read/write
- Atomic writes for safety
- Minimal disk access

## Error Handling Strategy

```
User Action → Try Block → Success → Continue
                   ↓
              Exception Caught
                   ↓
           Display User-Friendly Message
                   ↓
           Log Error Details
                   ↓
           Offer Recovery Options
```

---

This architecture provides:
- ✅ Modularity (easy to modify components)
- ✅ Scalability (can grow with needs)
- ✅ Maintainability (clear structure)
- ✅ Security (password hashing, session management)
- ✅ Performance (caching, efficient data structures)
