import tempfile
import unittest
from pathlib import Path
from unittest import mock

import globales


class ConfigResolutionTest(unittest.TestCase):
    def test_resolve_config_path_prioritizes_external_file_next_to_executable(self):
        with tempfile.TemporaryDirectory() as executable_dir, tempfile.TemporaryDirectory() as bundled_dir:
            external_path = Path(executable_dir) / "config.yaml"
            bundled_path = Path(bundled_dir) / "config.yaml"
            external_path.write_text("title: EXTERNO\nfullscreen: false\n", encoding="utf-8")
            bundled_path.write_text("title: INTERNO\nfullscreen: true\n", encoding="utf-8")

            with mock.patch.object(globales.sys, "frozen", True, create=True), mock.patch.object(
                globales.sys, "executable", str(Path(executable_dir) / "AnimalesExplotan.exe")
            ), mock.patch.object(globales.sys, "_MEIPASS", str(bundled_dir), create=True):
                config = globales.load_config()

            self.assertEqual(config["title"], "EXTERNO")
            self.assertFalse(config["fullscreen"])

    def test_resolve_config_path_uses_bundled_fallback_when_external_file_is_missing(self):
        with tempfile.TemporaryDirectory() as executable_dir, tempfile.TemporaryDirectory() as bundled_dir:
            bundled_path = Path(bundled_dir) / "config.yaml"
            bundled_path.write_text("title: INTERNO\nfullscreen: true\n", encoding="utf-8")

            with mock.patch.object(globales.sys, "frozen", True, create=True), mock.patch.object(
                globales.sys, "executable", str(Path(executable_dir) / "AnimalesExplotan.exe")
            ), mock.patch.object(globales.sys, "_MEIPASS", str(bundled_dir), create=True):
                config = globales.load_config()

            self.assertEqual(config["title"], "INTERNO")
            self.assertTrue(config["fullscreen"])


class DisplayCreationTest(unittest.TestCase):
    def test_create_display_sets_window_icon(self):
        config = {
            **globales.DEFAULT_CONFIG,
            "fullscreen": False,
            "window_width": 800,
            "window_height": 600,
            "title": "TEST",
            "show_cursor": True,
        }

        with mock.patch.object(globales, "_set_window_icon") as set_window_icon, mock.patch.object(
            globales.pygame.display, "set_mode", return_value="pantalla"
        ) as set_mode, mock.patch.object(globales.pygame.display, "set_caption") as set_caption, mock.patch.object(
            globales.pygame.mouse, "set_visible"
        ) as set_visible:
            pantalla = globales.create_display(config)

        self.assertEqual(pantalla, "pantalla")
        set_mode.assert_called_once_with((800, 600), 0)
        set_window_icon.assert_called_once_with()
        set_caption.assert_called_once_with("TEST")
        set_visible.assert_called_once_with(True)

    def test_set_window_icon_loads_png_when_present(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            icon_path = Path(tmp_dir) / "icono-ventana.png"
            icon_path.write_bytes(b"png")

            with mock.patch.object(globales, "resource_path", return_value=str(icon_path)), mock.patch.object(
                globales.pygame.image, "load", return_value="icon-surface"
            ) as image_load, mock.patch.object(globales.pygame.display, "set_icon") as set_icon:
                globales._set_window_icon()

        image_load.assert_called_once_with(str(icon_path))
        set_icon.assert_called_once_with("icon-surface")


if __name__ == "__main__":
    unittest.main()
