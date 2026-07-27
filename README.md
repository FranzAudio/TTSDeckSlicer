# TTS Deck Slicer

TTS Deck Slicer is a macOS desktop application that splits deck-sheet images
into individual cards for Tabletop Simulator and other virtual tabletops.

## Features

- JPG, PNG, WebP, BMP, GIF and TIFF input
- Configurable grid with live preview and Option-key magnifier
- Optional front/back and shared-back export
- JPEG, PNG and WebP output with configurable quality/background
- Tile naming, CSV import/export and reusable templates
- Undo/redo history
- ArkhamDB card search and embedded card metadata

## Requirements

- macOS 11 or newer
- Python 3.9 or newer (Python 3.11 is recommended)
- Internet access only for ArkhamDB integration

## Run from source

```bash
make venv
make run
```

The Makefile prefers `python3.11` when available. To choose another interpreter:

```bash
make venv PYTHON_BOOTSTRAP=/path/to/python3
```

## Tests and lint

```bash
make test
make lint
```

The test suite runs Qt in offscreen mode and covers slicing, all export formats,
metadata, settings recovery, undo/redo, ArkhamDB failures and important UI
regressions.

## macOS build

Create a standalone application:

```bash
make clean
make build
```

The result is `dist/TTS Deck Slicer.app`. For a faster development-only alias
bundle, use `make build-alias`.

To create an ad-hoc signed DMG:

```bash
make sign
make dmg
```

## ArkhamDB limitation

The integration uses ArkhamDB's public API. Spoiler-protected cards requiring
authentication are not available to third-party applications.
