---
status: diagnosed
trigger: "Investigate why the chatbot presents timestamps in UTC without timezone adjustment or clear labeling."
created: 2026-02-19T00:00:00Z
updated: 2026-02-19T00:00:00Z
---

## Current Focus

hypothesis: Timestamps flow through three layers without UTC labeling being added at any layer, and the system prompt does not instruct the LLM to annotate them as UTC.
test: Traced entire pipeline from KQL -> parse -> serialize -> LLM prompt -> LLM output.
expecting: Confirmed. No UTC annotation is injected anywhere in the stack.
next_action: Report diagnosis (find_root_cause_only mode).

## Symptoms

expected: Timestamps presented to users are clearly labeled as UTC (e.g., "2026-02-18T14:32:00Z (UTC)") OR converted to a local/configurable timezone.
actual: Timestamps are displayed by the LLM without any UTC label or timezone conversion. Users see bare ISO strings like "2026-02-18T14:32:00+00:00" with no indication of timezone.
errors: No runtime errors -- purely a UX/presentation gap.
reproduction: Query incidents or alerts. LLM receives ISO timestamps. Nothing in the pipeline labels them as UTC before the LLM synthesizes a response.
started: Always -- never implemented.

## Eliminated

- hypothesis: The datetime objects lose their timezone info during parsing
  evidence: _parse_datetime() (sentinel_client.py:356-376) explicitly attaches tzinfo=UTC to all datetimes, including naive datetimes and epoch fallbacks. Timezone info is NOT lost.
  timestamp: 2026-02-19

- hypothesis: isoformat() strips timezone info during serialization
  evidence: datetime objects with UTC tzinfo produce "+00:00" suffix when isoformat() is called (Python stdlib behavior). The suffix is present in serialized output. Timezone info is NOT stripped.
  timestamp: 2026-02-19

- hypothesis: The projection layer strips timezone-related fields
  evidence: Projections (projections.py) filter by field name (e.g., "created_time", "time_generated"), not by value. They pass through whatever isoformat() produced including the "+00:00" suffix.
  timestamp: 2026-02-19

## Evidence

- timestamp: 2026-02-19
  checked: sentinel_client.py _parse_datetime() (lines 356-376)
  found: All datetimes are normalized to UTC. Naive datetimes get tzinfo=UTC attached. String "Z" suffix is replaced with "+00:00" for fromisoformat(). Epoch fallback also carries UTC. No timezone conversion to local time is performed.
  implication: Data is UTC at parse time, but there is no opportunity for conversion here without knowing the user's timezone preference.

- timestamp: 2026-02-19
  checked: models.py Incident.to_dict() (lines 117-130), Alert.to_dict() (lines 150-156), TrendPoint.to_dict() (lines 167-172)
  found: All three serialize datetimes via val.isoformat() with no additional annotation. datetime(2026, 2, 18, 14, 32, 0, tzinfo=UTC).isoformat() produces "2026-02-18T14:32:00+00:00". No "UTC" label is appended, no field rename to "created_time_utc" occurs.
  implication: The serialized dict that reaches the LLM has keys like "created_time": "2026-02-18T14:32:00+00:00". The "+00:00" suffix is technically correct, but non-SOC-analysts may not recognize it as UTC.

- timestamp: 2026-02-19
  checked: models.py format_relative_time() (lines 12-44)
  found: This function produces human strings like "5 minutes ago", "yesterday at 3:14 PM". The "yesterday at 3:14 PM" branch uses dt.strftime('%I:%M %p') with no timezone suffix. The time shown is in UTC but reads as a local-style time, which is the most confusing case.
  implication: Relative-time strings like "yesterday at 3:14 PM" contain a time component (from a UTC datetime) with no UTC label. A user in UTC-5 seeing "yesterday at 3:14 PM" would interpret it as 3:14 PM local time, but it is actually 3:14 PM UTC (10:14 AM their time).

