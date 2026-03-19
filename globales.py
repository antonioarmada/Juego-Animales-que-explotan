from pathlib import Path
import sys

import pygame
import yaml


DEFAULT_CONFIG = {
    "title": "MAGIA EN EL ZOOLÓGICO",
    "fullscreen": True,
    "window_width": 1280,
    "window_height": 720,
    "show_cursor": False,
    "fps": 10,
    "music_volume": 0.05,
    "hover_explode_delay_seconds": 0.5,
    "time_out_seconds": 10,
    "session_target_count": 6,
    "cursor_trace_hz": 20,
    "data_output_dir": "sessions",
    "show_session_progress": True,
    "background_color": [57, 67, 82],
}


def resource_path(relative_path):
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


def executable_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_config_path(config_file="config.yaml"):
    external_path = executable_dir() / config_file
    if external_path.exists():
        return external_path

    bundled_base_path = Path(getattr(sys, "_MEIPASS", executable_dir()))
    return bundled_base_path / config_file


def load_config(config_file="config.yaml"):
    config = DEFAULT_CONFIG.copy()
    config_path = resolve_config_path(config_file)

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded_config = yaml.safe_load(handle) or {}

        if not isinstance(loaded_config, dict):
            raise ValueError("config.yaml debe contener un objeto YAML.")

        config.update(loaded_config)

    config["background_color"] = [int(value) for value in config["background_color"]]
    config["hover_explode_delay_seconds"] = max(
        0.0, float(config["hover_explode_delay_seconds"])
    )
    config["time_out_seconds"] = max(0.0, float(config["time_out_seconds"]))
    config["session_target_count"] = max(1, int(config["session_target_count"]))
    config["cursor_trace_hz"] = max(1, int(config["cursor_trace_hz"]))
    config["data_output_dir"] = str(config["data_output_dir"])
    config["show_session_progress"] = bool(config["show_session_progress"])
    return config


def create_display(config):
    fullscreen = bool(config["fullscreen"])
    flags = pygame.FULLSCREEN if fullscreen else 0

    if fullscreen:
        info_pantalla = pygame.display.Info()
        size = (info_pantalla.current_w, info_pantalla.current_h)
    else:
        size = (int(config["window_width"]), int(config["window_height"]))

    pantalla = pygame.display.set_mode(size, flags)
    pygame.display.set_caption(str(config["title"]))
    pygame.mouse.set_visible(bool(config["show_cursor"]))
    return pantalla
