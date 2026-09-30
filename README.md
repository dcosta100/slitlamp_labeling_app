# 🔬 Slitlamp Image Labeling Application

Streamlit application for labeling slit lamp photographs with clinical context
(EHR notes, structured exam annotations, order diagnosis) alongside each image.
Multi-user, with per-user routes so labelers do not collide, and an admin
dashboard for weekly progress reporting.

## 📋 Features

- **Labeling interface** with laterality, image quality, optional illumination
  technique, and a hierarchical **multilabel** diagnosis (an image can carry
  several conditions at once)
- **Clinical context**: closest EHR progress notes and slit lamp exam
  annotations for the same patient, matched by date
- **AI pre-labels**: suggestions loaded from a previous model run, shown for
  review rather than accepted blindly
- **Route strategies** so each labeler works a disjoint slice of the dataset
- **Session activity logging**: login, working time and labels per session
- **Admin dashboard**: weekly report, session history, import of labeler files,
  cumulative statistics, user management, label review and CSV export

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Windows (paths assume Windows and a mounted image share)
- Access to the source data files and to the image share

### Installation

```bash
git clone <your-repo-url>
cd slitlamp_labeling_app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

All machine-specific paths come from a `.env` file in the project root. Copy the
template and fill it in — **the application will refuse to start if any required
path is missing**:

```bash
copy .env.example .env
```

```ini
DIAGNOSIS_PATH=...\studyinfo_laterality_diagnosis.dta
NOTES_PATH=...\ehr_anonymized_all.parquet
CROSS_PATH=...\slitlamp_crosswalk_complete_12082025.csv
ANNOTATIONS_PATH=...\BPGR_slexam_all.csv
IMAGE_BASE_PATH=L:\SlitLamp
PREPROCESSED_PATH=...\data\preprocessed_dataset.parquet
USE_PREPROCESSED=True
```

Do **not** edit `config/config.py` for paths. It only reads them from `.env`.

Optional settings, all with sensible defaults:

| Variable | Default | Meaning |
|---|---|---|
| `DEFAULT_DATASET_FILTER` | `WITH_AI_PRELABEL` | Which images enter the routes |
| `MAX_NOTE_DAYS_DIFFERENCE` | 365 | Window for matching EHR notes |
| `MAX_ANNOTATION_DAYS_DIFFERENCE` | 7 | Window for matching annotations |
| `ENABLE_AUTOFILL_SAME_STUDYID` | True | Prefill from another image of the same study |
| `HEARTBEAT_INTERVAL_SECONDS` | 60 | How often an open session logs a heartbeat |
| `SESSION_IDLE_TIMEOUT_MINUTES` | 15 | Gap above which a labeler counts as away |

### Preprocessing (once)

Joining the source files on demand is far too slow for ~215k images. Build the
preprocessed parquet first — see [preprocessing/README.md](preprocessing/README.md):

```bash
python preprocessing/create_preprocessed_dataset.py
```

### Running

```bash
run_streamlit.bat          # or: streamlit run app.py
```

Opens at `http://localhost:8501`.

### Updating

```bash
update_repo.bat
```

Stops Streamlit, force-syncs tracked files to `origin`, clears bytecode caches
and reinstalls requirements. It deliberately does **not** run `git clean`, so
locally saved labels and logs survive.

### Default login

`admin` / `admin123` — change this before giving anyone else access.

## 📁 Project Structure

```
slitlamp_labeling_app/
├── app.py                    # entry point: login gate, sidebar, routing
├── config/config.py          # .env loading + the whole label taxonomy
├── utils/
│   ├── auth.py               # users.json, password hashing, session state
│   ├── data_loader.py        # dataset loading, filtering, route building
│   ├── label_manager.py      # label storage, migration, statistics
│   ├── session_logger.py     # per-session activity log
│   └── reporting.py          # weekly aggregation for the admin dashboard
├── pages/
│   ├── login_page.py
│   ├── labeling_page.py
│   └── admin_page.py
├── preprocessing/            # one-off dataset build
└── data/
    ├── labels/               # {username}_labels.json  (gitignored)
    ├── logs/                 # {username}_sessions.jsonl (gitignored)
    ├── users/users.json
    └── backups/              # pre-migration and pre-import copies
```

## 🏷️ Label Schema

