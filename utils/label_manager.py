"""
Label management module for saving and loading labels

Labels are keyed by a normalised image path rather than by a position in the
route. A route position only means something relative to the dataset filter and
the parquet that were in use when the label was made: change either and every
key silently points at a different image. The image path does not move.

Files written before this change are migrated automatically on first load, with
a copy of the original kept in data/backups/.
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from config.config import BACKUPS_DIR, DATETIME_FORMAT, LABELS_DIR

SCHEMA_VERSION = 2

_IMAGE_ROOT = re.compile(r"SlitLamp[/\\]", re.IGNORECASE)


def normalize_image_path(path):
    """Stable key for an image, independent of where the share is mounted.

    Everything from "SlitLamp\\" onwards, lowercased, backslash separated, so
    two machines that map the image drive to different letters still agree.
    """
    text = str(path)
    match = _IMAGE_ROOT.search(text)
    if match:
        text = text[match.start():]
    return text.replace("/", "\\").lower()


class LabelManager:
    """Class to manage label saving and loading"""

    def __init__(self, username, read_only=False):
        self.username = username
        self.read_only = read_only
        self.labels_file = LABELS_DIR / f"{username}_labels.json"
        self.backup_file = self.labels_file.with_name(self.labels_file.name + ".bak")
        self.migration_report = None
        self.labels = self.load_labels()

    # ==================================================
    # Reading and writing
    # ==================================================

    def load_labels(self):
        """Load existing labels, recovering from the backup if the file is broken."""
        data = None

        for candidate, source in ((self.labels_file, "file"), (self.backup_file, "backup")):
            if not candidate.exists():
                continue
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if source == "backup":
                    print(f"⚠️  {self.labels_file.name} was unreadable — recovered from .bak")
                break
            except (OSError, json.JSONDecodeError) as exc:
                print(f"⚠️  Could not read {candidate.name}: {exc}")

        if data is None:
            return {
                "user": self.username,
                "schema_version": SCHEMA_VERSION,
                "created_at": datetime.now().strftime(DATETIME_FORMAT),
                "last_modified": datetime.now().strftime(DATETIME_FORMAT),
                "labels": {},
                "review_queue": [],
                "current_position": 0,
            }

        return self._migrate(data)

    def save_labels(self):
        """Save labels to file.

        Written to a temporary file, flushed to disk, then swapped in with an
        atomic replace, so a crash or power cut mid-write can never leave a
        truncated file behind. The previous version is kept as .bak.
        """
        if self.read_only:
            return

        self.labels["last_modified"] = datetime.now().strftime(DATETIME_FORMAT)
        self.labels["schema_version"] = SCHEMA_VERSION

        temp_file = self.labels_file.with_name(self.labels_file.name + ".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(self.labels, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        self._refresh_backup()
        os.replace(temp_file, self.labels_file)

    def _refresh_backup(self):
        """Point .bak at the current file, just before it is replaced.

        A hard link is free on NTFS. If the labels live somewhere that cannot
        link (a network share, a different filesystem) fall back to a copy, and
        give up quietly rather than block a save.
        """
        if not self.labels_file.exists():
            return
        try:
            if self.backup_file.exists():
                self.backup_file.unlink()
            os.link(self.labels_file, self.backup_file)
        except OSError:
            try:
                shutil.copy2(self.labels_file, self.backup_file)
            except OSError:
                pass

    # ==================================================
    # Migration from index-keyed files
    # ==================================================

    def _migrate(self, data):
        """Convert an index-keyed file to path keys, once."""
        if data.get("schema_version") == SCHEMA_VERSION:
            return data

        old_labels = data.get("labels") or {}
        if not old_labels:
            data["schema_version"] = SCHEMA_VERSION
            data.setdefault("review_queue", [])
            return data

        new_labels = {}
        index_to_key = {}
        merged = 0
        unresolved = 0

        for old_key, label in old_labels.items():
            # Files written by the app used the route index as key and stored the
            # path inside the record. The AI pre-label file already uses the path
            # as its key - and its inner image_path is unreliable, because the
            # study expansion copied the first image's path onto every sibling.
            if old_key.isdigit():
                source_path = label.get("image_path")
                if not source_path:
                    new_labels[old_key] = label
                    unresolved += 1
                    continue
                label.setdefault("image_index", int(old_key))
            else:
                source_path = old_key

            new_key = normalize_image_path(source_path)
            index_to_key[old_key] = new_key

            existing = new_labels.get(new_key)
            if existing is None:
                new_labels[new_key] = label
                continue

            # Same image labeled more than once (duplicate rows in the route):
            # keep the most recent and preserve the other in the edit history.
            merged += 1
            newer, older = (
                (label, existing)
                if (label.get("labeled_at") or "") >= (existing.get("labeled_at") or "")
                else (existing, label)
            )
            history = list(newer.get("edit_history") or [])
            history.extend(older.get("edit_history") or [])
            superseded = {k: v for k, v in older.items() if k != "edit_history"}
            superseded["superseded_at"] = datetime.now().strftime(DATETIME_FORMAT)
            history.append(superseded)
            newer["edit_history"] = history
            new_labels[new_key] = newer

        migrated_queue = []
        for entry in data.get("review_queue") or []:
            migrated_queue.append(index_to_key.get(str(entry), str(entry)))

        if not self.read_only:
            self._archive_pre_migration()

        data["labels"] = new_labels
        data["review_queue"] = migrated_queue
        data["schema_version"] = SCHEMA_VERSION

        self.migration_report = {
            "before": len(old_labels),
            "after": len(new_labels),
            "merged": merged,
            "unresolved": unresolved,
        }
        if self.read_only:
            # Not written back: keys are normalised in memory only.
            print(f"   {self.username}: {len(new_labels):,} labels indexed by path")
        else:
            print(f"🔁 {self.username}: migrated {len(old_labels):,} labels to path keys "
                  f"({len(new_labels):,} unique, {merged:,} duplicates merged, "
                  f"{unresolved:,} unresolved)")

        if not self.read_only:
            # __init__ has not assigned self.labels yet; save_labels() reads it.
            self.labels = data
            self.save_labels()
        return data

    def _archive_pre_migration(self):
        """Keep an untouched copy of the pre-migration file."""
        if not self.labels_file.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = BACKUPS_DIR / f"{self.username}_labels_preV{SCHEMA_VERSION}_{stamp}.json"
        try:
            BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.labels_file, archive)
            print(f"   original kept at {archive}")
        except OSError as exc:
            print(f"   ⚠️  could not archive original: {exc}")

    # ==================================================
    # Position within the route
    # ==================================================

    def save_position(self, position):
        """Save current position in route"""
        self.labels["current_position"] = position
        self.save_labels()

    def get_position(self):
        """Get saved position in route"""
        return self.labels.get("current_position", 0)

    # ==================================================
    # Labels
    # ==================================================

    def add_label(self, image_path, laterality, quality, conditions=None,
                  metadata=None, illumination=None, image_index=None):
        """
        Add or update a label with multilabel hierarchical structure

        Parameters:
        - image_path: Path to the image file; also the identity of the label
        - laterality: Left or Right
        - quality: Usable or Non Usable
        - illumination: Optional slit lamp illumination technique (or None)
        - conditions: Dictionary with condition names as keys and their data as values
          Example: {
              "Dry Eye Disease": {"severity": "Moderate", "signs": ["MGD", "Foamy tear film"]},
              "Cataract": {"type": "Nuclear", "severity": "Mild", "features": []}
          }
        - metadata: Additional metadata
        - image_index: Route index the image was at, kept for reference only
        """
        image_key = normalize_image_path(image_path)
        previous = self.labels["labels"].get(image_key)
        is_edit = previous is not None

        label_data = {
            "image_path": str(image_path),
            "image_index": image_index,
            "laterality": laterality,
            "quality": quality,
            "illumination": illumination,
            "conditions": conditions or {},
            "labeled_by": self.username,
            "labeled_at": datetime.now().strftime(DATETIME_FORMAT),
            "is_edit": is_edit,
            "metadata": metadata or {},
        }

        if is_edit:
            history = list(previous.get("edit_history") or [])
            superseded = {k: v for k, v in previous.items() if k != "edit_history"}
            superseded["edited_at"] = label_data["labeled_at"]
            history.append(superseded)
            label_data["edit_history"] = history

        self.labels["labels"][image_key] = label_data
        self.save_labels()

    def get_label(self, image_path):
        """Get the label for an image, or None."""
        return self.labels["labels"].get(normalize_image_path(image_path))

    # Kept so existing callers keep working; identical to get_label now that
    # labels are keyed by path.
    get_label_by_path = get_label

    def is_labeled(self, image_path):
        """Check if an image has been labeled"""
        return normalize_image_path(image_path) in self.labels["labels"]

    def labeled_keys(self):
        """Every labeled image key, for cheap membership tests over a route."""
        return set(self.labels["labels"])

    def get_labeled_count(self):
        """Get count of labeled images"""
        return len(self.labels["labels"])

    # ==================================================
    # Review queue
    # ==================================================

    def add_to_review_queue(self, image_path):
        """Add an image to review queue"""
        image_key = normalize_image_path(image_path)
        queue = self.labels.setdefault("review_queue", [])
        if image_key not in queue:
            queue.append(image_key)
            self.save_labels()

    def remove_from_review_queue(self, image_path):
        """Remove an image from review queue"""
        image_key = normalize_image_path(image_path)
        queue = self.labels.get("review_queue", [])
        if image_key in queue:
            queue.remove(image_key)
            self.save_labels()

    def get_review_queue(self):
        """Get review queue"""
        return self.labels.get("review_queue", [])

    # ==================================================
    # Statistics
    # ==================================================

    def get_statistics(self):
        """Get statistics about labels"""
        labels = self.labels["labels"]

        stats = {
            "total": len(labels),
            "by_laterality": {},
            "by_quality": {},
            "by_illumination": {},
            "by_condition": {},
            "edited": 0,
        }
        if not labels:
            return stats

        for label in labels.values():
            lat = label.get("laterality")
            stats["by_laterality"][lat] = stats["by_laterality"].get(lat, 0) + 1

            quality = label.get("quality")
            stats["by_quality"][quality] = stats["by_quality"].get(quality, 0) + 1

            illumination = label.get("illumination") or "Not specified"
            stats["by_illumination"][illumination] = stats["by_illumination"].get(illumination, 0) + 1

            if quality == "Usable":
                for condition_name in (label.get("conditions") or {}):
                    stats["by_condition"][condition_name] = stats["by_condition"].get(condition_name, 0) + 1

            if label.get("is_edit", False):
                stats["edited"] += 1

        return stats

    def get_detailed_statistics(self):
        """Get detailed statistics including condition-specific data"""
        labels = self.labels["labels"]
        stats = self.get_statistics()

        stats["detailed"] = {
            "dry_eye": {"by_severity": {}, "by_signs": {}},
            "cataract": {"by_type": {}, "by_severity": {}, "by_features": {}},
            "infectious": {"by_type": {}, "by_etiology": {}, "by_size": {}},
            "tumor": {"by_type": {}, "by_malignancy": {}, "by_location": {}},
            "sch": {"by_presence": {}, "by_extent": {}},
        }

        def bump(group, bucket, value):
            if value:
                target = stats["detailed"][group][bucket]
                target[value] = target.get(value, 0) + 1

        for label in labels.values():
            if label.get("quality") != "Usable":
                continue

            conditions = label.get("conditions") or {}

            if "Dry Eye Disease" in conditions:
                data = conditions["Dry Eye Disease"]
                bump("dry_eye", "by_severity", data.get("severity"))
                for sign in data.get("signs", []):
                    bump("dry_eye", "by_signs", sign)

            if "Cataract" in conditions:
                data = conditions["Cataract"]
                bump("cataract", "by_type", data.get("type"))
                bump("cataract", "by_severity", data.get("severity"))
                for feature in data.get("features", []):
                    bump("cataract", "by_features", feature)

            if "Infectious Keratitis / Conjunctivitis" in conditions:
                data = conditions["Infectious Keratitis / Conjunctivitis"]
                bump("infectious", "by_type", data.get("type"))
                bump("infectious", "by_etiology", data.get("etiology"))
                bump("infectious", "by_size", data.get("keratitis_size"))

            if "Ocular Surface Tumors" in conditions:
                data = conditions["Ocular Surface Tumors"]
                bump("tumor", "by_type", data.get("type"))
                bump("tumor", "by_malignancy", data.get("malignancy"))
                bump("tumor", "by_location", data.get("location"))

            if "Subconjunctival Hemorrhage" in conditions:
                data = conditions["Subconjunctival Hemorrhage"]
                bump("sch", "by_presence", data.get("presence"))
                bump("sch", "by_extent", data.get("extent"))

        return stats

    def get_last_label_for_studyid(self, studyid):
        """
        Get the most recent label for a given studyid
        Returns the label data (without metadata like labeled_at, is_edit, etc.)
        """
        if not studyid:
            return None

        matching = [
            label for label in self.labels["labels"].values()
            if (label.get("metadata") or {}).get("maskedid_studyid") == studyid
        ]
        if not matching:
            return None

        most_recent = max(matching, key=lambda label: label.get("labeled_at") or "")
        return {
            "laterality": most_recent.get("laterality"),
            "quality": most_recent.get("quality"),
            "illumination": most_recent.get("illumination"),
            "conditions": most_recent.get("conditions", {}),
        }

    @staticmethod
    def get_all_user_stats():
        """Get statistics for all human labelers (AI pre-labels excluded)."""
        all_stats = {}

        for labels_file in LABELS_DIR.glob("*_labels.json"):
            if not labels_file.stem.endswith("_labels"):
                continue
            username = labels_file.stem[: -len("_labels")]
            if username.startswith("AI_prelabel"):
                continue

            manager = LabelManager(username)
            all_stats[username] = {
                "created_at": manager.labels.get("created_at"),
                "last_modified": manager.labels.get("last_modified"),
                "statistics": manager.get_statistics(),
            }

        return all_stats
