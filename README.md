# TTS Deck Slicer

**TTS Deck Slicer** is a lightweight desktop app that slices an image into a grid of tiles — perfect for preparing card decks for Tabletop Simulator (TTS) or any virtual tabletop.

## ✨ Features

- 🖼️ Load standard image formats (JPG, PNG, BMP, etc.)
- 🔢 Choose number of columns and rows (default 10×7)
- 🧮 Live preview with grid overlay
- 🔁 Toggle between `(front)` or `(back)` tile suffix
- 📁 Export to a chosen folder with proper naming
- 🧾 Output filenames like: `tile03-01(front).jpg`
- 🧱 Built with Python 3 + PyQt6

## 🚀 How to Use

1. Launch the app.
2. Click **Open Image** to load your deck sheet.
3. Adjust the number of columns and rows.
4. Choose the suffix: `(front)` or `(back)`.
5. Select the output folder.
6. Click **Split and Save** to generate image tiles.

## 🛠️ Development

To build the application locally:

### Using `py2app` (for macOS)

```bash
python3 setup.py py2app