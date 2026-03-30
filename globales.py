import ctypes
from pathlib import Path
import sys

import pygame
import yaml


DEFAULT_CONFIG = {
    "title": "MAGIA EN EL ZOOLÓGICO",
    "fullscreen": True,
    "window_width": 1280,
    "window_height": 720,
    "ui_scale_multiplier": 1.0,
    "font_scale_multiplier": 1.7,
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
WINDOW_ICON_PATH = "img/icono-ventana.png"
BASE_WINDOW_SIZE = (1280, 720)
MIN_SCALE_MULTIPLIER = 0.5
MIN_AUTO_UI_SCALE = 0.75
MAX_AUTO_UI_SCALE = 1.15


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
    config["ui_scale_multiplier"] = sanitize_scale_multiplier(
        config.get("ui_scale_multiplier", DEFAULT_CONFIG["ui_scale_multiplier"])
    )
    config["font_scale_multiplier"] = sanitize_scale_multiplier(
        config.get("font_scale_multiplier", DEFAULT_CONFIG["font_scale_multiplier"])
    )
    config["hover_explode_delay_seconds"] = max(
        0.0, float(config["hover_explode_delay_seconds"])
    )
    config["time_out_seconds"] = max(0.0, float(config["time_out_seconds"]))
    config["session_target_count"] = max(1, int(config["session_target_count"]))
    config["cursor_trace_hz"] = max(1, int(config["cursor_trace_hz"]))
    config["data_output_dir"] = str(config["data_output_dir"])
    config["show_session_progress"] = bool(config["show_session_progress"])
    return config


def sanitize_scale_multiplier(value, default=1.0):
    try:
        return max(MIN_SCALE_MULTIPLIER, float(value))
    except (TypeError, ValueError):
        return max(MIN_SCALE_MULTIPLIER, float(default))


def get_windows_dpi_scale():
    if sys.platform != "win32":
        return 1.0

    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return 1.0

    user32 = getattr(windll, "user32", None)
    if user32 is not None:
        get_dpi_for_system = getattr(user32, "GetDpiForSystem", None)
        if get_dpi_for_system is not None:
            try:
                dpi_value = int(get_dpi_for_system())
                if dpi_value > 0:
                    return max(1.0, dpi_value / 96.0)
            except Exception:
                pass

    shcore = getattr(windll, "shcore", None)
    if shcore is not None:
        get_scale_factor = getattr(shcore, "GetScaleFactorForDevice", None)
        if get_scale_factor is not None:
            try:
                scale_factor = ctypes.c_uint()
                if get_scale_factor(0, ctypes.byref(scale_factor)) == 0:
                    return max(1.0, scale_factor.value / 100.0)
            except Exception:
                pass

    return 1.0


def calculate_auto_ui_scale(
    window_size, dpi_scale=1.0, base_window_size=BASE_WINDOW_SIZE
):
    base_width, base_height = base_window_size
    window_width, window_height = window_size
    normalized_dpi = max(1.0, float(dpi_scale))
    effective_width = max(1.0, float(window_width) / normalized_dpi)
    effective_height = max(1.0, float(window_height) / normalized_dpi)
    resolution_scale = min(effective_width / base_width, effective_height / base_height)
    return max(MIN_AUTO_UI_SCALE, min(MAX_AUTO_UI_SCALE, resolution_scale))


def calculate_ui_scales(config, window_size, dpi_scale=1.0):
    auto_scale = calculate_auto_ui_scale(window_size, dpi_scale=dpi_scale)
    return (
        auto_scale * sanitize_scale_multiplier(
            config.get("ui_scale_multiplier", DEFAULT_CONFIG["ui_scale_multiplier"])
        ),
        auto_scale * sanitize_scale_multiplier(
            config.get("font_scale_multiplier", DEFAULT_CONFIG["font_scale_multiplier"])
        ),
    )


def _set_window_icon(icon_path=WINDOW_ICON_PATH):
    icon_resource = Path(resource_path(icon_path))
    if not icon_resource.exists():
        return

    try:
        icon_surface = pygame.image.load(str(icon_resource))
        pygame.display.set_icon(icon_surface)
    except pygame.error:
        return


def enable_high_dpi_support():
    if sys.platform != "win32":
        return False

    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return False

    user32 = getattr(windll, "user32", None)
    shcore = getattr(windll, "shcore", None)

    if user32 is not None:
        set_awareness_context = getattr(user32, "SetProcessDpiAwarenessContext", None)
        if set_awareness_context is not None:
            try:
                # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                if set_awareness_context(ctypes.c_void_p(-4)):
                    return True
            except Exception:
                pass

    if shcore is not None:
        set_awareness = getattr(shcore, "SetProcessDpiAwareness", None)
        if set_awareness is not None:
            try:
                # PROCESS_PER_MONITOR_DPI_AWARE
                if set_awareness(2) == 0:
                    return True
            except Exception:
                pass

    if user32 is not None:
        set_dpi_aware = getattr(user32, "SetProcessDPIAware", None)
        if set_dpi_aware is not None:
            try:
                return bool(set_dpi_aware())
            except Exception:
                pass

    return False


def create_display(config):
    fullscreen = bool(config["fullscreen"])
    flags = pygame.FULLSCREEN if fullscreen else 0

    if fullscreen:
        info_pantalla = pygame.display.Info()
        size = (info_pantalla.current_w, info_pantalla.current_h)
    else:
        size = (int(config["window_width"]), int(config["window_height"]))

    pantalla = pygame.display.set_mode(size, flags)
    _set_window_icon()
    pygame.display.set_caption(str(config["title"]))
    pygame.mouse.set_visible(bool(config["show_cursor"]))
    return pantalla
