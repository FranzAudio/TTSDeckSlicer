from setuptools import setup
import sys
import traceback

VERSION = "1.2"

APP = ['TTSDeckSlicer.py']
OPTIONS = {
    'argv_emulation': True,
    'includes': ['PIL.Image', 'PIL.ImageQt'],
    'packages': ['PyQt6', 'PIL'],
    'resources': ['icon.icns'],
    'plist': {
        'CFBundleName': 'TTS Deck Slicer',
        'CFBundleIconFile': 'icon',
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
