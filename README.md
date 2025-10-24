# TTS Deck Slicer

**TTS Deck Slicer** is a powerful desktop app that slices an image into a grid of tiles — perfect for preparing card decks for Tabletop Simulator (TTS) or any virtual tabletop. Features integrated ArkhamDB card search for easy tile naming.

## ✨ Features

- 🖼️ Load standard image formats (JPG, PNG, WebP, BMP, GIF, TIFF)
- 🔢 Choose number of columns and rows (default 10×7)
- 🧮 Live preview with grid overlay and zoom lens (hold Alt/Option)
- 🃏 **ArkhamDB Integration**: Search and select cards from ArkhamDB to name tiles
- 🔁 Toggle between front/back tiles with flexible back image handling
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
2. Click any tile, then use the ArkhamDB search dialog to find the matching card
3. Filter results with the "Include encounter cards" checkbox when needed
4. Select a card to autofill the tile name (with optional card code prefix)

**Note**: Spoiler-protected cards still require ArkhamDB authentication, which is not available to third-party applications. The integration provides access to public ArkhamDB cards (1700+) but not spoiler-protected content.

## 🛠️ Development

### Requirements

- Python 3.8+
- PyQt6
- Pillow (PIL)
- requests

### Installation

```bash
pip install PyQt6 Pillow requests
```

### Building (macOS)

```bash
python3 setup.py py2app
```
