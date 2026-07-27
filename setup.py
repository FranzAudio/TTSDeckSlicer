"""py2app configuration for the macOS application bundle."""

import sys

from setuptools import setup

# Version and application metadata
VERSION = "1.5.0"
APP_NAME = "TTS Deck Slicer"

# Validate Python version
if sys.version_info < (3, 9):
    sys.exit("Python 3.9 or higher is required")

APP = ["TTSDeckSlicer.py"]
# Configure build options
OPTIONS = {
    # We handle argv ourselves; no AppleEvent argv-emulation needed
    "argv_emulation": False,
    # Essential includes for image processing and UI
    "includes": [
        "PIL.Image",
        "PIL.ImageQt",
    ],
    # Required packages
    "packages": [
        "PyQt6",
        "PIL",
    ],
    # Exclude unnecessary packages to reduce size
    "excludes": [
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
    ],
    # Application metadata
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.franzaudio.ttsdeckslicer",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
}

setup(
    name="TTSDeckSlicer",
    version=VERSION,
    app=APP,
    options={"py2app": OPTIONS},
)
