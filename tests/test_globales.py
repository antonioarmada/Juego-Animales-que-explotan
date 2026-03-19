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


if __name__ == "__main__":
    unittest.main()
