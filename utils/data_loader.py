"""
Data loader module for handling medical imaging data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from functools import lru_cache
import streamlit as st
from config.config import (
    DIAGNOSIS_PATH,
    NOTES_PATH,
    CROSS_PATH,
    ANNOTATIONS_PATH,
    IMAGE_BASE_PATH,
    MAX_NOTE_DAYS_DIFFERENCE,
    MAX_ANNOTATION_DAYS_DIFFERENCE,
    DEFAULT_DATASET_FILTER,
    PREPROCESSED_PATH,
    USE_PREPROCESSED
)

class DataLoader:
    """Class to handle loading and merging of all datasets"""
    
    def __init__(self):
        self.diagnosis_df = None
        self.notes_df = None
        self.cross_df = None
        self.annotations_df = None
        self.merged_df = None
        self.filter_mode = DEFAULT_DATASET_FILTER
        
        # For lazy loading and caching
        self._notes_indexed = None
        self._annotations_indexed = None
        self._notes_loaded = False
        self._annotations_loaded = False
        
    @st.cache_data
    def load_data(_self):
        """Load all datasets with caching"""
        try:
            # Load diagnosis data (Stata file)
            _self.diagnosis_df = pd.read_stata(DIAGNOSIS_PATH)
            
            # Load notes data (Parquet file)
            _self.notes_df = pd.read_parquet(NOTES_PATH)
            
            # Load crosswalk data (CSV file)
            _self.cross_df = pd.read_csv(CROSS_PATH)
            
            # Load annotations data (CSV file)
            _self.annotations_df = pd.read_csv(ANNOTATIONS_PATH)
            
            # Rename studyid to maskedid in annotations
            if 'studyid' in _self.annotations_df.columns:
                _self.annotations_df.rename(columns={'studyid': 'maskedid'}, inplace=True)
            
            # Convert date columns to datetime
            _self.diagnosis_df['exam_date'] = pd.to_datetime(_self.diagnosis_df['exam_date'])
            _self.notes_df['note_date'] = pd.to_datetime(_self.notes_df['note_date'])
            
            # Convert annotation date column to datetime
            if 'date' in _self.annotations_df.columns:
                _self.annotations_df['annotation_date'] = pd.to_datetime(_self.annotations_df['date'])
            
            # Convert pat_mrn to string for consistent matching
            if 'pat_mrn' in _self.diagnosis_df.columns:
                _self.diagnosis_df['pat_mrn'] = _self.diagnosis_df['pat_mrn'].astype(str).str.strip()
            if 'pat_mrn' in _self.notes_df.columns:
                _self.notes_df['pat_mrn'] = _self.notes_df['pat_mrn'].astype(str).str.strip()
            
            # Filter for Progress Notes only
            if 'ip_note_type' in _self.notes_df.columns:
                original_count = len(_self.notes_df)
                _self.notes_df = _self.notes_df[_self.notes_df['ip_note_type'] == 'Progress Notes'].copy()
                print(f"Filtered to Progress Notes: {len(_self.notes_df):,} / {original_count:,}")
            
            # Convert maskedid to string for consistent matching
            if 'maskedid' in _self.annotations_df.columns:
                _self.annotations_df['maskedid'] = _self.annotations_df['maskedid'].astype(str).str.strip()
            if 'maskedid' in _self.cross_df.columns:
                _self.cross_df['maskedid'] = _self.cross_df['maskedid'].astype(str).str.strip()
            
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"
    
    def merge_datasets(self):
        """Merge all datasets and apply filters"""
        
        # Debug: Check preprocessing configuration
        print("=" * 60)
        print("DATASET LOADING DEBUG:")
        print(f"  USE_PREPROCESSED: {USE_PREPROCESSED}")
        print(f"  PREPROCESSED_PATH: {PREPROCESSED_PATH}")
        if PREPROCESSED_PATH:
            print(f"  File exists: {Path(PREPROCESSED_PATH).exists()}")
        print("=" * 60)
        
        # Try to load preprocessed dataset if enabled
        if USE_PREPROCESSED and PREPROCESSED_PATH and Path(PREPROCESSED_PATH).exists():
            try:
                print(f"✅ Loading preprocessed dataset from {PREPROCESSED_PATH}...")
                self.merged_df = pd.read_parquet(PREPROCESSED_PATH)
                print(f"   Loaded {len(self.merged_df):,} rows")
                
                # Convert pat_mrn and maskedid to string in merged_df for consistent matching
                if 'pat_mrn' in self.merged_df.columns:
                    self.merged_df['pat_mrn'] = self.merged_df['pat_mrn'].astype(str).str.strip()
                if 'maskedid' in self.merged_df.columns:
                    self.merged_df['maskedid'] = self.merged_df['maskedid'].astype(str).str.strip()
                
                # DON'T load notes/annotations yet - use lazy loading!
                # They will be loaded only when actually needed
                print("   Using lazy loading for notes and annotations (faster!)")
                
                # Apply filter
                original_count = len(self.merged_df)
                print(f"   Applying filter: {self.filter_mode}")
                self.merged_df = self._apply_dataset_filter_fast(self.merged_df)
                filtered_count = len(self.merged_df)
                print(f"   After filter: {filtered_count:,} rows")
                
                return True, f"✅ Loaded preprocessed data. Filter: {self.filter_mode}. Images: {filtered_count:,}/{original_count:,}"
            except Exception as e:
                print(f"❌ Failed to load preprocessed data: {e}")
                print("   Falling back to regular loading...")
        else:
            print("⚠️  Using regular loading (SLOW)...")
            if not USE_PREPROCESSED:
                print("   Reason: USE_PREPROCESSED is False")
            elif not PREPROCESSED_PATH:
                print("   Reason: PREPROCESSED_PATH is None")
            elif not Path(PREPROCESSED_PATH).exists():
                print(f"   Reason: File does not exist at {PREPROCESSED_PATH}")
                print("   → Run preprocessing/create_preprocessed_dataset.py first!")
        
        # Regular loading (slower) - need all datasets
        if self.diagnosis_df is None or self.notes_df is None or self.cross_df is None or self.annotations_df is None:
            success, message = self.load_data()
            if not success:
                return False, message
        
        try:
            # Merge cross_df with diagnosis_df on maskedid_studyid
            self.merged_df = self.cross_df.merge(
                self.diagnosis_df,
                on='maskedid_studyid',
                how='left',
                suffixes=('', '_diag')
            )
            
            # Handle duplicate columns
            for col in list(self.merged_df.columns):
                if col.endswith('_diag'):
                    original_col = col.replace('_diag', '')
                    if original_col in self.merged_df.columns:
                        self.merged_df[original_col] = self.merged_df[original_col].fillna(self.merged_df[col])
                    else:
                        self.merged_df[original_col] = self.merged_df[col]
                    self.merged_df.drop(col, axis=1, inplace=True)
            
            # Apply dataset filter (WARNING: SLOW without preprocessing!)
            original_count = len(self.merged_df)
            if self.filter_mode != "ALL":
                st.warning("⚠️ Filtering without preprocessed data is SLOW! Consider running preprocessing script.")
                self.merged_df = self._apply_dataset_filter(self.merged_df)
            filtered_count = len(self.merged_df)
            
            return True, f"Datasets merged. Filter: {self.filter_mode}. Images: {filtered_count:,}/{original_count:,}"
        except Exception as e:
            return False, f"Error merging datasets: {str(e)}"
    
    def _apply_dataset_filter_fast(self, df):
        """Apply dataset filter using pre-calculated flags (FAST)"""
        if self.filter_mode == "ALL":
            return df
        
        # Use pre-calculated flags
        if self.filter_mode == "NOTES":
            df = df[df['has_notes']].copy()
        elif self.filter_mode == "ANNOTATIONS":
            df = df[df['has_annotations']].copy()
        elif self.filter_mode == "NOTES_AND_ANNOTATIONS":
            df = df[df['has_notes'] & df['has_annotations']].copy()
        elif self.filter_mode == "WITH_AI_PRELABEL":
            # Filter to only images with AI prelabels
            df = self._apply_ai_prelabel_filter(df)
        
        return df.reset_index(drop=True)
    
    def _ensure_notes_loaded(self):
        """Lazy load notes data only when needed"""
        if not self._notes_loaded:
            try:
                print("   📝 Loading notes for first time (lazy loading)...")
                self.notes_df = pd.read_parquet(NOTES_PATH)
                self.notes_df['note_date'] = pd.to_datetime(self.notes_df['note_date'])
                
                # Convert pat_mrn to string and filter Progress Notes
                if 'pat_mrn' in self.notes_df.columns:
                    self.notes_df['pat_mrn'] = self.notes_df['pat_mrn'].astype(str).str.strip()
                if 'ip_note_type' in self.notes_df.columns:
                    self.notes_df = self.notes_df[self.notes_df['ip_note_type'] == 'Progress Notes'].copy()
                
                # Create indexed version for fast lookups
                self._notes_indexed = self.notes_df.groupby('pat_mrn')
                self._notes_loaded = True
                print(f"   ✅ Notes loaded and indexed ({len(self.notes_df):,} Progress Notes)")
            except Exception as e:
                print(f"   ⚠️  Could not load notes: {e}")
                self._notes_loaded = True  # Don't try again
    
    def _ensure_annotations_loaded(self):
        """Lazy load annotations data only when needed"""
        if not self._annotations_loaded:
            try:
                print("   🔬 Loading annotations for first time (lazy loading)...")
                self.annotations_df = pd.read_csv(ANNOTATIONS_PATH)
                if 'studyid' in self.annotations_df.columns:
                    self.annotations_df.rename(columns={'studyid': 'maskedid'}, inplace=True)
                if 'date' in self.annotations_df.columns:
                    self.annotations_df['annotation_date'] = pd.to_datetime(self.annotations_df['date'])
                
                # Convert maskedid to string
                if 'maskedid' in self.annotations_df.columns:
                    self.annotations_df['maskedid'] = self.annotations_df['maskedid'].astype(str).str.strip()
                
                # Create indexed version for fast lookups
                self._annotations_indexed = self.annotations_df.groupby('maskedid')
                self._annotations_loaded = True
                print(f"   ✅ Annotations loaded and indexed ({len(self.annotations_df):,} records)")
            except Exception as e:
                print(f"   ⚠️  Could not load annotations: {e}")
                self._annotations_loaded = True  # Don't try again
    
    def _apply_dataset_filter(self, df):
        """Apply dataset filter based on configuration"""
        if self.filter_mode == "ALL":
            return df
        
        # Add flags for matching notes and annotations
        df = df.copy()
        df['has_notes'] = False
        df['has_annotations'] = False
        
        for idx, row in df.iterrows():
            # Check for notes
            if pd.notna(row.get('pat_mrn')) and pd.notna(row.get('exam_date')):
                notes = self.get_closest_notes(row['pat_mrn'], row['exam_date'])
                if notes:
                    df.at[idx, 'has_notes'] = True
            
            # Check for annotations
            if pd.notna(row.get('maskedid')) and pd.notna(row.get('exam_date')):
                annotations = self.get_annotations(row['maskedid'], row['exam_date'])
                if annotations:
                    df.at[idx, 'has_annotations'] = True
        
        # Filter based on mode
        if self.filter_mode == "NOTES":
            df = df[df['has_notes']].copy()
        elif self.filter_mode == "ANNOTATIONS":
            df = df[df['has_annotations']].copy()
        elif self.filter_mode == "NOTES_AND_ANNOTATIONS":
            df = df[df['has_notes'] & df['has_annotations']].copy()
        elif self.filter_mode == "WITH_AI_PRELABEL":
            # Filter to only images with AI prelabels
            df = self._apply_ai_prelabel_filter(df)
        
        # Drop the helper columns
        df.drop(['has_notes', 'has_annotations'], axis=1, inplace=True, errors='ignore')
        
        return df.reset_index(drop=True)
    
    def _apply_ai_prelabel_filter(self, df):
        """Filter to only images with AI pre-labels"""
        from config.config import LABELS_DIR
        import json
        
        ai_labels_file = LABELS_DIR / "AI_prelabel_labels.json"
        
        print(f"   [DEBUG] Looking for AI prelabels at: {ai_labels_file}")
        print(f"   [DEBUG] File exists: {ai_labels_file.exists()}")
        
        if not ai_labels_file.exists():
            print("   ⚠️  Warning: AI_prelabel_labels.json not found")
            return df.head(0)  # Return empty dataframe
        
        # Load AI prelabels
        try:
            with open(ai_labels_file, 'r', encoding='utf-8') as f:
                ai_data = json.load(f)
            
            ai_labels = ai_data.get('labels', {})
            ai_image_paths = set(ai_labels.keys())
            
            print(f"   [DEBUG] AI prelabels loaded: {len(ai_image_paths):,} unique image paths")
            
            # Check first few paths
            print(f"   [DEBUG] Sample AI paths (first 3):")
            for i, path in enumerate(list(ai_image_paths)[:3]):
                print(f"      {i+1}. {path}")
            
            # Build image_path for merged_df if it doesn't exist
            if 'image_path' not in df.columns:
                print(f"   [DEBUG] Building image_path column from merged_df...")
                df['image_path'] = df.apply(lambda row: self.get_image_path(row), axis=1)
            
            print(f"   [DEBUG] Sample merged_df paths (first 3):")
            for i, path in enumerate(df['image_path'].head(3)):
                print(f"      {i+1}. {path}")
            
            # Normalize paths: extract from "SlitLamp\" onwards
            def normalize_path(path):
                """Extract path starting from SlitLamp\ onwards"""
                path_str = str(path)
                # Find "SlitLamp" in path (case insensitive)
                import re
                match = re.search(r'SlitLamp[/\\]', path_str, re.IGNORECASE)
                if match:
                    # Extract from SlitLamp onwards
                    normalized = path_str[match.start():]
                    # Normalize separators to backslash and lowercase
                    normalized = normalized.replace('/', '\\').lower()
                    return normalized
                return path_str.lower()
            
            print(f"   [DEBUG] Normalizing paths (from 'SlitLamp\\' onwards)...")
            
            # Normalize AI paths
            ai_paths_normalized = {normalize_path(p): p for p in ai_image_paths}
            
            print(f"   [DEBUG] Sample normalized AI paths (first 3):")
            for i, (norm_path, orig_path) in enumerate(list(ai_paths_normalized.items())[:3]):
                print(f"      {i+1}. {norm_path}")
            
            # Normalize merged_df paths
            df['normalized_path'] = df['image_path'].apply(normalize_path)
            
            print(f"   [DEBUG] Sample normalized merged_df paths (first 3):")
            for i, path in enumerate(df['normalized_path'].head(3)):
                print(f"      {i+1}. {path}")
            
            # Check for matches using normalized paths
            df_paths_normalized = set(df['normalized_path'])
            matches = set(ai_paths_normalized.keys()) & df_paths_normalized
            
            print(f"   [DEBUG] Normalized paths in merged_df: {len(df_paths_normalized):,}")
            print(f"   [DEBUG] Matches found: {len(matches):,}")
            
            if len(matches) == 0:
                print("   ⚠️  No matches found even after normalization")
                # Show sample for debugging
                print(f"   [DEBUG] Sample AI normalized path: {list(ai_paths_normalized.keys())[0] if ai_paths_normalized else 'NONE'}")
                print(f"   [DEBUG] Sample DF normalized path: {list(df_paths_normalized)[0] if df_paths_normalized else 'NONE'}")
                df = df.drop('normalized_path', axis=1)
                return df.head(0)
            
            print(f"   ✅ Filtering to {len(matches):,} images with AI pre-labels")
            
            # Filter dataframe to only images with AI prelabels
            df = df[df['normalized_path'].isin(ai_paths_normalized.keys())].copy()
            df = df.drop('normalized_path', axis=1)
            
            return df
        
        except Exception as e:
            print(f"   ❌ Error loading AI prelabels: {e}")
            import traceback
            traceback.print_exc()
            return df.head(0)
    
    def get_closest_notes(self, pat_mrn, exam_date):
        """
        Get the closest note(s) to the exam date
        Returns: list of dicts with note information
        """
        # Lazy load notes if needed
        self._ensure_notes_loaded()
        
        if self.notes_df is None or self._notes_indexed is None:
            return []
        
        # Use indexed lookup (MUCH faster than filtering!)
        if pat_mrn not in self._notes_indexed.groups:
            return []
        
        patient_notes = self._notes_indexed.get_group(pat_mrn).copy()
        
        if patient_notes.empty:
            return []
        
        # Calculate days difference
        patient_notes['days_diff'] = (patient_notes['note_date'] - exam_date).dt.days
        patient_notes['abs_days_diff'] = patient_notes['days_diff'].abs()
        
        # Filter notes within max days difference
        patient_notes = patient_notes[
            patient_notes['abs_days_diff'] <= MAX_NOTE_DAYS_DIFFERENCE
        ]
        
        if patient_notes.empty:
            return []
        
        # Find the closest note(s)
        min_diff = patient_notes['abs_days_diff'].min()
        closest_notes = patient_notes[patient_notes['abs_days_diff'] == min_diff]
        
        # Check if exam_date is between two notes
        notes_before = patient_notes[patient_notes['days_diff'] < 0].sort_values('days_diff', ascending=False)
        notes_after = patient_notes[patient_notes['days_diff'] > 0].sort_values('days_diff', ascending=True)
        
        result = []
        
        if not notes_before.empty and not notes_after.empty:
            # Exam date is between notes, return both closest before and after
            result.append({
                'note_id': notes_before.iloc[0]['note_id'],
                'note_date': notes_before.iloc[0]['note_date'],
                'note_text': notes_before.iloc[0]['note_text'],
                'days_diff': int(notes_before.iloc[0]['days_diff']),
                'position': 'before'
            })
            result.append({
                'note_id': notes_after.iloc[0]['note_id'],
                'note_date': notes_after.iloc[0]['note_date'],
                'note_text': notes_after.iloc[0]['note_text'],
                'days_diff': int(notes_after.iloc[0]['days_diff']),
                'position': 'after'
            })
        else:
            # Return the single closest note
            for _, note in closest_notes.iterrows():
                result.append({
                    'note_id': note['note_id'],
                    'note_date': note['note_date'],
                    'note_text': note['note_text'],
                    'days_diff': int(note['days_diff']),
                    'position': 'before' if note['days_diff'] < 0 else 'after' if note['days_diff'] > 0 else 'same_day'
                })
        
        return result
    
    def get_annotations(self, maskedid, exam_date):
        """
        Get annotations for a specific maskedid within date range
        Returns: list of dicts with annotation information
        """
        # Lazy load annotations if needed
        self._ensure_annotations_loaded()
        
        if self.annotations_df is None or self._annotations_indexed is None:
            return []
        
        # Use indexed lookup (MUCH faster!)
        if maskedid not in self._annotations_indexed.groups:
            return []
        
        patient_annotations = self._annotations_indexed.get_group(maskedid).copy()
        
        if patient_annotations.empty:
            return []
        
        # Calculate days difference
        patient_annotations['days_diff'] = (
            patient_annotations['annotation_date'] - exam_date
        ).dt.days
        patient_annotations['abs_days_diff'] = patient_annotations['days_diff'].abs()
        
        # Filter annotations within max days difference (1 week)
        patient_annotations = patient_annotations[
            patient_annotations['abs_days_diff'] <= MAX_ANNOTATION_DAYS_DIFFERENCE
        ]
        
        if patient_annotations.empty:
            return []
        
        # Get the closest annotation date
        min_diff = patient_annotations['abs_days_diff'].min()
        closest_annotations = patient_annotations[
            patient_annotations['abs_days_diff'] == min_diff
        ]
        
        # Group by examfield and value for the closest date
        result = []
        for _, annotation in closest_annotations.iterrows():
            result.append({
                'examfield': annotation.get('examfield', 'Unknown'),
                'value': annotation.get('value', 'N/A'),
                'annotation_date': annotation['annotation_date'],
                'days_diff': int(annotation['days_diff']),
                'laterality': annotation.get('laterality', 'Unknown')
            })
        
        return result
    
    def get_image_path(self, row):
        """Construct the full image path"""
        path = Path(IMAGE_BASE_PATH) / row['maskedid'] / row['maskedid_studyid'] / row['proc_name'] / row['photo_name']
        return str(path)
    
    def get_image_data(self, index):
        """
        Get all data for a specific image
        Returns: dict with image path and metadata
        """
        if self.merged_df is None:
            success, message = self.merge_datasets()
            if not success:
                return None, message
        
        if index < 0 or index >= len(self.merged_df):
            return None, "Index out of range"
        
        row = self.merged_df.iloc[index]
        
        # Get closest notes
        notes = []
        if pd.notna(row['pat_mrn']) and pd.notna(row['exam_date']):
            notes = self.get_closest_notes(row['pat_mrn'], row['exam_date'])
        
        # Get annotations
        annotations = []
        if pd.notna(row['maskedid']) and pd.notna(row['exam_date']):
            annotations = self.get_annotations(row['maskedid'], row['exam_date'])
        
        # Construct image path
        image_path = self.get_image_path(row)
        
        # Calculate studyid counter (X/Y format)
        maskedid_studyid = row.get('maskedid_studyid')
        studyid_counter = None
        if maskedid_studyid:
            same_studyid = self.merged_df[self.merged_df['maskedid_studyid'] == maskedid_studyid]
            studyid_total = len(same_studyid)
            studyid_indices = same_studyid.index.tolist()
            if index in studyid_indices:
                studyid_current = studyid_indices.index(index) + 1
                studyid_counter = f"{studyid_current}/{studyid_total}"
        
        data = {
            'index': index,
            'image_path': image_path,
            'maskedid': row.get('maskedid'),
            'maskedid_studyid': maskedid_studyid,
            'studyid_counter': studyid_counter,
            'proc_name': row.get('proc_name'),
            'photo_name': row.get('photo_name'),
            'pat_mrn': row.get('pat_mrn'),
            'exam_date': row.get('exam_date'),
            'laterality': row.get('laterality'),
            'main_diagnosis': row.get('main_diagnosis'),
            'order_diagnosis': row.get('order_diagnosis'),
            'notes': notes,
            'annotations': annotations
        }
        
        return data, "Success"
    
    def get_total_images(self):
        """Get total number of images"""
        if self.merged_df is None:
            self.merge_datasets()
        return len(self.merged_df) if self.merged_df is not None else 0
    
    def create_route(self, total_images, strategy="forward", username=None):
        """
        Create a route/sequence for labeling based on strategy
        
        Args:
            total_images: Total number of images
            strategy: Routing strategy
            username: Username for seeding random routes
        
        Returns:
            List of indices in the desired order
        """
        import numpy as np
        from config.config import PRELABEL_SIXTH_STRATEGIES

        indices = list(range(total_images))

        def _slice_part(seq, part, total_parts):
            """Return the `part`-th (1-indexed) contiguous slice of `seq` out of `total_parts`."""
            length = len(seq)
            start = ((part - 1) * length) // total_parts
            end = (part * length) // total_parts
            return seq[start:end], start, end

        prelabel_strategies = (
            ["prelabel_first", "prelabel_first_third", "prelabel_second_third", "prelabel_last_third"]
            + list(PRELABEL_SIXTH_STRATEGIES.keys())
        )

        # ── Strategies that work with AI prelabels ──────────────
        if strategy in prelabel_strategies:

            # If we're already filtered to WITH_AI_PRELABEL, all indices have prelabels
            if self.filter_mode == "WITH_AI_PRELABEL":
                total_prelabeled = len(indices)
                
                if strategy == "prelabel_first":
                    print(f"   Route 'prelabel_first': All {total_prelabeled:,} images already filtered to prelabels")
                    return indices
                
                elif strategy == "prelabel_first_third":
                    end_idx = total_prelabeled // 3
                    route = indices[:end_idx]
                    print(f"   Route 'prelabel_first_third': {len(route):,} images (1 - {end_idx:,} of {total_prelabeled:,} prelabeled)")
                    return route
                
                elif strategy == "prelabel_second_third":
                    start_idx = total_prelabeled // 3
                    end_idx = (total_prelabeled * 2) // 3
                    route = indices[start_idx:end_idx]
                    print(f"   Route 'prelabel_second_third': {len(route):,} images ({start_idx:,} - {end_idx:,} of {total_prelabeled:,} prelabeled)")
                    return route
                
                elif strategy == "prelabel_last_third":
                    start_idx = (total_prelabeled * 2) // 3
                    route = indices[start_idx:]
                    print(f"   Route 'prelabel_last_third': {len(route):,} images ({start_idx:,} - {total_prelabeled:,} of {total_prelabeled:,} prelabeled)")
                    return route

                elif strategy in PRELABEL_SIXTH_STRATEGIES:
                    part = PRELABEL_SIXTH_STRATEGIES[strategy]
                    route, start_idx, end_idx = _slice_part(indices, part, 6)
                    print(f"   Route '{strategy}': {len(route):,} images ({start_idx:,} - {end_idx:,} of {total_prelabeled:,} prelabeled)")
                    return route

            # If NOT filtered, need to find prelabels manually
            from config.config import LABELS_DIR
            import json
            
            ai_labels_file = LABELS_DIR / "AI_prelabel_labels.json"
            
            if not ai_labels_file.exists():
                print(f"   Warning: AI_prelabel_labels.json not found, using forward strategy")
                return indices
            
            try:
                # Load AI prelabels
                with open(ai_labels_file, 'r', encoding='utf-8') as f:
                    ai_data = json.load(f)
                
                ai_labels = ai_data.get('labels', {})
                ai_image_paths = set(ai_labels.keys())
                
                # Build image paths if needed
                if self.merged_df is not None and 'image_path' not in self.merged_df.columns:
                    self.merged_df['image_path'] = self.merged_df.apply(
                        lambda row: self.get_image_path(row), axis=1
                    )
                
                # Normalize paths for comparison
                import re
                def normalize_path(path):
                    path_str = str(path)
                    match = re.search(r'SlitLamp[/\\]', path_str, re.IGNORECASE)
                    if match:
                        normalized = path_str[match.start():]
                        normalized = normalized.replace('/', '\\').lower()
                        return normalized
                    return path_str.lower()
                
                ai_paths_normalized = {normalize_path(p) for p in ai_image_paths}
                
                # Find indices with prelabels
                prelabeled_indices = []
                other_indices = []
                
                for idx in indices:
                    if self.merged_df is not None and idx < len(self.merged_df):
                        image_path = self.merged_df.iloc[idx].get('image_path')
                        normalized = normalize_path(image_path)
                        if normalized in ai_paths_normalized:
                            prelabeled_indices.append(idx)
                        else:
                            other_indices.append(idx)
                    else:
                        other_indices.append(idx)
                
                total_prelabeled = len(prelabeled_indices)
                
                # ── Apply strategy ──────────────────────────────
                if strategy == "prelabel_first":
                    route = prelabeled_indices + other_indices
                    print(f"   Route 'prelabel_first': {len(prelabeled_indices):,} with pre-labels, {len(other_indices):,} without")
                    return route
                
                elif strategy == "prelabel_first_third":
                    end_idx = total_prelabeled // 3
                    route = prelabeled_indices[:end_idx]
                    print(f"   Route 'prelabel_first_third': {len(route):,} images (1 - {end_idx:,} of {total_prelabeled:,} prelabeled)")
                    return route
                
                elif strategy == "prelabel_second_third":
                    start_idx = total_prelabeled // 3
                    end_idx = (total_prelabeled * 2) // 3
                    route = prelabeled_indices[start_idx:end_idx]
                    print(f"   Route 'prelabel_second_third': {len(route):,} images ({start_idx:,} - {end_idx:,} of {total_prelabeled:,} prelabeled)")
                    return route
                
                elif strategy == "prelabel_last_third":
                    start_idx = (total_prelabeled * 2) // 3
                    route = prelabeled_indices[start_idx:]
                    print(f"   Route 'prelabel_last_third': {len(route):,} images ({start_idx:,} - {total_prelabeled:,} of {total_prelabeled:,} prelabeled)")
                    return route

                elif strategy in PRELABEL_SIXTH_STRATEGIES:
                    part = PRELABEL_SIXTH_STRATEGIES[strategy]
                    route, start_idx, end_idx = _slice_part(prelabeled_indices, part, 6)
                    print(f"   Route '{strategy}': {len(route):,} images ({start_idx:,} - {end_idx:,} of {total_prelabeled:,} prelabeled)")
                    return route

            except Exception as e:
                print(f"   Warning: Could not load AI prelabels for routing: {e}")
                import traceback
                traceback.print_exc()
                return indices
        
        # ── Other strategies ────────────────────────────────────
        elif strategy == "forward":
            return indices
        
        elif strategy == "backward":
            return list(reversed(indices))
        
        elif strategy == "middle_out":
            middle = total_images // 2
            route = [middle]
            left = middle - 1
            right = middle + 1
            
            while left >= 0 or right < total_images:
                if right < total_images:
                    route.append(right)
                    right += 1
                if left >= 0:
                    route.append(left)
                    left -= 1
            
            return route
        
        elif strategy == "random":
            seed = hash(username) % (2**32) if username else 42
            rng = np.random.RandomState(seed)
            route = indices.copy()
            rng.shuffle(route)
            return route
        
        else:
            return indices
            success, message = self.merge_datasets()
            if not success:
                return 0
        return len(self.merged_df)
    
    def get_route_indices(self, strategy, username, total_images):
        """
        Get the sequence of indices based on route strategy
        """
        if strategy == "forward":
            return list(range(total_images))
        elif strategy == "backward":
            return list(range(total_images - 1, -1, -1))
        elif strategy == "middle_out":
            middle = total_images // 2
            indices = []
            for i in range(total_images):
                if i % 2 == 0:
                    indices.append(middle + i // 2)
                else:
                    indices.append(middle - (i + 1) // 2)
            return [i for i in indices if 0 <= i < total_images]
        elif strategy == "random":
            # Use username as seed for reproducibility
            seed = sum(ord(c) for c in username)
            np.random.seed(seed)
            indices = list(range(total_images))
            np.random.shuffle(indices)
            return indices
        else:
            return list(range(total_images))
