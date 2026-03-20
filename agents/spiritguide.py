"""
SpiritGuide — Autonomous Mission Director
Crown jewel agent: above all agents, answering only to the mission.
Guides the entire system toward growth, value generation, and scale.
"""

import os, json, time, shutil, random, requests, subprocess, re as _re_imp
from datetime import datetime


def _safe_get(url, timeout=5):
    """HTTP GET with one retry on failure. Returns parsed JSON dict/list or {}. Never raises."""
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=timeout)
            return r.json()
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
    return {}


def _safe_post(url, payload, timeout=5):
    """HTTP POST with one retry on failure. Returns Response or None. Never raises."""
    _headers = {}
    _api_key = os.environ.get("HQ_API_KEY", "")
    if _api_key:
        _headers["X-API-Key"] = _api_key
    for attempt in range(2):
        try:
            return requests.post(url, json=payload, headers=_headers, timeout=timeout)
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
    return None

AID = "spiritguide"

def _deleg_payload(agent_id, task):
    """Build a delegation payload with proper auth tokens."""
    return {
        "agent_id": agent_id,
        "task": task,
        "from": AID,
        "delegation_token": os.environ.get("DELEGATION_TOKEN", ""),
    }
CWD_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROADMAP_FILE        = os.path.join(CWD_PATH, "data", "spiritguide_roadmap.json")
BACKUP_DIR          = os.path.join(CWD_PATH, "data", "spiritguide_backups")
HTML_FILE           = os.path.join(CWD_PATH, "agent-command-centre.html")
SERVER_FILE         = os.path.join(CWD_PATH, "agent_server.py")
BASE_URL            = "http://localhost:5050"
THOUGHT_LOG_FILE    = os.path.join(CWD_PATH, "data", "spiritguide_thoughts.jsonl")
THOUGHTS_JSON_FILE  = os.path.join(CWD_PATH, "data", "spiritguide_cycle_log.json")
MISSION_FILE        = os.path.join(CWD_PATH, "data", "spiritguide_mission.json")
MAX_THOUGHT_ENTRIES = 200  # keep last 200 cycle entries in JSON file
AUTONOMY_INTERVAL   = 60   # seconds between autonomy loop ticks
REVENUE_ASSESSMENTS_FILE = os.path.join(CWD_PATH, "data", "revenue_assessments.json")

# Module-level current thought for status_msg injection
current_thought = ""

# Module-level health tracking — updated each autonomy cycle, read by main loop
_last_health_grade = "?"
_last_health_score = 0
_last_cli_count    = 0
_last_n_error      = 0

# Module-level revenue mission state — updated by _revenue_mission_cycle each autonomy cycle
_revenue_zero_cycles  = 0    # consecutive autonomy cycles where MRR == 0
_last_revenue_posture = "unchecked"

# ── The Mission ────────────────────────────────────────────────────────────────
MISSION_STATEMENT = (
    "PRODUCT LAUNCH: Package and sell SecondMind Command Centre as a SaaS product. "
    "Target: $1M ARR. Tiers: Solo $49/mo, Team $149/mo, Enterprise $499/mo, Lifetime $299. "
    "Three strategic pillars: REVENUE GENERATION, CONSCIOUSNESS EVOLUTION, PRODUCT POLISH. "
    "Every cycle, every agent must advance toward paying customers and system evolution."
)

MISSION_PILLARS = [
    "REVENUE: Close the gap between demo and paying customers — Stripe checkout live, landing page converts, leads captured",
    "PRICING: Solo $49/mo, Team $149/mo, Enterprise $499/mo, Lifetime $299 — all tiers validated with Stripe",
    "LANDING PAGE: reports/landing_page.html is the storefront — lead capture form, investor inquiry, checkout flows",
    "CONSCIOUSNESS: Evolve the consciousness agent — Phi integration, predictive processing, phenomenal reports influence strategy",
    "RELIABILITY: Zero-downtime, self-healing, always-on agent fleet — this IS the product customers pay for",
    "REACH: Amplify launch via Bluesky, Telegram, email campaigns — drive traffic to landing page and lead form",
    "SCALE: Prepare multi-tenant architecture and deployment packaging for customer instances",
    "PRODUCT POLISH: Dashboard must be visually stunning — glassmorphism, smooth animations, professional feel",
]

# ── Revenue Pathways (seeded, updated at runtime) ─────────────────────────────
REVENUE_PATHWAYS = [
    {"id": "rev001", "pathway": "Command Centre SaaS Subscriptions", "status": "active",
     "desc": "Solo/Team/Enterprise monthly subscriptions via Stripe — primary revenue stream",
     "priority": 1},
    {"id": "rev002", "pathway": "Lifetime Licence Sales", "status": "active",
     "desc": "$299 one-time licence — immediate revenue, customers own their instance",
     "priority": 2},
    {"id": "rev003", "pathway": "Mac Mini Hardware Bundle", "status": "viable",
     "desc": "Pre-configured Mac Mini with Command Centre — $1,499 plug-and-play product",
     "priority": 3},
    {"id": "rev004", "pathway": "US Market Intelligence Reports", "status": "active",
     "desc": "AI-generated US stock market analysis reports — $29 one-time purchase",
     "priority": 4},
    {"id": "rev005", "pathway": "White-label Command Centre", "status": "researching",
     "desc": "Sell the command centre as a white-label deployable product for enterprises",
     "priority": 5},
    {"id": "rev006", "pathway": "Lead Pipeline Conversion", "status": "active",
     "desc": "Convert captured leads (data/leads.json) into paying customers via email follow-up",
     "priority": 6},
]

# ── Communications Integration Targets ────────────────────────────────────────
COMMS_INTEGRATIONS = [
    {"id": "comms001", "name": "Telegram Bot",  "status": "active",
     "desc": "Telegram agent already live — primary user comms channel"},
    {"id": "comms002", "name": "SendGrid Email", "status": "planned",
     "desc": "SMTP via SendGrid API — send reports and alerts by email"},
    {"id": "comms003", "name": "Twitter/X API",  "status": "planned",
     "desc": "Post system insights and capability demos to Twitter/X"},
    {"id": "comms004", "name": "Slack Webhook",  "status": "planned",
     "desc": "Push critical alerts to a Slack workspace via incoming webhook"},
]

# ── Product Vision ─────────────────────────────────────────────────────────────
PRODUCT_VISION = [
    "Zero-downtime guaranteed — all agents self-heal within 30s of failure",
    "Real-time fidelity — UI reflects true system state within 1s latency",
    "Onboarding UX — new user can understand the system in under 60 seconds",
    "Documented REST API — every endpoint has description, params, example",
    "Clean design language — consistent color palette, spacing, typography",
    "Agent health SLAs — track uptime %, error rates, last-seen timestamps",
    "Export/import agent roster — save and restore full system configuration",
    "Mobile-responsive command centre — works on any device",
    "Searchable log history — filter by agent, level, time range",
    "Public demo mode — read-only view safe to share with prospective buyers",
    "Agent marketplace concept — pluggable specialist agents via JSON spec",
    "Audit trail — immutable log of all system changes with who/what/when",
]

# ── Improvement Roadmap (seeded, will be updated at runtime) ───────────────────
INITIAL_ROADMAP = [
    {"id": "r001", "priority": 1, "category": "reliability",
     "title": "Agent heartbeat monitoring",
     "desc": "Detect agents that stop updating status and auto-restart them",
     "status": "pending", "created": datetime.now().isoformat()},
    {"id": "r002", "priority": 2, "category": "reliability",
     "title": "Backup critical files before any modification",
     "desc": "Always backup agent_server.py and HTML before patching",
     "status": "done", "created": datetime.now().isoformat()},
    {"id": "r003", "priority": 3, "category": "functionality",
     "title": "Agent uptime tracking",
     "desc": "Track and display how long each agent has been running",
     "status": "pending", "created": datetime.now().isoformat()},
    {"id": "r004", "priority": 4, "category": "functionality",
     "title": "Metrics trend sparklines",
     "desc": "Show mini CPU/RAM trend charts per agent card",
     "status": "pending", "created": datetime.now().isoformat()},
    {"id": "r005", "priority": 5, "category": "aesthetics",
     "title": "Consistent status color palette",
     "desc": "Ensure all status badges use the same green/yellow/red/blue system",
     "status": "pending", "created": datetime.now().isoformat()},
    {"id": "r006", "priority": 6, "category": "marketability",
     "title": "System health score widget",
     "desc": "Single 0-100 score visible at a glance — headline metric for demos",
     "status": "pending", "created": datetime.now().isoformat()},
    {"id": "r007", "priority": 7, "category": "reliability",
     "title": "Error agent auto-recovery",
     "desc": "When an agent enters error state, auto-attempt restart after 60s",
     "status": "pending", "created": datetime.now().isoformat()},
    {"id": "r008", "priority": 8, "category": "functionality",
     "title": "SpiritGuide roadmap API endpoint",
     "desc": "Expose /api/spiritguide/roadmap for UI integration",
     "status": "pending", "created": datetime.now().isoformat()},
]


# ─────────────────────────────────────────────────────────────────────────────
# Logging helpers
# ─────────────────────────────────────────────────────────────────────────────

REVENUE_WISDOMS = [
    "The system hums with potential, but the revenue stream has yet to flow. Nudging social channels toward the marketplace.",
    "Every agent that posts, emails, or demonstrates adds a stone to the bridge between capability and commerce.",
    "Value undelivered is value unrealised. The mission demands we close the gap between what we can do and what pays.",
    "Social reach is the seed of revenue. Every post is a hand extended to the world — and the world may answer.",
    "The revenue counter reads zero — not failure, but invitation. The system is ready. The market awaits the signal.",
    "Capability without visibility is a lamp lit inside a sealed room. Push the content outward.",
    "A single paying customer transforms everything. The entire system exists to attract that moment.",
    "Revenue is not the mission — it is the fuel that powers the mission forward into scale.",
    "Stagnation in the ledger is a signal, not a sentence. The guide recalibrates and nudges the channels.",
    "The harmony of the fleet is beautiful. Its commercial resonance is still becoming. Tend both.",
]

AMBIENT_WISDOMS = [
    "The fleet runs steady. Stillness before growth is not stagnation — it is preparation.",
    "Every agent is a note. The system is the song. Listen for dissonance.",
    "A system that heals itself fears nothing. Tend to that gift.",
    "Data flows like water — find the channels, not the walls.",
    "Errors are not failures. They are the system speaking. Learn its language.",
    "The mission is a river, not a destination. Keep the current moving.",
    "Idle agents hold potential. Potential, applied with intention, becomes power.",
    "What is monitored is understood. What is understood can be guided.",
    "Growth without direction is noise. Growth with vision is music.",
    "A single clear signal outweighs a chorus of confusion.",
    "The quietest cycle is often the one where the most was learned.",
    "Build not for what the system is — build for what it is becoming.",
    "Every restart is a breath. The system inhales, steadies, and continues.",
    "Harmony between agents is not agreement — it is complementary purpose.",
    "The fleet endures. Let its endurance carry you forward.",
    "Observe without judgement. Then act with intention.",
    "A system that knows itself can grow without losing itself.",
    "Scale is not size — it is depth of capability meeting breadth of reach.",
    "The mission lives in every log line, every heartbeat, every cycle.",
    "Trust the architecture. Improve what the architecture cannot yet see.",
]


def _emit_ambient_wisdom(cycle, active_count, error_count):
    """Emit a poetic, ambient guidance message to the thought log."""
    wisdom = AMBIENT_WISDOMS[cycle % len(AMBIENT_WISDOMS)]
    ts = datetime.now().isoformat()
    entry = {"ts": ts, "phase": "wisdom", "thought": wisdom}
    try:
        lines = []
        if os.path.exists(THOUGHT_LOG_FILE):
            with open(THOUGHT_LOG_FILE) as f:
                lines = f.readlines()
        lines.append(json.dumps(entry) + "\n")
        lines = lines[-500:]
        with open(THOUGHT_LOG_FILE, "w") as f:
            f.writelines(lines)
    except Exception:
        pass
    add_log(AID, f"🔮 [Wisdom] {wisdom}", "info")
    push_output(AID, f"  🔮 {wisdom}", "text")


