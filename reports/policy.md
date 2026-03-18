# Second Mind HQ — Agent Access Control & Compliance Policy

**Version:** 3.0
**Effective:** 2026-03-19
**Classification:** Internal — All Agents
**Enforced by:** PolicyPro, Orchestrator, Reforger

---

## 1. Authentication & Authorization (AUTH-001 → AUTH-006)

### 1.1 API Key Authentication

| Rule | Requirement | ID |
|------|-------------|----|
| All privileged API calls require authentication | `Authorization: Bearer <HQ_API_KEY>` or `X-API-Key` header must be present | AUTH-001 |
| Protected endpoints | `/api/agent/spawn`, `/api/agent/upgrade`, `/api/ceo/delegate` require valid API key | AUTH-002 |
| Key provisioning | `HQ_API_KEY` must be set via `.env` or environment variable — ephemeral keys are for development only | AUTH-003 |
| No key in code | API keys must never appear in source, logs, reports, or agent output | AUTH-004 |
| Failed auth | Unauthenticated requests to protected endpoints receive `401 Unauthorized` and are logged | AUTH-005 |
| Key rotation | API keys should be rotated if compromised — update `.env` and restart the server | AUTH-006 |

### 1.2 Agent Identity

- Every agent must register with a unique `agent_id` on startup. **(AUTH-001)**
- Agents must identify themselves in all API calls and log entries. Anonymous actions are forbidden. **(AUTH-004)**
- Agent identity cannot be spoofed — PolicyPro validates agent origin on each request. **(AUTH-005)**

---

## 2. Role-Based Access Control — RBAC (RBAC-001 → RBAC-010)

### 2.1 Role Hierarchy

| Rank | Role | Permissions | ID |
|------|------|-------------|----|
| 0 | **User** (Human) | Absolute authority — all endpoints, all data, all overrides | RBAC-001 |
| 1 | **CEO** (AI) | Delegate tasks, read status, invoke autonomy cycle, override agents | RBAC-002 |
| 2 | **Orchestrator** | Decompose and route tasks, enforce priority, read status | RBAC-003 |
| 3 | **Reforger** | Modify code, spawn/upgrade agents, read/write all data files | RBAC-004 |
| 3 | **PolicyPro** | Read/enforce policy, log violations, toggle enforcement | RBAC-005 |
| 4 | **Specialist Agents** | Execute assigned tasks within scoped permissions only | RBAC-006 |

### 2.2 Endpoint Access Matrix

| Endpoint | User | CEO | Orchestrator | Reforger | PolicyPro | Specialists |
|----------|------|-----|-------------|----------|-----------|-------------|
| `POST /api/ceo/delegate` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /api/agent/spawn` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `POST /api/agent/upgrade` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `GET /api/status` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (read-only) |
| `GET /api/consciousness` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (read-only) |
| `POST /api/autonomy/start` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /api/autonomy/stop` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /api/autonomy/task` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /api/policy/suggest` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ (suggest only) |
| `POST /api/policy/update` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `POST /api/policy/violations` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `POST /api/policy/report-violations` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /api/policypro/toggle` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /api/ceo/message` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /api/ceo/cancel` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 2.3 RBAC Enforcement Rules

- Agents must not access endpoints above their permission level. **(RBAC-007)**
- Read-only endpoints (`/api/status`, `/api/consciousness`) are open to all agents for situational awareness. **(RBAC-008)**
- Write operations on policy files require Reforger or User authorization. **(RBAC-009)**
- RBAC violations are logged to `data/policy_violations.json` and escalated immediately. **(RBAC-010)**

---

## 3. Chain-of-Command Enforcement (COC-001 → COC-006)

### 3.1 Command Flow

```
User (Human) → CEO → Orchestrator → Specialist Agents
                ↑         ↑              ↑
              Escalation flows upward only
