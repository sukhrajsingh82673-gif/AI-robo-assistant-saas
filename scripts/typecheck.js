#!/usr/bin/env node
/**
 * Lightweight type/syntax gate for the browser app.
 *
 * The project is plain ES2020 JavaScript (no TypeScript build), so the real
 * "type check" available without adding a compiler is a full parse of every
 * shipped script plus JSON validation. This catches the class of error that
 * would otherwise only appear in the browser.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const dirs = ['web', 'tests', 'scripts'];
let checked = 0;
const failures = [];

for (const dir of dirs) {
  const full = path.join(root, dir);
  if (!fs.existsSync(full)) continue;
  for (const name of fs.readdirSync(full)) {
    if (!name.endsWith('.js')) continue;
    const file = path.join(full, name);
    try {
      execFileSync(process.execPath, ['--check', file], { stdio: 'pipe' });
      checked += 1;
    } catch (err) {
      failures.push(`${dir}/${name}\n${err.stderr ? err.stderr.toString() : err.message}`);
    }
  }
}

for (const json of ['package.json', 'playwright.config.ts']) {
  const file = path.join(root, json);
  if (!fs.existsSync(file) || !json.endsWith('.json')) continue;
  try {
    JSON.parse(fs.readFileSync(file, 'utf8'));
    checked += 1;
  } catch (err) {
    failures.push(`${json}\n${err.message}`);
  }
}

if (failures.length) {
  console.error(`typecheck failed for ${failures.length} file(s):\n`);
  failures.forEach((failure) => console.error(failure + '\n'));
  process.exit(1);
}

console.log(`typecheck: ${checked} JavaScript files parsed successfully.`);