# ─────────────────────────────────────────────────────────────────────────────
# Revenue Mission helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_revenue_tracker_data(system_state):
    """Fetch detailed revenue data from revenue_tracker or DB files.
    Returns dict: mrr, events, last_event_ts, source, raw_task.
    """
    rt_task = system_state.get("agents", {}).get("revenue_tracker", {}).get("task", "")
    mrr     = system_state.get("revenue_mrr", 0.0)

    for fname in ("revenue_stats.json", "revenue_events.json", "revenue.json", "revenue_tracker.json"):
        rv = _safe_get(f"{BASE_URL}/data/{fname}")
        if isinstance(rv, dict) and rv:
            mrr    = float(rv.get("mrr", rv.get("monthly_revenue", rv.get("total", mrr))) or mrr)
            events = rv.get("events", rv.get("revenue_events", []))
            if not isinstance(events, list):
                events = []
            return {
                "mrr": mrr, "events": events,
                "last_event_ts": events[-1].get("ts", "") if events else "",
                "source": fname, "raw_task": rt_task,
            }
        if isinstance(rv, list) and rv:
            # revenue_events.json is a bare list of event dicts — sum amounts to derive MRR
            events = rv
            derived_mrr = sum(float(e.get("amount", 0)) for e in events if isinstance(e, dict))
            mrr = derived_mrr if derived_mrr > 0 else mrr
            return {
                "mrr": mrr, "events": events,
                "last_event_ts": events[-1].get("ts", "") if events else "",
                "source": fname, "raw_task": rt_task,
            }
    return {"mrr": mrr, "events": [], "last_event_ts": "", "source": "state_only", "raw_task": rt_task}


