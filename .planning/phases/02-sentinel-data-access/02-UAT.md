---
status: testing
phase: 02-sentinel-data-access
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-02-18T12:00:00Z
updated: 2026-02-19T09:28:45Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 3
name: Get Incident Detail by Number
expected: |
  get_incident_detail(1) returns a composite result with three sections: incident detail (with classification, labels, incident_url), related alerts, and related entities. entity_count matches actual entity list length.
awaiting: user response

## Tests

### 1. Unit Test Suite Passes
expected: Running `pytest` produces 77 passing tests across 4 files with zero failures and zero ruff lint errors.
result: pass

### 2. Query Incidents from Live Sentinel
expected: query_incidents(last_30d, Informational, limit=5) returns a QueryResult with incident objects containing fields: number, title, severity, status, created_time. Query time shown in metadata.
result: pass

### 3. Get Incident Detail by Number
expected: get_incident_detail(1) returns a composite result with three sections: incident detail (with classification, labels, incident_url), related alerts, and related entities. entity_count matches actual entity list length.
result: [pending]

### 4. Query Alerts from Live Sentinel
expected: query_alerts(last_30d, Informational, limit=5) returns typed Alert objects with fields: display_name, severity, status, time_generated, tactics, techniques, provider_name.
result: [pending]

### 5. Get Alert Trend with Auto-Bin
expected: get_alert_trend(last_30d, Informational) returns TrendPoint objects bucketed by day (auto-selected "1d" bin for 30-day window). Each point has timestamp, count, and severity.
result: [pending]

### 6. Get Top Entities Ranked by Alert Count
expected: get_top_entities(last_30d, Informational, limit=10) returns EntityCount objects with entity_type (account/ip/host), entity_name, and count — sorted descending by count.
result: [pending]

### 7. Error Handling — Invalid Time Window
expected: query_incidents(time_window="last_999d") returns a QueryError (not an exception) with code "invalid_time_window" and retry_possible=False.
result: [pending]

## Summary

total: 7
passed: 2
issues: 0
pending: 5
skipped: 0

## Gaps

[none yet]