Labels are keyed by a **normalised image path** — everything from `SlitLamp\`
onwards, lowercased. A route position would not survive a change of dataset
filter or parquet; the image path does. Files written before this change are
migrated automatically on first load, with the original copied to
`data/backups/`.

```json
{
  "user": "taka",
  "schema_version": 2,
  "labels": {
    "slitlamp\\bpg000168\\bpg000168_125606678\\slit lamp photography - os - left eye\\bpg000168_125606678_001.png": {
      "image_path": "L:\\SlitLamp\\BPG000168\\...\\BPG000168_125606678_001.png",
      "image_index": 10541,
      "laterality": "Left",
      "quality": "Usable",
      "illumination": "Diffuse",
      "conditions": {
        "Dry Eye Disease": {"severity": "Moderate", "signs": ["MGD"]},
        "Cataract": {"type": "Pseudophakia", "severity": null, "features": []}
      },
      "labeled_by": "taka",
      "labeled_at": "2026-03-01 11:11:44",
      "is_edit": false,
      "metadata": {"maskedid_studyid": "...", "exam_date": "...", "pat_mrn": "..."},
      "edit_history": []
    }
  },
  "review_queue": [],
  "current_position": 3002
}
```

Conditions and their sub-fields are defined in `config/config.py`:
Dry Eye Disease, Cataract, Infectious Keratitis / Conjunctivitis, Ocular Surface
Tumors, Subconjunctival Hemorrhage. Change the taxonomy there, not in the pages.

**Saves are crash-safe.** Each save is written to a temporary file, flushed, then
swapped in atomically, and the previous version is kept as `.bak`. If the main
file is ever unreadable, the `.bak` is loaded automatically.

## 🛠️ Route Strategies

Each user has a `route_strategy` in `data/users/users.json` that decides which
images they see and in what order. Admins can reassign it from the dashboard;
the change takes effect on the labeler's next interaction, with no restart.

| Strategy | Meaning |
|---|---|
| `prelabel_first` | AI pre-labeled images first, then the rest |
| `prelabel_first_third` … `prelabel_last_third` | Thirds of the pre-labeled set |
| `prelabel_1_6` … `prelabel_6_6` | Sixths of the pre-labeled set |
| `forward` / `backward` | Whole dataset, in order or reversed |
| `middle_out` | From the middle, alternating outwards |
| `random` | Shuffled, seeded by username |

Changing a user's strategy discards their saved position (it belonged to the old
route) and drops them at the first unlabeled image of the new one. Their labels
are unaffected — they are keyed by image, not by position.

## 💾 Data Storage

| What | Where | In git? |
|---|---|---|
| Labels | `data/labels/{username}_labels.json` | No |
| Crash backup | `data/labels/{username}_labels.json.bak` | No |
| Session activity | `data/logs/{username}_sessions.jsonl` | No |
| Pre-migration / pre-import copies | `data/backups/` | No |
| AI pre-labels | `data/labels/AI_prelabel_labels.json` | Yes |
| Users | `data/users/users.json` | Yes |

## 📅 Weekly Workflow

**Labelers** send two files at the end of each week:

- `data/labels/{username}_labels.json`
- `data/logs/{username}_sessions.jsonl`

**Admin** loads them on the dashboard's **Import** tab. The existing copies are
backed up first, session logs are merged rather than replaced, and a warning is
shown if an incoming file has fewer labels than the stored one (usually a sign
that an older file was sent by mistake).

Then open **Weekly Report**, pick the week, and use the generated markdown or CSV
for the status update.

## 🔒 Security Notes

- Passwords are SHA-256 hashed, **unsalted**, and `users.json` is tracked in git
- There is no password-change screen; passwords are set when the user is created
- Authentication is local only, intended for a trusted network

## 🐛 Troubleshooting

**Application will not start, complains about a path** — a required variable is
missing from `.env`. Compare against `.env.example`.

**Images not loading** — check `IMAGE_BASE_PATH` and that the share is mounted.
The path is built as
`IMAGE_BASE_PATH/maskedid/maskedid_studyid/proc_name/photo_name`.

**Very slow startup** — the preprocessed parquet is missing, so the app is
joining the source files at runtime. Run the preprocessing script.

**Labeler starts from the beginning again** — their saved position was reset,
usually by a route strategy change. The app scans forward to the first unlabeled
image, so no work is repeated.

**A label file will not open** — the app falls back to the `.bak` automatically
and prints a warning to the console. Older copies live in `data/backups/`.

---

**Last Updated:** August 2026
