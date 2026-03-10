import os
import re
import subprocess
import sys

import tomlkit

SEMVER_RE = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
)

SECTION_MAP = {
    "cargo.toml": "package",
    "pyproject.toml": "project",
}


def clean_version(raw):
    cleaned = re.sub(r"^[\sv=]+", "", raw).rstrip()
    match = re.fullmatch(SEMVER_RE, cleaned)
    if not match:
        return None
    return match.group(0)


def detect_section(filepath):
    return SECTION_MAP.get(os.path.basename(filepath).lower())


def update_file(filepath, version):
    section = detect_section(filepath)
    if not section:
        die(f"Unsupported file type: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        doc = tomlkit.parse(f.read())

    if section not in doc or "version" not in doc[section]:
        die(f"No [{section}].version in {filepath}")

    if doc[section]["version"] == version:
        return False

    doc[section]["version"] = version

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))

    return True


def normalize_path(p):
    normalized = os.path.normpath(p.strip()).replace("\\", "/")
    return normalized.removeprefix("./")


def changed_files():
    tracked = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True, text=True, check=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    )
    paths = tracked.stdout.splitlines() + untracked.stdout.splitlines()
    return {normalize_path(f) for f in paths if f.strip()}


def verify_no_unexpected_changes(expected_files, baseline):
    new_changes = changed_files() - baseline
    expected = {normalize_path(f) for f in expected_files}
    unexpected = sorted(new_changes - expected)
    if unexpected:
        die(f"Version injection modified unexpected files: {', '.join(unexpected)}")


def die(msg):
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def main():
    verify = os.environ.get("INPUT_VERIFY", "false").lower() == "true"
    baseline = changed_files() if verify else set()

    raw = os.environ.get("INPUT_VERSION") or os.environ.get("GITHUB_REF_NAME", "")
    version = clean_version(raw)
    if not version:
        die(f"Invalid version: {raw}")

    files_input = os.environ.get("INPUT_FILES")
    if files_input:
        files = [f.strip() for f in files_input.split("\n") if f.strip()]
    else:
        files = [f for f in ("pyproject.toml", "Cargo.toml") if os.path.exists(f)]

    if not files:
        die("No supported manifest files found")

    updated = []
    for filepath in files:
        if not os.path.exists(filepath):
            die(f"File not found: {filepath}")
        if update_file(filepath, version):
            updated.append(filepath)

    if not updated:
        die("No files were updated")

    print(f"Set version {version} in: {', '.join(updated)}")

    if verify:
        verify_no_unexpected_changes(files, baseline)

    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"version={version}\n")
            f.write(f"version_underscored={version.replace('.', '_')}\n")


if __name__ == "__main__":
    main()
