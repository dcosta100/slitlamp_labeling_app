"""
Label management module for saving and loading labels
"""

import json
from pathlib import Path
from datetime import datetime
from config.config import LABELS_DIR, DATETIME_FORMAT

class LabelManager:
    """Class to manage label saving and loading"""
    
    def __init__(self, username):
        self.username = username
        self.labels_file = LABELS_DIR / f"{username}_labels.json"
        self.labels = self.load_labels()
    
    def load_labels(self):
        """Load existing labels for this user"""
        if self.labels_file.exists():
            with open(self.labels_file, 'r') as f:
                return json.load(f)
        return {
            "user": self.username,
            "created_at": datetime.now().strftime(DATETIME_FORMAT),
            "last_modified": datetime.now().strftime(DATETIME_FORMAT),
            "labels": {}
        }
    
    def save_labels(self):
        """Save labels to file"""
        self.labels["last_modified"] = datetime.now().strftime(DATETIME_FORMAT)
        with open(self.labels_file, 'w') as f:
            json.dump(self.labels, f, indent=2)
    
    def add_label(self, image_index, image_path, laterality, diagnosis, 
                  diagnosis_other, flag, quality, metadata=None):
        """
        Add or update a label
        """
        image_key = str(image_index)
        
        # Check if this is an edit
        is_edit = image_key in self.labels["labels"]
        
        label_data = {
            "image_path": image_path,
            "laterality": laterality,
            "diagnosis": diagnosis,
            "diagnosis_other": diagnosis_other if diagnosis == "Other" else None,
            "flag": flag,
            "quality": quality,
            "labeled_by": self.username,
            "labeled_at": datetime.now().strftime(DATETIME_FORMAT),
            "is_edit": is_edit,
            "metadata": metadata or {}
        }
        
        # If it's an edit, keep history
        if is_edit:
            if "edit_history" not in self.labels["labels"][image_key]:
                self.labels["labels"][image_key]["edit_history"] = []
            
            # Save previous version to history
            previous = {k: v for k, v in self.labels["labels"][image_key].items() 
                       if k != "edit_history"}
            previous["edited_at"] = datetime.now().strftime(DATETIME_FORMAT)
            self.labels["labels"][image_key]["edit_history"].append(previous)
        
        self.labels["labels"][image_key] = label_data
        self.save_labels()
    
    def get_label(self, image_index):
        """Get label for a specific image"""
        return self.labels["labels"].get(str(image_index))
    
    def is_labeled(self, image_index):
        """Check if an image has been labeled"""
        return str(image_index) in self.labels["labels"]
    
    def get_labeled_count(self):
        """Get count of labeled images"""
        return len(self.labels["labels"])
    
    def get_last_labeled_index(self, route_indices):
        """Get the last labeled index in the route"""
        for i in range(len(route_indices) - 1, -1, -1):
            if self.is_labeled(route_indices[i]):
                return i
        return -1
    
    def get_next_unlabeled_index(self, route_indices, current_position=0):
        """Get the next unlabeled index in the route"""
        for i in range(current_position, len(route_indices)):
            if not self.is_labeled(route_indices[i]):
                return i
        return None
    
    def get_statistics(self):
        """Get statistics about labels"""
        labels = self.labels["labels"]
        total = len(labels)
        
        if total == 0:
            return {
                "total": 0,
                "by_laterality": {},
                "by_diagnosis": {},
                "flagged": 0,
                "not_usable": 0,
                "edited": 0
            }
        
        stats = {
            "total": total,
            "by_laterality": {},
            "by_diagnosis": {},
            "flagged": 0,
            "not_usable": 0,
            "edited": 0
        }
        
        for label in labels.values():
            # Count by laterality
            lat = label["laterality"]
            stats["by_laterality"][lat] = stats["by_laterality"].get(lat, 0) + 1
            
            # Count by diagnosis
            diag = label["diagnosis"]
            if diag == "Other" and label["diagnosis_other"]:
                diag = f"Other: {label['diagnosis_other']}"
            stats["by_diagnosis"][diag] = stats["by_diagnosis"].get(diag, 0) + 1
            
            # Count flags
            if label["flag"] == "Yes":
                stats["flagged"] += 1
            
            # Count not usable
            if label["quality"] == "Not Usable":
                stats["not_usable"] += 1
            
            # Count edits
            if label.get("is_edit", False):
                stats["edited"] += 1
        
        return stats
    
    def add_to_review_queue(self, image_index):
        """Add an image to review queue"""
        if "review_queue" not in self.labels:
            self.labels["review_queue"] = []
        
        if str(image_index) not in self.labels["review_queue"]:
            self.labels["review_queue"].append(str(image_index))
            self.save_labels()
    
    def remove_from_review_queue(self, image_index):
        """Remove an image from review queue"""
        if "review_queue" in self.labels and str(image_index) in self.labels["review_queue"]:
            self.labels["review_queue"].remove(str(image_index))
            self.save_labels()
    
    def get_review_queue(self):
        """Get review queue"""
        return self.labels.get("review_queue", [])
    
    @staticmethod
    def get_all_user_stats():
        """Get statistics for all users"""
        all_stats = {}
        
        for labels_file in LABELS_DIR.glob("*_labels.json"):
            username = labels_file.stem.replace("_labels", "")
            
            with open(labels_file, 'r') as f:
                data = json.load(f)
            
            manager = LabelManager(username)
            manager.labels = data
            stats = manager.get_statistics()
            
            all_stats[username] = {
                "created_at": data.get("created_at"),
                "last_modified": data.get("last_modified"),
                "statistics": stats
            }
        
        return all_stats
