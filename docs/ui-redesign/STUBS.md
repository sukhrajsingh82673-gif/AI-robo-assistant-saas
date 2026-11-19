# Stubs and unconnected services

The assistant consolidation removes fabricated answers and sample conversations.
A missing service is always behind an adapter and always says it is not
connected. A sample provider exists only when an operator turns it on and every
result it produces is labelled in the UI.

## Built adapters (Stage 3)

### Web search — `core/ura_assistant_web.py`

| Provider | Switch | Default | Label shown in the UI |
|----------|--------|---------|-----------------------|
| None | `URA_ASSISTANT_WEB_SEARCH_PROVIDER=none` (or unset) | yes | "No web search provider is configured on the server." |
| Tavily | `URA_ASSISTANT_WEB_SEARCH_PROVIDER=tavily`, `TAVILY_API_KEY=…` | no | "Tavily" |
| Brave Search | `URA_ASSISTANT_WEB_SEARCH_PROVIDER=brave`, `BRAVE_SEARCH_API_KEY` (or `BRAVE_API_KEY`) | no | "Brave Search" |
| Sample | `URA_ASSISTANT_WEB_SEARCH_PROVIDER=sample` | no | "Sample web results (not connected)" and "Sample provider is on. Results are labelled sample and are not real sources." |

`auto` (the default) selects Tavily, then Brave, when their key is present;
otherwise it stays on "none". API keys are read from the server environment and
are never sent to the browser.

Web access itself is a Company setting (`assistant_web_access`: `off` |
`allowlist` | `open`, plus `assistant_web_allowlist` and
`assistant_web_blocklist`). Research refuses to run when access is off, when no
provider is configured, or when no source passes the policy, and it says which.
Every excluded source is listed with its reason; nothing is silently dropped.

## Built adapters (Stage 4)

### Calendar — `core/calendar_provider.py`

| Provider | Switch | Default | Label shown in the UI |
|----------|--------|---------|-----------------------|
| Google Calendar | `ZONATA_GOOGLE_CALENDAR_ACCESS_TOKEN` + `ZONATA_GOOGLE_CALENDAR_ID` | — | "Google Calendar" |
| None | unset | yes | "Calendar not connected" and "Calendar is not connected. No meeting can be booked and no link exists." |

Scheduling goes through `AiCeoMeetingService.schedule_meeting_autonomous`. The
assistant only reports a meeting as scheduled when the provider returns
`provider_status=CONFIRMED`; otherwise it returns
`CALENDAR_PROVIDER_NOT_CONFIGURED`, books nothing and shows no link. There is no
fake Meet URL generator anywhere in the assistant.

### Transcription — `core/ura_assistant_meetings.py`

| Provider | Switch | Default | Label shown in the UI |
|----------|--------|---------|-----------------------|
| None | `URA_ASSISTANT_TRANSCRIPTION_PROVIDER=none` (or unset) | yes | "Transcription not connected"; listening returns `TRANSCRIPTION_NOT_CONFIGURED` and opens no microphone. |
| Sample | `URA_ASSISTANT_TRANSCRIPTION_PROVIDER=sample` | no | "Sample transcript (not connected)" and "Sample transcript. No microphone was opened and no audio was captured." |

The sample adapter returns four clearly-labelled lines with `sample=true` and
persists nothing. The recording announcement is a Company setting
(`assistant_meeting_recording_notice`, default on); when it is on, listening
writes one `NOTICE` transcript entry with `related_context='Recording
announcement'` before any further transcript is added.

## Planned adapters

| Need | Adapter (planned) | Default behaviour |
|------|-------------------|-------------------|
| Model | Existing `core/llm_runtime.py` / `core/neon_ai_gateway.py` | Uses the app's configured model. API keys stay in server environment variables; never in the front end. |

When each adapter lands, this file names the exact env switch and the visible
label the UI shows.
