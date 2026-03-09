import os
import re
import subprocess
import sys

import tomlkit


def clean_version(raw):
    cleaned = re.sub(r"^[v=]+", "", raw.strip())
    match = re.fullmatch(
        r"(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)",
        cleaned,
    )
    if not match:
        return None
    return match.group(1)


def detect_section(filepath):
    basename = os.path.basename(filepath).lower()
    if "cargo" in basename:
        return "package"
    if "pyproject" in basename:
        return "project"
    return None


def update_file(filepath, version):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (not found)")
        return False

    section = detect_section(filepath)
    if not section:
        print(f"::warning::Unsupported file type: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        doc = tomlkit.parse(f.read())

    if section not in doc:
        print(f"::error::Section [{section}] not found in {filepath}", file=sys.stderr)
        sys.exit(1)

    if "version" not in doc[section]:
        print(
            f"::error::No version field in [{section}] of {filepath}",
            file=sys.stderr,
        )
        sys.exit(1)

    doc[section]["version"] = version

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))

    return True


def changed_files():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return {f.strip() for f in result.stdout.splitlines() if f.strip()}


def verify_no_unexpected_changes(expected_files, baseline):
    current = changed_files()
    new_changes = current - baseline
    expected = {f.strip() for f in expected_files if f.strip()}
    unexpected = sorted(new_changes - expected)
    if unexpected:
        print(
            f"::error::Version injection modified unexpected files: {', '.join(unexpected)}",
            file=sys.stderr,
        )
        sys.exit(1)
    print("Verified: no unexpected files modified")


def main():
    verify = os.environ.get("INPUT_VERIFY", "false").lower() == "true"
    baseline = changed_files() if verify else set()

    raw = os.environ.get("INPUT_VERSION") or os.environ.get("GITHUB_REF_NAME", "")
    version = clean_version(raw)
    if not version:
        print(f"::error::Invalid version: {raw}", file=sys.stderr)
        sys.exit(1)

    print(f"Setting version to: {version}")

    files_input = os.environ.get("INPUT_FILES", "pyproject.toml\nCargo.toml")
    files = [f.strip() for f in files_input.split("\n") if f.strip()]

    updated = []
    for filepath in files:
        if update_file(filepath, version):
            updated.append(filepath)
            print(f"  - {filepath}")

    if not updated:
        print("::error::No files were updated", file=sys.stderr)
        sys.exit(1)

    if verify:
        verify_no_unexpected_changes(files, baseline)

    version_underscored = version.replace(".", "_")

    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"version={version}\n")
            f.write(f"version_underscored={version_underscored}\n")


if __name__ == "__main__":
    main()