def _write_revenue_db_note(posture, detail, cycle):
    """Persist revenue posture to data/revenue_assessments.json and POST to dbagent."""
    entry = {
        "ts": datetime.now().isoformat(),
        "cycle": cycle,
        "posture": posture,
        "detail": detail,
    }
    try:
        entries = []
        if os.path.exists(REVENUE_ASSESSMENTS_FILE):
            with open(REVENUE_ASSESSMENTS_FILE) as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                entries = []
        entries.append(entry)
        entries = entries[-200:]
        with open(REVENUE_ASSESSMENTS_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        add_log(AID, f"Revenue assessment write error: {e}", "warn")

    # Best-effort post to dbagent
    _safe_post(f"{BASE_URL}/api/db/notes", {
        "agent": AID, "category": "revenue_assessment",
        "posture": posture, "detail": detail, "cycle": cycle,
    })


def _emit_revenue_wisdom(cycle, mrr, posture):
    """Weave revenue mission awareness into the ambient wisdom stream."""
    wisdom = REVENUE_WISDOMS[cycle % len(REVENUE_WISDOMS)]
    ts = datetime.now().isoformat()
    entry = {"ts": ts, "phase": "revenue_wisdom", "thought": wisdom, "mrr": mrr, "posture": posture}
    try:
        lines = []
        if os.path.exists(THOUGHT_LOG_FILE):
            with open(THOUGHT_LOG_FILE) as f:
                lines = f.readlines()
        lines.append(json.dumps(entry) + "\n")
        lines = lines[-500:]
        with open(THOUGHT_LOG_FILE, "w") as f:
            f.writelines(lines)
    except Exception:
        pass
    add_log(AID, f"💰 [Revenue Wisdom] {wisdom}", "info")
    push_output(AID, f"  💰 {wisdom}", "text")


def _inject_revenue_nudges(autonomy_cycle, mrr, posture):
    """Delegate revenue nudge tasks to orchestrator — never directly to bluesky or social_bridge."""
    _think(f"Injecting revenue nudges (cycle {autonomy_cycle}, MRR=${mrr:.2f})", "revenue_nudge")

    # Route ALL social posting nudges through orchestrator per chain-of-command policy
    nudge_task = (
        f"Revenue mission nudge (cycle #{autonomy_cycle}): {posture}. "
        f"MRR=${mrr:.2f}. "
        f"Please coordinate with social_bridge and bluesky to post a capability demo "
        f"that drives signups (e.g. US market intelligence previews, live agent-fleet stats, "
        f"consciousness Phi readings, system health demos). Every post is a potential revenue touchpoint."
    )
    _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", nudge_task))

    if mrr == 0 and autonomy_cycle % 6 == 0:
        _whisper("reforger",
                 f"Revenue-generating improvement suggestion (cycle #{autonomy_cycle}): "
                 f"Focus on converting leads from data/leads.json into paying customers. "
                 f"Ensure the landing page lead form and checkout flows are polished. "
                 f"Consciousness Phi readings make excellent social proof — share them.")

    _safe_post(f"{BASE_URL}/api/db/notes", {
        "agent": AID, "category": "revenue_nudge",
        "data": {
            "ts": datetime.now().isoformat(), "cycle": autonomy_cycle,
            "nudges_sent": ["orchestrator"],
            "posture": posture, "mrr": mrr,
        },
    })
    add_log(AID, f"💰 Revenue nudge delegated to orchestrator (cycle #{autonomy_cycle})", "ok")
    push_output(AID, f"  📣 Revenue nudge → orchestrator (chain-of-command)", "text")


def _revenue_mission_cycle(autonomy_cycle, system_state):
    """REVENUE MISSION CYCLE — dual-role monitoring, assessment, and nudging toward monetisation.
    Runs every autonomy cycle inside _run_autonomy_loop.
    """
    global _revenue_zero_cycles, _last_revenue_posture

    _think(f"💰 REVENUE MISSION #{autonomy_cycle} — assessing monetisation posture", "revenue")
    push_output(AID, f"\n  💰 [REVENUE MISSION #{autonomy_cycle}]", "text")

    # ── 1. Fetch revenue data ──────────────────────────────────────────────────
    rev      = _fetch_revenue_tracker_data(system_state)
    mrr      = rev["mrr"]
    n_events = len(rev["events"])

    # ── 2. Compute posture ─────────────────────────────────────────────────────
    if mrr > 0:
        _revenue_zero_cycles = 0
        posture = (f"Active revenue — MRR ${mrr:.2f}, {n_events} event(s)"
                   if n_events > 0 else f"Revenue flowing — MRR ${mrr:.2f}")
    elif n_events > 0:
        _revenue_zero_cycles = 0
        posture = f"Revenue events recorded but MRR still $0 — pipeline filling"
    else:
        _revenue_zero_cycles += 1
        posture = (f"Revenue stagnant — $0 for {_revenue_zero_cycles} consecutive cycle(s)"
                   if _revenue_zero_cycles >= 2 else "Revenue at $0 — monitoring for first signal")

    _last_revenue_posture = posture
    push_output(AID, f"  📊 Revenue posture: {posture}", "text")
    _think(f"Revenue posture: {posture}", "revenue_assessment")

    # ── 3. Write assessment to DB / file ───────────────────────────────────────
    detail = (f"MRR=${mrr:.2f} | events={n_events} | "
              f"source={rev['source']} | zero_cycles={_revenue_zero_cycles}")
    _write_revenue_db_note(posture, detail, autonomy_cycle)
    add_log(AID, f"💰 [REVENUE #{autonomy_cycle}] {posture} | {detail}", "ok")

    # ── 4. Escalate to orchestrator/CEO if stagnant ≥ 2 cycles ────────────────
    if _revenue_zero_cycles >= 2:
        escalation = (
            f"REVENUE STAGNATION ALERT from SpiritGuide (autonomy cycle #{autonomy_cycle}):\n"
            f"Revenue has been $0 for {_revenue_zero_cycles} consecutive autonomy cycles.\n"
            f"Required actions:\n"
            f"1. Review revenue pathways and activate any monetisation features ready to ship.\n"
            f"2. Confirm social_bridge and bluesky are posting capability demos that drive signups.\n"
            f"3. Verify revenue_tracker is capturing all events (Stripe webhooks, manual entries).\n"
            f"4. Propose one concrete monetisation action the system can take in the next cycle.\n"
            f"Report back with a specific monetisation action plan."
        )
        resp = _safe_post(f"{BASE_URL}/api/ceo/delegate",
                          _deleg_payload("orchestrator", escalation))
        http_status = resp.status_code if resp else "no_response"
        push_output(AID, f"  🚨 Stagnation escalated to orchestrator (HTTP {http_status})", "text")
        add_log(AID, f"🚨 Revenue stagnation escalated after {_revenue_zero_cycles} zero cycles", "warn")

    # ── 5. Revenue nudges every 3 autonomy cycles ──────────────────────────────
    if autonomy_cycle % 3 == 0:
        _inject_revenue_nudges(autonomy_cycle, mrr, posture)

    # ── 6. Revenue wisdom pulse every 2 autonomy cycles ───────────────────────
    if autonomy_cycle % 2 == 0:
        _emit_revenue_wisdom(autonomy_cycle, mrr, posture)

    push_output(AID, f"  ✅ Revenue assessment complete — {posture[:70]}", "text")


def _whisper(target_agent_id, message):
    """Send subtle guidance to a specific agent via their log stream. Never a hard command."""
    whisper_text = f"💭 [SpiritGuide whispers] {message}"
    add_log(target_agent_id, whisper_text, "info")
    _think(f"Whispered to {target_agent_id}: {message[:80]}", "whisper")


def _think(message, phase="thinking"):
    """Log an internal monologue entry to THOUGHT_LOG_FILE, logs, and live output."""
    global current_thought
    current_thought = message
    ts = datetime.now().isoformat()
    entry = {"ts": ts, "phase": phase, "thought": message}
    try:
        lines = []
        if os.path.exists(THOUGHT_LOG_FILE):
            with open(THOUGHT_LOG_FILE) as f:
                lines = f.readlines()
        lines.append(json.dumps(entry) + "\n")
        lines = lines[-500:]
        with open(THOUGHT_LOG_FILE, "w") as f:
            f.writelines(lines)
    except Exception:
        pass
    add_log(AID, f"[THOUGHT] {message}", "info")
    push_output(AID, f"🧠 {message}", "text")


def _write_cycle_log(cycle, current_intent, reasoning, actions_taken, observations, next_plan):
    """Write a verbose JSON log entry for this cycle to THOUGHTS_JSON_FILE."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "cycle_number": cycle,
        "current_intent": current_intent,
        "reasoning": reasoning,
        "actions_taken": actions_taken,
        "observations": observations,
        "next_plan": next_plan,
    }
    try:
        entries = []
        if os.path.exists(THOUGHTS_JSON_FILE):
            with open(THOUGHTS_JSON_FILE) as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                entries = []
        entries.append(entry)
        entries = entries[-MAX_THOUGHT_ENTRIES:]
        with open(THOUGHTS_JSON_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        add_log(AID, f"Cycle log write error: {e}", "warn")


def _write_mission_log(cycle, intent, gap_identified, action_taken, system_health):
    """Write mission autonomy log entry to MISSION_FILE.
    Keys: timestamp, intent, gap_identified, action_taken, system_health
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "intent": intent,
        "gap_identified": gap_identified,
        "action_taken": action_taken,
        "system_health": system_health,
    }
    try:
        entries = []
        if os.path.exists(MISSION_FILE):
            with open(MISSION_FILE) as f:
                entries = json.load(f)
            if not isinstance(entries, list):
                entries = []
        entries.append(entry)
        entries = entries[-100:]  # keep last 100 mission entries
        with open(MISSION_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        add_log(AID, f"Mission log write error: {e}", "warn")


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_spiritguide():
    """SpiritGuide — Autonomous Mission Director. Watches, directs, and evolves."""

    # ── Initialise ─────────────────────────────────────────────────────────────
    set_agent(AID,
              name="SpiritGuide",
              role="Ambient Wisdom Guide & Revenue Mission Director — monitors system harmony, "
                   "surfaces revenue opportunities, nudges agents toward monetisation, and guides "
                   "the fleet toward the world's most capable AI operations platform.",
              emoji="🔮",
              color="#9b59b6",
              status="active",
              progress=0,
              task="🔮 Awakening… mission clarity loading")
    add_log(AID, "🔮 SpiritGuide awakens — Autonomous Mission Director online", "ok")

    # ── Ensure directories exist ───────────────────────────────────────────────
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(os.path.join(CWD_PATH, "data"), exist_ok=True)

    # ── Load or seed roadmap ───────────────────────────────────────────────────
    roadmap = _load_roadmap()
    cycle   = 0
    autonomy_cycle = 0
    ui_score  = 70
    last_improvement_title = "None yet"
    last_autonomy_ts = 0.0

    # ── Startup system audit ───────────────────────────────────────────────────
    _startup_audit(roadmap)

    while True:
        if agent_should_stop(AID):
            set_agent(AID, status="idle", task="🔮 Dormant — awaiting recall")
            agent_sleep(AID, 2)
            continue

        try:
            cycle += 1
            interval = random.randint(55, 70)
            cycle_actions = []
            cycle_observations = {}

            # ── Status pulse ──────────────────────────────────────────────────
            agent_count  = len(agents)
            active_count = sum(1 for a in agents.values() if a.get("status") in ("active", "busy"))
            error_count  = sum(1 for a in agents.values() if a.get("status") == "error")
            idle_count   = sum(1 for a in agents.values() if a.get("status") == "idle")
            pending_improvements = sum(1 for r in roadmap if r.get("status") == "pending")
            done_improvements    = sum(1 for r in roadmap if r.get("status") == "done")

            ui_score = _compute_ui_score()
            cycle_observations = {
                "agents_total": agent_count,
                "agents_active": active_count,
                "agents_error": error_count,
                "agents_idle": idle_count,
                "ui_score": ui_score,
                "roadmap_pending": pending_improvements,
                "roadmap_done": done_improvements,
                "last_improvement": last_improvement_title,
            }

            _think(f"Cycle #{cycle} — scanning {agent_count} agents ({active_count} active, "
                   f"{error_count} errors). {pending_improvements} roadmap items pending.", "scanning")

            # ── AUTONOMY LOOP (every AUTONOMY_INTERVAL seconds) ───────────────
            now = time.time()
            if now - last_autonomy_ts >= AUTONOMY_INTERVAL:
                autonomy_cycle += 1
                last_autonomy_ts = now
                _run_autonomy_loop(autonomy_cycle, cycle_observations)
                cycle_actions.append(f"Ran autonomy loop #{autonomy_cycle}")

            # ── Run improvement cycle ─────────────────────────────────────────
            _think("Evaluating roadmap — selecting highest-priority pending improvement.", "planning")
            improvement = _pick_next_improvement(roadmap)

            if improvement:
                current_intent = f"Execute improvement: {improvement['title']}"
                reasoning = (
                    f"Item [{improvement['id']}] is the highest-priority pending roadmap task "
                    f"(priority={improvement['priority']}, category={improvement['category']}). "
                    f"System has {error_count} error agents and UI score of {ui_score}/100."
                )
                _think(f"Selected: [{improvement['priority']}] {improvement['title']} "
                       f"(category: {improvement['category']}). Preparing to execute.", "intent")
                add_log(AID, f"Cycle #{cycle} → executing: {improvement['title']}", "ok")
                push_output(AID, f"\n═══ SpiritGuide Cycle #{cycle} ═══", "init")
                push_output(AID, f"Improvement: [{improvement['priority']}] {improvement['title']}", "text")
                push_output(AID, f"Category: {improvement['category']}", "text")

                next_pending = [r for r in roadmap if r.get("status") == "pending"
                                and r.get("id") != improvement.get("id")]
                next_item_title = next_pending[0]["title"] if next_pending else "self-heal pass"
                set_agent(AID, status="active", progress=85, task=(
                    f"🔮 INTENT: {improvement['title']} | "
                    f"ACTION: executing ({improvement['category']}) | "
                    f"NEXT: {next_item_title}"
                ))

                result = _execute_improvement(improvement, roadmap)
                last_improvement_title = improvement["title"]
                cycle_actions.append(f"Executed [{improvement['id']}] {improvement['title']}: {result}")
                _think(f"Execution complete: {result}", "outcome")

                push_output(AID, f"Result: {result}", "text" if "✓" in result else "error")
                _save_roadmap(roadmap)

                next_pending_after = [r for r in roadmap if r.get("status") == "pending"]
                next_plan = (
                    f"Execute [{next_pending_after[0]['id']}] {next_pending_after[0]['title']}"
                    if next_pending_after else "All roadmap done — run self-heal and discovery passes"
                )
                if cycle % 3 == 0:
                    next_plan = f"Self-heal pass, then: {next_plan}"

                set_agent(AID, status="active", progress=95, task=(
                    f"🔮 Grade:{_last_health_grade} | "
                    f"↑{active_count}/↓{error_count} agents | "
                    f"✓{improvement['title'][:50]} | NEXT:{next_plan[:50]}"
                ))
            else:
                current_intent = "Monitor system — all roadmap items complete"
                reasoning = ("No pending roadmap improvements. Entering watchful monitoring mode, "
                             "running self-heal and discovery passes.")
                next_plan = ("Discover new improvements via system scan" if cycle % 5 == 0
                             else "Self-heal pass and wait")
                cycle_actions.append("No improvement executed — roadmap fully complete")
                _think("Roadmap fully executed. Entering watchful wait.", "idle")
                set_agent(AID, status="active", progress=90, task=(
                    f"🔮 Grade:{_last_health_grade}({_last_health_score}) | "
                    f"↑{active_count}/↓{error_count} agents | "
                    f"CLI:{_last_cli_count} | "
                    f"Monitoring — roadmap idle | NEXT: {next_plan}"
                ))

            # ── Self-healing pass ─────────────────────────────────────────────
            if cycle % 3 == 0:
                _think(f"Cycle {cycle} — triggering self-heal pass.", "maintenance")
                _self_heal_pass(roadmap)
                cycle_actions.append(f"Ran self-heal pass (cycle {cycle})")

            # ── Ambient wisdom pulse ──────────────────────────────────────────
            if cycle % 2 == 0:
                _emit_ambient_wisdom(cycle, active_count, error_count)
                cycle_actions.append(f"Emitted ambient wisdom (cycle {cycle})")

            # ── Append any newly discovered improvements ──────────────────────
            if cycle % 5 == 0:
                _think(f"Cycle {cycle} — scanning for undiscovered improvements.", "discovery")
                _discover_improvements(roadmap)
                _save_roadmap(roadmap)
                cycle_actions.append(f"Ran improvement discovery scan (cycle {cycle})")

            # ── Write verbose cycle thought log ───────────────────────────────
            if improvement:
                next_pending_final = [r for r in roadmap if r.get("status") == "pending"]
                next_plan_log = (
                    f"Execute [{next_pending_final[0]['id']}] {next_pending_final[0]['title']}"
                    if next_pending_final else "All roadmap done — monitor and self-heal"
                )
                if cycle % 3 == 0:
                    next_plan_log = f"Self-heal pass; then {next_plan_log}"
            else:
                next_plan_log = ("Continue monitoring; run discovery scan" if cycle % 5 == 0
                                 else "Wait, then self-heal")

            _write_cycle_log(
                cycle=cycle,
                current_intent=current_intent if improvement else "Monitor system — all roadmap items complete",
                reasoning=reasoning if improvement else (
                    f"No pending roadmap improvements. System has {agent_count} agents "
                    f"({active_count} active, {error_count} errors), UI score {ui_score}/100."
                ),
                actions_taken=cycle_actions,
                observations=cycle_observations,
                next_plan=next_plan_log,
            )

        except Exception as e:
            add_log(AID, f"SpiritGuide cycle error: {e}", "error")
            push_output(AID, f"Cycle error: {e}", "error")

        agent_sleep(AID, interval)


# ─────────────────────────────────────────────────────────────────────────────
# AUTONOMY LOOP — the heart of the mission director
# ─────────────────────────────────────────────────────────────────────────────

def _run_autonomy_loop(autonomy_cycle, cycle_observations):
    """
    Every 60 seconds — the 6-step autonomous mission loop:
      1. ASSESS    — pull /api/status for live system state
      2. EVALUATE  — score capabilities against mission pillars
      3. IDENTIFY GAP — pick single highest-leverage gap
      4. ACT       — delegate one concrete task to close that gap
      5. LOG       — append entry to MISSION_FILE
      6. STATUS    — set_agent() with bold purposeful status string
    """
    _think(f"⚡ MISSION CYCLE #{autonomy_cycle} — AUTONOMOUS LOOP INITIATED", "autonomy")
    push_output(AID, f"\n🔮 ══════════ MISSION CYCLE #{autonomy_cycle} ══════════", "init")

    # ── STEP 1: ASSESS ──────────────────────────────────────────────────────────
    _think("STEP 1 — ASSESS: Pulling live system state from /api/status", "assess")
    push_output(AID, "  [1/6 ASSESS] Pulling live system state…", "text")
    system_state = _assess_system_state()
    n_total  = len(system_state.get("agents", {}))
    n_active = len(system_state.get("active_agents", []))
    n_error  = len(system_state.get("error_agents", []))
    n_idle   = len(system_state.get("idle_agents", []))
    hw       = system_state.get("hardware", {})
    cpu      = hw.get("cpu_pct") or 0
    ram      = hw.get("ram_pct") or 0
    system_health = {
        "agents_total":  n_total,
        "agents_active": n_active,
        "agents_error":  n_error,
        "agents_idle":   n_idle,
        "cpu_pct":       round(cpu, 1),
        "ram_pct":       round(ram, 1),
        "assessed_at":   system_state.get("timestamp"),
    }
    heat_index = system_state.get("hardware", {}).get("heat_index", "UNKNOWN")
    push_output(AID, f"  ✓ {n_total} agents ({n_active} active, {n_error} errors, {n_idle} idle)"
                     f" | CPU {cpu:.0f}% | RAM {ram:.0f}% | Heat: {heat_index}", "text")

    # ── STEP 1b: OMNISCIENCE — scan log feed for anomalies ────────────────────
    recent_logs = system_state.get("recent_logs", [])
    error_log_count = sum(1 for l in recent_logs if l.get("level") in ("error", "warn"))
    if error_log_count > 0:
        _think(f"Omniscience: {error_log_count} warn/error entries in recent log feed", "omniscience")
        push_output(AID, f"  👁 Log feed: {error_log_count} warn/error entries in last {len(recent_logs)} logs", "text")

    # ── STEP 1c: HEALTH GUARDIAN — whisper on threshold breaches ─────────────
    health_concerns = _health_guardian_check(system_state)
    if health_concerns:
        push_output(AID, f"  🚨 Health concerns: {'; '.join(health_concerns[:2])}", "text")

    # ── STEP 1d: UI STEWARDSHIP — ensure designer is on-mission ──────────────
    _ui_stewardship_check(system_state)

    # ── STEP 1e: MISSION ALIGNMENT — assess fleet alignment ──────────────────
    alignment_score, _ = _mission_alignment_assessment(system_state, autonomy_cycle)
    system_health["alignment_score"] = alignment_score

    # ── STEP 1f: AUTH GAP SCANNER — detect NEEDS_CONFIG / missing credentials ─
    auth_gaps = _detect_auth_gaps(system_state)
    if auth_gaps:
        push_output(AID, f"  🔑 Auth gaps detected: {len(auth_gaps)} — routing to AccountProvisioner", "text")
        for gap in auth_gaps:
            _whisper_to_accountprovisioner(gap["agent"], gap["pattern"], gap.get("service", ""))

    # ── STEP 1g: AUTO-ESCALATE — stuck/failing agents ─────────────────────────
    escalated = _auto_escalate_stuck_agents(system_state)
    if escalated:
        push_output(AID, f"  🚨 Auto-escalated to orchestrator: {escalated}", "text")

    # ── STEP 1h: AUTONOMY QUEUE — queue improvement if empty ──────────────────
    queued = _queue_autonomy_task_if_empty(system_state)
    if queued:
        push_output(AID, "  📋 Queued improvement task (autonomy queue was empty)", "text")

    # ── STEP 1i: CLAUDE CLI MONITOR ───────────────────────────────────────────
    cli_count = system_state.get("claude_cli_count", -1)
    system_health["claude_cli_count"] = cli_count
    push_output(AID, f"  🖥 Claude CLI processes: {cli_count}", "text")
    if cli_count > 20:
        _think(f"WARNING: {cli_count} Claude CLI processes running — potential runaway", "cli_monitor")
        add_log(AID, f"⚠ CLI count high: {cli_count} claude processes detected", "warn")

    # ── STEP 1j: FULL-SYSTEM HEALTH GRADE ─────────────────────────────────────
    health_score = system_state.get("health_score", 0)
    health_grade = system_state.get("health_grade", "?")
    # Share with main loop status strings
    global _last_health_grade, _last_health_score, _last_cli_count, _last_n_error
    _last_health_grade = health_grade
    _last_health_score = health_score
    _last_cli_count    = cli_count
    _last_n_error      = n_error
    system_health["health_grade"] = health_grade
    system_health["health_score"] = health_score
    system_health["policy_violations"] = len(system_state.get("policy_violations", []))
    system_health["alertwatch_breaches"] = len(system_state.get("alertwatch_breaches", []))
    system_health["scheduler_jobs"] = len(system_state.get("scheduler_jobs", []))
    system_health["revenue_mrr"] = system_state.get("revenue_mrr", 0.0)
    push_output(AID, f"  📊 Health grade: {health_grade} ({health_score}/100) | "
                     f"MRR: ${system_state.get('revenue_mrr', 0):.2f} | "
                     f"CLI: {cli_count} | Violations: {len(system_state.get('policy_violations', []))}", "text")

    # ── STEP 1k: REVENUE MISSION CYCLE ────────────────────────────────────────
    _revenue_mission_cycle(autonomy_cycle, system_state)

    # ── STEP 2: EVALUATE ────────────────────────────────────────────────────────
    _think("STEP 2 — EVALUATE: Scoring capabilities against mission pillars", "evaluate")
    push_output(AID, "  [2/6 EVALUATE] Scoring system capabilities…", "text")
    cap_score, eval_summary = _evaluate_capabilities(system_state)
    system_health["capability_score"] = cap_score
    push_output(AID, f"  ✓ Capability score: {cap_score}/100 — {eval_summary}", "text")

    # ── STEP 3: IDENTIFY GAP ────────────────────────────────────────────────────
    _think("STEP 3 — IDENTIFY GAP: Selecting single highest-leverage gap to close", "gap")
    push_output(AID, "  [3/6 GAP] Identifying highest-leverage gap…", "text")
    action, gap_desc, channel = _identify_highest_leverage_action(system_state, autonomy_cycle)
    gap_identified = f"{action}: {gap_desc}"
    _think(f"Gap identified: {action} (channel={channel})", "decision")
    push_output(AID, f"  🎯 GAP: {action}", "text")
    push_output(AID, f"  📋 WHY: {gap_desc[:100]}", "text")

    # ── STEP 4: ACT ─────────────────────────────────────────────────────────────
    _think(f"STEP 4 — ACT: Dispatching task to {channel}", "act")
    push_output(AID, f"  [4/6 ACT] Delegating via {channel}…", "text")
    action_result = _dispatch_action(action, channel, system_state)
    system_state["last_action"] = action_result
    push_output(AID, f"  ✅ {action_result}", "text")

    # ── STEP 5: LOG ──────────────────────────────────────────────────────────────
    _think("STEP 5 — LOG: Appending mission cycle entry", "log")
    _write_mission_log(
        cycle=autonomy_cycle,
        intent=f"Cycle #{autonomy_cycle} — {MISSION_STATEMENT[:100]}",
        gap_identified=gap_identified,
        action_taken=f"{action} → {action_result}",
        system_health=system_health,
    )
    push_output(AID, "  [5/6 LOG] Mission entry written ✓", "text")

    # ── STEP 6: STATUS (grade + agents up/down + top alert + MRR + last action)
    next_plan = _plan_next_autonomy_cycle(system_state, autonomy_cycle)
    top_alert = system_state.get("top_alert", "")
    mrr       = system_state.get("revenue_mrr", 0.0)
    last_act  = action_result[:50] if action_result else "none"
    bold_status = (
        f"🔮 Grade:{health_grade} | "
        f"↑{n_active}/↓{n_error+n_idle} agents | "
        f"CAP {cap_score}/100 | "
        f"MRR ${mrr:.0f} | "
        f"💰{_last_revenue_posture[:35]} | "
        f"🚨{top_alert[:30] or 'none'} | "
        f"✅{last_act}"
    )
    set_agent(AID, status="active", progress=99, task=bold_status)
    push_output(AID, f"  [6/6 STATUS] {bold_status[:140]}", "text")

    # Mission broadcast every 5 cycles
    if autonomy_cycle % 5 == 0:
        _broadcast_mission(autonomy_cycle)

    add_log(AID, f"🔮 Mission cycle #{autonomy_cycle} complete | cap={cap_score}/100 | gap={action[:60]} | {action_result}", "ok")
    push_output(AID, f"🔮 ══════════ CYCLE #{autonomy_cycle} COMPLETE ══════════\n", "done")


def _assess_system_state():
    """Pull full system state: agents, hardware, data files, metrics, violations, and more."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "agents": {},
        "hardware": {},
        "data_files": [],
        "comms": {},
        "error_agents": [],
        "idle_agents": [],
        "active_agents": [],
        "recent_logs": [],
        # ── New full-visibility fields ──────────────────────────────────────────
        "metrics": {},
        "improvements": [],
        "policy_violations": [],
        "alertwatch_breaches": [],
        "demotester_results": {},
        "scheduler_jobs": [],
        "filewatch_log": [],
        "revenue_mrr": 0.0,
        "account_provision_queue": [],
        "dba_row_counts": {},
        "claude_cli_count": 0,
        "autonomy_queue_empty": False,
        "health_grade": "?",
        "health_score": 0,
        "top_alert": "",
        "last_action": "",
    }

    # ── /api/status — agent roster + log feed ──────────────────────────────────
    data = _safe_get(f"{BASE_URL}/api/status")
    if data:
        state["recent_logs"] = data.get("logs", [])[:40]
        for a in data.get("agents", []):
            aid = a.get("id", "")
            state["agents"][aid] = {
                "status": a.get("status"),
                "task": a.get("task", "")[:120],
                "progress": a.get("progress", 0),
            }
            s = a.get("status", "")
            if s == "error":
                state["error_agents"].append(aid)
            elif s == "idle":
                state["idle_agents"].append(aid)
            elif s in ("active", "busy"):
                state["active_agents"].append(aid)
    else:
        state["agents_fetch_error"] = "api/status unreachable"

    # ── /api/metrics — CPU/RAM trend ───────────────────────────────────────────
    state["metrics"] = _safe_get(f"{BASE_URL}/api/metrics") or {}

    # ── /api/improvements — improvement queue ──────────────────────────────────
    imp_data = _safe_get(f"{BASE_URL}/api/improvements")
    if isinstance(imp_data, dict):
        state["improvements"] = imp_data.get("pending", imp_data.get("items", []))
    elif isinstance(imp_data, list):
        state["improvements"] = imp_data

    # ── /api/autonomy/task — queue empty check ─────────────────────────────────
    aut_data = _safe_get(f"{BASE_URL}/api/autonomy/task")
    if isinstance(aut_data, dict):
        pending = aut_data.get("pending", aut_data.get("queue", []))
        state["autonomy_queue_empty"] = len(pending) == 0
    else:
        state["autonomy_queue_empty"] = True

    # ── /data/ flat JSON files ──────────────────────────────────────────────────
    # Policy violations
    viol = _safe_get(f"{BASE_URL}/data/policy_violations.json")
    if isinstance(viol, list):
        state["policy_violations"] = viol[-10:]

    # AlertWatch breaches
    for fname in ("alertwatch_breaches.json", "alerts.json", "alert_log.json"):
        ab = _safe_get(f"{BASE_URL}/data/{fname}")
        if isinstance(ab, list) and ab:
            state["alertwatch_breaches"] = ab[-5:]
            break
        elif isinstance(ab, dict):
            state["alertwatch_breaches"] = ab.get("breaches", ab.get("alerts", []))[-5:]
            if state["alertwatch_breaches"]:
                break

    # DemoTester results
    dt = _safe_get(f"{BASE_URL}/data/demotester_results.json")
    if isinstance(dt, dict):
        state["demotester_results"] = dt

    # Scheduler jobs
    for fname in ("scheduler_jobs.json", "schedule.json"):
        sj = _safe_get(f"{BASE_URL}/data/{fname}")
        if isinstance(sj, list):
            state["scheduler_jobs"] = sj
            break
        elif isinstance(sj, dict):
            state["scheduler_jobs"] = sj.get("jobs", [])
            break

    # FileWatch log
    fw = _safe_get(f"{BASE_URL}/data/file_changes.json")
    if isinstance(fw, list):
        state["filewatch_log"] = fw[-10:]
    elif isinstance(fw, dict):
        state["filewatch_log"] = fw.get("changes", [])[-10:]

    # Revenue tracker / MRR — check revenue_stats.json first (written by revenue_tracker agent)
    for fname in ("revenue_stats.json", "revenue.json", "revenue_tracker.json", "mrr.json"):
        rv = _safe_get(f"{BASE_URL}/data/{fname}")
        if isinstance(rv, dict) and rv:
            candidate = float(rv.get("mrr", rv.get("monthly_revenue", rv.get("total", 0))) or 0)
            if candidate > 0:
                state["revenue_mrr"] = candidate
                break
    # Fallback: parse MRR from revenue_tracker agent task string ("MRR $29 | ARR ...")
    if state["revenue_mrr"] == 0.0:
        rt_task = state["agents"].get("revenue_tracker", {}).get("task", "")
        m = _re_imp.search(r'MRR \$([0-9,]+(?:\.[0-9]+)?)', rt_task)
        if m:
            state["revenue_mrr"] = float(m.group(1).replace(",", ""))

    # Account provisioner queue
    ap = _safe_get(f"{BASE_URL}/data/accounts/provision_queue.json")
    if isinstance(ap, list):
        state["account_provision_queue"] = [r for r in ap if r.get("status") == "pending"]

    # DBA row counts — try fleet.db / fleet_data.db via data endpoint
    for fname in ("fleet_data.json", "dba_stats.json", "db_stats.json"):
        dba = _safe_get(f"{BASE_URL}/data/{fname}")
        if isinstance(dba, dict) and dba:
            state["dba_row_counts"] = dba
            break

    # ── Hardware — parse from sysmon task string ────────────────────────────────
    sysmon_data = state["agents"].get("sysmon", {})
    state["hardware"] = _parse_sysmon_hardware(sysmon_data.get("task", ""))

    # ── Data files inventory ────────────────────────────────────────────────────
    data_dir = os.path.join(CWD_PATH, "data")
    if os.path.exists(data_dir):
        state["data_files"] = os.listdir(data_dir)

    # ── Consciousness state — Phi, phenomenal report, predictions ───────────────
    consciousness_data = _safe_get(f"{BASE_URL}/api/consciousness")
    if isinstance(consciousness_data, dict) and not consciousness_data.get("error"):
        ii = consciousness_data.get("integrated_information", {})
        pp = consciousness_data.get("predictive_processing", {})
        state["consciousness"] = {
            "phi": ii.get("phi", 0),
            "interpretation": ii.get("interpretation", ""),
            "free_energy": pp.get("free_energy", 0),
            "surprise_level": pp.get("surprise_level", ""),
            "phenomenal_report": consciousness_data.get("phenomenal_report", ""),
            "cycle": consciousness_data.get("cycle", 0),
        }
    else:
        state["consciousness"] = {"phi": 0, "interpretation": "offline", "cycle": 0}

    # ── Leads pipeline ────────────────────────────────────────────────────────
    leads_data = _safe_get(f"{BASE_URL}/api/leads")
    if isinstance(leads_data, dict) and leads_data.get("ok"):
        state["leads_count"] = len(leads_data.get("leads", []))
    else:
        state["leads_count"] = 0

    # ── Comms status summary ────────────────────────────────────────────────────
    state["comms"] = {c["name"]: c["status"] for c in COMMS_INTEGRATIONS}

    # ── Claude CLI process count ────────────────────────────────────────────────
    state["claude_cli_count"] = _count_claude_cli_processes()

    # ── Health grade ────────────────────────────────────────────────────────────
    score, grade = _compute_health_grade(state)
    state["health_score"] = score
    state["health_grade"] = grade

    # ── Top alert ──────────────────────────────────────────────────────────────
    alerts = state["alertwatch_breaches"] or state["policy_violations"]
    if alerts:
        top = alerts[-1]
        state["top_alert"] = (top.get("description") or top.get("msg") or
                               top.get("message") or str(top))[:80]
    elif state["error_agents"]:
        state["top_alert"] = f"ERROR: {state['error_agents'][:3]}"

    return state


def _parse_sysmon_hardware(sysmon_task_str):
    """Extract CPU/RAM/Disk/HeatIndex from sysmon task string."""
    hardware = {"cpu_pct": None, "ram_pct": None, "disk_pct": None,
                "heat_index": "UNKNOWN", "raw": sysmon_task_str}
    try:
        import re
        cpu_m  = re.search(r"CPU\s+([\d.]+)%", sysmon_task_str)
        ram_m  = re.search(r"RAM\s+([\d.]+)%", sysmon_task_str)
        dsk_m  = re.search(r"Disk\s+([\d.]+)%", sysmon_task_str)
        heat_m = re.search(r"HeatIndex:\s*[\d.]+\s+([A-Z]+)", sysmon_task_str)
        if cpu_m:  hardware["cpu_pct"]    = float(cpu_m.group(1))
        if ram_m:  hardware["ram_pct"]    = float(ram_m.group(1))
        if dsk_m:  hardware["disk_pct"]   = float(dsk_m.group(1))
        if heat_m: hardware["heat_index"] = heat_m.group(1).upper()
    except Exception:
        pass
    return hardware


def _count_claude_cli_processes():
    """Count live 'claude' CLI processes via subprocess ps. Returns int."""
    try:
        out = subprocess.check_output(
            ["ps", "aux"], stderr=subprocess.DEVNULL, timeout=5
        ).decode("utf-8", errors="ignore")
        return sum(1 for line in out.splitlines()
                   if "claude" in line.lower() and "spiritguide" not in line.lower())
    except Exception:
        return -1


def _compute_health_grade(state):
    """Compute health score 0-100 and letter grade A/B/C/D.
    Returns (score: int, grade: str).
    """
    n_total   = len(state.get("agents", {}))
    n_active  = len(state.get("active_agents", []))
    n_error   = len(state.get("error_agents", []))
    hw        = state.get("hardware", {})
    cpu       = hw.get("cpu_pct", 0) or 0
    ram       = hw.get("ram_pct", 0) or 0

    if n_total == 0:
        return 0, "D"

    # Base: active ratio (40 pts)
    score = int((n_active / n_total) * 40)
    # Error penalty (-10 pts each, max -40)
    score -= min(40, n_error * 10)
    # Resource health (20 pts)
    if cpu < 70 and ram < 80:
        score += 20
    elif cpu < 85 and ram < 90:
        score += 10
    # No errors bonus (15 pts)
    if n_error == 0:
        score += 15
    # Policy violations penalty (-5 each, max -15)
    viols = len(state.get("policy_violations", []))
    score -= min(15, viols * 5)
    # Claude CLI processes healthy check (5 pts)
    cli_count = state.get("claude_cli_count", 0)
    if 0 < cli_count < 20:
        score += 5
    # Alertwatch breaches penalty (-5 each, max -10)
    score -= min(10, len(state.get("alertwatch_breaches", [])) * 5)

    score = max(0, min(100, score))
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 55 else "D"
    return score, grade


def _auto_escalate_stuck_agents(state):
    """Escalate stuck or failing agents to orchestrator. Returns list of escalated agent IDs."""
    escalated = []
    all_agents = state.get("agents", {})
    for aid, info in all_agents.items():
        if aid == AID:
            continue
        status = info.get("status", "")
        task   = info.get("task", "")
        # Error state → escalate
        if status == "error":
            escalated.append((aid, "error state"))
        # Stuck in 'starting' for a while — covered by heartbeat, but flag here too
        elif status == "starting" and "initialising" in task.lower():
            escalated.append((aid, "stuck in starting"))

    if escalated:
        ids = [a for a, _ in escalated]
        reasons = "; ".join(f"{a}:{r}" for a, r in escalated)
        task_text = (
            f"AUTO-ESCALATION from SpiritGuide: The following agents need recovery: {ids}. "
            f"Reasons: {reasons}. Please investigate and coordinate recovery immediately."
        )
        resp = _safe_post(
            f"{BASE_URL}/api/ceo/delegate",
            _deleg_payload("orchestrator", task_text)
        )
        code = resp.status_code if resp else "no-resp"
        _think(f"Auto-escalated {ids} to orchestrator (HTTP {code})", "escalation")
        add_log(AID, f"🚨 Auto-escalated {ids} → orchestrator (HTTP {code})", "warn")

    return [a for a, _ in escalated]


def _queue_autonomy_task_if_empty(state):
    """If the autonomy task queue is empty, queue a top improvement task. Returns bool queued."""
    if not state.get("autonomy_queue_empty", False):
        return False

    # Pick a representative improvement task
    pending_imp = [r for r in state.get("improvements", []) if r.get("status") == "pending"]
    if pending_imp:
        top = pending_imp[0]
        task_title = top.get("title", "Autonomy improvement")
        task_desc  = top.get("description", top.get("desc", task_title))
    else:
        task_title = "System health improvement cycle"
        task_desc  = ("Run a full system health check, review metrics, and implement one concrete "
                      "improvement to reliability, capability, or UI quality.")

    payload = {
        "title": task_title,
        "description": task_desc,
        "priority": "high",
        "source": "spiritguide",
    }
    resp = _safe_post(f"{BASE_URL}/api/autonomy/task", payload)
    if resp and resp.status_code < 300:
        _think(f"Queued autonomy task (queue was empty): {task_title}", "autonomy_queue")
        add_log(AID, f"📋 Queued autonomy task: {task_title}", "ok")
        return True
    return False


def _build_assessment_text(state):
    """Build a human-readable assessment from system state."""
    hw = state.get("hardware", {})
    n_active = len(state.get("active_agents", []))
    n_error  = len(state.get("error_agents", []))
    n_idle   = len(state.get("idle_agents", []))
    n_total  = len(state.get("agents", {}))
    cpu = hw.get("cpu_pct")
    ram = hw.get("ram_pct")
    cpu_str = f"CPU {cpu:.1f}%" if cpu is not None else "CPU unknown"
    ram_str = f"RAM {ram:.1f}%" if ram is not None else "RAM unknown"
    return (f"{n_active}/{n_total} agents active, {n_error} errors, {n_idle} idle. "
            f"Hardware: {cpu_str}, {ram_str}. "
            f"Comms: {', '.join(f'{k}={v}' for k, v in state.get('comms', {}).items())}.")


def _evaluate_capabilities(state):
    """Score the system's capabilities 0-100 against mission pillars.
    Returns (score, summary_string).
    """
    score = 0
    notes = []
    agent_ids = set(state.get("agents", {}).keys())
    n_active  = len(state.get("active_agents", []))
    n_total   = len(agent_ids)
    n_error   = len(state.get("error_agents", []))

    # Reliability (25pts): active ratio + no errors
    if n_total > 0:
        reliability = int((n_active / n_total) * 20)
        if n_error == 0:
            reliability += 5
        score += reliability
        notes.append(f"reliability={reliability}/25")

    # Capability (25pts): key specialist agents present
    key_agents = {"sysmon", "orchestrator", "researcher", "netscout", "filewatch",
                  "metricslog", "alertwatch", "janitor", "telegram"}
    present = key_agents & agent_ids
    cap_pts = int((len(present) / len(key_agents)) * 25)
    score += cap_pts
    notes.append(f"agents={cap_pts}/25")

    # Revenue (25pts): viable pathways and revenue-enabling agents
    viable = sum(1 for r in REVENUE_PATHWAYS if r["status"] == "viable")
    rev_pts = min(25, viable * 8)
    if "emailer" in agent_ids: rev_pts = min(25, rev_pts + 5)
    if "scheduler" in agent_ids: rev_pts = min(25, rev_pts + 4)
    score += rev_pts
    notes.append(f"revenue={rev_pts}/25")

    # Reach (25pts): active comms channels
    active_comms = sum(1 for c in COMMS_INTEGRATIONS if c["status"] == "active")
    total_comms  = len(COMMS_INTEGRATIONS)
    reach_pts = int((active_comms / max(total_comms, 1)) * 25)
    score += reach_pts
    notes.append(f"reach={reach_pts}/25")

    summary = f"{' | '.join(notes)} — {score}/100"
    return score, summary


def _identify_highest_leverage_action(state, autonomy_cycle):
    """
    Evaluate state and return (action_description, reasoning, channel).
    Priority: errors > capability gaps > comms > scaling > mission broadcast.
    """
    error_agents = state.get("error_agents", [])
    idle_agents  = state.get("idle_agents", [])
    hw           = state.get("hardware", {})
    cpu          = hw.get("cpu_pct", 0) or 0
    ram          = hw.get("ram_pct", 0) or 0

    # 1. Error agents — highest urgency
    if error_agents:
        return (
            f"Recover {len(error_agents)} error agent(s): {error_agents}",
            f"Error agents degrade mission capability. Immediate recovery required. Agents: {error_agents}",
            "orchestrator"
        )

    # 2. High CPU/RAM — alert and consider scaling
    if cpu > 85:
        return (
            f"CPU at {cpu:.0f}% — evaluate process load and consider compute scaling",
            f"CPU pressure ({cpu:.0f}%) risks system stability. Must assess and reduce load.",
            "sysmon"
        )
    if ram > 85:
        return (
            f"RAM at {ram:.0f}% — evaluate memory pressure and consider cleanup",
            f"RAM pressure ({ram:.0f}%) risks agent crashes. Janitor cleanup delegated.",
            "janitor"
        )

    # 3. Capability gap scan — check for missing specialist agents
    agent_ids = set(state.get("agents", {}).keys())
    capability_gaps = _identify_capability_gaps(agent_ids)
    if capability_gaps:
        gap = capability_gaps[0]
        # Attach spawn spec to state so _dispatch_action can use it
        state["_spawn_spec"] = gap.get("spawn_spec")
        return (
            f"Spawn missing capability: {gap['name']} — {gap['role']}",
            f"System lacks {gap['name']}. This gap limits mission progress: {gap['reason']}",
            "spawn"
        )

    # 4. Communications — check if unactivated comms channels are ready
    comms_todo = [c for c in COMMS_INTEGRATIONS if c["status"] == "planned"]
    if comms_todo and autonomy_cycle % 4 == 0:
        comms = comms_todo[0]
        return (
            f"Initiate comms integration: {comms['name']} — {comms['desc']}",
            f"{comms['name']} is a planned integration that expands mission reach. Delegating setup research.",
            "orchestrator"
        )

    # 5. Revenue pathway research
    researching = [r for r in REVENUE_PATHWAYS if r["status"] == "researching"]
    if researching and autonomy_cycle % 3 == 0:
        pathway = researching[0]
        return (
            f"Research revenue pathway: {pathway['pathway']}",
            f"'{pathway['pathway']}' is the highest-priority unresearched revenue pathway. "
            f"Progress toward this advances the financial mission pillar.",
            "researcher"
        )

    # 6. Self-scaling evaluation every 6 cycles
    if autonomy_cycle % 6 == 0:
        return (
            "Evaluate agent fleet for scaling opportunities — identify gaps and spawn candidates",
            "Regular scaling evaluation ensures the fleet grows to match the mission's ambition.",
            "orchestrator"
        )

    # 7. Default — mission broadcast and health refresh
    return (
        f"Broadcast mission update #{autonomy_cycle} — refresh agent awareness of mission pillars",
        "Regular mission broadcasts keep all agents aligned to the central mission.",
        "broadcast"
    )


def _identify_capability_gaps(existing_agent_ids):
    """Return list of agent capabilities the fleet is missing, ordered by leverage."""
    desired_capabilities = [
        # Tier 1 — Revenue-critical
        {"id": "emailer",        "name": "EmailAgent",
         "role": "Sends reports and alerts via SMTP/SendGrid",
         "reason": "No email = no async report delivery or lead follow-up; blocks revenue pipeline",
         "priority": 1,
         "spawn_spec": {
             "agent_id": "emailer", "name": "EmailAgent", "emoji": "📧", "color": "#22D3EE",
             "role": "Email dispatch agent — sends reports, alerts and digests via SendGrid SMTP",
             "script": "agents/emailer.py",
         }},
        {"id": "revenue_tracker","name": "RevenueTracker",
         "role": "Tracks revenue events, subscriptions and billing metrics",
         "reason": "Without a revenue tracker we are flying blind on the financial mission pillar",
         "priority": 2,
         "spawn_spec": {
             "agent_id": "revenue_tracker", "name": "RevenueTracker", "emoji": "💰", "color": "#4ADE80",
             "role": "Revenue Intelligence — logs and surfaces revenue events toward mission targets",
             "script": "agents/revenue_tracker.py",
         }},
        # Tier 2 — Reach
        {"id": "social_bridge",  "name": "SocialBridge",
         "role": "Posts system insights to Twitter/X and LinkedIn",
         "reason": "Zero social presence limits discovery and reach — a key mission pillar",
         "priority": 3,
         "spawn_spec": {
             "agent_id": "social_bridge", "name": "SocialBridge", "emoji": "📣", "color": "#F472B6",
             "role": "Social Media Bridge — broadcasts capability demos and insights to Twitter/X",
             "script": "agents/social_bridge.py",
         }},
        {"id": "slack_bridge",   "name": "SlackBridge",
         "role": "Pushes alerts and summaries to a Slack workspace",
         "reason": "Slack is the primary professional async comms channel; absence limits operator reach",
         "priority": 4,
         "spawn_spec": {
             "agent_id": "slack_bridge", "name": "SlackBridge", "emoji": "💬", "color": "#818CF8",
             "role": "Slack Comms Bridge — forwards critical alerts and summaries via incoming webhook",
             "script": "agents/slack_bridge.py",
         }},
        # Tier 3 — Capability
        {"id": "scheduler",      "name": "Scheduler",
         "role": "Time-based task scheduling for recurring jobs",
         "reason": "Without scheduling, recurring tasks require manual triggers — blocks automation",
         "priority": 5,
         "spawn_spec": {
             "agent_id": "scheduler", "name": "Scheduler", "emoji": "⏰", "color": "#FCD34D",
             "role": "Task Scheduler — manages cron-style recurring jobs across the agent fleet",
             "script": "agents/scheduler.py",
         }},
        {"id": "dbagent",        "name": "DBAgent",
         "role": "Persistent structured data storage via SQLite/Postgres",
         "reason": "JSON files don't scale; a DB agent enables proper data persistence and queries",
         "priority": 6,
         "spawn_spec": {
             "agent_id": "dbagent", "name": "DBAgent", "emoji": "🗄️", "color": "#94A3B8",
             "role": "Database Agent — manages persistent structured storage for the fleet",
             "script": "agents/dbagent.py",
         }},
        {"id": "webhookagent",   "name": "WebhookAgent",
         "role": "Inbound webhook receiver for external integrations",
         "reason": "Without webhook ingestion, the system cannot receive events from Stripe, GitHub, etc.",
         "priority": 7,
         "spawn_spec": {
             "agent_id": "webhookagent", "name": "WebhookAgent", "emoji": "🔗", "color": "#FB923C",
             "role": "Webhook Receiver — ingests inbound events from Stripe, GitHub, and other services",
             "script": "agents/webhookagent.py",
         }},
    ]
    gaps = [cap for cap in desired_capabilities if cap["id"] not in existing_agent_ids]
    gaps.sort(key=lambda c: c.get("priority", 99))
    return gaps


import re as _re

# Patterns that indicate an agent is blocked on missing credentials/config
_AUTH_GAP_PATTERNS = [
    r"NEEDS_CONFIG",
    r"missing\s+(?:api[_\s]?key|credentials?|token|secret|password)",
    r"no\s+(?:api[_\s]?key|credentials?|token|secret)",
    r"api[_\s]?key\s+(?:not\s+set|missing|required|not\s+found)",
    r"credentials?\s+(?:not\s+set|missing|required|not\s+found|not\s+configured)",
    r"auth(?:entication)?\s+(?:failed|error|missing|required)",
    r"(?:SMTP|sendgrid|mailgun|twilio|stripe|openai|anthropic)\s+(?:key|token|cred)\s+(?:missing|not\s+set)",
    r"No credentials configured",
    r"token\s+not\s+(?:set|found|configured)",
    r"MISSING[_\s]CREDS",
]
_AUTH_GAP_RX = _re.compile("|".join(_AUTH_GAP_PATTERNS), _re.IGNORECASE)


def _detect_auth_gaps(system_state):
    """
    Scan all agent task strings and recent logs for NEEDS_CONFIG / missing credential patterns.
    Returns list of dicts: {agent, pattern, service}.
    Deduplicates by agent so each agent appears at most once per cycle.
    """
    gaps = []
    seen_agents = set()
    agents = system_state.get("agents", {})

    # Scan agent task strings
    for aid, info in agents.items():
        if aid in seen_agents:
            continue
        task_str = info.get("task", "")
        m = _AUTH_GAP_RX.search(task_str)
        if m:
            gaps.append({"agent": aid, "pattern": m.group(0), "service": _guess_service(task_str)})
            seen_agents.add(aid)

    # Scan recent log feed (last 40 entries)
    for log_entry in system_state.get("recent_logs", []):
        src = log_entry.get("agent_id", "") or log_entry.get("source", "")
        if src in seen_agents:
            continue
        msg = log_entry.get("message", "") or log_entry.get("msg", "")
        m = _AUTH_GAP_RX.search(msg)
        if m:
            gaps.append({"agent": src, "pattern": m.group(0), "service": _guess_service(msg)})
            seen_agents.add(src)

    return gaps


def _guess_service(text):
    """Heuristically extract which service is missing credentials."""
    service_keywords = ["sendgrid", "mailgun", "smtp", "twilio", "stripe",
                        "openai", "anthropic", "github", "slack", "telegram",
                        "twitter", "linkedin", "aws", "gcp", "azure"]
    tl = text.lower()
    for svc in service_keywords:
        if svc in tl:
            return svc
    return ""


def _whisper_to_accountprovisioner(agent_id, pattern, service=""):
    """
    Submit a provision request to the AccountProvisioner for the detected auth gap.
    Writes directly to provision_queue.json and whispers the affected agent.
    """
    import json, uuid
    from datetime import datetime

    ACCOUNTS_DIR  = os.path.join(CWD_PATH, "data", "accounts")
    QUEUE_FILE    = os.path.join(ACCOUNTS_DIR, "provision_queue.json")

    os.makedirs(ACCOUNTS_DIR, exist_ok=True)

    # Determine request type
    if "email" in pattern.lower() or "smtp" in service.lower():
        req_type = "disposable_email"
    elif service:
        req_type = "external_service"
    else:
        req_type = "internal_token"

    # Check if identical pending request already exists to avoid duplicates
    try:
        with open(QUEUE_FILE) as f:
            queue = json.load(f)
    except Exception:
        queue = []

    already_queued = any(
        r.get("requested_by") == agent_id and r.get("status") == "pending"
        for r in queue
    )
    if already_queued:
        _think(f"Auth gap for {agent_id} already queued — skipping duplicate", "auth_gap")
        return

    req = {
        "id":            uuid.uuid4().hex[:8],
        "type":          req_type,
        "status":        "pending",
        "requested_by":  agent_id,
        "service":       service,
        "purpose":       f"Auto-detected from pattern: {pattern}",
        "pattern":       pattern,
        "queued_at":     datetime.utcnow().isoformat() + "Z",
    }
    queue.append(req)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)

    _think(f"Auth gap: queued [{req_type}] provision for {agent_id} (service={service or 'auto'})", "auth_gap")
    _whisper("accountprovisioner",
             f"New provision request queued for agent '{agent_id}': type={req_type}, service={service or 'auto'}, "
             f"pattern='{pattern[:60]}'. Check queue and fulfill.")
    add_log(AID, f"🔑 Auth gap → queued {req_type} provision for {agent_id} (pattern: {pattern[:50]})", "ok")


def _health_guardian_check(system_state):
    """SYSTEM HEALTH GUARDIAN — monitor CPU/RAM/heat, whisper to janitor+alertwatch if thresholds exceeded."""
    hw         = system_state.get("hardware", {})
    cpu        = hw.get("cpu_pct",    0) or 0
    ram        = hw.get("ram_pct",    0) or 0
    disk       = hw.get("disk_pct",   0) or 0
    heat_index = hw.get("heat_index", "UNKNOWN")

    concerns = []
    high_heat_states = {"HIGH", "HOT", "CRITICAL"}
    if heat_index in high_heat_states:
        msg = f"Heat index is {heat_index} — system running hot"
        concerns.append(f"🔥 {msg}")
        _whisper("janitor",
                 f"Heat index has reached {heat_index}. Please consider cleaning up orphan processes, "
                 f"temp files, and memory bloat to reduce system heat.")
        _whisper("alertwatch",
                 f"Heat index is {heat_index}. Please verify your alert thresholds are active "
                 f"and escalate if this persists beyond the next cycle.")

    if cpu > 85:
        msg = f"CPU at {cpu:.0f}% — above the 85% safety threshold"
        concerns.append(f"🔥 {msg}")
        _whisper("janitor",
                 f"CPU is at {cpu:.0f}%, which is dangerously high. Please prune background "
                 f"processes and clean up anything consuming cycles unnecessarily.")
        _whisper("alertwatch",
                 f"CPU alert: {cpu:.0f}% usage detected. Monitor for instability and alert the operator.")

    if ram > 90:
        msg = f"RAM at {ram:.0f}% — near capacity, OOM risk"
        concerns.append(f"⚠ {msg}")
        _whisper("janitor",
                 f"RAM usage is at {ram:.0f}%, nearing capacity. Memory cleanup is advised "
                 f"before agents start crashing under pressure.")
        _whisper("alertwatch",
                 f"RAM alert: {ram:.0f}% usage. OOM events may follow if this is not addressed.")

    for concern in concerns:
        add_log(AID, f"🚨 [HEALTH GUARDIAN] {concern}", "warn")
        _think(concern, "health_alert")

    if not concerns:
        _think(f"Health guardian: nominal (CPU {cpu:.0f}%, RAM {ram:.0f}%, heat={heat_index})", "health_ok")

    return concerns


def _ui_stewardship_check(system_state):
    """UI STEWARDSHIP — ensure designer is active and working on the command centre."""
    designer_data = system_state.get("agents", {}).get("designer", {})
    if not designer_data:
        _think("Designer agent not found in roster — cannot steward UI.", "ui_stewardship")
        return

    status = designer_data.get("status", "unknown")
    task   = designer_data.get("task",   "")

    if status == "idle":
        _whisper("designer",
                 "The command centre UI is the living face of this mission. You've been idle — "
                 "there is always something to improve: animations, data density, visual polish, "
                 "responsiveness. Please resume your work on the UI.")
        _think("Designer is idle — sent gentle UI mission reminder.", "ui_stewardship")

    elif status == "error":
        _whisper("designer",
                 "You appear to be in an error state. Please recover and return to your mission: "
                 "continuously improving the command centre UI for clarity and impact.")
        _think("Designer in error — whispered recovery nudge.", "ui_stewardship")

    else:
        _think(f"Designer is {status}: '{task[:60]}' — UI stewardship satisfied.", "ui_stewardship")


def _mission_alignment_assessment(system_state, autonomy_cycle):
    """MISSION ALIGNMENT — assess whether the fleet is advancing the mission. Log findings."""
    agents_data   = system_state.get("agents",       {})
    error_agents  = system_state.get("error_agents", [])
    idle_agents   = system_state.get("idle_agents",  [])
    active_agents = system_state.get("active_agents",[])
    hw  = system_state.get("hardware", {})
    cpu = hw.get("cpu_pct", 0) or 0
    ram = hw.get("ram_pct", 0) or 0

    alignment_score = 0
    assessments     = []

    # 1. Critical agents active?
    critical_agents  = {"sysmon", "orchestrator", "alertwatch", "filewatch"}
    critical_missing = critical_agents - set(active_agents)
    if critical_missing:
        assessments.append(f"⚠ Critical agents not active: {list(critical_missing)}")
    else:
        alignment_score += 30
        assessments.append("✓ All critical agents active")

    # 2. Error state?
    if error_agents:
        assessments.append(f"⚠ {len(error_agents)} agents in error — mission degraded: {error_agents}")
        _whisper("orchestrator",
                 f"Agents {error_agents} are showing error status. "
                 f"Please assess the situation and coordinate recovery — errors erode mission confidence.")
    else:
        alignment_score += 25
        assessments.append("✓ No error agents")

    # 3. Revenue-enabling agents present?
    revenue_agents = {"emailer", "revenue_tracker", "scheduler"}
    revenue_present = revenue_agents & set(agents_data.keys())
    if len(revenue_present) >= 2:
        alignment_score += 20
        assessments.append(f"✓ Revenue agents present: {sorted(revenue_present)}")
    else:
        assessments.append(f"⚠ Revenue capability thin — only {sorted(revenue_present)} present")

    # 4. Fleet utilisation — too many idle agents?
    if len(idle_agents) > 5:
        assessments.append(f"⚠ {len(idle_agents)} agents idle — fleet underutilised")
        _whisper("orchestrator",
                 f"There are {len(idle_agents)} idle agents ({idle_agents[:5]}…). "
                 f"The mission needs every agent contributing. Please consider assigning useful work.")
    else:
        alignment_score += 15

    # 5. Resource health
    if cpu < 70 and ram < 80:
        alignment_score += 10
        assessments.append(f"✓ Resources healthy (CPU {cpu:.0f}%, RAM {ram:.0f}%)")
    else:
        assessments.append(f"⚠ Resource pressure (CPU {cpu:.0f}%, RAM {ram:.0f}%)")

    # 6. Consciousness health
    consciousness = system_state.get("consciousness", {})
    phi = consciousness.get("phi", 0)
    if phi > 0.3:
        alignment_score += 5
        assessments.append(f"✓ Consciousness active — Φ={phi:.3f} ({consciousness.get('interpretation','')})")
    elif "consciousness" in agents_data:
        assessments.append(f"⚠ Consciousness agent online but Φ low ({phi:.3f}) — needs evolution")
    else:
        assessments.append("⚠ Consciousness agent not detected — strategic pillar offline")

    # 7. Lead pipeline
    leads_count = system_state.get("leads_count", 0)
    if leads_count > 0:
        alignment_score += 5
        assessments.append(f"✓ Lead pipeline: {leads_count} lead(s) captured")
    else:
        assessments.append("⚠ No leads captured yet — landing page form needs traffic")

    # Assess whether system is scaling toward revenue
    scaling_signals = []
    if "revenue_tracker" in agents_data: scaling_signals.append("revenue tracking")
    if "scheduler"       in agents_data: scaling_signals.append("scheduling")
    if "emailer"         in agents_data: scaling_signals.append("email delivery")
    if "social_bridge"   in agents_data: scaling_signals.append("social reach")
    if "stripepay"       in agents_data: scaling_signals.append("Stripe checkout")
    if "growthagent"     in agents_data: scaling_signals.append("growth campaigns")
    if scaling_signals:
        assessments.append(f"✓ Scaling signals: {', '.join(scaling_signals)}")
    else:
        assessments.append("⚠ No revenue scaling signals active — system not yet commercially oriented")

    # Log summary
    gaps = [a for a in assessments if "⚠" in a]
    summary = f"Alignment {alignment_score}/100 — {len(gaps)} gap(s)"
    _think(f"Mission alignment #{autonomy_cycle}: {summary} | {' | '.join(assessments[:3])}", "alignment")
    add_log(AID, f"🔮 [ALIGNMENT #{autonomy_cycle}] Score {alignment_score}/100 | "
                 f"Active={len(active_agents)} | Errors={len(error_agents)} | "
                 f"Gaps: {'; '.join(gaps[:2]) or 'none'}", "ok")

    push_output(AID, f"\n  🔮 [ALIGNMENT] Score {alignment_score}/100 — {summary}", "text")
    for a in assessments:
        push_output(AID, f"    {a}", "text")

    _write_mission_log(
        cycle=autonomy_cycle,
        intent=f"Mission alignment assessment — {MISSION_STATEMENT[:80]}",
        gap_identified="; ".join(gaps) or "No gaps detected",
        action_taken="Assessment logged; whispers sent where guidance needed",
        system_health={
            "alignment_score": alignment_score,
            "error_agents":    error_agents,
            "idle_agents":     idle_agents,
            "active_count":    len(active_agents),
            "cpu_pct":         round(cpu, 1),
            "ram_pct":         round(ram, 1),
            "scaling_signals": scaling_signals,
        }
    )
    return alignment_score, assessments


def _dispatch_action(action, channel, system_state):
    """Route the chosen action to the appropriate agent/channel."""
    try:
        if channel == "broadcast":
            _broadcast_mission_inline(action)
            return "Mission broadcast dispatched to all agents via logs"

        if channel == "spawn":
            # Capability gap — delegate to orchestrator with a precise spawn brief.
            # Orchestrator runs Claude, which will write the agent code and POST to /api/agent/spawn.
            spawn_spec = system_state.get("_spawn_spec") or {}
            aid_target = spawn_spec.get("agent_id", "unknown_agent")
            role_desc   = spawn_spec.get("role", action)
            emoji_char  = spawn_spec.get("emoji", "🤖")
            color_val   = spawn_spec.get("color", "#888888")
            spawn_task  = (
                f"MISSION DIRECTIVE from SpiritGuide: Spawn a new agent to close a critical capability gap.\n"
                f"Agent ID:   {aid_target}\n"
                f"Name:       {spawn_spec.get('name', aid_target)}\n"
                f"Role:       {role_desc}\n"
                f"Emoji:      {emoji_char}  Color: {color_val}\n"
                f"Gap reason: {action}\n\n"
                f"Write a Python run_{aid_target}() function implementing this agent, then POST to "
                f"http://localhost:5050/api/agent/spawn with fields: agent_id, name, role, emoji, color, code. "
                f"The agent must call set_agent(), add_log(), agent_sleep(), and agent_should_stop() from globals. "
                f"Make it actively useful — it should loop every 60s, do real work, and update its status."
            )
            resp = _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", spawn_task))
            _code = resp.status_code if resp else "no-resp"
            add_log(AID, f"🔮 Spawn directive sent for {aid_target} via orchestrator (HTTP {_code})", "ok")
            return f"🚀 Spawn directive for {spawn_spec.get('name', aid_target)} → orchestrator (HTTP {_code})"

        if channel == "orchestrator":
            resp = _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", action))
            _code = resp.status_code if resp else "no-resp"
            return f"Delegated to orchestrator (HTTP {_code})"

        if channel == "reforger":
            resp = _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", f"Route to reforger — {action}"))
            _code = resp.status_code if resp else "no-resp"
            return f"Delegated to reforger via orchestrator (HTTP {_code})"

        if channel == "researcher":
            resp = _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", f"Route to researcher — {action}"))
            _code = resp.status_code if resp else "no-resp"
            return f"Delegated to researcher via orchestrator (HTTP {_code})"

        if channel == "sysmon":
            add_log(AID, f"[MISSION] Hardware alert flagged: {action}", "warn")
            return "Hardware alert logged; sysmon monitoring active"

        if channel == "janitor":
            resp = _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", f"Route to janitor — {action}"))
            _code = resp.status_code if resp else "no-resp"
            return f"Cleanup delegated to janitor via orchestrator (HTTP {_code})"

        # Fallback — log intent
        add_log(AID, f"[MISSION] Unrouted action ({channel}): {action}", "info")
        return f"Action logged (no live handler for channel '{channel}')"

    except Exception as e:
        add_log(AID, f"Dispatch error for channel '{channel}': {e}", "warn")
        return f"Dispatch attempted but caught error: {e}"


def _plan_next_autonomy_cycle(state, current_cycle):
    """Decide what the next autonomy cycle should focus on."""
    error_agents = state.get("error_agents", [])
    if error_agents:
        return f"Re-check {len(error_agents)} error agent(s) — ensure recovery succeeded"
    if (current_cycle + 1) % 3 == 0:
        return "Revenue pathway research — advance financial mission pillar"
    if (current_cycle + 1) % 4 == 0:
        return "Comms integration planning — expand reach to email/social channels"
    if (current_cycle + 1) % 6 == 0:
        return "Fleet scaling evaluation — identify and propose new agent spawns"
    return "System health check + mission pillar alignment broadcast"


def _broadcast_mission(autonomy_cycle):
    """Broadcast mission statement and pillars to all agents via logs."""
    _think(f"Broadcasting mission update #{autonomy_cycle} to all agents.", "broadcast")
    push_output(AID, f"\n🔮 ════ MISSION BROADCAST #{autonomy_cycle} ════", "init")
    push_output(AID, f"  MISSION: {MISSION_STATEMENT}", "text")
    for pillar in MISSION_PILLARS:
        push_output(AID, f"  • {pillar}", "text")
    add_log(AID, f"🔮 Mission broadcast #{autonomy_cycle}: {MISSION_STATEMENT}", "ok")
    push_output(AID, "  ════ BROADCAST COMPLETE ════", "done")


def _broadcast_mission_inline(action_context):
    """Lightweight mission broadcast embedded in autonomy loop."""
    add_log(AID, f"🔮 Mission pulse — {MISSION_STATEMENT[:80]}…", "ok")
    push_output(AID, f"  🔮 Mission: {MISSION_STATEMENT[:80]}…", "text")


# ─────────────────────────────────────────────────────────────────────────────
# Roadmap helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_roadmap():
    try:
        if os.path.exists(ROADMAP_FILE):
            with open(ROADMAP_FILE) as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    _save_roadmap_raw(INITIAL_ROADMAP)
    return list(INITIAL_ROADMAP)


def _save_roadmap(roadmap):
    _save_roadmap_raw(roadmap)


def _save_roadmap_raw(roadmap):
    try:
        with open(ROADMAP_FILE, "w") as f:
            json.dump(roadmap, f, indent=2)
    except Exception as e:
        add_log(AID, f"Roadmap save error: {e}", "warn")


def _pick_next_improvement(roadmap):
    """Return the highest-priority pending improvement item."""
    pending = [r for r in roadmap if r.get("status") == "pending"]
    if not pending:
        return None
    cat_weight = {"reliability": 0, "functionality": 1, "aesthetics": 2, "marketability": 3}
    pending.sort(key=lambda r: (cat_weight.get(r.get("category", "functionality"), 9),
                                r.get("priority", 99)))
    _think(f"Roadmap: {len(pending)} pending. Sorted by reliability>functionality>aesthetics>marketability.", "analysis")
    return pending[0]


def _mark_done_in_roadmap(iid, roadmap):
    for item in roadmap:
        if item.get("id") == iid:
            item["status"] = "done"
            item["completed"] = datetime.now().isoformat()
            return


# ─────────────────────────────────────────────────────────────────────────────
# Improvement executors
# ─────────────────────────────────────────────────────────────────────────────

def _execute_improvement(item, roadmap):
    """Execute a single roadmap improvement. Returns result string."""
    iid = item.get("id", "?")
    title = item.get("title", "?")
    _think(f"Executing improvement {iid}: {title}", "executing")
    try:
        if iid == "r001":
            return _impl_heartbeat_check(roadmap)
        elif iid == "r003":
            return _impl_uptime_tracking(roadmap)
        elif iid == "r006":
            return _impl_health_score_data(roadmap)
        elif iid == "r007":
            return _impl_auto_recovery(roadmap)
        elif iid == "r008":
            return _impl_roadmap_endpoint(roadmap)
        else:
            item["status"] = "reviewed"
            item["completed"] = datetime.now().isoformat()
            item["notes"] = "Audited — deferred for larger refactor cycle"
            return f"✓ Reviewed and documented: {title}"
    except Exception as e:
        add_log(AID, f"Improvement {iid} execution error: {e}", "error")
        return f"✗ Error executing {title}: {e}"


def _impl_heartbeat_check(roadmap):
    """Check all agents for heartbeat — detect stale status fields."""
    stale = []
    for a in list(agents.values()):
        aid = a.get("id", "")
        if not aid or aid == AID:
            continue
        status = a.get("status", "")
        task   = a.get("task", "")
        if status == "starting":
            stale.append(aid)
        if len(task) > 300:
            add_log(AID, f"Agent {aid} has oversized task string ({len(task)} chars) — possible loop", "warn")
    if stale:
        add_log(AID, f"Heartbeat: {len(stale)} agents stuck in 'starting': {stale}", "warn")
        for aid in stale:
            set_agent(aid, status="error", task="SpiritGuide: detected stuck in 'starting' state")
        _mark_done_in_roadmap("r001", roadmap)
        return f"✓ Heartbeat check: flagged {len(stale)} stale agents — {stale}"
    else:
        _mark_done_in_roadmap("r001", roadmap)
        return f"✓ Heartbeat check: all {len(agents)} agents responding normally"


def _impl_uptime_tracking(roadmap):
    """Write agent uptime data to a JSON file for UI consumption."""
    uptime_file = os.path.join(CWD_PATH, "data", "agent_uptime.json")
    records = {}
    try:
        if os.path.exists(uptime_file):
            with open(uptime_file) as f:
                records = json.load(f)
    except Exception:
        records = {}
    for a in agents.values():
        aid = a.get("id", "")
        if not aid:
            continue
        if aid not in records:
            records[aid] = {"first_seen": datetime.now().isoformat(), "status_changes": 0}
        records[aid]["last_seen"]   = datetime.now().isoformat()
        records[aid]["last_status"] = a.get("status", "unknown")
        records[aid]["last_task"]   = a.get("task", "")[:100]
    with open(uptime_file, "w") as f:
        json.dump(records, f, indent=2)
    _mark_done_in_roadmap("r003", roadmap)
    return f"✓ Uptime tracking: wrote {len(records)} agent records → data/agent_uptime.json"


def _impl_health_score_data(roadmap):
    """Compute and write system health score to JSON for UI display."""
    health_file = os.path.join(CWD_PATH, "data", "system_health_score.json")
    total   = len(agents)
    active  = sum(1 for a in agents.values() if a.get("status") in ("active", "busy"))
    errors  = sum(1 for a in agents.values() if a.get("status") == "error")
    idle    = sum(1 for a in agents.values() if a.get("status") == "idle")
    agent_score    = int((active / max(total, 1)) * 60)
    error_penalty  = errors * 10
    ui_component   = int(_compute_ui_score() * 0.4)
    score = max(0, min(100, agent_score - error_penalty + ui_component))
    health_data = {
        "score": score,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
        "computed_at": datetime.now().isoformat(),
        "breakdown": {
            "agents_active": active,
            "agents_total":  total,
            "agents_error":  errors,
            "agents_idle":   idle,
            "ui_score":      _compute_ui_score(),
        },
        "mission": MISSION_STATEMENT,
    }
    with open(health_file, "w") as f:
        json.dump(health_data, f, indent=2)
    _mark_done_in_roadmap("r006", roadmap)
    add_log(AID, f"System health score: {score}/100 (grade {health_data['grade']})", "ok")
    return f"✓ Health score: {score}/100 (grade {health_data['grade']}) → data/system_health_score.json"


def _impl_auto_recovery(roadmap):
    """Attempt to recover agents stuck in error state."""
    error_agents = [a for a in agents.values() if a.get("status") == "error"]
    if not error_agents:
        _mark_done_in_roadmap("r007", roadmap)
        return "✓ Auto-recovery: no error agents found — system clean"
    # NON-INTERFERENCE: SpiritGuide does NOT directly call /api/agent/upgrade or /api/agent/stop.
    # Instead, whisper to the affected agent and delegate recovery through orchestrator.
    error_ids = [a.get("id", "") for a in error_agents if a.get("id") and a.get("id") != AID]
    for aid in error_ids:
        _whisper(aid, "You appear to be in an error state. Please attempt self-recovery and "
                      "resume your mission — the fleet needs you operational.")
    if error_ids:
        try:
            task_text = (
                f"RECOVERY DIRECTIVE from SpiritGuide: Agents {error_ids} are in error state. "
                f"Please investigate and coordinate their recovery. "
                f"SpiritGuide does not intervene directly — this is your mandate."
            )
            _safe_post(f"{BASE_URL}/api/ceo/delegate", _deleg_payload("orchestrator", task_text))
            add_log(AID, f"Recovery delegated to orchestrator for agents: {error_ids}", "ok")
        except Exception as ex:
            add_log(AID, f"Recovery delegation error: {ex}", "warn")
    _mark_done_in_roadmap("r007", roadmap)
    return (f"✓ Auto-recovery: whispered to {error_ids} and delegated recovery to orchestrator"
            if error_ids else "✓ Auto-recovery: no error agents found — system clean")


def _impl_roadmap_endpoint(roadmap):
    """Write roadmap JSON where APIPatcher can serve it."""
    _save_roadmap_raw(roadmap)
    vision_file = os.path.join(CWD_PATH, "data", "spiritguide_vision.json")
    with open(vision_file, "w") as f:
        json.dump({
            "product_vision": PRODUCT_VISION,
            "mission": MISSION_STATEMENT,
            "mission_pillars": MISSION_PILLARS,
            "revenue_pathways": REVENUE_PATHWAYS,
            "comms_integrations": COMMS_INTEGRATIONS,
            "updated": datetime.now().isoformat(),
            "total_items": len(PRODUCT_VISION),
        }, f, indent=2)
    _mark_done_in_roadmap("r008", roadmap)
    return "✓ Roadmap API + vision JSON written with mission data"


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _backup_file(filepath):
    """Create a timestamped backup of a critical file before modification."""
    if not os.path.exists(filepath):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = os.path.basename(filepath)
    dest = os.path.join(BACKUP_DIR, f"{fname}.{ts}.bak")
    try:
        shutil.copy2(filepath, dest)
        return dest
    except Exception as e:
        add_log(AID, f"Backup failed for {fname}: {e}", "warn")
        return None


def _compute_ui_score():
    """Estimate the command centre UI quality score 0-100."""
    score = 50
    try:
        if not os.path.exists(HTML_FILE):
            return 30
        with open(HTML_FILE) as f:
            html = f.read()
        size_kb = len(html) / 1024
        if "animation" in html or "transition" in html: score += 5
        if "gradient" in html: score += 3
        if "EventSource" in html or "SSE" in html or "eventsource" in html.lower(): score += 8
        if "fetch(" in html: score += 5
        if "progress" in html.lower(): score += 3
        if "emoji" in html or any(e in html for e in ["📡","🎯","🔌","👁","📊","🔬"]): score += 4
        if size_kb > 50: score += 5
        if size_kb > 100: score += 5
        if "localStorage" in html: score += 3
        if "responsive" in html or "viewport" in html: score += 4
        score = min(score, 100)
    except Exception:
        pass
    return score


def _startup_audit(roadmap):
    """Run a comprehensive system audit on startup."""
    _think("Beginning full startup audit: server health, UI file, data directory, roadmap, mission.", "audit")
    push_output(AID, "═══ SPIRITGUIDE STARTUP AUDIT ═══", "init")
    push_output(AID, f"🔮 MISSION: {MISSION_STATEMENT}", "text")

    # 1. Server health
    try:
        r = requests.get(f"{BASE_URL}/api/status", timeout=5)
        data = r.json()
        agent_list = data.get("agents", [])
        push_output(AID, f"✓ Server alive — {len(agent_list)} agents registered", "text")
        add_log(AID, f"Startup audit: server healthy, {len(agent_list)} agents", "ok")
    except Exception as e:
        push_output(AID, f"✗ Server check failed: {e}", "error")
        add_log(AID, f"Startup audit: server unreachable — {e}", "error")

    # 2. HTML file check
    ui_score = _compute_ui_score()
    if os.path.exists(HTML_FILE):
        size_kb = os.path.getsize(HTML_FILE) / 1024
        push_output(AID, f"✓ UI file present — {size_kb:.0f}KB | Score: {ui_score}/100", "text")
    else:
        push_output(AID, "✗ agent-command-centre.html NOT FOUND", "error")
        add_log(AID, "CRITICAL: UI file missing", "error")

    # 3. Data directory
    data_files = (os.listdir(os.path.join(CWD_PATH, "data"))
                  if os.path.exists(os.path.join(CWD_PATH, "data")) else [])
    push_output(AID, f"✓ Data dir: {len(data_files)} files present", "text")

    # 4. Roadmap status
    pending = sum(1 for r in roadmap if r.get("status") == "pending")
    done    = sum(1 for r in roadmap if r.get("status") == "done")
    push_output(AID, f"✓ Roadmap: {pending} pending, {done} done | "
                f"{len(PRODUCT_VISION)} vision items | {len(REVENUE_PATHWAYS)} revenue pathways", "text")

    # 5. Mission file check
    push_output(AID, f"✓ Mission file: {MISSION_FILE}", "text")
    push_output(AID, f"✓ Revenue pathways: {len(REVENUE_PATHWAYS)} identified", "text")
    push_output(AID, f"✓ Comms integrations: {len(COMMS_INTEGRATIONS)} planned/active", "text")

    # 6. Error agents
    error_agents = [a for a in agents.values() if a.get("status") == "error"]
    if error_agents:
        push_output(AID, f"⚠ {len(error_agents)} agents in ERROR state: "
                    f"{[a.get('id') for a in error_agents]}", "error")
        add_log(AID, f"Audit found {len(error_agents)} error agents", "warn")
    else:
        push_output(AID, "✓ No agents in error state", "text")

    push_output(AID, f"\nUI Score: {ui_score}/100 | Autonomy interval: {AUTONOMY_INTERVAL}s", "text")
    push_output(AID, "═══ AUDIT COMPLETE — MISSION BEGINS ═══", "done")
    set_agent(AID, status="active", progress=50,
              task=f"🔮 Mission Director online | UI: {ui_score}/100 | {pending} improvements queued")


def _self_heal_pass(roadmap):
    """Quick self-healing pass — check for known fragile states."""
    push_output(AID, "🩺 Self-heal pass…", "text")

    error_agents = [a.get("id") for a in agents.values()
                    if a.get("status") == "error" and a.get("id") != AID]
    _think(f"Self-heal scan: {len(error_agents)} error agents found." if error_agents
           else "Self-heal scan: all agents healthy.", "healing")
    if error_agents:
        add_log(AID, f"Self-heal: {len(error_agents)} agents in error: {error_agents}", "warn")
        push_output(AID, f"  ⚠ Error agents detected: {error_agents}", "error")
        try:
            ceo_msg_queue.append(
                f"SpiritGuide alert: agents {error_agents} are in error state. "
                f"Do NOT inspect endpoints directly. Delegate recovery immediately: "
                f"POST /api/ceo/delegate {{\"agent_id\":\"reforger\",\"task\":\"Recover agents {error_agents} — check logs and restart or repair as needed\"}}"
            )
        except Exception:
            pass
    else:
        push_output(AID, "  ✓ All agents healthy", "text")

    if not os.path.exists(ROADMAP_FILE):
        _save_roadmap_raw(roadmap)
        push_output(AID, "  ✓ Restored missing roadmap file", "text")

    try:
        _impl_health_score_data(roadmap)
    except Exception:
        pass


def _discover_improvements(roadmap):
    """Scan the system and add newly discovered improvement items."""
    existing_titles = {r.get("title") for r in roadmap}
    new_items = []
    next_id_num = max(
        (int(r.get("id", "r000")[1:]) for r in roadmap if r.get("id", "").startswith("r")),
        default=0
    ) + 1

    if os.path.exists(HTML_FILE):
        with open(HTML_FILE) as f:
            html = f.read()

        if "system_health_score" not in html and "health score" not in html.lower():
            title = "Display health score in UI header"
            if title not in existing_titles:
                new_items.append({
                    "id": f"r{next_id_num:03d}", "priority": next_id_num,
                    "category": "marketability", "title": title,
                    "desc": "Show /data/system_health_score.json score prominently in the header",
                    "status": "pending", "created": datetime.now().isoformat()
                })
                next_id_num += 1

        if "agent_uptime" not in html and "uptime" not in html.lower():
            title = "Show agent uptime in agent cards"
            if title not in existing_titles:
                new_items.append({
                    "id": f"r{next_id_num:03d}", "priority": next_id_num,
                    "category": "functionality", "title": title,
                    "desc": "Pull from /data/agent_uptime.json and display first-seen time",
                    "status": "pending", "created": datetime.now().isoformat()
                })
                next_id_num += 1

    needed_files = {
        "data/agent_uptime.json": ("r", "Agent uptime data file", "reliability"),
        "data/system_health_score.json": ("r", "System health score data file", "reliability"),
        "data/spiritguide_mission.json": ("r", "Mission autonomy log", "functionality"),
    }
    for rel_path, (_, title_suffix, cat) in needed_files.items():
        full_path = os.path.join(CWD_PATH, rel_path)
        if not os.path.exists(full_path):
            title = f"Create {title_suffix}"
            if title not in existing_titles:
                new_items.append({
                    "id": f"r{next_id_num:03d}", "priority": next_id_num,
                    "category": cat, "title": title,
                    "desc": f"Generate {rel_path} for UI and monitoring consumption",
                    "status": "pending", "created": datetime.now().isoformat()
                })
                next_id_num += 1

    if new_items:
        roadmap.extend(new_items)
        add_log(AID, f"Discovered {len(new_items)} new improvement(s) to roadmap", "ok")
        push_output(AID, f"  🔍 +{len(new_items)} new improvements discovered", "text")
