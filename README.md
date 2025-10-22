# TTS Deck Slicer

**TTS Deck Slicer** is a powerful desktop app that slices an image into a grid of tiles — perfect for preparing card decks for Tabletop Simulator (TTS) or any virtual tabletop. Features integrated ArkhamDB card search for easy tile naming.

## ✨ Features

- 🖼️ Load standard image formats (JPG, PNG, WebP, BMP, GIF, TIFF)
- 🔢 Choose number of columns and rows (default 10×7)
- 🧮 Live preview with grid overlay and zoom lens (hold Alt/Option)
- 🃏 **ArkhamDB Integration**: Search and select cards from ArkhamDB to name tiles
- � **Browser Authentication**: Secure login to ArkhamDB using embedded browser
- �🔁 Toggle between front/back tiles with flexible back image handling
- 📁 Export to a chosen folder with customizable naming
- 🧾 Smart output filenames: `CardName[A].jpg` or `tile03-01[A].jpg`
- 💾 Undo/Redo functionality for tile naming
- 📋 Export/Import tile names as CSV
- 🧱 Built with Python 3 + PyQt6

## 🚀 How to Use

### Basic Usage

1. Launch the app
2. Click or drag & drop to load your front image (and optionally back image)
3. Adjust the grid size using the column/row spinboxes
4. Hold **Alt/Option** and move your mouse over the image to see a zoomed preview of tiles
5. Click on any tile to name it (either manually or via ArkhamDB search)
6. Select output folder and click **Split Images**

### ArkhamDB Integration

1. Enable ArkhamDB integration via **Edit → ArkhamDB Integration → Enable ArkhamDB Integration**
2. Click **Edit → ArkhamDB Integration → Log in to ArkhamDB...** to authenticate
3. An embedded browser will open - log in with your ArkhamDB credentials
4. Once authenticated, clicking on tiles will open the ArkhamDB card search dialog
5. Search for cards by name, faction, or type and select the matching card

**Note**: Currently, spoiler cards require OAuth2 authentication which is not yet available to third-party applications. The integration provides access to public ArkhamDB cards (1700+) but not spoiler-protected content.

## 🛠️ Development

### Requirements

- Python 3.8+
- PyQt6
- PyQt6-WebEngine (for ArkhamDB login)
- Pillow (PIL)
- requests

### Installation

```bash
pip install PyQt6 PyQt6-WebEngine Pillow requests
```

### Building (macOS)

```bash
python3 setup.py py2app
```
