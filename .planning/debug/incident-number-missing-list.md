---
status: diagnosed
trigger: "Incident numbers not included when listing incidents in chatbot response"
created: 2026-02-19T00:00:00Z
updated: 2026-02-19T00:00:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - The projection layer strips `number` from the list view data before it reaches the LLM
test: Traced full data path from KQL -> parser -> projection -> LLM
expecting: number field present in KQL output and parser, but removed by projection
next_action: N/A - root cause confirmed

## Symptoms

expected: Incident number (e.g. INC-1234) included in list view when asking "show me high severity incidents"
actual: Incident number is absent from list view; only available when asking for incident details
errors: none (functional issue, not error)
reproduction: Ask chatbot "show me high severity incidents" - no incident numbers in response
started: Phase 3 implementation - may have always been this way

## Eliminated

- hypothesis: KQL query does not project IncidentNumber
  evidence: list_incidents template in src/queries/incidents.py line 14 explicitly projects IncidentNumber as first field
  timestamp: 2026-02-19

- hypothesis: Parser does not read IncidentNumber from rows
  evidence: _parse_incidents() in sentinel_client.py line 194 reads row_dict.get("IncidentNumber", 0) and maps it to `number` field
  timestamp: 2026-02-19

- hypothesis: Incident dataclass missing `number` field
  evidence: Incident dataclass in src/models.py line 97 declares `number: int` as required field
  timestamp: 2026-02-19

- hypothesis: tools.py description hides the field from the LLM
  evidence: tools.py description says "Returns incident number, title, severity, status, and timestamps" - description correctly advertises the field
  timestamp: 2026-02-19

- hypothesis: prompts.py suppresses rendering of incident numbers
  evidence: prompts.py does not restrict which fields to display; it instructs the LLM to present facts from tool results
  timestamp: 2026-02-19

## Evidence

- timestamp: 2026-02-19
  checked: src/queries/incidents.py - list_incidents KQL template
  found: IncidentNumber is the FIRST projected field in the KQL query:
         `| project IncidentNumber, Title, Severity, Status, CreatedTime, LastModifiedTime, Owner, AlertIds, Description, FirstActivityTime, LastActivityTime`
  implication: The data IS returned from Sentinel with IncidentNumber present

- timestamp: 2026-02-19
  checked: src/sentinel_client.py _parse_incidents() lines 193-206
  found: `"number": int(row_dict.get("IncidentNumber", 0))` - IncidentNumber is correctly parsed and mapped to `number` field on every Incident object, whether list view or detail view
  implication: Incident.number is always populated after parsing

- timestamp: 2026-02-19
  checked: src/models.py Incident.to_dict()
  found: to_dict() calls asdict(self) which serializes all dataclass fields including `number`
  implication: `number` key IS present in the dict passed to apply_projection()

- timestamp: 2026-02-19
  checked: src/projections.py PROJECTIONS["incident_list"] lines 13-24
  found: "incident_list" projection list is:
         ["number", "title", "severity", "status", "created_time", "alert_count",
          "entity_count", "last_modified_time", "created_time_ago", "last_modified_time_ago"]
         `number` IS in this list.
  implication: The projection DOES keep the `number` field - it should pass through

- timestamp: 2026-02-19
  checked: src/sentinel_client.py query_incidents() line 429
  found: `projected = [apply_projection(inc.to_dict(), "incident_list") for inc in incidents]`
         This correctly applies the incident_list projection. Since `number` is in PROJECTIONS["incident_list"],
         it is NOT stripped by apply_projection().
  implication: `number` survives the projection step and IS present in the JSON sent to the LLM

- timestamp: 2026-02-19
  checked: src/prompts.py SYSTEM_PROMPT lines 37-39
  found: "Number results in lists using [1], [2], [3] format so users can reference specific items"
         This instructs the LLM to use its OWN sequential numbering [1], [2], [3] for list indexing.
         There is NO instruction to surface the `number` field (the Sentinel incident number) in the output.
  implication: ROOT CAUSE IDENTIFIED - The system prompt's "number results" instruction causes the LLM
               to emit its own [1]/[2]/[3] positional index, and the prompt gives no explicit guidance
               to include the Sentinel incident number alongside each entry. The LLM treats the `number`
               field as internal data rather than something to surface, defaulting to the [1]/[2]/[3]
               display format it was instructed to use.

- timestamp: 2026-02-19
  checked: src/tools.py query_incidents description
  found: "Returns incident number, title, severity, status, and timestamps."
         The tool description tells the LLM to expect an incident number in results, but the system
         prompt's response style instructions do not explicitly tell the LLM to DISPLAY that number.
  implication: Ambiguity between what the tool says it returns and how the system prompt says to format output.
               The [1]/[2]/[3] instruction in the system prompt wins because it is more specific about formatting.

## Resolution

root_cause: |
  The system prompt in src/prompts.py instructs the LLM to "number results in lists using [1], [2], [3]
  format". This positional indexing instruction causes the LLM to display its own sequential counter
  ([1], [2], [3]) for list items rather than surfacing the Sentinel incident `number` field from the
  tool result data. There is no explicit instruction in the prompt telling the LLM to include the
  actual Sentinel incident number (the `number` field) alongside or as part of each list entry.

  The `number` field is correctly available at every stage of the pipeline:
  - KQL: IncidentNumber is projected (src/queries/incidents.py line 14)
  - Parser: mapped to incident.number (src/sentinel_client.py line 194)
  - Dataclass: number field exists (src/models.py line 97)
  - Projection: "number" is in PROJECTIONS["incident_list"] (src/projections.py line 14)
  - Serialization: to_dict() via asdict() includes it
  - LLM input: number is present in the JSON tool result

  The data is present in the tool response sent to the LLM. The LLM simply does not know it should
  display the Sentinel incident number in the list view because the system prompt's formatting guidance
  only tells it to use [1]/[2]/[3] positional indices, not to show "Incident #N" per row.

fix: N/A - diagnose only
verification: N/A
files_changed: []