- timestamp: 2026-02-19
  checked: projections.py PROJECTIONS dict (lines 12-57)
  found: incident_list and incident_detail projections include both "created_time" (raw ISO) and "created_time_ago" (relative string). alert_list includes "time_generated" and "time_generated_ago". Both the raw ISO and the relative string reach the LLM for every incident/alert.
  implication: The LLM receives two representations -- the "+00:00"-suffixed ISO and the ambiguous relative string. It may use either when composing a response.

- timestamp: 2026-02-19
  checked: prompts.py SYSTEM_PROMPT (lines 8-81)
  found: The system prompt contains no instruction about timezone handling. It does not tell the LLM to: (a) label timestamps as UTC, (b) append "(UTC)" to times it presents, (c) mention timezone in any context. The only timestamp-adjacent rule is Grounding Rule 1 (present only facts from tool results).
  implication: The LLM is free to present timestamps in whatever format it deems natural. Without explicit instruction, it will likely drop the "+00:00" technical suffix and present times as bare clock values, or use the relative strings without any timezone qualifier.

- timestamp: 2026-02-19
  checked: openai_client.py send_message() (lines 78-196)
  found: Tool results are JSON-serialized via json.dumps(result) (line 154) and injected into conversation as tool messages. No post-processing of timestamps occurs here. The LLM receives the raw JSON from to_dict() directly.
  implication: No opportunity for timezone annotation exists at the send_message layer either.

- timestamp: 2026-02-19
  checked: main.py run_chat() (lines 24-94)
  found: The response string from session.send_message() is printed as-is via print(f"\nAssistant: {response}"). There is no post-processing, regex, or formatting pass that could add timezone labels to displayed timestamps.
  implication: Final display layer also adds no UTC context. Whatever the LLM says is printed verbatim.

## Resolution

root_cause: Three compounding gaps across the stack:

  GAP 1 (PRIMARY -- models.py format_relative_time, lines 38-39):
    The "yesterday at HH:MM AM/PM" branch of format_relative_time() formats a UTC datetime
    using strftime('%I:%M %p') with no timezone qualifier. The resulting string looks like
    local clock time but is actually UTC. This is the most misleading case because it
    presents a specific wall-clock time with no timezone context, so any user not in UTC
    will misread it.

  GAP 2 (PRIMARY -- prompts.py SYSTEM_PROMPT):
    The system prompt contains zero instructions about timezone labeling. The LLM has no
    directive to label timestamps as UTC, append "(UTC)", or caveat that all times are in UTC.
    Without this directive the LLM will present timestamps however it deems natural, which
    typically means omitting the technical "+00:00" suffix and presenting bare times.

  GAP 3 (SECONDARY -- models.py Incident/Alert/TrendPoint to_dict(), lines 128-130, 154-156, 169):
    isoformat() produces "+00:00" rather than "Z". While technically correct, "+00:00" is less
    immediately recognizable as UTC than "Z" or an explicit "(UTC)" annotation. More importantly,
    there is no field naming convention (e.g., "created_time_utc") that would signal to the LLM
    that the value is UTC.

fix: (not applied -- diagnosis-only mode)
  File 1: src/models.py
    - format_relative_time(): In the "yesterday" branch (line 38), append " UTC" to the
      formatted time string so it reads "yesterday at 3:14 PM UTC".
    - Incident.to_dict(), Alert.to_dict(), TrendPoint.to_dict(): Replace val.isoformat()
      with val.strftime("%Y-%m-%dT%H:%M:%SZ") to use the conventional "Z" suffix, OR
      append a comment-style key alongside (e.g., include a "_timezone": "UTC" field).

  File 2: src/prompts.py
    - Add a rule to the SYSTEM_PROMPT's "Response Style" or "Grounding Rules" section
      instructing the LLM to always label timestamps as UTC when presenting them to users.
      Example addition: "All timestamps from tool results are in UTC. Always include '(UTC)'
      when presenting specific times to users."

verification: n/a -- diagnosis only, no fix applied.
files_changed: []
