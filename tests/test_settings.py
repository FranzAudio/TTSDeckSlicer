import json

from settings import Settings


def test_settings_round_trip_all_user_options(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings = Settings(settings_path)
    settings.set("front_suffix", "-front")
    settings.set("include_card_code", False)
    settings.set("templates", {"Deck": {"rows": 2, "cols": 3, "names": {}}})

    loaded = Settings(settings_path)
    assert loaded.get("front_suffix") == "-front"
    assert loaded.get("include_card_code") is False
    assert loaded.get("templates")["Deck"]["cols"] == 3


def test_settings_clamp_invalid_numeric_values(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "window_size": [1, 99999],
                "grid_cols": 500,
                "grid_rows": -2,
                "jpeg_quality": 200,
                "webp_quality": 0,
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(settings_path)
    assert settings.get("window_size") == (640, 4320)
    assert settings.get("grid_cols") == 50
    assert settings.get("grid_rows") == 1
    assert settings.get("jpeg_quality") == 100
    assert settings.get("webp_quality") == 1


def test_corrupt_settings_are_backed_up(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{broken", encoding="utf-8")
    settings = Settings(settings_path)
    assert settings.get("grid_cols") == 10
    assert (tmp_path / "settings.json.bak").exists()
