"""
Data loader module for handling medical imaging data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st
from config.config import (
    DIAGNOSIS_PATH,
    NOTES_PATH,
    CROSS_PATH,
    IMAGE_BASE_PATH,
    MAX_NOTE_DAYS_DIFFERENCE
)

class DataLoader:
    """Class to handle loading and merging of all datasets"""
    
    def __init__(self):
        self.diagnosis_df = None
        self.notes_df = None
        self.cross_df = None
        self.merged_df = None
        
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
            
            # Convert date columns to datetime
            _self.diagnosis_df['exam_date'] = pd.to_datetime(_self.diagnosis_df['exam_date'])
            _self.notes_df['note_date'] = pd.to_datetime(_self.notes_df['note_date'])
            
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"
    
    def merge_datasets(self):
        """Merge all datasets"""
        if self.diagnosis_df is None or self.notes_df is None or self.cross_df is None:
            success, message = self.load_data()
            if not success:
                return False, message
        
        try:
            # Merge cross_df with diagnosis_df on maskedid_studyid
            self.merged_df = self.cross_df.merge(
                self.diagnosis_df,
                on='maskedid_studyid',
                how='left'
            )
            
            return True, "Datasets merged successfully"
        except Exception as e:
            return False, f"Error merging datasets: {str(e)}"
    
    def get_closest_notes(self, pat_mrn, exam_date):
        """
        Get the closest note(s) to the exam date
        Returns: list of dicts with note information
        """
        if self.notes_df is None:
            return []
        
        # Filter notes for this patient
        patient_notes = self.notes_df[self.notes_df['pat_mrn'] == pat_mrn].copy()
        
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
        
        # Construct image path
        image_path = self.get_image_path(row)
        
        data = {
            'index': index,
            'image_path': image_path,
            'maskedid': row.get('maskedid'),
            'maskedid_studyid': row.get('maskedid_studyid'),
            'proc_name': row.get('proc_name'),
            'photo_name': row.get('photo_name'),
            'pat_mrn': row.get('pat_mrn'),
            'exam_date': row.get('exam_date'),
            'laterality': row.get('laterality'),
            'main_diagnosis': row.get('main_diagnosis'),
            'order_diagnosis': row.get('order_diagnosis'),
            'notes': notes
        }
        
        return data, "Success"
    
    def get_total_images(self):
        """Get total number of images"""
        if self.merged_df is None:
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
