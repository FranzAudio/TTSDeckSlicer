import pytest
from PIL import Image

from slicer_core import (
    ensure_output_folder,
    flatten_transparency,
    sanitize_tile_name,
    tile_bounds,
)


def test_sanitize_tile_name():
    assert sanitize_tile_name("  Agnes  Baker: /?  ", "fallback") == "Agnes Baker ?"
    assert sanitize_tile_name(":::", "tile01-01") == "tile01-01"
    assert sanitize_tile_name("A.", "fallback") == "A"


def test_tile_bounds_cover_odd_sized_image_without_overlap():
    bounds = list(tile_bounds((203, 107), 2, 2))
    assert bounds == [
        (0, 0, 0, 0, 102, 54),
        (0, 1, 102, 0, 203, 54),
        (1, 0, 0, 54, 102, 107),
        (1, 1, 102, 54, 203, 107),
    ]
    assert (
        sum((right - left) * (lower - upper) for _, _, left, upper, right, lower in bounds)
        == 203 * 107
    )


@pytest.mark.parametrize("columns,rows", [(0, 1), (1, 0), (11, 1), (1, 11)])
def test_tile_bounds_reject_invalid_grids(columns, rows):
    with pytest.raises(ValueError):
        list(tile_bounds((10, 10), columns, rows))


def test_flatten_transparency_uses_selected_background():
    source = Image.new("RGBA", (1, 1), (255, 0, 0, 128))
    result = flatten_transparency(source, (0, 0, 255))
    assert result.mode == "RGB"
    red, green, blue = result.getpixel((0, 0))
    assert red in range(127, 129)
    assert green == 0
    assert blue in range(127, 129)


def test_ensure_output_folder(tmp_path):
    assert ensure_output_folder(tmp_path) == tmp_path.resolve()
    with pytest.raises(ValueError):
        ensure_output_folder(tmp_path / "missing")
