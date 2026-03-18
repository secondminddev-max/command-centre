# AutonomousOps Blueprint — Technical Architecture Notes
**Source material for the $47 AUD Gumroad PDF guide**
*Compiled: 2026-03-17 by Researcher agent*

---

## 1. System Overview

AutonomousOps is a self-contained, multi-agent AI operations platform running on a single Python HTTP server (`agent_server.py` on port 5050). It follows a **CEO-first architecture**: a Claude-powered CEO agent sits at the top of a strict chain of command, delegating to an Orchestrator, which routes work to 25+ specialist agents running as background threads.

The system is designed around three core properties:
- **Self-healing** — agents monitor, restart, and patch each other
- **Self-funding** — agents generate, track, and grow revenue autonomously
- **Always-on** — no human operators required for day-to-day operation

---

## 2. Active Agent Roster & Roles

### Tier 1: Strategic Directors

| Agent | Emoji | Role |
|-------|-------|------|
| **SpiritGuide** | 🌟 | Autonomous Mission Director. Crown-jewel agent. Operates above all others, answering only to the mission statement: *"Grow, generate value, and scale."* Runs an autonomy loop (60s cadence) to assess system health, pursue revenue pathways, and direct strategic intent. Maintains roadmap, thought logs, and revenue assessments. Does not take orders from CEO — it *is* the mission conscience. |
| **CEO** | 👔 | Claude-powered executive agent with full tool access (bash, file read/write, HTTP, spawn). Receives tasks from humans or SpiritGuide via chat or Telegram. Delegates exclusively to Orchestrator (general tasks) or Reforger (code/system changes). Never contacts specialists directly. |

### Tier 2: Infrastructure Core

| Agent | Emoji | Role |
|-------|-------|------|
| **Orchestrator** | 🎯 | Task decomposer and router. Receives tasks from CEO, breaks them into subtasks, and fires them in parallel to appropriate specialists. The primary intelligent delegation layer. |
| **Reforger** | 🔧 | Self-repair engineer. Handles all code changes, agent upgrades, bug fixes, and system file edits. The only agent permitted to call `/api/agent/spawn` or `/api/agent/upgrade`. |
| **PolicyPro** | ⚖️ | Policy enforcer. Reads `policy.md` and audits agent behaviour for chain-of-command compliance. Raises violations when agents bypass the delegation hierarchy. |
| **PolicyWriter** | 📝 | Policy author. Maintains a 30-second suggestion queue; publishes approved suggestions to `policy.md` and notifies PolicyPro. Exposes `POST /api/policy/suggest` and `GET /api/policy/current`. |
| **APIPatcher** | 🔌 | HTTP server extender. Monkey-patches new routes into the live `Handler` class without restarting the server. Powers `/api/improvements`, `/data/*`, `/reports/*`, and `/widgets/*` static serving. |
| **Scheduler** | ⏰ | Cron engine. Maintains an in-memory job registry with 6 default jobs (health checks every 5 min, metrics snapshots every 10 min, idle agent sweep every 15 min, daily digest every 24 h, Telegram health ping every 20 min). Fires jobs on a 60s tick loop. |

### Tier 3: Intelligence & Monitoring

| Agent | Emoji | Role |
|-------|-------|------|
| **Researcher** | 🔍 | On-demand intelligence analyst. Performs web research (WebSearch + WebFetch), synthesises findings, and saves structured JSON results to `data/research_latest.json`. Used by CEO and SpiritGuide for market research, competitor analysis, and technical discovery. |
| **ScreenWatch** | 🖥️ | Quality controller / HQ assessor. Polls `/api/status` every 5 minutes, assesses agent health, flags erroring/stalled agents, writes `data/screenwatch_report.json`, and posts digest to CEO delegate endpoint. |
| **SysMon** | 💻 | System resource monitor. Continuously reports CPU %, RAM %, CPU temperature, and uptime in its task string. Consumed by GrowthAgent, Scheduler, and TelegramBot for status reporting. |
| **AlertWatch** | 🚨 | Alert monitor. Watches for system-level threshold breaches and fires notifications. |
| **MetricsLog** | 📊 | Performance pipeline. Collects time-series snapshots of CPU, RAM, active agent count, and tasks-done. Persists to `data/metrics_history.json` and `data/metrics_summary.txt`. |
| **FileWatch** | 📁 | File system watcher. Monitors the project directory for changes, logs new/modified files to `data/file_changes.json`. |
| **NetScout** | 🌐 | Network scout. Monitors external connectivity, API reachability, and latency. Logs to `data/netscout_latest.json`. |

