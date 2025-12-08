"""
Initialization script to set up the application
Run this once after installation to create necessary directories
"""

import os
from pathlib import Path

def initialize_app():
    """Create necessary directories and files"""
    
    print("🚀 Initializing Slitlamp Labeling Application...")
    
    # Get base directory
    base_dir = Path(__file__).parent
    
    # Create directories
    directories = [
        base_dir / "data",
        base_dir / "data" / "labels",
        base_dir / "data" / "users",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Initialize users file
    from utils.auth import initialize_users_file
    users_file = initialize_users_file()
    print(f"✓ Initialized users file: {users_file}")
    
    print("\n✅ Application initialized successfully!")
    print("\n📝 Next steps:")
    print("1. Edit config/config.py with your data paths")
    print("2. Run: streamlit run app.py")
    print("3. Login with admin/admin123")
    print("4. Change the default admin password!")
    print("\n🔒 Default admin credentials:")
    print("   Username: admin")
    print("   Password: admin123")

if __name__ == "__main__":
    initialize_app()
