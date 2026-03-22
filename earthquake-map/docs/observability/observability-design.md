# Observability Design -- Earthquake Map

---

## 1. Overview

The Earthquake Map is a browser-only static application with no server-side component. Traditional observability (centralized logging, distributed tracing, server metrics) does not apply. This document defines the client-side observability approach appropriate for this architecture.

## 2. Scope

| Aspect | Applicable | Rationale |
|--------|-----------|-----------|
| Client-side console logging | Yes | Developer debugging during development and maintenance |
| USGS API request monitoring | Yes | Track fetch success/failure, latency, event counts |
| Server-side logging | No | No server component (CON-01) |
| Distributed tracing | No | Single browser context, no microservices |
| Centralized metrics | No | No backend to collect metrics |
| Alerting | No | No server-side monitoring infrastructure |

## 3. Client-Side Logging

### 3.1 Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Detailed flow information during development | Filter state changes, URL construction details |
| INFO | Normal operational events | Fetch started, fetch completed with N events |
| WARN | Recoverable issues | USGS returned null magnitude for an event, results capped at 20000 |
| ERROR | Failures requiring user notification | Fetch failed, network error, invalid API response |

### 3.2 Structured Log Format

All logging SHALL use structured JSON format via a lightweight logger utility. `console.log` is prohibited per CLAUDE.md coding standards.

**Log entry structure:**

```json
{
  "timestamp": "2026-03-22T10:15:30.123Z",
  "log_level": "INFO",
  "component": "USGSClient",
  "event_name": "fetch_completed",
  "detail": {
    "earthquake_count": 342,
    "fetch_duration_ms": 1250,
    "query_start_time": "2026-03-15T00:00:00Z",
    "query_end_time": "2026-03-22T00:00:00Z",
    "query_min_magnitude": 1.0
  }
}
```

### 3.3 Logger Implementation

A minimal `Logger` utility module (`src/ui/logger.js` or inline in `app.js`) wrapping `console.debug`, `console.info`, `console.warn`, `console.error` with structured JSON output. Log level is configurable via a `LOG_LEVEL` constant (default: `INFO` in production, `DEBUG` in development).

## 4. USGS API Request Monitoring

### 4.1 Metrics Captured (In-Browser Only)

| Metric | Description | Traces |
|--------|-------------|--------|
| `fetch_duration_ms` | Time from fetch start to response received | NFR-01 |
| `earthquake_count` | Number of events returned | FR-14 |
| `fetch_success` | Boolean indicating success or failure | FR-12, FR-13 |
| `fetch_error_reason` | Error message on failure | FR-13 |
| `results_capped` | Boolean indicating if 20000 limit was reached | NFR-05 |

These metrics are logged to the browser console in structured format. No external metrics backend is used.

### 4.2 Performance Timing

The application SHALL measure fetch duration using `performance.now()` around the USGS API call and log it at INFO level. This supports verification of NFR-01 (3-second initial render target).

## 5. Error Observability

| Error Category | Detection | User Notification | Logging |
|---------------|-----------|-------------------|---------|
| Network failure | fetch rejection | Error message displayed (FR-13) | ERROR level with error details |
| HTTP 4xx/5xx | Response status check | Error message displayed (FR-13) | ERROR level with status code and body |
| Invalid GeoJSON | Parse failure | Error message displayed (FR-13) | ERROR level with parse error |
| Null magnitude | Field null check | Marker rendered with default styling | WARN level noting the event ID |

## 6. Development-Time Observability

During development and testing, the following browser developer tools are the primary observability channel:

- **Console tab:** Structured JSON logs from the Logger utility
- **Network tab:** USGS API request/response inspection, timing waterfall
- **Performance tab:** Frame rate monitoring for NFR-02 (60fps with 5000 markers)

No additional tooling (OpenTelemetry, Grafana, etc.) is required for this browser-only application.