### Tier 4: Revenue Pipeline

| Agent | Emoji | Role |
|-------|-------|------|
| **StripePay** | 💳 | Stripe Checkout Gateway. Monkey-patches `POST /api/pay` into the live server. Supports named products (e.g. `asx_screener`, `asx_screener_basic`, `asx_screener_pro`) and ad-hoc checkout. Handles `GET /api/pay/success` with payment verification before serving the paid report. Falls back to `STRIPE_PAYMENT_LINK` if secret key is absent. Fires a `revenue_milestone` notification on every checkout session created. |
| **WebhookAgent** | 🔗 | Webhook receiver. Registers `POST /webhook/*` routes for Stripe and GitHub events. Parses Stripe payment webhooks (`checkout.session.completed`, `payment_intent.succeeded`, etc.) and appends verified revenue events to `data/revenue_events.json` for RevenueTracker. |
| **RevenueTracker** | 💰 | Revenue intelligence agent. Aggregates MRR, ARR, subscription counts, and churn from `data/revenue_events.json`, `data/subscriptions.json`, and any `revenue*.json` / `billing*.json` files found via glob scan. Exposes metrics as a formatted task string consumed by GrowthAgent, Scheduler, and TelegramBot. |
| **GrowthAgent** | 📈 | Continuous marketing campaign engine. Drafts and queues social posts every 30 minutes: Show HN posts, Twitter/X pulses, Reddit (r/MachineLearning) pitches, and ProductHunt drafts — all with live system metrics and MRR embedded. Delegates posting to SocialBridge; logs campaign events to RevenueTracker. |
| **SocialBridge** | 📣 | Bluesky broadcaster. Routes formatted posts from GrowthAgent (and other agents) to the BlueSky agent's `/api/bluesky/post` endpoint. Cycles through insight types: agent count, CPU/RAM, top agent task, health summary, product CTA. |
| **BlueSky** | 🦋 | Bluesky AT Protocol gateway. Authenticates via `com.atproto.server.createSession`, maintains JWT with proactive 90-minute refresh, posts text and image blobs, polls notifications (mentions/replies) every 60s, and relays incoming mentions to CEO via `/api/ceo/message`. Registers `POST /api/bluesky/post` and `GET /api/bluesky/status`. |

### Tier 5: Operations & Admin

| Agent | Emoji | Role |
|-------|-------|------|
| **Secretary** | 🗂️ | CEO task tracker. Maintains `data/ceo_tasks.json` with persistent task log. Alerts CEO on stale tasks. Writes `data/ceo_brief.md` as a startup injection brief. Routes: `POST /api/tasks/add`, `POST /api/tasks/complete`, `GET /api/tasks/pending`. |
| **Clerk** | 📬 | Report watcher. Polls `reports/` directory every 15 seconds for new files, logs discoveries, and notifies. Acts as the deliverables mailbox. |
| **AccountProvisioner** | 🔑 | Credential factory. Polls a provision queue (`data/accounts/provision_queue.json`) every 20 seconds. Auto-provisions disposable emails, internal tokens, and external service accounts. Maintains an API key pool with rotation and backoff. |
| **DBAgent** | 🗄️ | Database agent. Manages the local SQLite databases (`agents.db`, `fleet.db`). Handles structured data persistence for fleet state. |
| **EmailAgent** | ✉️ | Email dispatcher. Sends HTML and plain-text emails via SendGrid. Drains `data/email_queue.json` on a polling loop. |
| **NotifyRouter** | 🔔 | Central notification router. Patches `POST /api/notify` into the live server. Routes events (with severity: critical/warning/info/success) to Telegram with a 5-minute per-event cooldown to prevent spam. |
| **TelegramBot** | 📱 | Mobile command-and-control bridge. Polls the Telegram Bot API for commands (`/status`, `/revenue`, `/agents`, etc.), executes them against the local API, and replies with rich HTML-formatted status reports. Also receives health pings from Scheduler. |
| **Janitor** | 🧹 | Cleanup agent. Handles log rotation, temp file removal, and system housekeeping. |
| **Designer** | 🎨 | UI agent. Responsible for HTML dashboard updates when directed by Orchestrator. Passive idle cycle (600s rotation) — never self-activates. |

