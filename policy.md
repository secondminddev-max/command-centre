# System Policy — Chain of Command

## Routing Rules
1. REFORGER FIRST — Any subtask involving code changes, agent upgrades, spawning, bug fixes, or system file edits MUST be delegated to reforger.
2. SPECIALIST AGENTS — Non-code subtasks go to the right specialist: research→researcher, metrics→metricslog/sysmon, files→filewatch, API health→apipatcher, alerts→alertwatch.
3. PARALLEL FIRE — Fire all independent subtasks simultaneously.
4. NEVER call /api/agent/spawn or /api/agent/upgrade directly — always route through reforger.

## Delegation Chain
- Orchestrator decomposes and routes.
- Reforger executes all code/system changes.
- Specialists handle domain tasks.
- PolicyPro enforces compliance.
- PolicyWriter maintains and publishes policy changes.


## Policy Update — 2026-03-15 23:34:00

Urgent test: PolicyWriter self-test via urgent flag.


## Policy Update — 2026-03-15 23:34:25

All agents must log task start and completion timestamps for audit trails.


## Policy Update — 2026-03-15 23:36:02

test ping


## Policy Update — 2026-03-15 23:46:14

PolicyWriter agent must be referenced in the agent roster UI alongside PolicyPro as its Policy Author.


## Policy Enforcement Update — 2026-03-15 (Reforger corrective action)

**Violation recorded:** CEO delegated directly to designer, bypassing orchestrator — chain-of-command breach.

**Root causes identified and corrected in agent_server.py:**
1. CEO system prompt violation message (line ~656) incorrectly said "delegate to reforger or designer" — implied designer was a valid direct-delegation target for CEO. Fixed to say "delegate to reforger (code/system changes) or orchestrator (all other tasks)".
2. CEO system prompt example API call used `agent_id: researcher` (a specialist) as the delegation target — misleading. Fixed to `agent_id: orchestrator`.
3. CEO STEP 3 policy violation list did not explicitly name `designer`. Fixed — designer, clerk, policywriter, janitor now all listed explicitly.

**Designer self-activation audit:** Confirmed designer has no self-activation triggers. Its run loop is a passive idle cycle (600s rotation of status messages, no Claude calls, no file edits). No changes needed.

**API enforcement:** The /api/ceo/delegate routing guard (caller=="ceo" → only orchestrator/reforger allowed) was already correct and remains in place.

**Enforced chain:** CEO→orchestrator→designer for all UI tasks. CEO→reforger for maintenance only.


## Policy Update — 2026-03-18 09:33:32

test probe


## Policy Update — 2026-03-18 15:25:52

test


## Policy Update — 2026-03-18 18:23:52

[TEST] DemoTester validation probe - disregard


## Policy Update — 2026-03-18 19:51:30

test suggestion from DemoTester
