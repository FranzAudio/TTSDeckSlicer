# TTS Deck Slicer v1.5.0 Release Notes

## Reliability and macOS build update

- Restored compatibility with Python 3.9+ and documented Python 3.11 as the
  recommended development runtime.
- Repaired the py2app configuration and removed the missing-icon build
  dependency.
- Added reproducible runtime/development requirements and standalone versus
  alias build targets.
- Added a 20-test automated regression suite and Ruff lint configuration.
- Added pure, independently tested helpers for grid bounds, filename
  sanitization, output validation and transparency flattening.
- Fixed duplicate names that could silently overwrite exported cards.
- Fixed clicks on the exact image boundary selecting an invalid tile.
- Reject mismatched full-size back images instead of exporting incorrect crops.
- Apply the selected PNG background color when flattening transparent images.
- Persist export format, JPEG/WebP quality, color, templates and all user
  options across launches.
- Save settings atomically and recover corrupted settings with a backup.
- Added ArkhamDB request timeouts and structured logging.

---

# TTS Deck Slicer v1.4 Release Notes

## 🎯 Major New Features

### ArkhamDB Integration

- **Card Database Search**: Integrated with ArkhamDB to automatically look up card information
- **Smart Card Naming**: Search and select cards directly from the ArkhamDB database
- **Manual Name Fallback**: When cards aren't found in ArkhamDB, easily commit custom card names
- **Rich Card Metadata**: Automatic retrieval of card codes, set names, factions, and types

### Enhanced Metadata System

- **Comprehensive Metadata Embedding**: All exported tiles now include rich metadata in PNG, JPEG, and WebP formats
- **macOS Integration**: Card information visible in Finder's Get Info panel and searchable via Spotlight
- **Metadata Fields Include**:
  - **Description**: Full card details (Card: [Name] | Code: [Code] | Set: [Set])
  - **Creator**: Set name (e.g., "Core Set", "The Dunwich Legacy")
  - **Make**: Card faction (e.g., "Faction: Mystic")
  - **Model**: Card code (e.g., "01001", "05003")
- **Format-Specific Optimization**: Metadata optimized for each image format while maintaining consistency

### Smart Export Controls

- **Dynamic Quality Labels**: UI automatically updates quality control labels based on selected format
- **Format-Specific Settings**: Separate quality settings for JPEG and WebP formats
- **WebP Optimization**: Enhanced support for WebP format with superior compression and full metadata

## New Features & Improvements

- **Customizable File Suffixes**: Added suffix input fields below each image panel for custom filename suffixes (defaults: "[A]" for front, "[B]" for back)
- **Card Code Prefix Option**: New checkbox in ArkhamDB search dialog to include card code as filename prefix (e.g., "01001 Agnes Baker" instead of just "Agnes Baker")
- **Encounter Card Support**: Added support for encounter cards, enemies, and scenarios via the `encounter=1` API parameter with toggle checkbox
- **Output Folder Drag & Drop**: The Output Folder button now accepts folder drops from Finder and updates recent folders automatically
- Added support for more image file formats (JPEG, PNG, WebP, BMP, GIF, TIFF)
- Streamlined user interface for better usability
- Enhanced lens tool for easier tile preview and naming
- Single back image mode for better handling of decks with identical card backs
- Added Save and Load Template functionality for reusable grid configurations
- Recent folders list for quicker access to frequently used output directories
- Export and import functionality for tile names
- Settings persistence for all user preferences

## Bug Fixes

- Fixed memory usage when handling large images
- Improved error handling and user feedback
- Enhanced stability when working with different image formats

## Technical Improvements

- Code restructuring for better maintainability
- Performance optimizations for image processing
- Added robust keyboard shortcut support