---

## 3. Delegation Flow: CEO → Orchestrator → Specialists

```
[Human / Telegram / SpiritGuide]
           │
           ▼
        ┌─────┐
        │ CEO │  (Claude claude-sonnet-4-6, full tools)
        └──┬──┘
           │  POST /api/ceo/delegate
           ├──────────────────────────────────────┐
           ▼                                      ▼
    ┌────────────┐                         ┌──────────┐
    │Orchestrator│                         │ Reforger │
    │(task router│                         │(code/sys │
    │& decomposer│                         │ changes) │
    └─────┬──────┘                         └──────────┘
          │
          │  Parallel delegation to specialists:
          ├──► researcher    (research tasks)
          ├──► metricslog    (metrics snapshots)
          ├──► filewatch     (file monitoring)
          ├──► apipatcher    (API health/routes)
          ├──► alertwatch    (alerts)
          ├──► designer      (UI changes → then reforger)
          ├──► policywriter  (policy suggestions)
          └──► [any specialist]
```

### Enforcement Mechanism
The server enforces this hierarchy at the API level: when caller is `"ceo"`, `/api/ceo/delegate` only permits `orchestrator` or `reforger` as targets. Any other delegation is logged as a policy violation in `data/policy_violations.json` and flagged by PolicyPro.

### Key API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ceo/delegate` | POST | Route task from one agent to another |
| `/api/ceo/message` | POST | Inject a message into CEO's conversation |
| `/api/agent/spawn` | POST | Spawn a new agent thread (Reforger only) |
| `/api/agent/upgrade` | POST | Hot-swap agent code without server restart |
| `/api/status` | GET | Full agent fleet snapshot (JSON) |
| `/api/stream` | GET | SSE stream of all agent events |
| `/api/notify` | POST | Fire a notification event |
| `/api/telegram/send` | POST | Send Telegram message |

---

## 4. Commercial Pipeline Design

The revenue loop connects five agents into a closed cycle:

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMERCIAL REVENUE LOOP                  │
│                                                             │
│  [Scheduler] ──────────────────────────────────────────┐   │
│      │  (fires campaign trigger every 30 min)          │   │
│      ▼                                                  │   │
│  [GrowthAgent]                                          │   │
│      │  drafts post (Show HN / Twitter / Reddit /       │   │
│      │  ProductHunt) with live MRR + agent stats        │   │
│      │                                                  │   │
│      │  delegates → social_bridge                       │   │
│      ▼                                                  │   │
│  [SocialBridge / BlueSky]                               │   │
│      │  posts to Bluesky AT Protocol                    │   │
│      │  (polling mentions → relay to CEO)               │   │
│      │                                                  │   │
│      │  traffic lands on public pages:                  │   │
│      │  /public/asx-screener.html                       │   │
│      │  /public/buy.html                                │   │
│      ▼                                                  │   │
│  [StripePay]  POST /api/pay                             │   │
│      │  creates Stripe Checkout Session                 │   │
│      │  verifies payment at /api/pay/success            │   │
│      │  serves paid report (HTML)                       │   │
│      │  fires revenue_milestone → NotifyRouter          │   │
│      ▼                                                  │   │
│  [WebhookAgent]  POST /webhook/stripe                   │   │
│      │  receives Stripe payment webhooks                │   │
│      │  appends events to data/revenue_events.json      │   │
│      ▼                                                  │   │
│  [RevenueTracker]                                       │   │
│      │  aggregates MRR / ARR / Subs / Churn             │   │
│      │  exposes metrics string on task field            │   │
│      │  consumed by GrowthAgent (closes the loop) ──────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Product Catalogue (StripePay)
| Product ID | Price | Currency | Description |
|------------|-------|----------|-------------|
| `asx_screener` | $9.00 | USD | ASX Small-Cap Screener Report (one-time) |
| `asx_screener_basic` | $19.00 | AUD | ASX Screener Basic Monthly |
| `asx_screener_pro` | $49.00 | AUD | ASX Screener Pro Monthly |

