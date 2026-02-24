import { test, before, after } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'smol-toml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const testDir = path.join(__dirname, 'test-fixtures');

let importCounter = 0;
async function runAction() {
  await import(`./index.js?t=${++importCounter}`);
}

before(() => {
  fs.mkdirSync(testDir, { recursive: true });
});

after(() => {
  if (fs.existsSync(testDir)) {
    fs.rmSync(testDir, { recursive: true });
  }
});

test('updates Cargo.toml version', async () => {
  const testFile = path.join(testDir, 'test-cargo.toml');
  const content = `[package]
name = "test"
version = "0.0.0"
edition = "2021"

[dependencies]
serde = "1.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '1.2.3';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.package.version, '1.2.3');

  fs.unlinkSync(testFile);
});

test('updates pyproject.toml version', async () => {
  const testFile = path.join(testDir, 'test-pyproject.toml');
  const content = `[project]
name = "test"
version = "0.0.0"
description = "Test"

[tool.poetry.dependencies]
python = "^3.8"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '2.0.0';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.project.version, '2.0.0');

  fs.unlinkSync(testFile);
});

test('handles version with v prefix', async () => {
  const testFile = path.join(testDir, 'test-v-prefix-cargo.toml');
  const content = `[package]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = 'v3.4.5';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.package.version, '3.4.5');

  fs.unlinkSync(testFile);
});

test('handles multiple files', async () => {
  const cargoFile = path.join(testDir, 'multi-cargo.toml');
  const pyFile = path.join(testDir, 'multi-pyproject.toml');

  fs.writeFileSync(
    cargoFile,
    `[package]
name = "test"
version = "0.0.0"
`
  );

  fs.writeFileSync(
    pyFile,
    `[project]
name = "test"
version = "0.0.0"
`
  );

  process.env.INPUT_VERSION = '5.0.0';
  process.env.INPUT_FILES = `${cargoFile}\n${pyFile}`;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const cargoParsed = parse(fs.readFileSync(cargoFile, 'utf8'));
  const pyParsed = parse(fs.readFileSync(pyFile, 'utf8'));

  assert.strictEqual(cargoParsed.package.version, '5.0.0');
  assert.strictEqual(pyParsed.project.version, '5.0.0');

  fs.unlinkSync(cargoFile);
  fs.unlinkSync(pyFile);
});

test('handles custom version input', async () => {
  const testFile = path.join(testDir, 'custom-version-cargo.toml');
  const content = `[package]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '10.20.30';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.package.version, '10.20.30');

  fs.unlinkSync(testFile);
});

test('handles version with = prefix', async () => {
  const testFile = path.join(testDir, 'equals-prefix-pyproject.toml');
  const content = `[project]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '=1.0.0';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.project.version, '1.0.0');

  fs.unlinkSync(testFile);
});

test('handles prerelease versions (rc, alpha, beta)', async () => {
  const testFile = path.join(testDir, 'prerelease-cargo.toml');
  const content = `[package]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = 'v2.0.0-rc.4';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.package.version, '2.0.0-rc.4');

  fs.unlinkSync(testFile);
});

test('handles alpha prerelease', async () => {
  const testFile = path.join(testDir, 'alpha-pyproject.toml');
  const content = `[project]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '3.0.0-alpha.1';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.project.version, '3.0.0-alpha.1');

  fs.unlinkSync(testFile);
});

test('handles beta prerelease', async () => {
  const testFile = path.join(testDir, 'beta-cargo.toml');
  const content = `[package]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '4.5.6-beta.2';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.package.version, '4.5.6-beta.2');

  fs.unlinkSync(testFile);
});

test('handles custom file paths', async () => {
  const customDir = path.join(testDir, 'custom', 'path');
  fs.mkdirSync(customDir, { recursive: true });

  const testFile = path.join(customDir, 'custom-pyproject.toml');
  const content = `[project]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '7.8.9';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.project.version, '7.8.9');

  fs.rmSync(path.join(testDir, 'custom'), { recursive: true });
});

test('detects file type from basename not full path', async () => {
  const cargoDir = path.join(testDir, 'cargo-workspace');
  fs.mkdirSync(cargoDir, { recursive: true });

  const testFile = path.join(cargoDir, 'pyproject.toml');
  const content = `[project]
name = "test"
version = "0.0.0"
`;
  fs.writeFileSync(testFile, content);

  process.env.INPUT_VERSION = '6.0.0';
  process.env.INPUT_FILES = testFile;
  process.env.GITHUB_REF_NAME = '';

  await runAction();

  const updated = fs.readFileSync(testFile, 'utf8');
  const parsed = parse(updated);
  assert.strictEqual(parsed.project.version, '6.0.0');

  fs.rmSync(cargoDir, { recursive: true });
});
