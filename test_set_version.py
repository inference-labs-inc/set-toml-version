import os
import tempfile

import tomlkit

from set_version import clean_version, detect_section, update_file


class TestCleanVersion:
    def test_plain_semver(self):
        assert clean_version("1.2.3") == "1.2.3"

    def test_v_prefix(self):
        assert clean_version("v3.4.5") == "3.4.5"

    def test_equals_prefix(self):
        assert clean_version("=1.0.0") == "1.0.0"

    def test_whitespace_prefix(self):
        assert clean_version("  2.0.0") == "2.0.0"

    def test_prerelease_rc(self):
        assert clean_version("v2.0.0-rc.4") == "2.0.0-rc.4"

    def test_prerelease_alpha(self):
        assert clean_version("3.0.0-alpha.1") == "3.0.0-alpha.1"

    def test_prerelease_beta(self):
        assert clean_version("4.5.6-beta.2") == "4.5.6-beta.2"

    def test_build_metadata(self):
        assert clean_version("1.0.0+build.123") == "1.0.0+build.123"

    def test_prerelease_and_build(self):
        assert clean_version("v1.0.0-rc.1+build.456") == "1.0.0-rc.1+build.456"

    def test_invalid_returns_none(self):
        assert clean_version("not-a-version") is None

    def test_empty_returns_none(self):
        assert clean_version("") is None

    def test_large_numbers(self):
        assert clean_version("10.20.30") == "10.20.30"


class TestDetectSection:
    def test_cargo_toml(self):
        assert detect_section("Cargo.toml") == "package"

    def test_pyproject_toml(self):
        assert detect_section("pyproject.toml") == "project"

    def test_nested_cargo(self):
        assert detect_section("crates/foo/Cargo.toml") == "package"

    def test_nested_pyproject(self):
        assert detect_section("some/path/pyproject.toml") == "project"

    def test_unknown_file(self):
        assert detect_section("setup.cfg") is None

    def test_case_insensitive(self):
        assert detect_section("CARGO.TOML") == "package"


class TestUpdateFile:
    def _write_toml(self, directory, filename, content):
        filepath = os.path.join(directory, filename)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def test_update_cargo(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[package]\nname = "test"\nversion = "0.0.0"\nedition = "2021"\n\n[dependencies]\nserde = "1.0"\n')
            assert update_file(fp, "1.2.3") is True
            parsed = tomlkit.parse(open(fp).read())
            assert parsed["package"]["version"] == "1.2.3"

    def test_update_pyproject(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "pyproject.toml", '[project]\nname = "test"\nversion = "0.0.0"\ndescription = "Test"\n')
            assert update_file(fp, "2.0.0") is True
            parsed = tomlkit.parse(open(fp).read())
            assert parsed["project"]["version"] == "2.0.0"

    def test_preserves_formatting(self):
        with tempfile.TemporaryDirectory() as d:
            original = '[package]\nname = "test"\nversion = "0.0.0"\nedition = "2021"\n\n[dependencies]\nserde = "1.0"\n'
            fp = self._write_toml(d, "Cargo.toml", original)
            update_file(fp, "1.0.0")
            result = open(fp).read()
            assert '[dependencies]\nserde = "1.0"' in result
            assert result.count("\n\n") == original.count("\n\n")

    def test_skip_missing_file(self):
        assert update_file("/nonexistent/Cargo.toml", "1.0.0") is False

    def test_skip_unsupported_file(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "setup.cfg", "[metadata]\nversion = 0.0.0\n")
            assert update_file(fp, "1.0.0") is False

    def test_missing_section_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[dependencies]\nserde = "1.0"\n')
            try:
                update_file(fp, "1.0.0")
                assert False, "Should have called sys.exit"
            except SystemExit as e:
                assert e.code == 1

    def test_missing_version_field_exits(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[package]\nname = "test"\n')
            try:
                update_file(fp, "1.0.0")
                assert False, "Should have called sys.exit"
            except SystemExit as e:
                assert e.code == 1

    def test_prerelease_version(self):
        with tempfile.TemporaryDirectory() as d:
            fp = self._write_toml(d, "Cargo.toml", '[package]\nname = "test"\nversion = "0.0.0"\n')
            update_file(fp, "2.0.0-rc.4")
            parsed = tomlkit.parse(open(fp).read())
            assert parsed["package"]["version"] == "2.0.0-rc.4"