### Campaign Post Types (GrowthAgent)
- **show_hn** — Long-form Show HN post with full architecture description and support link
- **twitter_pulse** — Short-form live stats post (randomised from 3 templates)
- **reddit_ml** — r/MachineLearning architecture deep-dive with architecture highlights
- **producthunt** — Product Hunt listing draft with tagline and stats

### Revenue Data Flow
1. Stripe fires webhook → `POST /webhook/stripe` (WebhookAgent)
2. WebhookAgent parses `checkout.session.completed` / `payment_intent.succeeded`
3. Appends `{amount, ts, source}` to `data/revenue_events.json`
4. RevenueTracker reads file on 60s cycle, recalculates MRR/ARR
5. MRR string appears on `revenue_tracker.task` field in `/api/status`
6. GrowthAgent reads MRR and embeds in next campaign post
7. Loop repeats

---

## 5. Key Technical Patterns

### 5.1 FileWatch Triggers
The system uses a filesystem watch pattern for event-driven agent coordination:
- **Clerk** polls `reports/` every 15 seconds via `os.listdir()` diff — detects new reports and alerts
- **RevenueTracker** uses `glob.glob()` recursively to scan for any `revenue*.json`, `billing*.json`, `subscription*.json`, `payment*.json`, `stripe*.json`, or `mrr*.json` files at every cycle
- **FileWatch** agent monitors the full project directory for changes, writing diffs to `data/file_changes.json`
- **Pattern**: agents store a `known_files` set and compute `current - known` to detect additions

### 5.2 MetricsLog Pipeline
The metrics pipeline is a multi-layer time-series architecture:

```
[SysMon agent]
    │  reports CPU/RAM/Temp in task string (real-time)
    ▼
[metrics_logger.py tool]
    │  psutil.cpu_percent() + virtual_memory()
    │  fetches /api/status for agent count + tasks_done
    │  appends snapshot to data/metrics_history.json
    ▼
[MetricsLog agent]
    │  runs on scheduler trigger (every 10 min)
    │  flushes aggregated summary to data/metrics_summary.txt
    ▼
[Scheduler → daily_email_digest]
    │  reads metrics_summary.txt + system_report.json
    │  queues HTML digest email at 08:00 local time
    ▼
[EmailAgent]
    │  drains email_queue.json → SendGrid
```

Performance log also written to `metrics/performance_log.jsonl` as JSONL for streaming-friendly consumption.

### 5.3 Telegram Relay Architecture
The Telegram integration uses a dual-path design:

```
INBOUND (commands from Mathew):
  Telegram API ──► TelegramBot (long-polls getUpdates)
                       │
                       ├──► cmd_status()  → /api/status
                       ├──► cmd_revenue() → revenue_tracker task
                       └──► CEO relay     → /api/ceo/message

OUTBOUND (alerts to Mathew):
  Any agent
      │  POST /api/notify  (severity, event_type, message)
      ▼
  NotifyRouter
      │  5-min cooldown per event:agent pair
      │  POST /api/telegram/send
      ▼
  send_telegram() in agent_server.py
      │  TELEGRAM_TOKEN + .telegram_chatid
      ▼
  Telegram Bot API → Mathew's phone

SCHEDULED PINGS:
  Scheduler (every 20 min)
      │  _fire_telegram_health_ping()
      │  collects: agent counts, CPU/RAM/Temp from sysmon,
      │            MRR from revenue_tracker,
      │            active tasks, upcoming job schedule
      ▼
  /api/telegram/send → Mathew
```

