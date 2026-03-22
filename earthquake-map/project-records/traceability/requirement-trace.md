# Requirement Traceability Matrix

| Req ID | Description | Design (Ch3) | Implementation | Test | Scenario |
|--------|------------|-------------|----------------|------|----------|
| FR-01 | Interactive world map | 3.2 MapRenderer | src/ui/map-renderer.js | E2E | SC-001 |
| FR-02 | Fetch default data on load | 3.2 USGSClient | src/adapter/usgs-client.js, src/app.js | usgs-client.test.js | SC-002 |
| FR-03 | Circle markers at epicenter | 3.2 MapRenderer | src/ui/map-renderer.js | E2E | SC-003 |
| FR-04 | Size by magnitude | 3.2 MagnitudeScale | src/domain/magnitude-scale.js | magnitude-scale.test.js | SC-004 |
| FR-05 | Color by magnitude | 3.2 MagnitudeScale | src/domain/magnitude-scale.js | magnitude-scale.test.js | SC-005 |
| FR-06 | Popup with details | 3.2 PopupBuilder | src/ui/popup-builder.js | E2E | SC-006 |
| FR-07 | Time range presets | 3.2 ControlPanel | src/ui/control-panel.js | date-range.test.js | SC-007 |
| FR-08 | Custom date range | 3.2 ControlPanel | src/ui/control-panel.js | date-range.test.js | SC-008 |
| FR-09 | Re-fetch on time change | 3.5 Filter Change | src/app.js | usgs-client.test.js | SC-009 |
| FR-10 | Magnitude slider | 3.2 ControlPanel | src/ui/control-panel.js | E2E | SC-011 |
| FR-11 | Re-fetch on mag change | 3.5 Filter Change | src/app.js | usgs-client.test.js | SC-012 |
| FR-12 | Loading indicator | 3.2 StatusDisplay | src/ui/status-display.js | E2E | SC-013 |
| FR-13 | Error message | 3.2 StatusDisplay | src/ui/status-display.js | usgs-client.test.js | SC-014 |
| FR-14 | Earthquake count | 3.2 StatusDisplay | src/ui/status-display.js | E2E | SC-015 |
| FR-15 | Pan and zoom | 3.2 MapRenderer | Leaflet built-in | E2E | SC-016 |
| FR-16 | Timeout handling | 3.5 Filter Change | src/adapter/usgs-client.js | usgs-client.test.js | — |
| FR-17 | Cancel in-flight request | 3.5 Filter Change | src/app.js | usgs-client.test.js | — |
| FR-18 | Unparseable response | 3.5 Filter Change | src/adapter/usgs-client.js | usgs-client.test.js | — |
| FR-19 | Reject invalid date range | 3.4 DateRange | src/domain/date-range.js | date-range.test.js | — |
| FR-20 | No future end date | 3.4 DateRange | src/domain/date-range.js | date-range.test.js | — |
| NFR-01 | 3s load time | — | Static files + CDN | E2E manual | SC-017 |
| NFR-02 | 60fps with 5000 markers | — | Leaflet circle markers | E2E manual | SC-018 |
| NFR-03 | Browser compatibility | — | Vanilla JS + ES modules | E2E manual | — |
| NFR-05 | Cap notification | 3.2 StatusDisplay | src/ui/status-display.js | usgs-client.test.js | SC-019 |
| NFR-06 | HTTPS only | 3.6 ADR-003 | src/adapter/usgs-client.js | usgs-client.test.js | SC-020 |
| NFR-07 | DOM sanitization | 3.2 PopupBuilder | src/ui/popup-builder.js | E2E | SC-021 |
