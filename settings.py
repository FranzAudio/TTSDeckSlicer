import json
import os
from typing import Dict, Any

class Settings:
    def __init__(self):
        self.settings_file = os.path.join(os.path.expanduser("~"), ".ttsdeck_settings.json")
        self.defaults = {
            "window_size": (800, 600),
            "last_input_folder": "",
            "last_output_folder": "",
            "recent_folders": [],
            "grid_cols": 10,
            "grid_rows": 7,
            "jpeg_quality": 85,
            "png_bg_color": "#FFFFFF",
            "recent_folders_max": 5,
            "use_arkhamdb": True,  # Default to enabled
            "front_suffix": "[A]",
            "back_suffix": "[B]",
            "include_card_code": True,  # Default to enabled
            "include_encounter_cards": True,  # Default to enabled

            # Removed title region settings as they are no longer used
        }
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        """Load settings with validation and error recovery."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    # Validate and sanitize loaded values
                    validated = {}
                    if isinstance(loaded.get('window_size'), (list, tuple)) and len(loaded['window_size']) == 2:
                        validated['window_size'] = tuple(map(int, loaded['window_size']))
                    if isinstance(loaded.get('grid_cols'), (int, float)):
                        validated['grid_cols'] = max(1, min(50, int(loaded['grid_cols'])))
                    if isinstance(loaded.get('grid_rows'), (int, float)):
                        validated['grid_rows'] = max(1, min(50, int(loaded['grid_rows'])))
                    if isinstance(loaded.get('jpeg_quality'), (int, float)):
                        validated['jpeg_quality'] = max(1, min(100, int(loaded['jpeg_quality'])))
                    if isinstance(loaded.get('recent_folders'), list):
                        validated['recent_folders'] = [
                            str(f) for f in loaded['recent_folders']
                            if isinstance(f, str) and os.path.exists(f)
                        ][:self.defaults['recent_folders_max']]
                    return {**self.defaults, **validated}
        except Exception as e:
            print(f"Warning: Failed to load settings ({str(e)}), using defaults")
            # Backup corrupted settings file if it exists
            if os.path.exists(self.settings_file):
                backup = f"{self.settings_file}.bak"
                try:
                    os.rename(self.settings_file, backup)
                    print(f"Backed up corrupted settings to: {backup}")
                except Exception:
                    pass
        return dict(self.defaults)

    def save(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

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
        recent = recent[:self.get("recent_folders_max", 5)]
        self.set("recent_folders", recent)