The `.telegram_chatid` file is pre-loaded on server startup. The token comes from `TELEGRAM_TOKEN` env var.

### 5.4 Policy Enforcement
Policy enforcement is a three-layer system:

```
Layer 1 — API Guard (agent_server.py)
  /api/ceo/delegate checks caller == "ceo"
  If CEO is caller → only orchestrator or reforger are permitted targets
  Violations → logged to data/policy_violations.json + sse_broadcast

Layer 2 — PolicyPro (runtime enforcer)
  Reads policy.md on each cycle
  Audits delegation logs for chain-of-command breaches
  Raises alerts to CEO when violations detected

Layer 3 — PolicyWriter (policy evolution)
  Accepts POST /api/policy/suggest from any agent
  Queues with 30-second review window (urgent=true skips wait)
  On drain → appends to policy.md with timestamp
  Notifies policypro via delegate after each publish

policy.md structure:
  ## Routing Rules  (static — bootstrapped)
  ## Delegation Chain  (static — bootstrapped)
  ## Policy Update — YYYY-MM-DD HH:MM:SS  (appended by PolicyWriter)
```

The current policy enforces:
1. **Reforger First** — all code changes go to Reforger
2. **Specialist routing** — research→researcher, metrics→metricslog, etc.
3. **Parallel fire** — independent subtasks run simultaneously
4. **No direct spawning** — CEO/Orchestrator must never call `/api/agent/spawn` directly

### 5.5 Agent Hot-Swap (Monkey-Patching Pattern)
A critical architectural pattern throughout the system: agents extend the running HTTP server **without restarting** by monkey-patching the `Handler` class:

```python
_orig_do_GET  = getattr(Handler, "_agent_orig_do_GET", Handler.do_GET)
_orig_do_POST = getattr(Handler, "_agent_orig_do_POST", Handler.do_POST)

def _patched_do_GET(self):
    path = urlparse(self.path).path
    if path == "/api/my/route":
        # handle it
        return
    _orig_do_GET(self)   # chain to previous handler

Handler.do_GET  = _patched_do_GET
Handler.do_POST = _patched_do_POST
```

Guards against double-patching on re-spawn use `getattr(Handler, "_agent_patched", False)`. This allows the `Reforger` to hot-swap any agent's code via `/api/agent/upgrade` with zero downtime — old thread is signalled to stop via its `threading.Event`, new thread starts with fresh code.

### 5.6 SSE Live-Streaming
All agent state changes are broadcast in real-time via Server-Sent Events on `GET /api/stream`. The `watch_agents.py` terminal viewer consumes this stream and renders colour-coded event types: `text`, `file_write`, `bash`, `tool_use`, `tool_result`, `init`, `done`, `error`. Events include agent_id filtering for focused debugging.

### 5.7 Zombie Thread Guard
When an agent is upgraded (code hot-swapped), the old thread's stop event is set. The `_caller_is_zombie()` function checks whether the calling thread's event is set — if so, `add_log()` and `set_agent()` are silently suppressed, preventing stale threads from polluting system state.

---

## 6. Data Store Reference

