from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

LOGGER = logging.getLogger(__name__)


class Settings:
    def __init__(self, settings_file: str | os.PathLike[str] | None = None):
        self.settings_file = Path(settings_file or Path.home() / ".ttsdeck_settings.json")
        self.defaults = {
            "window_size": (800, 600),
            "last_input_folder": "",
            "last_output_folder": "",
            "recent_folders": [],
            "grid_cols": 10,
            "grid_rows": 7,
            "jpeg_quality": 85,
            "webp_quality": 85,
            "png_bg_color": "#FFFFFF",
            "export_format": "JPEG",
            "recent_folders_max": 5,
            "use_arkhamdb": True,  # Default to enabled
            "front_suffix": "[A]",
            "back_suffix": "[B]",
            "include_card_code": True,  # Default to enabled
            "include_encounter_cards": True,  # Default to enabled
            "templates": {},
        }
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        """Load settings with validation and error recovery."""
        try:
            if self.settings_file.exists():
                with self.settings_file.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if not isinstance(loaded, dict):
                        raise ValueError("Settings root must be a JSON object")
                    # Validate and sanitize loaded values
                    validated = {
                        key: loaded[key]
                        for key in (
                            "last_input_folder",
                            "last_output_folder",
                            "front_suffix",
                            "back_suffix",
                            "png_bg_color",
                            "export_format",
                        )
                        if isinstance(loaded.get(key), str)
                    }
                    for key in (
                        "use_arkhamdb",
                        "include_card_code",
                        "include_encounter_cards",
                    ):
                        if isinstance(loaded.get(key), bool):
                            validated[key] = loaded[key]
                    if (
                        isinstance(loaded.get("window_size"), (list, tuple))
                        and len(loaded["window_size"]) == 2
                    ):
                        width, height = map(int, loaded["window_size"])
                        validated["window_size"] = (
                            max(640, min(7680, width)),
                            max(480, min(4320, height)),
                        )
                    if isinstance(loaded.get("grid_cols"), (int, float)):
                        validated["grid_cols"] = max(1, min(50, int(loaded["grid_cols"])))
                    if isinstance(loaded.get("grid_rows"), (int, float)):
                        validated["grid_rows"] = max(1, min(50, int(loaded["grid_rows"])))
                    if isinstance(loaded.get("jpeg_quality"), (int, float)):
                        validated["jpeg_quality"] = max(1, min(100, int(loaded["jpeg_quality"])))
                    if isinstance(loaded.get("webp_quality"), (int, float)):
                        validated["webp_quality"] = max(1, min(100, int(loaded["webp_quality"])))
                    if isinstance(loaded.get("recent_folders"), list):
                        validated["recent_folders"] = [
                            str(f)
                            for f in loaded["recent_folders"]
                            if isinstance(f, str) and os.path.isdir(f)
                        ][: self.defaults["recent_folders_max"]]
                    if isinstance(loaded.get("templates"), dict):
                        validated["templates"] = loaded["templates"]
                    if validated.get("export_format") not in {"JPEG", "PNG", "WEBP"}:
                        validated.pop("export_format", None)
                    return {**self.defaults, **validated}
        except Exception as e:
            LOGGER.warning("Failed to load settings (%s), using defaults", e)
            # Backup corrupted settings file if it exists
            if self.settings_file.exists():
                backup = self.settings_file.with_suffix(self.settings_file.suffix + ".bak")
                try:
                    self.settings_file.replace(backup)
                    LOGGER.warning("Backed up corrupted settings to %s", backup)
                except OSError:
                    LOGGER.exception("Could not back up corrupt settings")
        return dict(self.defaults)

    def save(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.settings_file.name}.",
                dir=self.settings_file.parent,
                text=True,
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(self.data, stream, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_name, self.settings_file)
            except Exception:
                try:
                    os.unlink(temporary_name)
                except OSError:
                    pass
                raise
        except OSError:
            LOGGER.exception("Could not save settings to %s", self.settings_file)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save()

    def add_recent_folder(self, folder: str):
        recent = self.get("recent_folders", [])
        if folder in recent:
            recent.remove(folder)
        recent.insert(0, folder)
        recent = recent[: self.get("recent_folders_max", 5)]
        self.set("recent_folders", recent)
