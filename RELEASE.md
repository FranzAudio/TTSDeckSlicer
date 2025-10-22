# Release Process

This document describes how to create a new release of TTS Deck Slicer.

## Prerequisites

- Ensure all code changes are committed and pushed
- All version numbers must be consistent across files
- Release notes should be up to date

## Version Numbers

Version numbers should be updated in the following files:

1. `TTSDeckSlicer.py` - `__version__` variable (line 24)
2. `setup.py` - `VERSION` variable (line 5)
3. `RELEASE_NOTES.md` - Release notes header

## Creating a Release

### 1. Update Version Numbers

Update the version in both files to match:
```python
# In TTSDeckSlicer.py
__version__ = "X.Y"

# In setup.py
VERSION = "X.Y"
```

### 2. Update Release Notes

Edit `RELEASE_NOTES.md` to include:
- Version number in the header
- New features and improvements
- Bug fixes
- Technical improvements

### 3. Commit Changes

```bash
git add TTSDeckSlicer.py setup.py RELEASE_NOTES.md
git commit -m "Bump version to vX.Y"
git push
```

### 4. Create Git Tag

```bash
git tag -a vX.Y -m "Version X.Y - Brief description"
git push origin vX.Y
```

### 5. Build the Application

For macOS:
```bash
python3 setup.py py2app
```

This will create the application bundle in the `dist/` directory.

### 6. Create GitHub Release

1. Go to https://github.com/FranzAudio/TTSDeckSlicer/releases/new
2. Select the tag you just created (vX.Y)
3. Set the release title: "TTS Deck Slicer vX.Y"
4. Copy the release notes from RELEASE_NOTES.md
5. Upload the built application (zip the .app bundle first)
6. Publish the release

## Current Version

- **Version 1.2** - Ready for release
- Release notes are in `RELEASE_NOTES.md`
- Git tag `v1.2` exists in the repository

### Next Steps for v1.2 Release:

Since the code is already at version 1.2 and the git tag exists, you need to:

1. Build the application:
   ```bash
   python3 setup.py py2app
   cd dist
   zip -r TTS_Deck_Slicer_v1.2.zip "TTS Deck Slicer.app"
   ```

2. Create the GitHub release:
   - Go to: https://github.com/FranzAudio/TTSDeckSlicer/releases/new
   - Choose tag: v1.2
   - Release title: "TTS Deck Slicer v1.2"
   - Description: Copy content from RELEASE_NOTES.md
   - Upload: TTS_Deck_Slicer_v1.2.zip
   - Click "Publish release"

## Tips

- Test the built application before releasing
- Keep release notes clear and user-friendly
- Include migration notes if there are breaking changes
- Use semantic versioning (MAJOR.MINOR.PATCH)
