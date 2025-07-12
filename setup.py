from setuptools import setup
import sys
import traceback

APP = ['TTSDeckSlicer.py']
OPTIONS = {
    'argv_emulation': True,
    'includes': ['PIL.Image', 'PIL.ImageQt'],
    'packages': ['PyQt6', 'PIL'],
    'resources': ['icon.icns'],
    'plist': {
        'CFBundleName': 'TTS Deck Slicer',
        'CFBundleIconFile': 'icon',
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
