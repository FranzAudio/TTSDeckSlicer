import pytest
from PIL import Image
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMessageBox

from TTSDeckSlicer import ImageSplitter, __version__


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok
    )
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok
    )
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok
    )
    instance = ImageSplitter()
    yield instance
    instance.close()


def test_window_starts_with_current_version(window):
    assert __version__ == "1.5.0"
    assert window.windowTitle() == "TTS Deck Slicer v1.5.0"


@pytest.mark.parametrize(
    "format_name,extension", [("PNG", "png"), ("JPEG", "jpeg"), ("WEBP", "webp")]
)
def test_split_image_end_to_end(window, tmp_path, format_name, extension):
    source_path = tmp_path / "front.png"
    output_path = tmp_path / "output"
    output_path.mkdir()
    Image.new("RGBA", (203, 107), (200, 30, 20, 128)).save(source_path)

    window.front_image_path = str(source_path)
    window.front_pixmap = QPixmap(str(source_path))
    window.output_folder = str(output_path)
    window.col_spin.setValue(2)
    window.row_spin.setValue(2)
    window.export_options.set_format(format_name)
    window.tile_names[(0, 0)] = "Agnes Baker"
    window.tile_metadata[(0, 0)] = {
        "name": "Agnes Baker",
        "code": "01004",
        "pack_name": "Core Set",
        "faction_name": "Mystic",
    }

    window.split_image()

    files = sorted(output_path.glob(f"*.{extension}"))
    assert len(files) == 4
    assert files[0].name == f"Agnes Baker[A].{extension}"
    assert window._last_failed_tile is None
    assert {Image.open(file).size for file in files} == {
        (102, 54),
        (101, 54),
        (102, 53),
        (101, 53),
    }


def test_duplicate_export_names_are_blocked_case_insensitively(window):
    window.tile_names[(0, 0)] = "Agnes Baker"
    assert window._name_conflicts((0, 1), "agnes baker", {"code": "other"})


def test_mismatched_back_image_is_rejected(window, tmp_path, monkeypatch):
    front = tmp_path / "front.png"
    back = tmp_path / "back.png"
    output = tmp_path / "output"
    output.mkdir()
    Image.new("RGB", (100, 100)).save(front)
    Image.new("RGB", (50, 50)).save(back)
    errors = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda _parent, title, message: errors.append((title, message)),
    )
    window.front_image_path = str(front)
    window.back_image_path = str(back)
    window.output_folder = str(output)
    window.col_spin.setValue(2)
    window.row_spin.setValue(2)
    window.use_single_back_image.setChecked(False)

    window.split_image()

    assert not list(output.iterdir())
    assert "identical dimensions" in errors[0][1]