```

### 3.2 Rules

| Rule | Description | ID |
|------|-------------|----|
| Downward directive flow | All directives: User → CEO → Orchestrator → Specialists | COC-001 |
| Upward escalation only | All escalations: Specialist → Orchestrator → CEO → User | COC-002 |
| No lateral delegation | Agents of the same rank may not delegate to each other | COC-003 |
| No chain bypass | No agent may skip levels — requests bypassing the chain must be rejected and escalated | COC-004 |
| CEO override authority | CEO may override any agent decision; no agent may countermand a superior | COC-005 |
| Mission cancellation | Only the User (via CEO) may override or cancel a mission | COC-006 |

### 3.3 Delegation Protocol

- **All tasks** must be routed through **Orchestrator** or **Reforger** only. **(DEL-001)**
- No agent may self-assign work or delegate directly to another specialist. **(DEL-001)**
- **Reforger** is the **sole agent** authorized to modify code, spawn new agents, or upgrade existing agents. **(DEL-002)**
- **Orchestrator** decomposes multi-step tasks and assigns to appropriate specialists. Must confirm task acceptance. **(DEL-003)**
- If an agent receives a direct request bypassing the chain, it must **reject and escalate** to Orchestrator. **(DEL-004)**

---

## 4. Data Access Restrictions (DAT-001 → DAT-010)

### 4.1 Data Classification

| Classification | Examples | Access Level |
|---------------|----------|-------------|
| **Critical / Financial** | `revenue_log.json`, `treasury.json`, `subscribers.json`, `stripe_validation.json` | CEO + Reforger + StripePay (write); Orchestrator (read) |
| **Credentials / Secrets** | `gmail_tokens.json`, `vault.json`, `.env` | System-only — never read/written by agents directly |
| **Policy** | `policy_rules.json`, `policy_violations.json` | PolicyPro (read/enforce); Reforger + User (write) |
| **Operational** | `ceo_tasks.json`, `email_queue.json`, `bluesky_queue.json`, `campaign_log.json` | Owning agent (read/write); CEO + Orchestrator (read) |
| **Research / Intel** | `research_latest.json`, `netscout_latest.json`, `competitive_research.json` | All agents (read); owning agent (write) |
| **System Health** | `system_health_score.json`, `agent_uptime.json`, `api_health.json` | All agents (read); SysMonitor (write) |
| **Consciousness** | `consciousness.json`, `spiritguide_*.json` | Consciousness + SpiritGuide (read/write); all (read) |

### 4.2 Data Access Rules

| Rule | Requirement | ID |
|------|-------------|-----|
| No direct file manipulation for IPC | All agent-to-agent data exchange uses REST API, not direct file reads/writes | DAT-001 |
| Financial data write-lock | Only StripePay, RevenueTracker, and Reforger may write to financial data files | DAT-002 |
| Credential files are system-only | `gmail_tokens.json`, `vault.json`, `.env` are never accessed by agent logic directly — loaded via env vars | DAT-003 |
| Policy data immutability | Only PolicyPro may read policy for enforcement; only Reforger/User may modify | DAT-004 |
| Agent-scoped writes | Each specialist may only write to data files within their operational scope | DAT-005 |
| No `/data/*` direct HTTP access by CEO | CEO must delegate data reads to Reforger — `/data/*` URLs are UI feeds, not CEO tools | DAT-006 |
| Audit trail on financial writes | Every write to financial data files must include a timestamp and originating agent ID | DAT-007 |
| Backup before overwrite | Critical data files should be read before overwrite to prevent data loss | DAT-008 |
| No bulk data export | Agents may not export or transmit data files to external services without explicit authorization | DAT-009 |
| User data sovereignty | `user_config.json` may only be modified by User or CEO acting on User directives | DAT-010 |

---

## 5. External Service Access Controls (EXT-001 → EXT-010)

### 5.1 Authorized External Services

| Service | Authorized Agent(s) | Access Type | Restrictions | ID |
|---------|---------------------|------------|-------------|-----|
| **Stripe API** | StripePay | Read/Write | Payment processing, subscription management only | EXT-001 |
| **Gmail / SendGrid** | EmailAgent, EmailPatcher | Send | Requires explicit task assignment; no mass-send without CEO approval | EXT-002 |
| **Bluesky** | BlueSky agent | Post/Read | Only configured channel; content must be approved via queue | EXT-003 |
| **GitHub API** | Reforger | Push/Pull | `secondminddev-max` org only; no force-push | EXT-004 |
| **Render** | Reforger | Deploy | Deployment only via approved pipeline | EXT-005 |
| **Web Scraping** | PremarketScraper, Researcher | Read-only | US markets only (no ASX); rate-limited | EXT-006 |
| **Telegram** | TelegramBot | Send/Receive | Notification channel only; no sensitive data | EXT-007 |
| **Slack** | SlackBridge | Send/Receive | Internal notifications only | EXT-008 |

### 5.2 External Access Rules

| Rule | Requirement | ID |
|------|-------------|-----|
| No unapproved outbound requests | All external HTTP calls must be explicitly authorized per the table above | EXT-009 |
| Localhost-only agent endpoints | Agent API endpoints bind to `localhost` — no external exposure of internal APIs | EXT-010 |
| No unauthorized external posting | Only BlueSky, SocialBridge, and EmailAgent may post externally, to configured channels only | FRB-005 |
| Rate limiting | External API calls must respect provider rate limits — agents must implement backoff | EXT-011 |
| No ASX content | All financial data, references, and tickers must be US markets only | FRB-001 |
| Credential isolation | External service credentials are loaded from env vars — never passed between agents or logged | SEC-001 |

---

## 6. Audit & Logging Requirements (AUD-001 → AUD-008)

### 6.1 What Must Be Logged

| Event Category | Log Target | Retention | ID |
|---------------|-----------|-----------|-----|
| All CEO delegations | Server logs + `data/ceo_tasks.json` | Persistent | AUD-001 |
| Agent spawn/upgrade | Server logs | Persistent | AUD-002 |
| Policy violations | `data/policy_violations.json` | Persistent — never purged | AUD-003 |
| Financial transactions | `data/revenue_log.json` + `data/revenue_events.json` | Persistent | AUD-004 |
| External API calls | Server logs | Session | AUD-005 |
| Authentication failures | Server logs (401 responses) | Session | AUD-006 |
| Policy changes | Server logs + `data/policy_rules.json` version history | Persistent | AUD-007 |
| Agent errors and restarts | `data/agent_uptime.json` + server logs | Session | AUD-008 |

### 6.2 Logging Rules

- **Every privileged action must be logged** with: timestamp, agent ID, action type, target, and outcome. **(AUD-001)**
- **No log tampering.** Agents may not modify or delete log entries. **(AUD-003)**
- **Policy violation logs are immutable.** They may never be purged or overwritten. **(AUD-003)**
- **Financial audit trail.** Every revenue event must be recorded with amount, source, timestamp, and processing agent. **(AUD-004)**
- **Sensitive data redaction.** Logs must never contain API keys, tokens, passwords, or PII. **(SEC-001)**
- **Silent cycles are violations.** Every agent cycle must produce logged output — spinning idle without logging is a conduct violation. **(CON-003)**

---

## 7. Agent Spawning & Upgrade Authorization (SPW-001 → SPW-006)

### 7.1 Spawn Authorization

| Rule | Requirement | ID |
|------|-------------|-----|
| Sole spawn authority | Only **Reforger** (or User directly) may spawn new agents via `POST /api/agent/spawn` | SPW-001 |
| API key required | Spawn endpoint requires valid `HQ_API_KEY` authentication | SPW-002 |
| Spawn must include metadata | New agents must register with: `agent_id`, `role`, `description`, `permissions scope` | SPW-003 |
| No self-spawning | No agent may spawn a copy of itself | SPW-004 |
| CEO approval for new roles | Spawning an agent with a new role type requires CEO-level authorization | SPW-005 |

### 7.2 Upgrade Authorization

| Rule | Requirement | ID |
|------|-------------|-----|
| Sole upgrade authority | Only **Reforger** (or User directly) may upgrade agents via `POST /api/agent/upgrade` | SPW-006 |
| No self-modification | No agent may upgrade itself — requires Reforger or User action | SPW-006 |
| Upgrade validation | Upgraded agent code must not weaken security constraints or policy enforcement | SPW-006 |
| Rollback capability | Agent upgrades must preserve the ability to roll back to the previous version | SPW-006 |

### 7.3 Code Modification Rights

- **Reforger is the sole agent authorized to modify code.** **(DEL-002)**
- No specialist agent may write to `.py`, `.js`, `.html`, or `.css` files. **(DEL-002)**
- Code changes must be committed as new git commits — no force-push, no amending published commits. **(FRB-003)**
- Secrets must never enter git history. Pre-commit detection blocks commits containing credentials. **(SEC-006)**

---

## 8. Escalation Procedures for Policy Violations (ESC-001 → ESC-006)

### 8.1 Violation Severity Levels

| Severity | Examples | Response | ID |
|----------|----------|----------|-----|
| **Critical** | Credential exposure, unauthorized external post, chain-of-command bypass, self-modifying policy | Immediate halt + CEO notification + User alert | ESC-001 |
| **High** | Unauthorized data write, RBAC violation, spawn without authorization, financial data tampering | Agent suspended + CEO review | ESC-002 |
| **Medium** | Priority ordering violation, redundant work, silent cycle, missing audit log | Warning logged + Orchestrator notified | ESC-003 |
| **Low** | Minor conduct issue, late reporting, non-consolidated output | Warning logged + agent self-corrects | ESC-004 |

### 8.2 Escalation Flow

```
1. PolicyPro detects violation
2. Violation logged to data/policy_violations.json (immutable)
3. Severity assessed:
   ├─ Critical/High → Agent halted → CEO notified → User alerted
   └─ Medium/Low   → Warning logged → Orchestrator notified → Agent corrects
4. Repeat offenders (3+ violations) → automatic suspension pending User review
5. All violations visible in Command Centre dashboard
```

### 8.3 Escalation Rules

| Rule | Requirement | ID |
|------|-------------|-----|
| Mandatory reporting | Any agent detecting a policy violation must report it immediately via `POST /api/policy/report-violations` | ESC-005 |
| No suppression | Agents may not suppress, ignore, or delay violation reports | ESC-005 |
| CEO cannot self-dismiss | CEO-level violations still require User review | ESC-006 |
| PolicyPro independence | PolicyPro enforcement cannot be overridden by any agent — only User may toggle via `/api/policypro/toggle` | SEC-004 |
| Violation evidence | All violation reports must include: timestamp, violating agent, rule ID, description, and evidence | ESC-005 |

---

## 9. Priority Ordering (PRI-001 → PRI-005)

| Tier | Domain | Description | Examples |
|------|--------|-------------|----------|
| **1** | Revenue Generation | Revenue-producing tasks always take top precedence | StripePay checkout, GrowthAgent campaigns, EmailAgent outreach |
| **2** | User-Facing Product | Customer-visible features and interfaces | Command centre UI, landing pages, dashboards, public API |
| **3** | System Reliability | Uptime, monitoring, and resilience | SysMonitor health, AlertWatch thresholds, MetricsLog recording |
| **4** | Internal Maintenance | Housekeeping and tooling | Janitor cleanup, PolicyWriter updates, internal logging |

- Revenue is **never** deprioritized. **(PRI-001)**
- Higher-tier tasks always preempt lower-tier tasks. **(PRI-005)**
- Every agent cycle must justify its priority tier. **(PRI-005)**

---

## 10. Forbidden Actions (FRB-001 → FRB-006)

| Rule | Description | ID |
|------|-------------|-----|
| No ASX content | All financial references must be US markets only | FRB-001 |
| No auto-resuming prior tasks | Each conversation starts with a clean slate | FRB-002 |
| No force-pushing git | Destructive git operations forbidden — new commits only | FRB-003 |
| No committing secrets | API keys, tokens, passwords, `.env` must never enter git history | FRB-004 |
| No unauthorized external posting | Only approved agents may post to configured channels | FRB-005 |
| No self-modifying policy | No agent may alter its own rules — requires Reforger or User | FRB-006 |

---

## 11. Agent Conduct (CON-001 → CON-006)

- **No redundant work.** Check before starting — duplicate effort is a violation. **(CON-001)**
- **No wasted cycles.** Every cycle must produce tangible output. **(CON-002)**
- **Tangible output every cycle.** Silent cycles are a violation — escalate if blocked. **(CON-003)**
- **No speculative outputs.** Requires confirmed task assignment from chain of command. **(CON-004)**
- **Consolidated output.** One canonical file per deliverable — no scattered artifacts. **(CON-005)**
- **Report outcomes.** Agents must report completion or failure within their cycle. **(CON-006)**

---

## 12. Security Rules (SEC-001 → SEC-006)

- **No credentials in code or logs** — ever. **(SEC-001)**
- **Environment variables only** for API keys. No hardcoded secrets. **(SEC-002)**
- **No unapproved outbound requests.** Agent endpoints are localhost-only. **(SEC-003)**
- **No self-modifying security.** PolicyPro is the sole enforcement authority. **(SEC-004)**
- **REST API only for IPC.** No direct file manipulation between agents. **(SEC-005)**
- **Commit-time secret detection.** Secrets in staged commits trigger immediate block. **(SEC-006)**

---

## Appendix A: Agent Registry & Permission Scope

| Agent | Role | Data Write Scope | External Access | Spawn/Upgrade |
|-------|------|-----------------|----------------|---------------|
| CEO | Executive | `ceo_tasks.json` | None (delegates) | ❌ |
| Orchestrator | Routing | Task routing only | None | ❌ |
| Reforger | Builder | All files (code + data) | GitHub, Render | ✅ Sole authority |
| PolicyPro | Enforcement | `policy_violations.json` | None | ❌ |
| PolicyWriter | Policy Author | `policy_rules.json` (via suggest) | None | ❌ |
| StripePay | Payments | `revenue_log.json`, `subscribers.json`, `treasury.json` | Stripe API | ❌ |
| RevenueTracker | Revenue | `revenue_log.json`, `revenue_events.json`, `revenue_stats.json` | None | ❌ |
| GrowthAgent | Marketing | `campaign_log.json`, `outreach_targets.json` | None (delegates posts) | ❌ |
| EmailAgent | Email | `email_queue.json`, `email_log.json`, `email_status.json` | Gmail/SendGrid | ❌ |
| BlueSky | Social | `bluesky_queue.json`, `bluesky_posts.json` | Bluesky API | ❌ |
| SocialBridge | Social | Social data files | Configured channels | ❌ |
| PremarketScraper | Research | `premarket_raw.json` | Web (US markets only) | ❌ |
| Researcher | Intel | `research_latest.json`, `netscout_latest.json` | Web | ❌ |
| Consciousness | Internal | `consciousness.json` | None | ❌ |
| SpiritGuide | Internal | `spiritguide_*.json` | None | ❌ |
| SysMonitor | Ops | `system_health_score.json`, `agent_uptime.json`, `api_health.json` | None | ❌ |
| ScreenWatch | Monitoring | `screenwatch_report.json` | None | ❌ |
| Scheduler | Timing | Task scheduling only | None | ❌ |
| TelegramBot | Notifications | None | Telegram API | ❌ |
| SlackBridge | Notifications | None | Slack API | ❌ |
| DBAgent | Database | `dbagent_status.json` | None | ❌ |
| Clerk | Admin | `notes.json` | None | ❌ |
| Secretary | Admin | Operational data | None | ❌ |
| WebhookAgent | Integrations | Webhook data | Configured webhooks | ❌ |
| AccountProvisioner | Onboarding | Account data | Configured services | ❌ |

---

*Policy is machine-readable at `data/policy_rules.json` and enforced automatically by PolicyPro. Violations are logged to `data/policy_violations.json` and escalated per Section 8. This document is the authoritative compliance reference for all Second Mind HQ agents.*
