#!/usr/bin/env node
/**
 * URA Assistant UI contract tests.
 *
 * These are static guarantees for the one-assistant rule, the Co-worker
 * boundary, route aliases, drag/snap persistence, upload honesty and the
 * non-fabricated meeting/screen/killswitch states.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const root = path.resolve(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const js = read('web/ura_assistant.js');
const app = read('web/app.js');
const index = read('web/index.html');
const css = read('web/ura_assistant.css');
const styles = read('web/styles.css');
let passed = 0;

function test(name, fn) {
  fn();
  passed += 1;
  console.log(`  ok  ${name}`);
}

test('exactly one assistant mount and no full-page assistant view', () => {
  assert.strictEqual((index.match(/id="uraAssistantRoot"/g) || []).length, 1);
  assert.ok(!index.includes('floatingAssistantContainer'));
  assert.ok(!index.includes('ask-ura-bar'));
  assert.ok(!index.includes('id="view-assistant"'));
  assert.ok(!index.includes('floating_assistant.js'));
});

test('the Co-worker screen, route, nav and renderer are preserved', () => {
  assert.ok(index.includes('data-nav="coworker"'));
  assert.ok(index.includes('id="view-coworker"'));
  assert.ok(index.includes('assistant_coworker_workspace.js'));
  assert.ok(index.includes('apple_coworker_assistant.js'));
  assert.ok(app.includes("cleanPath.startsWith('/coworker')"));
  assert.ok(app.includes("navKey = 'coworker'"));
  assert.ok(app.includes("renderCoworker('view-coworker')"));
});

test('AI CEO chat is gone and legacy CEO links open the assistant', () => {
  assert.ok(!index.includes('ceoCommandInput'));
  assert.ok(!index.includes('ceoChatFeedback'));
  assert.ok(app.includes("cleanPath.startsWith('/ceo')"));
  assert.ok(app.includes('window.URAAssistant.open({ focus'));
  assert.ok(index.includes('data-nav="ceo-records"'));
  assert.ok(app.includes("cleanPath.startsWith('/company/ceo-records')"));
  assert.ok(app.includes("render('view-ceo-records')"));
});

test('mobile navigation has one assistant tab and no floating launcher', () => {
  const mobileNav = index.slice(index.indexOf('mobile-bottom-nav'));
  assert.strictEqual((mobileNav.match(/id="mobileAssistantTab"/g) || []).length, 1);
  assert.ok(mobileNav.includes('toggleSheet()'));
  assert.ok(css.includes('.ura-launcher { display: none !important; }'));
});

test('legacy /assistant and /meeting links open the single window', () => {
  assert.ok(app.includes("cleanPath.startsWith('/assistant')"));
  assert.ok(app.includes("cleanPath.startsWith('/meeting')"));
  assert.ok(app.includes('window.URAAssistant.open()'));
  assert.ok(app.includes("focus: 'meetings'"));
});

test('launcher drag uses pointer events and persists eight snap anchors', () => {
  assert.ok(js.includes("addEventListener('pointerdown'"));
  assert.ok(js.includes("pointermove"));
  assert.ok(js.includes('computeAnchor'));
  assert.ok(js.includes("['top-left'"));
  assert.ok(js.includes("['bottom-right'"));
  assert.ok(js.includes('localStorage.setItem(this.storageKey'));
  assert.ok(js.includes("data-anchor"));
  assert.ok(js.includes('startResize'));
  assert.ok(js.includes('clamp(rect.width'));
});

test('window has dock, expand, minimise, close and persisted size/mode', () => {
  assert.ok(js.includes("action === 'dock'"));
  assert.ok(js.includes("action === 'expand'"));
  assert.ok(js.includes("action === 'minimise'"));
  assert.ok(js.includes("action === 'close'"));
  assert.ok(js.includes('this.winPos'));
  assert.ok(css.includes(".ura-window[data-mode='docked']"));
  assert.ok(css.includes(".ura-window[data-mode='expanded']"));
});

test('clarification resumes the original prompt instead of a placeholder', () => {
  assert.ok(js.includes('this.lastPrompt = prompt'));
  assert.ok(js.includes('if (this.lastPrompt) this.send(this.lastPrompt)'));
  assert.ok(!js.includes('Proceed with this request as a'));
});

test('attachments are uploaded before being reported as attached', () => {
  assert.ok(js.includes('/api/assistant/documents/upload'));
  assert.ok(js.includes('content_base64'));
  assert.ok(js.includes('readAsDataURL'));
  assert.ok(!js.includes('Attachment metadata was received'));
});

test('meeting card only claims confirmation when the provider confirmed', () => {
  assert.ok(js.includes("action.status === 'SCHEDULED' && action.provider_status === 'CONFIRMED'"));
  assert.ok(js.includes('Meeting not scheduled'));
  assert.ok(!js.includes('Google Meet Scheduled'));
  assert.ok(!js.includes('gcal_'));
});

test('screen observation does not fabricate a hash or seal', () => {
  assert.ok(js.includes('Screen observation is not connected in this build'));
  assert.ok(!js.includes('sha256:verified'));
  assert.ok(!js.includes('Observation sealed into audit evidence'));
});

test('emergency stop calls the real endpoint and reports its answer', () => {
  assert.ok(js.includes('/api/assistant/emergency-stop'));
  assert.ok(js.includes('data.switch_id'));
  assert.ok(!js.includes('/api/multimodal/task/interrupt'));
  assert.ok(!js.includes('EMERGENCY CONTAINMENT ACTIVATED'));
});

test('approval decisions use the real approval endpoint', () => {
  assert.ok(js.includes('/api/approvals/'));
  assert.ok(js.includes('/decide'));
  assert.ok(!js.includes("this.send('Authorized sensitive action.')"));
});

test('workforce mission card shows delegation and unverified status', () => {
  assert.ok(js.includes('verification_status'));
  assert.ok(js.includes('UNVERIFIED'));
  assert.ok(!js.includes('Workforce Mission Active'));
});

test('deliverable card only shows checksum and download when present', () => {
  assert.ok(js.includes('deliverable.sha256 ?'));
  assert.ok(js.includes('deliverable.download_url ?'));
  assert.ok(!js.includes("(deliv.sha256 || '').substring"));
});

test('the shell reserves one global bottom clearance, not per-page offsets', () => {
  assert.ok(styles.includes('var(--ura-clearance, 104px)'));
  assert.ok(styles.includes('padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px))'));
  assert.ok(!styles.includes('padding-bottom: 70px !important'));
});

test('non-modal dialog, aria-live and keyboard contract', () => {
  assert.ok(js.includes('aria-modal="false"'));
  assert.ok(js.includes('aria-live="polite"'));
  assert.ok(js.includes("event.key === 'Enter' && !event.shiftKey"));
  assert.ok(js.includes("event.key === 'ArrowUp'"));
  assert.ok(js.includes('Ctrl/Cmd+J'));
  assert.ok(app.includes("e.key.toLowerCase() === 'j'"));
});

test('no fabricated Meet link generator remains in the assistant UI', () => {
  assert.ok(!js.includes('meet.google.com/'));
  assert.ok(!js.includes('+1 415-555-0199'));
});

// ---------------------------------------------------------------------------
// Stage 2 — streaming service, typed tools, agents, memory, confirmations
// ---------------------------------------------------------------------------

test('the browser consumes the NDJSON assistant stream with a fallback', () => {
  assert.ok(js.includes('/api/assistant/stream'));
  assert.ok(js.includes('getReader()'));
  assert.ok(js.includes('consumeLines'));
  assert.ok(js.includes('handleStreamEvent'));
  assert.ok(js.includes("event.type === 'tool'"));
  assert.ok(js.includes("event.type === 'confirm'"));
  assert.ok(js.includes('page_context'));
  assert.ok(js.includes('/api/assistant/interact'));
  const service = read('core/ura_assistant_service.py');
  assert.ok(service.includes('def stream('));
  assert.ok(service.includes('"type": "tool"'));
  assert.ok(service.includes('"type": "answer"'));
  assert.ok(service.includes('"type": "done"'));
});

test('typed tools are gated, previewed and executed only after confirmation', () => {
  const service = read('core/ura_assistant_service.py');
  for (const tool of [
    'navigate', 'query_data', 'delegate_task', 'decide_approval',
    'change_setting', 'run_security_scan', 'generate_report',
    'install_agent', 'connect_integration', 'run_terminal'
  ]) {
    assert.ok(service.includes(`"${tool}"`), `missing typed tool ${tool}`);
  }
  assert.ok(service.includes('def execute_tool('));
  assert.ok(service.includes('requires_confirmation') || service.includes('mutating'));
  assert.ok(js.includes('/api/assistant/tool'));
  assert.ok(js.includes('confirmTool'));
  assert.ok(js.includes('data-confirm-index'));
});

test('company scope requires an approved cowork permission and never fakes it', () => {
  const service = read('core/ura_assistant_service.py');
  assert.ok(service.includes('(kind:'));
  assert.ok(service.includes('cowork)'));
  assert.ok(service.includes('company_permission'));
  assert.ok(service.includes('request_company_permission'));
  assert.ok(service.includes('PERMISSION_REQUIRED'));
  assert.ok(js.includes('Company scope is locked'));
});

test('agent routing supports the six executive roles', () => {
  const service = read('core/ura_assistant_service.py');
  for (const role of ['CEO', 'COO', 'CMO', 'CTO', 'CFO', 'CHRO']) {
    assert.ok(service.includes(`"${role}": {`), `missing agent ${role}`);
  }
  assert.ok(service.includes('resolve_agent'));
  assert.ok(js.includes('setAgentChip'));
  assert.ok(js.includes('uraAgentChip'));
});

test('memory has remember, list, forget and clear paths', () => {
  assert.ok(js.includes("data-plus=\"remember\""));
  assert.ok(js.includes("data-plus=\"memory\""));
  assert.ok(js.includes('/api/assistant/memory'));
  assert.ok(js.includes('rememberLast'));
  assert.ok(js.includes('openMemory'));
  assert.ok(js.includes('forgetMemory'));
  const service = read('core/ura_assistant_service.py');
  assert.ok(service.includes('def remember('));
  assert.ok(service.includes('def list_memories('));
  assert.ok(service.includes('def forget('));
  assert.ok(service.includes('def clear_memories('));
  const server = read('api_server.py');
  assert.ok(server.includes('/api/assistant/stream'));
  assert.ok(server.includes('/api/assistant/tool'));
  assert.ok(server.includes('/api/assistant/memory'));
  assert.ok(server.includes('/api/assistant/permission'));
});

test('stream events are honest about permissions and confirmations', () => {
  const service = read('core/ura_assistant_service.py');
  assert.ok(service.includes('Nothing was read from company data'));
  assert.ok(service.includes('I have not executed it'));
  const server = read('api_server.py');
  assert.ok(server.includes('The assistant stream failed. Nothing was executed.'));
  assert.ok(service.includes('def _tool_connect_integration'));
  assert.ok(service.includes('cannot complete it from chat'));
  assert.ok(service.includes('Terminal commands are not executed from the assistant chat'));
});

// ---------------------------------------------------------------------------
// Stage 3 — background jobs, web research and web access
// ---------------------------------------------------------------------------

test('background jobs use the server store with a three-job limit', () => {
  const jobs = read('core/ura_assistant_jobs.py');
  const server = read('api_server.py');
  const service = read('core/ura_assistant_service.py');
  assert.ok(jobs.includes('MAX_ACTIVE_JOBS = 3'));
  assert.ok(jobs.includes('def create('));
  assert.ok(jobs.includes('def active_count('));
  assert.ok(jobs.includes('def reset_for_retry('));
  assert.ok(jobs.includes('def recover_jobs(') || service.includes('def recover_jobs('));
  for (const action of ['pause', 'resume', 'cancel', 'retry', 'takeover']) {
    assert.ok(service.includes(`"${action}"`), `missing job action ${action}`);
  }
  assert.ok(server.includes('/api/assistant/jobs'));
  assert.ok(server.includes('/action'));
  assert.ok(server.includes('/watch'));
  assert.ok(js.includes("fetch('/api/assistant/jobs'"));
  assert.ok(js.includes('/action`'));
  assert.ok(js.includes('/watch`'));
  assert.ok(js.includes('startBackground'));
  assert.ok(js.includes('watchJob'));
  assert.ok(js.includes('jobRequest'));
  assert.ok(js.includes('markJobsSeen'));
  assert.ok(js.includes('of ${limit} active') || js.includes('active`'));
});

test('jobs render their status, progress and result honestly', () => {
  const jobs = read('core/ura_assistant_jobs.py');
  const service = read('core/ura_assistant_service.py');
  assert.ok(js.includes('uraJobsPanel'));
  assert.ok(js.includes('uraJobsList'));
  assert.ok(js.includes('jobStatusLabel'));
  assert.ok(js.includes('JOB_RESULT'));
  assert.ok(js.includes('HANDOFF'));
  assert.ok(css.includes('.ura-job-bar'));
  assert.ok(css.includes(".ura-job-status[data-status='FAILED']"));
  assert.ok(jobs.includes('status="FAILED"'));
  assert.ok(service.includes('so it did not') || jobs.includes('so it did not'));
  assert.ok(!js.includes('Job completed successfully'));
});

test('web research is provider-backed, cited and labelled when sample', () => {
  const web = read('core/ura_assistant_web.py');
  const service = read('core/ura_assistant_service.py');
  assert.ok(web.includes('class WebSearchProvider'));
  assert.ok(web.includes('class NoWebSearchProvider'));
  assert.ok(web.includes('class SampleWebSearchProvider'));
  assert.ok(web.includes('provider_id = "sample"'));
  assert.ok(web.includes('Sample data. Not a real source.'));
  assert.ok(web.includes('WEB') || service.includes('"source_type": "WEB"'));
  assert.ok(service.includes('def _tool_web_research'));
  assert.ok(service.includes('web_research'));
  assert.ok(js.includes('WEB_SOURCES'));
  assert.ok(js.includes('Sample provider is on'));
  assert.ok(js.includes('sample data, not real pages'));
  assert.ok(js.includes('WEB_ACCESS_OFF'));
  assert.ok(!js.includes('TAVILY_API_KEY'));
  assert.ok(!js.includes('BRAVE_SEARCH_API_KEY'));
});

test('web access is a company setting with off, allow list and open modes', () => {
  const definitions = read('core/settings/definitions.py');
  const server = read('api_server.py');
  const web = read('core/ura_assistant_web.py');
  for (const key of ['assistant_web_access', 'assistant_web_allowlist', 'assistant_web_blocklist']) {
    assert.ok(definitions.includes(`"${key}"`), `missing setting ${key}`);
  }
  assert.ok(web.includes('def load_web_access('));
  assert.ok(web.includes('def filter_results('));
  assert.ok(web.includes('"off", "allowlist", "open"'));
  assert.ok(server.includes('/api/assistant/web-access'));
  assert.ok(js.includes('/api/assistant/web-access'));
  assert.ok(js.includes('saveWebAccess'));
  assert.ok(js.includes('uraWebPanel'));
  assert.ok(css.includes('.ura-field'));
});

test('a background job that cannot run fails with a plain reason', () => {
  const jobs = read('core/ura_assistant_jobs.py');
  const service = read('core/ura_assistant_service.py');
  assert.ok(jobs.includes('Web access is off for this workspace'));
  assert.ok(jobs.includes('No web search provider is configured'));
  assert.ok(jobs.includes('Company scope is required'));
  assert.ok(service.includes('The server restarted while this job was running'));
  assert.ok(jobs.includes('Excluded by the access policy'));
  assert.ok(!jobs.includes('No problem'));
});

// ---------------------------------------------------------------------------
// Stage 4 — meetings, briefs, live notes and governed action items
// ---------------------------------------------------------------------------

test('meetings run behind typed adapters and never fake a calendar', () => {
  const meetings = read('core/ura_assistant_meetings.py');
  assert.ok(meetings.includes('class TranscriptionAdapter'));
  assert.ok(meetings.includes('class NoTranscriptionAdapter'));
  assert.ok(meetings.includes('class SampleTranscriptionAdapter'));
  assert.ok(meetings.includes('URA_ASSISTANT_TRANSCRIPTION_PROVIDER'));
  assert.ok(meetings.includes('def calendar_status('));
  assert.ok(meetings.includes('Calendar not connected'));
  assert.ok(meetings.includes('resolve_calendar_provider'));
  assert.ok(!meetings.includes('meet.google.com/new'));
  assert.ok(!meetings.includes('Generate a link'));
});

test('a sample transcript is opt-in, labelled and records no audio', () => {
  const meetings = read('core/ura_assistant_meetings.py');
  assert.ok(meetings.includes('Sample transcript line'));
  assert.ok(meetings.includes('no audio was captured'));
  assert.ok(meetings.includes('"sample": True'));
  assert.ok(meetings.includes('TRANSCRIPTION_NOT_CONFIGURED'));
  assert.ok(meetings.includes('did not open a microphone'));
  assert.ok(js.includes('Sample transcript. No microphone was opened'));
  assert.ok(!js.includes('Recording started'));
});

test('meeting notes, summaries and minutes come from the stored record', () => {
  const meetings = read('core/ura_assistant_meetings.py');
  assert.ok(meetings.includes("mode=\"NOTE\""));
  assert.ok(meetings.includes('generate_post_meeting_records'));
  assert.ok(meetings.includes('No live notes were recorded.'));
  assert.ok(meetings.includes('No decisions were recorded in this session.'));
  assert.ok(meetings.includes('Recording announcement'));
  assert.ok(js.includes('MEETING_SUMMARY'));
  assert.ok(js.includes('Minutes PDF'));
  assert.ok(css.includes('.ura-meeting-summary'));
  assert.ok(js.includes('MEETING_NOTES') && js.includes('MEETING_NOTE'));
});

test('action items become a governed task or a pending approval', () => {
  const meetings = read('core/ura_assistant_meetings.py');
  assert.ok(meetings.includes('create_coworker_task'));
  assert.ok(meetings.includes('ApprovalPipeline.create_request'));
  assert.ok(js.includes('waiting for a decision'));
  assert.ok(js.includes('MEETING_ACTION'));
  assert.ok(js.includes("kind === 'APPROVAL'"));
  assert.ok(js.includes('Nothing was executed'));
  assert.ok(!js.includes('Task completed'));
});

test('the meeting brief counts live rows and invents nothing', () => {
  const meetings = read('core/ura_assistant_meetings.py');
  const service = read('core/ura_assistant_service.py');
  assert.ok(meetings.includes('def brief('));
  assert.ok(meetings.includes('Pending approvals'));
  assert.ok(meetings.includes('Suggested agenda'));
  assert.ok(meetings.includes('No pending approvals'));
  assert.ok(service.includes('"meeting_brief"'));
  assert.ok(service.includes('"meeting_library"'));
  assert.ok(service.includes('"meeting_listen"'));
  assert.ok(service.includes('"meeting_note"'));
  assert.ok(service.includes('"meeting_summary"'));
  assert.ok(service.includes('"meeting_action"'));
  assert.ok(service.includes('"schedule_meeting"'));
  assert.ok(js.includes('MEETING_BRIEF'));
  assert.ok(js.includes('MEETING_LIBRARY'));
  assert.ok(css.includes('.ura-agenda'));
});

test('meeting endpoints are company-gated and the panel says why', () => {
  const server = read('api_server.py');
  assert.ok(server.includes('def _ura_meeting_access('));
  assert.ok(server.includes('/api/assistant/meetings'));
  assert.ok(server.includes('/api/assistant/meetings/brief'));
  assert.ok(server.includes('/api/assistant/meetings/listen'));
  assert.ok(server.includes('/api/assistant/meetings/notes'));
  assert.ok(server.includes('/api/assistant/meetings/summary'));
  assert.ok(server.includes('/api/assistant/meetings/actions'));
  assert.ok(server.includes('/api/assistant/meetings/recording'));
  assert.ok(server.includes('PERMISSION_REQUIRED'));
  assert.ok(js.includes('renderMeetingsGate'));
  assert.ok(js.includes('uraMeetingsPanel'));
  assert.ok(js.includes('data-meetings-close'));
  assert.ok(js.includes('data-meeting-listen'));
  assert.ok(js.includes('data-recording-toggle'));
});

test('recording announcement is a company setting and scheduling stays honest', () => {
  const definitions = read('core/settings/definitions.py');
  const meetings = read('core/ura_assistant_meetings.py');
  const service = read('core/ura_assistant_service.py');
  assert.ok(definitions.includes('"assistant_meeting_recording_notice"'));
  assert.ok(meetings.includes('RECORDING_SETTING'));
  assert.ok(meetings.includes('announcement'));
  assert.ok(service.includes('CALENDAR_PROVIDER_NOT_CONFIGURED'));
  assert.ok(js.includes('schedule_meeting') || js.includes('MEETING_INVITE'));
  assert.ok(js.includes("action.status === 'SCHEDULED' && action.provider_status === 'CONFIRMED'"));
});

// ---------------------------------------------------------------------------
// Stage 5 — assistant settings are real controls
// ---------------------------------------------------------------------------

test('assistant settings carry a hint, a suggestion and a reason', () => {
  const definitions = read('core/settings/definitions.py');
  const keys = [
    'assistant_show_button', 'assistant_open_as', 'assistant_default_scope',
    'assistant_confirmations', 'assistant_remember_conversations',
    'assistant_background_work', 'assistant_meetings_enabled',
    'assistant_web_access', 'assistant_web_allowlist', 'assistant_web_blocklist',
    'assistant_meeting_recording_notice',
  ];
  keys.forEach((key) => {
    assert.ok(definitions.includes(`"id": "${key}"`), `${key} is defined`);
  });
  const assistantBlock = definitions.slice(definitions.indexOf('--- 8b. URA Assistant ---'));
  assert.ok(assistantBlock.split('"hint":').length - 1 >= keys.length);
  assert.ok(assistantBlock.split('"suggestion":').length - 1 >= keys.length);
  assert.ok(assistantBlock.split('"reason":').length - 1 >= keys.length);
  const models = read('core/settings/models.py');
  assert.ok(models.includes('hint: str = ""'));
  assert.ok(models.includes('suggestion: Any = None'));
  assert.ok(models.includes('reason: str = ""'));
  assert.ok(models.includes('"suggestion":'));
  const registry = read('core/settings/registry.py');
  assert.ok(registry.includes('hint=str(raw.get("hint"'));
  assert.ok(registry.includes('suggestion=raw.get("suggestion")'));
});

test('every assistant setting is enforced somewhere real', () => {
  const registry = read('core/settings/registry.py');
  const enforced = registry.slice(registry.indexOf('ENFORCED_BY'));
  const keys = [
    'assistant_show_button', 'assistant_open_as', 'assistant_default_scope',
    'assistant_confirmations', 'assistant_remember_conversations',
    'assistant_background_work', 'assistant_meetings_enabled',
    'assistant_web_access', 'assistant_web_allowlist', 'assistant_web_blocklist',
    'assistant_meeting_recording_notice',
  ];
  keys.forEach((key) => {
    assert.ok(enforced.includes(`"${key}":`), `${key} names its enforcement point`);
  });
  const sections = read('core/settings/sections.py');
  assert.ok(sections.includes('"assistant": "ai_agents_employees"'));
});

test('the server enforces the assistant settings', () => {
  const service = read('core/ura_assistant_service.py');
  assert.ok(service.includes('def _setting('));
  assert.ok(service.includes('"assistant_background_work"'));
  assert.ok(service.includes('Background work is turned off'));
  assert.ok(service.includes('"assistant_remember_conversations"'));
  assert.ok(service.includes('"assistant_confirmations"'));
  assert.ok(service.includes('confirmations or tool_name == "run_terminal"'));
  assert.ok(service.includes('if not remember:'));
  const server = read('api_server.py');
  assert.ok(server.includes('"assistant_meetings_enabled"'));
  assert.ok(server.includes('MEETINGS_DISABLED'));
  assert.ok(server.includes('code or "PERMISSION_REQUIRED"'));
});

test('the client applies the settings and hides what is off', () => {
  assert.ok(js.includes('async loadAssistantSettings()'));
  assert.ok(js.includes('applyAssistantSettings()'));
  assert.ok(js.includes('backgroundWorkOff()'));
  assert.ok(js.includes('/api/settings/v2/values?category=assistant'));
  assert.ok(js.includes("settings.assistant_show_button !== false"));
  assert.ok(js.includes("settings.assistant_meetings_enabled !== false"));
  assert.ok(js.includes("settings.assistant_background_work !== false"));
  assert.ok(js.includes("settings.assistant_open_as === 'docked'"));
  assert.ok(js.includes("settings.assistant_default_scope === 'COMPANY'"));
  assert.ok(js.includes('Background work is turned off'));
});

test('Settings V2 shows hints, suggestions and applies them in bulk', () => {
  const v2 = read('web/settings_v2.js');
  const v2css = read('web/settings_v2.css');
  assert.ok(v2.includes('definition.hint'));
  assert.ok(v2.includes('sz-suggestion'));
  assert.ok(v2.includes('Suggested:'));
  assert.ok(v2.includes('Use all suggestions'));
  assert.ok(v2.includes('applySuggestions'));
  assert.ok(v2.includes("API + '/values/bulk'"));
  assert.ok(v2.includes("definition.status === 'live'"));
  assert.ok(v2css.includes('.sz-suggestion'));
  assert.ok(v2css.includes('.sz-suggest-btn'));
});

console.log(`\n${passed} URA Assistant UI contract tests passed.`);
