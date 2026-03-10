import os
import tempfile
import unittest
from unittest.mock import patch

import tomlkit

from set_version import clean_version, detect_section, normalize_path, update_file, verify_no_unexpected_changes


class TestCleanVersion(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(clean_version("1.2.3"), "1.2.3")

    def test_v_prefix(self):
        self.assertEqual(clean_version("v3.4.5"), "3.4.5")

    def test_equals_prefix(self):
        self.assertEqual(clean_version("=1.0.0"), "1.0.0")

    def test_whitespace(self):
        self.assertEqual(clean_version("  2.0.0  "), "2.0.0")

    def test_prerelease(self):
        self.assertEqual(clean_version("v2.0.0-rc.4"), "2.0.0-rc.4")

    def test_alpha(self):
        self.assertEqual(clean_version("3.0.0-alpha.1"), "3.0.0-alpha.1")

    def test_beta(self):
        self.assertEqual(clean_version("4.5.6-beta.2"), "4.5.6-beta.2")

    def test_build_metadata(self):
        self.assertEqual(clean_version("1.0.0+build.123"), "1.0.0+build.123")

    def test_prerelease_and_build(self):
        self.assertEqual(clean_version("v1.0.0-rc.1+build.456"), "1.0.0-rc.1+build.456")

    def test_large_numbers(self):
        self.assertEqual(clean_version("10.20.30"), "10.20.30")

    def test_trailing_junk(self):
        self.assertIsNone(clean_version("v1.2.3junk"))

    def test_empty(self):
        self.assertIsNone(clean_version(""))

    def test_invalid(self):
        self.assertIsNone(clean_version("not-a-version"))

    def test_leading_zero_major(self):
        self.assertIsNone(clean_version("01.2.3"))

    def test_leading_zero_prerelease(self):
        self.assertIsNone(clean_version("1.2.3-01"))

    def test_empty_prerelease_segment(self):
        self.assertIsNone(clean_version("1.2.3-alpha..1"))

    def test_zero_major(self):
        self.assertEqual(clean_version("0.1.0"), "0.1.0")


class TestDetectSection(unittest.TestCase):
    def test_cargo(self):
        self.assertEqual(detect_section("Cargo.toml"), "package")

    def test_pyproject(self):
        self.assertEqual(detect_section("pyproject.toml"), "project")

    def test_nested_cargo(self):
        self.assertEqual(detect_section("crates/foo/Cargo.toml"), "package")

    def test_nested_pyproject(self):
        self.assertEqual(detect_section("some/path/pyproject.toml"), "project")

    def test_unknown(self):
        self.assertIsNone(detect_section("setup.cfg"))

    def test_cargo_lock_rejected(self):
        self.assertIsNone(detect_section("Cargo.lock"))

    def test_backup_rejected(self):
        self.assertIsNone(detect_section("pyproject.toml.bak"))


class TestUpdateFile(unittest.TestCase):
    def _write(self, d, name, content):
        fp = os.path.join(d, name)
        with open(fp, "w") as f:
            f.write(content)
        return fp

    def test_cargo(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "Cargo.toml", '[package]\nname = "t"\nversion = "0.0.0"\n\n[dependencies]\nserde = "1"\n')
            self.assertTrue(update_file(fp, "1.2.3"))
            with open(fp) as f:
                self.assertEqual(tomlkit.parse(f.read())["package"]["version"], "1.2.3")

    def test_pyproject(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "pyproject.toml", '[project]\nname = "t"\nversion = "0.0.0"\n')
            self.assertTrue(update_file(fp, "2.0.0"))
            with open(fp) as f:
                self.assertEqual(tomlkit.parse(f.read())["project"]["version"], "2.0.0")

    def test_preserves_formatting(self):
        with tempfile.TemporaryDirectory() as d:
            original = '[package]\nname = "t"\nversion = "0.0.0"\n\n[dependencies]\nserde = "1"\n'
            fp = self._write(d, "Cargo.toml", original)
            update_file(fp, "1.0.0")
            with open(fp) as f:
                result = f.read()
            self.assertIn('[dependencies]\nserde = "1"', result)
            self.assertEqual(result.count("\n\n"), original.count("\n\n"))

    def test_unsupported_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "setup.cfg", "[metadata]\nversion = 0\n")
            with self.assertRaises(SystemExit):
                update_file(fp, "1.0.0")

    def test_missing_section_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "Cargo.toml", '[dependencies]\nserde = "1"\n')
            with self.assertRaises(SystemExit):
                update_file(fp, "1.0.0")

    def test_missing_version_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "Cargo.toml", '[package]\nname = "t"\n')
            with self.assertRaises(SystemExit):
                update_file(fp, "1.0.0")

    def test_noop_returns_false(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "Cargo.toml", '[package]\nname = "t"\nversion = "1.0.0"\n')
            self.assertFalse(update_file(fp, "1.0.0"))

    def test_noop_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "Cargo.toml", '[package]\nname = "t"\nversion = "1.0.0"\n')
            with patch("builtins.open", wraps=open) as m:
                update_file(fp, "1.0.0")
            self.assertFalse([c for c in m.call_args_list if len(c.args) >= 2 and "w" in c.args[1]])

    def test_prerelease(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write(d, "Cargo.toml", '[package]\nname = "t"\nversion = "0.0.0"\n')
            update_file(fp, "2.0.0-rc.4")
            with open(fp) as f:
                self.assertEqual(tomlkit.parse(f.read())["package"]["version"], "2.0.0-rc.4")


class TestNormalizePath(unittest.TestCase):
    def test_dot_slash(self):
        self.assertEqual(normalize_path("./pyproject.toml"), "pyproject.toml")

    def test_backslash(self):
        self.assertEqual(normalize_path("dir\\Cargo.toml"), "dir/Cargo.toml")

    def test_passthrough(self):
        self.assertEqual(normalize_path("pyproject.toml"), "pyproject.toml")

    def test_parent_collapse(self):
        self.assertEqual(normalize_path("./dir/../dir/Cargo.toml"), "dir/Cargo.toml")

    def test_whitespace(self):
        self.assertEqual(normalize_path("  pyproject.toml  "), "pyproject.toml")


class TestVerify(unittest.TestCase):
    def test_no_changes(self):
        with patch("set_version.changed_files", return_value=set()):
            verify_no_unexpected_changes(["pyproject.toml"], set())

    def test_expected_only(self):
        with patch("set_version.changed_files", return_value={"pyproject.toml", "Cargo.toml"}):
            verify_no_unexpected_changes(["pyproject.toml", "Cargo.toml"], set())

    def test_subset(self):
        with patch("set_version.changed_files", return_value={"pyproject.toml"}):
            verify_no_unexpected_changes(["pyproject.toml", "Cargo.toml"], set())

    def test_unexpected_exits(self):
        with patch("set_version.changed_files", return_value={"pyproject.toml", "sneaky.txt"}):
            with self.assertRaises(SystemExit):
                verify_no_unexpected_changes(["pyproject.toml"], set())

    def test_baseline_excluded(self):
        with patch("set_version.changed_files", return_value={"pyproject.toml", "pre.txt"}):
            verify_no_unexpected_changes(["pyproject.toml"], {"pre.txt"})

    def test_baseline_plus_unexpected_exits(self):
        with patch("set_version.changed_files", return_value={"pyproject.toml", "pre.txt", "sneaky.txt"}):
            with self.assertRaises(SystemExit):
                verify_no_unexpected_changes(["pyproject.toml"], {"pre.txt"})

    def test_dot_slash_matches(self):
        with patch("set_version.changed_files", return_value={"pyproject.toml"}):
            verify_no_unexpected_changes(["./pyproject.toml"], set())

    def test_backslash_matches(self):
        with patch("set_version.changed_files", return_value={"dir/Cargo.toml"}):
            verify_no_unexpected_changes(["dir\\Cargo.toml"], set())


if __name__ == "__main__":
    unittest.main()
