# Stubs and unconnected services

Nothing is on sample data in this build yet. The assistant consolidation
(stage 1 onward) removes the fabricated Ask URA answer and the sample coworker
conversation. The following services are missing and will be built behind
adapters; until then the assistant must say they are not connected.

| Need | Adapter (planned) | Default behaviour |
|------|-------------------|-------------------|
| Web search / page reading | `WebSearchProvider` | Off unless the Web access setting allows it and a provider is configured. No invented sources. A sample provider exists only when explicitly enabled and is labelled in the UI. |
| Calendar | `CalendarAdapter` around `core/calendar_provider.py` | Google Calendar when `ZONATA_GOOGLE_CALENDAR_*` env is configured; otherwise "Calendar not connected". No fake meeting link. |
| Transcription | `TranscriptionAdapter` | "Transcription not connected" when no provider is configured. Browser speech input can still compose messages. A sample transcript is labelled and opt-in. |
| Model | Existing `core/llm_runtime.py` / `core/neon_ai_gateway.py` | Uses the app's configured model. API keys stay in server environment variables; never in the front end. |

When each adapter lands, this file will name the exact env switch and the
visible label the UI shows.
