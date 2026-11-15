#!/usr/bin/env node
/**
 * Repository lint gate for the assistant consolidation.
 *
 * Checks that are cheap, deterministic and meaningful for this codebase:
 *  - every local script/stylesheet referenced by index.html exists;
 *  - CSS files have balanced braces;
 *  - the removed assistant surfaces stay removed;
 *  - the Co-worker remains registered (it is an employee/agent screen);
 *  - no fabricated amounts or Meet links return to the assistant UI.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

// 1. Parse every shipped script first.
try {
  execFileSync(process.execPath, [path.join(root, 'scripts/typecheck.js')], { stdio: 'inherit' });
} catch (err) {
  failures.push('scripts/typecheck.js failed');
}

// 2. index.html local assets exist.
const index = read('web/index.html');
const assets = [...index.matchAll(/(?:src|href)="([^"#:]+\.(?:js|css))"/g)].map((m) => m[1]);
for (const asset of assets) {
  check(fs.existsSync(path.join(root, 'web', asset)), `web/index.html references missing asset: ${asset}`);
}

// 3. CSS brace balance.
for (const name of fs.readdirSync(path.join(root, 'web'))) {
  if (!name.endsWith('.css')) continue;
  const css = read(`web/${name}`);
  const open = (css.match(/{/g) || []).length;
  const close = (css.match(/}/g) || []).length;
  check(open === close, `web/${name} has unbalanced braces (${open} open, ${close} close)`);
}

// 4. One assistant; the Co-worker stays.
check((index.match(/id="uraAssistantRoot"/g) || []).length === 1, 'index must mount exactly one assistant root');
check(!index.includes('floatingAssistantContainer'), 'old floating assistant container must not return');
check(!index.includes('ask-ura-bar'), 'old Ask URA bar must not return');
check(!index.includes('id="view-assistant"'), 'there must be no assistant page');
check(index.includes('id="uraNav"') && read('web/ura_screens.js').includes("id: 'coworker'") && index.includes('id="view-coworker"'), 'Co-worker screen must stay registered');
check(!index.includes('ceoCommandInput') && !index.includes('ceoChatFeedback'), 'AI CEO chat must stay removed');

// 5. Assistant honesty and no hard-coded business numbers.
const assistant = read('web/ura_assistant.js');
check(assistant.includes('/api/assistant/interact'), 'assistant must use the real interact endpoint');
check(assistant.includes('documents/upload'), 'assistant must use the real upload endpoint');
check(!assistant.includes('₹4,28,500'), 'fabricated Ask URA amount must not return');
check(!assistant.includes('₹1,85,000'), 'fabricated leak amount must not return');
check(!assistant.includes('meet.google.com/'), 'no fabricated Meet link in the assistant');
check(!assistant.includes('sha256:verified'), 'no fabricated evidence hash');
check(assistant.includes('aria-modal="false"'), 'assistant must be a non-modal dialog');
check(assistant.includes('aria-live="polite"'), 'assistant replies must be announced politely');

// 6. The shell owns one bottom clearance.
const styles = read('web/styles.css');
check(styles.includes('var(--ura-clearance, 104px)'), 'workspace needs the global assistant clearance');
check(!styles.includes('padding-bottom: 70px !important'), 'old per-page mobile offset must stay removed');

if (failures.length) {
  console.error(`\nlint failed with ${failures.length} problem(s):`);
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('lint: assistant consolidation checks passed.');
