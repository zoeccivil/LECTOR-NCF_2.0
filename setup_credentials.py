#!/usr/bin/env python3
"""
Local Development Credential Setup Script
Interactive GUI for configuring Firebase and Google Cloud Vision credentials
"""
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import json
import shutil
import sys
from pathlib import Path


def validate_json_file(file_path: str) -> bool:
    """Validate that a file is valid JSON"""
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except Exception as e:
        print(f"❌ Invalid JSON file: {e}")
        return False


def select_file(title: str, root: tk.Tk) -> str:
    """Open file dialog to select a JSON file"""
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        parent=root
    )
    return file_path


def setup_credentials():
    """Main setup function with GUI"""
    # Create hidden root window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    print("🔧 LECTOR-NCF - Local Credential Setup")
    print("=" * 50)
    print()
    
    # Create credentials directory if it doesn't exist
    cred_dir = Path("credentials")
    cred_dir.mkdir(exist_ok=True)
    print("✅ Created credentials/ directory")
    
    # Step 1: Select Firebase credentials
    print("\n📁 Step 1: Select Firebase credentials JSON file")
    messagebox.showinfo(
        "Firebase Credentials",
        "Please select your Firebase credentials JSON file.\n\n"
        "This file is downloaded from:\n"
        "Firebase Console → Project Settings → Service Accounts",
        parent=root
    )
    
    firebase_path = select_file("Select Firebase Credentials JSON", root)
    if not firebase_path:
        print("❌ No Firebase file selected. Setup cancelled.")
        root.destroy()
        return False
    
    if not validate_json_file(firebase_path):
        messagebox.showerror(
            "Invalid File",
            "The selected Firebase credentials file is not valid JSON.",
            parent=root
        )
        root.destroy()
        return False
    
    # Copy Firebase credentials
    firebase_dest = cred_dir / "firebase-credentials.json"
    shutil.copy2(firebase_path, firebase_dest)
    print(f"✅ Firebase credentials copied to: {firebase_dest}")
    
    # Step 2: Select Google Vision credentials
    print("\n📁 Step 2: Select Google Cloud Vision credentials JSON file")
    use_same = messagebox.askyesno(
        "Google Vision Credentials",
        "Do you want to use the same credentials for Google Cloud Vision?\n\n"
        "(If your Firebase service account has Vision API enabled, select Yes)",
        parent=root
    )
    
    if use_same:
        vision_dest = cred_dir / "google-vision-credentials.json"
        shutil.copy2(firebase_path, vision_dest)
        print(f"✅ Using same credentials for Google Vision: {vision_dest}")
    else:
        messagebox.showinfo(
            "Google Vision Credentials",
            "Please select your Google Cloud Vision credentials JSON file.\n\n"
            "This file is downloaded from:\n"
            "Google Cloud Console → IAM → Service Accounts",
            parent=root
        )
        
        vision_path = select_file("Select Google Vision Credentials JSON", root)
        if not vision_path:
            print("❌ No Google Vision file selected. Setup cancelled.")
            root.destroy()
            return False
        
        if not validate_json_file(vision_path):
            messagebox.showerror(
                "Invalid File",
                "The selected Google Vision credentials file is not valid JSON.",
                parent=root
            )
            root.destroy()
            return False
        
        vision_dest = cred_dir / "google-vision-credentials.json"
        shutil.copy2(vision_path, vision_dest)
        print(f"✅ Google Vision credentials copied to: {vision_dest}")
    
    # Step 3: Get Firebase Database URL
    print("\n🔗 Step 3: Enter Firebase Database URL")
    database_url = simpledialog.askstring(
        "Firebase Database URL",
        "Enter your Firebase Realtime Database URL:\n\n"
        "(Example: https://your-project-default-rtdb.firebaseio.com/)",
        initialvalue="https://facot-app-default-rtdb.firebaseio.com/",
        parent=root
    )
    
    if not database_url:
        database_url = "https://facot-app-default-rtdb.firebaseio.com/"
        print(f"⚠️  Using default database URL: {database_url}")
    else:
        print(f"✅ Database URL: {database_url}")
    
    # Step 4: Generate .env file
    print("\n📝 Step 4: Generating .env file")
    env_content = f"""# Firebase Configuration
FIREBASE_CREDENTIALS=credentials/firebase-credentials.json
FIREBASE_DATABASE_URL={database_url}

# Google Cloud Vision Configuration
GOOGLE_APPLICATION_CREDENTIALS=credentials/google-vision-credentials.json

# Twilio Configuration (Optional - configure if using Twilio)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Green-API Configuration (Optional - configure if using Green-API)
GREENAPI_INSTANCE_ID=
GREENAPI_TOKEN=

# WhatsApp Mode (twilio, greenapi, or dual)
WHATSAPP_MODE=dual

# Application Configuration
DEBUG=False
PORT=8000
LOG_LEVEL=INFO
"""
    
    env_path = Path(".env")
    with open(env_path, 'w') as f:
        f.write(env_content)
    print(f"✅ .env file created: {env_path}")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("=" * 50)
    print("\nConfigured files:")
    print(f"  ✅ {firebase_dest}")
    print(f"  ✅ {vision_dest}")
    print(f"  ✅ {env_path}")
    print("\nNext steps:")
    print("  1. Run: python setup_credentials.py verify")
    print("  2. Run: uvicorn app.main:app --reload")
    print("  3. Open: http://localhost:8000")
    print()
    
    messagebox.showinfo(
        "Setup Complete! ✅",
        "Credentials configured successfully!\n\n"
        "Next steps:\n"
        "1. Run: python setup_credentials.py verify\n"
        "2. Run: uvicorn app.main:app --reload\n"
        "3. Open: http://localhost:8000",
        parent=root
    )
    
    root.destroy()
    return True


def verify_credentials():
    """Verify that all credential files exist"""
    print("🔍 Verifying credentials...")
    print("=" * 50)
    
    files_to_check = [
        "credentials/firebase-credentials.json",
        "credentials/google-vision-credentials.json",
        ".env"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - NOT FOUND")
            all_exist = False
    
    print("=" * 50)
    if all_exist:
        print("✅ All credential files are present!")
        print("\nYou can now run:")
        print("  uvicorn app.main:app --reload")
    else:
        print("❌ Some credential files are missing.")
        print("\nPlease run setup:")
        print("  python setup_credentials.py")
    
    return all_exist


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        # Verify mode
        verify_credentials()
    else:
        # Setup mode
        try:
            setup_credentials()
        except Exception as e:
            print(f"\n❌ Error during setup: {e}")
            print("\nPlease try again or check the error message above.")
            sys.exit(1)


if __name__ == "__main__":
    main()
