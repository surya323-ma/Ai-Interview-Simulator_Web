#!/usr/bin/env python3
"""
Setup script - Run this first to install all dependencies
"""

import subprocess
import sys

def install_dependencies():
    """Install all required packages."""
    print("=" * 60)
    print("AI INTERVIEW SIMULATOR - DEPENDENCY INSTALLER")
    print("=" * 60)
    
    packages = [
        "opencv-python>=4.8.0",
        "mediapipe>=0.10.0",
        "numpy>=1.24.0",
        "SpeechRecognition>=3.10.0",
        "pyttsx3>=2.90",
        "sounddevice>=0.4.6",
        "scipy>=1.11.0",
    ]
    
    for package in packages:
        print(f"\nInstalling {package}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "-q"
            ])
            print(f"  ✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to install {package}: {e}")
            print("    Try: pip install " + package)
    
    print("\n" + "=" * 60)
    print("Setup complete! Run: python main.py")
    print("=" * 60)

if __name__ == "__main__":
    install_dependencies()