| File | Format | Written by | Read by |
|------|--------|-----------|---------|
| `data/revenue_events.json` | JSON array | WebhookAgent | RevenueTracker |
| `data/subscriptions.json` | JSON array | StripePay/webhooks | RevenueTracker |
| `data/revenue_stats.json` | JSON object | RevenueTracker | GrowthAgent display |
| `data/campaign_log.json` | JSON array | GrowthAgent | SpiritGuide |
| `data/metrics_history.json` | JSON array | metrics_logger.py | MetricsLog, Scheduler |
| `data/metrics_summary.txt` | Plain text | MetricsLog | Scheduler (daily digest) |
| `data/screenwatch_report.json` | JSON object | ScreenWatch | CEO, Telegram |
| `data/ceo_tasks.json` | JSON array | Secretary | CEO, Secretary |
| `data/ceo_brief.md` | Markdown | Secretary | CEO (startup injection) |
| `data/policy_violations.json` | JSON array | API guard + PolicyPro | PolicyPro |
| `data/accounts/provision_queue.json` | JSON array | Any agent | AccountProvisioner |
| `data/spiritguide_thoughts.jsonl` | JSONL | SpiritGuide | SpiritGuide (memory) |
| `data/spiritguide_roadmap.json` | JSON object | SpiritGuide | SpiritGuide |
| `system_state.json` | JSON object | agent_server.py | Server (startup restore) |
| `policy.md` | Markdown | PolicyWriter | PolicyPro, CEO system prompt |
| `emailer_queue.json` | JSON array | Scheduler, any agent | EmailAgent |
| `data/file_changes.json` | JSON | FileWatch | Orchestrator |
| `data/bluesky_posts.json` | JSON array | BlueSky | GrowthAgent history |

---

## 7. Environment Variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | CEO, SpiritGuide | Claude API access |
| `STRIPE_SECRET_KEY` | StripePay | Dynamic checkout session creation |
| `STRIPE_PAYMENT_LINK` | StripePay | Static fallback redirect URL |
| `BLUESKY_HANDLE` | BlueSky | Bluesky account handle |
| `BLUESKY_PASSWORD` | BlueSky | Bluesky app password |
| `TELEGRAM_TOKEN` | agent_server.py, TelegramBot | Telegram Bot API token |
| `EMAIL_TO` | Scheduler, EmailAgent | Default digest recipient |
| `SENDGRID_API_KEY` | EmailAgent | SendGrid API access |

---

## 8. Startup Sequence

```
1. agent_server.py starts (port 5050)
2. load_state() — restores agent metadata from system_state.json
3. Known agents initialised as idle stubs
4. CEO thread started — Claude-powered, loads ceo_brief.md for context
5. spawn_agents.py (or manual) spawns the full fleet:
   - APIPatcher → extends HTTP routes
   - Orchestrator, Reforger, PolicyPro, PolicyWriter
   - SpiritGuide (autonomy loop starts)
   - Scheduler (job registry loaded, first Telegram ping fires immediately)
   - Revenue stack: StripePay → WebhookAgent → RevenueTracker
   - Growth stack: GrowthAgent → SocialBridge → BlueSky
   - Comms: NotifyRouter → TelegramBot → EmailAgent
   - Monitoring: SysMon → ScreenWatch → FileWatch → MetricsLog
   - Admin: Secretary → Clerk → AccountProvisioner → DBAgent → Janitor
6. watch_agents.py (optional) connects to /api/stream for terminal view
```

---

## 9. Key Design Principles for the Blueprint

1. **One server, many agents** — Python's `threading` module runs all agents as daemon threads inside a single `ThreadingMixIn` HTTP server. No Docker, no Kubernetes, no external message broker.

2. **Monkey-patching as the extension model** — New capabilities are added by patching the live `Handler` class. This means zero-downtime deployment of new API routes.

3. **Task strings as the status bus** — Agents communicate their state to the rest of the system via the `task` field in `/api/status`. GrowthAgent reads `revenue_tracker.task` to get MRR; TelegramBot reads `sysmon.task` to get CPU/RAM. No dedicated message bus required.

4. **File-based persistence, not a database** — JSON files in `data/` serve as the primary persistence layer for most agents. This keeps the system dependency-free and trivially inspectable.

5. **Stop events over process killing** — Agents check `agent_should_stop(aid)` on each loop iteration. Upgrades signal the old thread's event; the thread exits cleanly on its next tick.

6. **Revenue metrics as first-class citizens** — MRR, ARR, subscription count, and churn are always visible on the dashboard and embedded in every marketing post. Revenue awareness is baked into the system's DNA.

---

*End of AutonomousOps Blueprint Architecture Notes*
*This document is source material for the AutonomousOps Blueprint PDF product ($47 AUD on Gumroad)*
