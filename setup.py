from setuptools import setup
import py2app
import os
import sys

# Version and application metadata
VERSION = "1.2"
APP_NAME = "TTS Deck Slicer"

# Validate Python version
if sys.version_info < (3, 8):
    sys.exit('Python 3.8 or higher is required')

APP = ['TTSDeckSlicer.py']
# Configure build options
OPTIONS = {
    # We handle argv ourselves; no AppleEvent argv-emulation needed
    'argv_emulation': False,
    
    # Essential includes for image processing and UI
    'includes': [
        'PIL.Image', 
        'PIL.ImageQt',
    ],
    
    # Required packages
    'packages': [
        'PyQt6',
        'PIL',
    ],
    
    # Exclude unnecessary packages to reduce size
    'excludes': [
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
    ],
    
    # Application metadata
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': 'com.franzaudio.ttsdeckslicer',
        'CFBundleIconFile': 'icon',
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
    }
}

setup(
    app=APP,
    data_files=['icon.png'],  # Include the icon file
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'PyQt6',
        'Pillow',
    ],
)
