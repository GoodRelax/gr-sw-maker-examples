# Interview Record

## Date: 2026-03-22

## Participants
- User (project owner)
- Claude Code (full-auto-dev)

## Interview Summary

### User Order (Input)
- **What:** Earthquake Map — browser-only interactive map showing global earthquake data
- **Why:** User wants to see where and when earthquakes happened in the world
- **Preferences:** Browser-only (no server), zoomable map, time span filtering

### Clarification Questions & Decisions

| # | Question | Decision | Decided By |
|---|----------|----------|------------|
| 1 | Magnitude filter? | Yes — slider to filter by minimum magnitude, default show all (M1.0+) | Claude (autonomous) |
| 2 | Visual style? | Circles sized and colored by magnitude (small/green → large/red) | Claude (autonomous) |
| 3 | Default time span? | Past 7 days. Custom date range picker for historical queries | Claude (autonomous) |
| 4 | Earthquake detail popup? | Show magnitude, location name, depth, time, link to USGS page | Claude (autonomous) |
| 5 | Historical vs real-time? | Both — default recent, custom date range for historical (USGS API supports decades of data) | Claude (autonomous) |

### Domain Boundaries
- **Core logic:** Date range validation, magnitude filtering, USGS API query construction, earthquake data parsing
- **External libraries (not domain):** Map rendering (Leaflet.js), tile serving (OpenStreetMap), earthquake data (USGS API)

### Scope Boundaries
- **In scope:** Map display, earthquake visualization, time filtering, magnitude filtering, earthquake detail popup
- **Out of scope:** User accounts, data persistence, server-side processing, push notifications, earthquake prediction

### Non-Functional Requirements
- Page load under 3 seconds on broadband
- Smooth map interaction (60fps pan/zoom)
- Graceful handling of USGS API unavailability
- Works on modern browsers (Chrome, Firefox, Safari, Edge)

### Constraints
- Browser-only, no server
- USGS API rate limits (no API key, public access)
- Free tile provider (OpenStreetMap)

### Known Compromises
- Historical queries with large date ranges may return many results; will cap at USGS API limit (20,000 events)
- No offline support
