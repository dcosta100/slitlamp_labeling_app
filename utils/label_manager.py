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
    
    def add_label(self, image_index, image_path, laterality, quality, 
                  conditions=None, metadata=None):
        """
        Add or update a label with multilabel hierarchical structure
        
        Parameters:
        - image_index: Index of the image
        - image_path: Path to the image file
        - laterality: Left or Right
        - quality: Usable or Non Usable
        - conditions: Dictionary with condition names as keys and their data as values
          Example: {
              "Dry Eye Disease": {"severity": "Moderate", "signs": ["MGD", "Foamy tear film"]},
              "Cataract": {"type": "Nuclear", "severity": "Mild", "features": []}
          }
        - metadata: Additional metadata
        """
        image_key = str(image_index)
        
        # Check if this is an edit
        is_edit = image_key in self.labels["labels"]
        
        label_data = {
            "image_path": image_path,
            "laterality": laterality,
            "quality": quality,
            "conditions": conditions or {},
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
                "by_quality": {},
                "by_condition": {},
                "edited": 0
            }
        
        stats = {
            "total": total,
            "by_laterality": {},
            "by_quality": {},
            "by_condition": {},
            "edited": 0
        }
        
        for label in labels.values():
            # Count by laterality
            lat = label["laterality"]
            stats["by_laterality"][lat] = stats["by_laterality"].get(lat, 0) + 1
            
            # Count by quality
            quality = label["quality"]
            stats["by_quality"][quality] = stats["by_quality"].get(quality, 0) + 1
            
            # Count by condition (if usable)
            if quality == "Usable":
                conditions = label.get("conditions", {})
                for condition_name in conditions.keys():
                    stats["by_condition"][condition_name] = stats["by_condition"].get(condition_name, 0) + 1
            
            # Count edits
            if label.get("is_edit", False):
                stats["edited"] += 1
        
        return stats
    
    def get_detailed_statistics(self):
        """Get detailed statistics including condition-specific data"""
        labels = self.labels["labels"]
        stats = self.get_statistics()
        
        # Add detailed statistics per condition
        stats["detailed"] = {
            "dry_eye": {"by_severity": {}, "by_signs": {}},
            "cataract": {"by_type": {}, "by_severity": {}, "by_features": {}},
            "infectious": {"by_type": {}, "by_etiology": {}, "by_size": {}},
            "tumor": {"by_type": {}, "by_malignancy": {}, "by_location": {}},
            "sch": {"by_presence": {}, "by_extent": {}}
        }
        
        for label in labels.values():
            if label.get("quality") != "Usable":
                continue
                
            conditions = label.get("conditions", {})
            
            # Dry Eye Disease
            if "Dry Eye Disease" in conditions:
                data = conditions["Dry Eye Disease"]
                severity = data.get("severity")
                if severity:
                    stats["detailed"]["dry_eye"]["by_severity"][severity] = \
                        stats["detailed"]["dry_eye"]["by_severity"].get(severity, 0) + 1
                
                for sign in data.get("signs", []):
                    stats["detailed"]["dry_eye"]["by_signs"][sign] = \
                        stats["detailed"]["dry_eye"]["by_signs"].get(sign, 0) + 1
            
            # Cataract
            if "Cataract" in conditions:
                data = conditions["Cataract"]
                cat_type = data.get("type")
                if cat_type:
                    stats["detailed"]["cataract"]["by_type"][cat_type] = \
                        stats["detailed"]["cataract"]["by_type"].get(cat_type, 0) + 1
                
                severity = data.get("severity")
                if severity:
                    stats["detailed"]["cataract"]["by_severity"][severity] = \
                        stats["detailed"]["cataract"]["by_severity"].get(severity, 0) + 1
                
                for feature in data.get("features", []):
                    stats["detailed"]["cataract"]["by_features"][feature] = \
                        stats["detailed"]["cataract"]["by_features"].get(feature, 0) + 1
            
            # Infectious Keratitis / Conjunctivitis
            if "Infectious Keratitis / Conjunctivitis" in conditions:
                data = conditions["Infectious Keratitis / Conjunctivitis"]
                inf_type = data.get("type")
                if inf_type:
                    stats["detailed"]["infectious"]["by_type"][inf_type] = \
                        stats["detailed"]["infectious"]["by_type"].get(inf_type, 0) + 1
                
                etiology = data.get("etiology")
                if etiology:
                    stats["detailed"]["infectious"]["by_etiology"][etiology] = \
                        stats["detailed"]["infectious"]["by_etiology"].get(etiology, 0) + 1
                
                size = data.get("keratitis_size")
                if size:
                    stats["detailed"]["infectious"]["by_size"][size] = \
                        stats["detailed"]["infectious"]["by_size"].get(size, 0) + 1
            
            # Ocular Surface Tumors
            if "Ocular Surface Tumors" in conditions:
                data = conditions["Ocular Surface Tumors"]
                tumor_type = data.get("type")
                if tumor_type:
                    stats["detailed"]["tumor"]["by_type"][tumor_type] = \
                        stats["detailed"]["tumor"]["by_type"].get(tumor_type, 0) + 1
                
                malignancy = data.get("malignancy")
                if malignancy:
                    stats["detailed"]["tumor"]["by_malignancy"][malignancy] = \
                        stats["detailed"]["tumor"]["by_malignancy"].get(malignancy, 0) + 1
                
                location = data.get("location")
                if location:
                    stats["detailed"]["tumor"]["by_location"][location] = \
                        stats["detailed"]["tumor"]["by_location"].get(location, 0) + 1
            
            # Subconjunctival Hemorrhage
            if "Subconjunctival Hemorrhage" in conditions:
                data = conditions["Subconjunctival Hemorrhage"]
                presence = data.get("presence")
                if presence:
                    stats["detailed"]["sch"]["by_presence"][presence] = \
                        stats["detailed"]["sch"]["by_presence"].get(presence, 0) + 1
                
                extent = data.get("extent")
                if extent:
                    stats["detailed"]["sch"]["by_extent"][extent] = \
                        stats["detailed"]["sch"]["by_extent"].get(extent, 0) + 1
        
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
