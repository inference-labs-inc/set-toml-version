import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import tomlkit

from set_version import clean_version, detect_section, update_file, verify_no_unexpected_changes


class TestCleanVersion(unittest.TestCase):
    def test_plain_semver(self):
        self.assertEqual(clean_version("1.2.3"), "1.2.3")

    def test_v_prefix(self):
        self.assertEqual(clean_version("v3.4.5"), "3.4.5")

    def test_equals_prefix(self):
        self.assertEqual(clean_version("=1.0.0"), "1.0.0")

    def test_whitespace_prefix(self):
        self.assertEqual(clean_version("  2.0.0"), "2.0.0")

    def test_prerelease_rc(self):
        self.assertEqual(clean_version("v2.0.0-rc.4"), "2.0.0-rc.4")

    def test_prerelease_alpha(self):
        self.assertEqual(clean_version("3.0.0-alpha.1"), "3.0.0-alpha.1")

    def test_prerelease_beta(self):
        self.assertEqual(clean_version("4.5.6-beta.2"), "4.5.6-beta.2")

    def test_build_metadata(self):
        self.assertEqual(clean_version("1.0.0+build.123"), "1.0.0+build.123")

    def test_prerelease_and_build(self):
        self.assertEqual(clean_version("v1.0.0-rc.1+build.456"), "1.0.0-rc.1+build.456")

    def test_invalid_returns_none(self):
        self.assertIsNone(clean_version("not-a-version"))

    def test_empty_returns_none(self):
        self.assertIsNone(clean_version(""))

    def test_large_numbers(self):
        self.assertEqual(clean_version("10.20.30"), "10.20.30")


class TestDetectSection(unittest.TestCase):
    def test_cargo_toml(self):
        self.assertEqual(detect_section("Cargo.toml"), "package")

    def test_pyproject_toml(self):
        self.assertEqual(detect_section("pyproject.toml"), "project")

    def test_nested_cargo(self):
        self.assertEqual(detect_section("crates/foo/Cargo.toml"), "package")

    def test_nested_pyproject(self):
        self.assertEqual(detect_section("some/path/pyproject.toml"), "project")

    def test_unknown_file(self):
        self.assertIsNone(detect_section("setup.cfg"))

    def test_case_insensitive(self):
        self.assertEqual(detect_section("CARGO.TOML"), "package")


class TestUpdateFile(unittest.TestCase):
    def _write_toml(self, directory, filename, content):
        filepath = os.path.join(directory, filename)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def test_update_cargo(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[package]\nname = "test"\nversion = "0.0.0"\nedition = "2021"\n\n[dependencies]\nserde = "1.0"\n')
            self.assertTrue(update_file(fp, "1.2.3"))
            with open(fp) as f:
                parsed = tomlkit.parse(f.read())
            self.assertEqual(parsed["package"]["version"], "1.2.3")

    def test_update_pyproject(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "pyproject.toml", '[project]\nname = "test"\nversion = "0.0.0"\ndescription = "Test"\n')
            self.assertTrue(update_file(fp, "2.0.0"))
            with open(fp) as f:
                parsed = tomlkit.parse(f.read())
            self.assertEqual(parsed["project"]["version"], "2.0.0")

    def test_preserves_formatting(self):
        with tempfile.TemporaryDirectory() as d:
            original = '[package]\nname = "test"\nversion = "0.0.0"\nedition = "2021"\n\n[dependencies]\nserde = "1.0"\n'
            fp = self._write_toml(d, "Cargo.toml", original)
            update_file(fp, "1.0.0")
            with open(fp) as f:
                result = f.read()
            self.assertIn('[dependencies]\nserde = "1.0"', result)
            self.assertEqual(result.count("\n\n"), original.count("\n\n"))

    def test_skip_missing_file(self):
        self.assertFalse(update_file("/nonexistent/Cargo.toml", "1.0.0"))

    def test_skip_unsupported_file(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "setup.cfg", "[metadata]\nversion = 0.0.0\n")
            self.assertFalse(update_file(fp, "1.0.0"))

    def test_missing_section_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[dependencies]\nserde = "1.0"\n')
            with self.assertRaises(SystemExit) as ctx:
                update_file(fp, "1.0.0")
            self.assertEqual(ctx.exception.code, 1)

    def test_missing_version_field_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[package]\nname = "test"\n')
            with self.assertRaises(SystemExit) as ctx:
                update_file(fp, "1.0.0")
            self.assertEqual(ctx.exception.code, 1)

    def test_prerelease_version(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[package]\nname = "test"\nversion = "0.0.0"\n')
            update_file(fp, "2.0.0-rc.4")
            with open(fp) as f:
                parsed = tomlkit.parse(f.read())
            self.assertEqual(parsed["package"]["version"], "2.0.0-rc.4")


class TestVerifyNoUnexpectedChanges(unittest.TestCase):
    def _mock_git_diff(self, files):
        stdout = "\n".join(files) + "\n" if files else ""
        return subprocess.CompletedProcess(
            args=["git", "diff", "--name-only"],
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    def test_no_changes_passes(self):
        with patch("set_version.subprocess.run", return_value=self._mock_git_diff([])):
            verify_no_unexpected_changes(["pyproject.toml"])

    def test_expected_changes_pass(self):
        with patch("set_version.subprocess.run", return_value=self._mock_git_diff(["pyproject.toml", "Cargo.toml"])):
            verify_no_unexpected_changes(["pyproject.toml", "Cargo.toml"])

    def test_subset_of_expected_passes(self):
        with patch("set_version.subprocess.run", return_value=self._mock_git_diff(["pyproject.toml"])):
            verify_no_unexpected_changes(["pyproject.toml", "Cargo.toml"])

    def test_unexpected_file_exits(self):
        with patch("set_version.subprocess.run", return_value=self._mock_git_diff(["pyproject.toml", "sneaky.txt"])):
            with self.assertRaises(SystemExit) as ctx:
                verify_no_unexpected_changes(["pyproject.toml"])
            self.assertEqual(ctx.exception.code, 1)

    def test_all_unexpected_exits(self):
        with patch("set_version.subprocess.run", return_value=self._mock_git_diff(["malicious.py"])):
            with self.assertRaises(SystemExit) as ctx:
                verify_no_unexpected_changes(["pyproject.toml"])
            self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
