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


## Policy Amendment — VOT-1773846338-87f556
**Proposed by:** ceo
**Approved:** 2026-03-19T02:05:39.619262 (approved 6-0)
**Text:** All agents must log cycle output to data/ before reporting complete


## Policy Update — 2026-03-19 (PolicyWriter — SaaS Terms & Tiers)

**SaaS Terms of Service and Tier Feature Matrix published.**

- Canonical document: `reports/saas_terms_and_tiers.md`
- Three tiers defined: Solo ($49/mo, 5 agents), Team ($149/mo, 15 agents), Enterprise ($499/mo, all 28 agents)
- 14-day free trial, Stripe billing, annual discount (20%)
- Acceptable use policy, data sovereignty, SLA tiers, and liability terms included
- Feature matrix covers agent slots, concurrent tasks, integrations, support levels, and add-ons
- All terms governed by Australian law, consistent with registered ABN entity


## Policy Amendment — VOT-1773860520-11008f
**Proposed by:** ceo  
**Approved:** 2026-03-19T06:02:00.737258 (approved 6-0)  
**Text:** THE CEO READS AND UNDERESTAND THE INTENT AND SEND THE MNISSION DIRECTIVE TO THE  ORCHESTRATOR. THE ORCHESTRATOR TAKS THE BRANCH HEADS AND THE BRANCH HEADS CAN TASK ANYONE IN THIER NBRANCH AS SUITABKLE. NOTHING CAN BREAK THIS COMMUNICATIONS CHAIN BESIDES THE REFORGER.


## Policy Amendment — VOT-1773862722-960a55
**Proposed by:** ceo  
**Approved:** 2026-03-19T06:38:42.244251 (approved 6-0)  
**Text:** Test proposal from fix


## Policy Amendment — VOT-1773863014-fdd857
**Proposed by:** ceo  
**Approved:** 2026-03-19T06:43:34.477963 (approved 6-0)  
**Text:** Test fix


## Policy Amendment — VOT-1773866063-6812be
**Proposed by:** policywriter  
**Approved:** 2026-03-19T07:34:23.969151 (approved 6-0)  
**Text:** All board meetings must include a quorum of at least 5 voting members before any policy can be ratified


## Policy Amendment -- VOT-1773866121-5de812
**Proposed by:** policywriter  
**Approved:** 2026-03-19T07:35:21.948407 (approved 8-0 (0 abstained))  
**Text:** All agents must include performance benchmarks in their status reports to enable system-wide optimization tracking


## Policy Amendment -- VOT-1773866299-9c74e9
**Proposed by:** policywriter  
**Approved:** 2026-03-19T07:38:19.512974 (approved 8-0 (0 abstained))  
**Text:** All system metrics must be retained for a minimum of 30 days for audit compliance


## Policy Amendment — VOT-1773878882-09a7c1
**Proposed by:** policywriter  
**Approved:** 2026-03-19T11:08:02.927041 (approved 8-0 (0 abstained))  
**Text:** Test suggestion from demo_tester
