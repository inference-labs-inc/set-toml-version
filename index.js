import fs from 'fs';
import * as core from '@actions/core';
import semver from 'semver';
import { parse, stringify } from 'smol-toml';

function updateToml(content, version, section) {
  const parsed = parse(content);
  if (!parsed[section]) {
    throw new Error(`Section [${section}] not found in TOML file`);
  }
  if (parsed[section].version === undefined) {
    throw new Error(
      `No version field found in [${section}] section. Please add 'version = "0.0.0"' to the section.`
    );
  }
  parsed[section].version = version;
  return stringify(parsed);
}

function updateTomlFile(filePath, version) {
  try {
    if (!fs.existsSync(filePath)) {
      core.info(`Skipping ${filePath} (not found)`);
      return null;
    }

    const content = fs.readFileSync(filePath, 'utf8');
    let updated;
    let section;

    if (filePath.includes('Cargo') || filePath.includes('cargo')) {
      section = 'package';
    } else if (filePath.includes('pyproject')) {
      section = 'project';
    } else {
      core.warning(`Unsupported file type: ${filePath}`);
      return null;
    }

    updated = updateToml(content, version, section);

    fs.writeFileSync(filePath, updated, 'utf8');
    return filePath;
  } catch (error) {
    core.error(`Failed to update ${filePath}: ${error.message}`);
    throw error;
  }
}

function run() {
  try {
    let version = core.getInput('version') || process.env.GITHUB_REF_NAME || '';
    const cleaned = semver.clean(version);

    if (!cleaned) {
      throw new Error(`Invalid version: ${version}`);
    }

    core.info(`Setting version to: ${cleaned}`);

    const filesInput = core.getInput('files') || 'pyproject.toml\nCargo.toml';
    const files = filesInput
      .split('\n')
      .map((f) => f.trim())
      .filter((f) => f.length > 0);

    const updatedFiles = [];
    for (const file of files) {
      const result = updateTomlFile(file, cleaned);
      if (result) {
        updatedFiles.push(result);
      }
    }

    if (updatedFiles.length === 0) {
      core.warning('No files were updated');
    } else {
      core.info(`Updated version to ${cleaned} in these files:`);
      updatedFiles.forEach((file) => core.info(`  - ${file}`));
    }

    const versionUnderscored = cleaned.replace(/\./g, '_');
    core.setOutput('version', cleaned);
    core.setOutput('version_underscored', versionUnderscored);
  } catch (error) {
    core.setFailed(`Action failed: ${error.message}`);
    if (error.stack) {
      core.debug(error.stack);
    }
  }
}

run();
