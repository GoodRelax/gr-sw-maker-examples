# Risk Register

## Date: 2026-03-22

| Risk ID | Description | Probability (1-3) | Impact (1-3) | Score | Mitigation | Status |
|---------|------------|-------------------|--------------|-------|-----------|--------|
| RSK-01 | USGS API becomes unavailable or changes format | 1 | 3 | 3 | Graceful error handling; adapter pattern isolates API dependency | Open |
| RSK-02 | Large date ranges return too many events, degrading browser performance | 2 | 2 | 4 | Cap results at API limit (20,000); warn user; use canvas renderer for large datasets | Open |
| RSK-03 | OpenStreetMap tile server temporarily unavailable | 1 | 2 | 2 | Display error message; map still functional with cached tiles | Open |
| RSK-04 | Cross-origin request issues with USGS API | 1 | 3 | 3 | USGS API supports CORS; fallback error message if blocked | Open |

No risks with score >= 6. No user notification required.
