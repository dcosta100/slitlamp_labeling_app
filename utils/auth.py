"""
Authentication module for user management
"""

import json
import hashlib
import streamlit as st
from pathlib import Path
from datetime import datetime
from config.config import (
    USERS_CONFIG_FILE,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD
)

def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def initialize_users_file():
    """Initialize users configuration file with default admin"""
    if not USERS_CONFIG_FILE.exists():
        users = {
            "users": {
                DEFAULT_ADMIN_USERNAME: {
                    "password": hash_password(DEFAULT_ADMIN_PASSWORD),
                    "role": "admin",
                    "created_at": datetime.now().isoformat(),
                    "route_strategy": "forward"
                }
            }
        }
        with open(USERS_CONFIG_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    return USERS_CONFIG_FILE

def load_users():
    """Load users from configuration file"""
    initialize_users_file()
    with open(USERS_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_users(users_data):
    """Save users to configuration file"""
    with open(USERS_CONFIG_FILE, 'w') as f:
        json.dump(users_data, f, indent=2)

def authenticate_user(username: str, password: str) -> tuple:
    """
    Authenticate a user
    Returns: (success: bool, role: str, message: str)
    """
    users_data = load_users()
    users = users_data.get("users", {})
    
    if username not in users:
        return False, None, "Username not found"
    
    user = users[username]
    hashed_password = hash_password(password)
    
    if user["password"] != hashed_password:
        return False, None, "Incorrect password"
    
    return True, user["role"], "Login successful"

def create_user(username: str, password: str, role: str = "labeler", route_strategy: str = "forward") -> tuple:
    """
    Create a new user
    Returns: (success: bool, message: str)
    """
    users_data = load_users()
    users = users_data.get("users", {})
    
    if username in users:
        return False, "Username already exists"
    
    users[username] = {
        "password": hash_password(password),
        "role": role,
        "created_at": datetime.now().isoformat(),
        "route_strategy": route_strategy
    }
    
    users_data["users"] = users
    save_users(users_data)
    
    return True, "User created successfully"

def get_user_route_strategy(username: str) -> str:
    """Get the route strategy for a user"""
    users_data = load_users()
    users = users_data.get("users", {})
    return users.get(username, {}).get("route_strategy", "forward")

def update_user_route_strategy(username: str, strategy: str) -> bool:
    """Update the route strategy for a user"""
    users_data = load_users()
    users = users_data.get("users", {})
    
    if username in users:
        users[username]["route_strategy"] = strategy
        users_data["users"] = users
        save_users(users_data)
        return True
    return False

def get_all_users():
    """Get all users (excluding passwords)"""
    users_data = load_users()
    users = users_data.get("users", {})
    
    result = {}
    for username, user_info in users.items():
        result[username] = {
            "role": user_info["role"],
            "created_at": user_info["created_at"],
            "route_strategy": user_info.get("route_strategy", "forward")
        }
    return result

def initialize_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'labels_saved' not in st.session_state:
        st.session_state.labels_saved = 0
    if 'review_queue' not in st.session_state:
        st.session_state.review_queue = []
