# Set TOML Version

GitHub Action to update version fields in `pyproject.toml` and `Cargo.toml` files.

## Usage

```yaml
- uses: inference-labs-inc/set-toml-version@v1
  with:
    files: |
      pyproject.toml
      Cargo.toml
```

### Inputs

| Input     | Description                           | Required | Default                            |
| --------- | ------------------------------------- | -------- | ---------------------------------- |
| `version` | Version to set (cleaned via `semver`) | No       | Tag version from `github.ref_name` |
| `files`   | Paths to TOML files (one per line)    | No       | `pyproject.toml` and `Cargo.toml`  |

### Outputs

| Output                | Description                                  | Example |
| --------------------- | -------------------------------------------- | ------- |
| `version`             | The version that was set                     | `1.2.3` |
| `version_underscored` | The version with underscores instead of dots | `1_2_3` |

## Examples

### Update version from git tag

```yaml
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: inference-labs-inc/set-toml-version@v1
        id: version

      - run: echo "Version set to ${{ steps.version.outputs.version }}"
```

### Custom version and files

```yaml
- uses: inference-labs-inc/set-toml-version@v1
  with:
    version: '2.0.0'
    files: |
      packages/core/pyproject.toml
      crates/cli/Cargo.toml
```

### Use version in later steps

```yaml
- uses: inference-labs-inc/set-toml-version@v1
  id: set_version

- run: echo "Building version ${{ steps.set_version.outputs.version }}"

- run: echo "Artifact name: my-app-${{ steps.set_version.outputs.version_underscored }}"
```

## How it works

- Parses TOML files using `smol-toml`
- Updates `package.version` in `Cargo.toml`
- Updates `project.version` in `pyproject.toml`
- Validates versions with `semver`
