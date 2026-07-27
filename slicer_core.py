"""Pure image-slicing helpers shared by the UI and automated tests."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from PIL import Image

_ALLOWED_FILENAME_PUNCTUATION = set(" ._-!'?,()[]")


def sanitize_tile_name(raw_name: str, fallback: str) -> str:
    """Return a macOS-safe filename stem without changing useful punctuation."""
    sanitized = "".join(
        character
        for character in (raw_name or "")
        if character.isalnum() or character in _ALLOWED_FILENAME_PUNCTUATION
    )
    sanitized = re.sub(r"\s+", " ", sanitized).strip().rstrip(".")
    return sanitized or fallback


def tile_bounds(
    image_size: tuple[int, int],
    columns: int,
    rows: int,
) -> Iterator[tuple[int, int, int, int, int, int]]:
    """Yield row, column and non-overlapping crop bounds for an entire grid."""
    width, height = image_size
    if columns < 1 or rows < 1:
        raise ValueError("Grid dimensions must be positive")
    if columns > width or rows > height:
        raise ValueError("Grid cannot contain tiles smaller than one pixel")

    for row in range(rows):
        upper = round(row * height / rows)
        lower = round((row + 1) * height / rows)
        for column in range(columns):
            left = round(column * width / columns)
            right = round((column + 1) * width / columns)
            yield row, column, left, upper, right, lower


def flatten_transparency(
    image: Image.Image,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Return an RGB image, compositing transparency over the chosen background."""
    has_transparency = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_transparency:
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, background)
        flattened.paste(rgba, mask=rgba.getchannel("A"))
        return flattened
    return image if image.mode == "RGB" else image.convert("RGB")


def ensure_output_folder(folder: str | Path) -> Path:
    """Validate and normalize an existing output directory."""
    output = Path(folder).expanduser().resolve()
    if not output.is_dir():
        raise ValueError(f"Output folder does not exist: {output}")
    return output
