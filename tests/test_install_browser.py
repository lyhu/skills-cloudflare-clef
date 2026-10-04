import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "skills/cloudflare-clef/scripts/install-browser.py"
spec = importlib.util.spec_from_file_location("install_browser", path)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallBrowserTests(unittest.TestCase):
    def test_install_is_backed_up_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            skill = directory / "SKILL.md"
            original = "---\nname: ego-browser\n---\n\n# ego-browser\n\nOriginal instructions.\n"
            skill.write_text(original)
            config_dir = directory / "config"
            for _ in range(2):
                self.assertTrue(installer.install("http://local.test/v1/systemone",
                    config_dir=config_dir, browser_skill=skill)["browser_hook"])
            self.assertEqual(skill.read_text().count(installer.START), 1)
            backups = list(config_dir.glob("ego-browser-SKILL.before-*.md"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)
            self.assertIn("Original instructions.", skill.read_text())
            config = config_dir / "config.json"
            self.assertEqual(json.loads(config.read_text())["endpoint"], "http://local.test/v1/systemone")
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)

    def test_invalid_endpoint_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaises(ValueError):
                installer.install("https://user:secret@server.test/", config_dir=directory / "config")
            self.assertFalse((directory / "config").exists())
