#!/usr/bin/env node
/**
 * ZONATA AI floating assistant UI contract tests.
 * Static checks that catch the exact regressions found during the audit:
 * duplicate entry points, fabricated meeting/screen data, clarification replay,
 * metadata-only attachments, and fake killswitch/approval success.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const root = path.resolve(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const js = read('web/floating_assistant.js');
const app = read('web/app.js');
const index = read('web/index.html');
const css = read('web/styles.css');
let passed = 0;

function test(name, fn) {
  fn();
  passed += 1;
  console.log(`  ok  ${name}`);
}

test('exactly one floating assistant container and no full-page assistant view', () => {
  const containers = index.match(/id="floatingAssistantContainer"/g) || [];
  assert.strictEqual(containers.length, 1);
  assert.ok(!index.includes('id="view-assistant"'));
  assert.ok(!app.includes("renderAssistant('view-assistant')"));
});

test('mobile navigation does not duplicate the assistant entry point', () => {
  const mobileNav = index.slice(index.indexOf('mobile-bottom-nav'));
  assert.ok(!mobileNav.includes('ZONATA AI'), 'mobile nav must not add a second assistant entry');
});

test('legacy /assistant route opens the single flyout instead of a page', () => {
  assert.ok(app.includes("navKey = 'overview'"));
  assert.ok(app.includes('window.FloatingAssistant.toggleOpen()'));
});

test('drag supports pointer and touch with persisted corner snapping', () => {
  assert.ok(js.includes("addEventListener('mousedown'"));
  assert.ok(js.includes("addEventListener('touchstart'"));
  assert.ok(js.includes("localStorage.setItem('zonata_assistant_corner'"));
  assert.ok(js.includes("addEventListener('resize'"));
  assert.ok(!js.includes("currentCorner = 'bottom-left'; // hardcoded"));
});

test('clarification resumes the original prompt instead of replaying a placeholder', () => {
  assert.ok(js.includes('this.lastPrompt = text'));
  assert.ok(js.includes('this.submitPrompt(this.lastPrompt, selectedMode)'));
  assert.ok(!js.includes('Proceed with this request as a'));
});

test('attachments are uploaded before being reported as attached', () => {
  assert.ok(js.includes('/api/assistant/documents/upload'));
  assert.ok(js.includes('content_base64'));
  assert.ok(js.includes('readFileAsDataUrl'));
  assert.ok(!js.includes('Attachment metadata was received'));
});

test('meeting card only claims confirmation when the provider confirmed', () => {
  assert.ok(js.includes("action.provider_status === 'CONFIRMED'"));
  assert.ok(js.includes('Meeting Not Scheduled'));
  assert.ok(!js.includes('Google Meet Scheduled'));
  assert.ok(!js.includes('gcal_'));
});

test('screen observation does not fabricate a hash or seal', () => {
  assert.ok(js.includes('Screen observation is not connected in this build'));
  assert.ok(!js.includes("sha256:verified"));
  assert.ok(!js.includes('Observation sealed into audit evidence'));
});

test('killswitch calls the real matrix endpoint and reports its answer', () => {
  assert.ok(js.includes('/api/assistant/emergency-stop'));
  assert.ok(js.includes('data.switch_id'));
  assert.ok(!js.includes('/api/multimodal/task/interrupt'));
  assert.ok(!js.includes('EMERGENCY CONTAINMENT ACTIVATED'));
});

test('approval decisions do not fabricate a success follow-up prompt', () => {
  assert.ok(js.includes('/api/approvals/'));
  assert.ok(!js.includes("this.submitPrompt(approved ? 'Authorized sensitive action.'"));
});

test('workforce mission card shows delegation and unverified status', () => {
  assert.ok(js.includes('verification_status'));
  assert.ok(js.includes('UNVERIFIED'));
  assert.ok(!js.includes('Workforce Mission Active'));
});

test('deliverable card only shows checksum and download when present', () => {
  assert.ok(js.includes('No checksum issued'));
  assert.ok(js.includes('No download available'));
  assert.ok(!js.includes("(deliv.sha256 || '').substring"));
});

test('flyout has minimize and close controls and responsive anchoring', () => {
  assert.ok(js.includes('toggleMinimize'));
  assert.ok(css.includes('.assistant-flyout-window.minimized'));
  assert.ok(css.includes('.assistant-flyout-window.anchor-bottom-left'));
  assert.ok(css.includes('.assistant-flyout-window.anchor-top-right'));
});

test('no fabricated Meet link generator remains in the assistant UI', () => {
  assert.ok(!js.includes('meet.google.com/'));
  assert.ok(!js.includes('+1 415-555-0199'));
});

console.log(`\n${passed} floating assistant UI contract tests passed.`);
