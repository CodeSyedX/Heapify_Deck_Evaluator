# 10. Server-sent events for progress

Status: accepted · 2026-10-01

## Decision
Pipeline progress is stored as rows in `pipeline_events` and served over SSE, resumable with `Last-Event-ID`. Plain status endpoints exist as a polling fallback. No WebSockets.

## Consequences
Streams are stateless to scale and work through ordinary proxies.
