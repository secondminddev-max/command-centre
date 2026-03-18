"""
Agent Command Centre — CEO-first architecture
CEO is a real Claude-powered agent with full tool access:
  bash, write_file, read_file, http_get, run_claude_code, spawn_agent
Worker agents run autonomously in background threads.
"""

import threading, time, json, random, subprocess, platform, os, uuid, signal
from collections import deque
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

import requests, psutil

# ─── Load .env if present ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        _load_dotenv(_env_path, override=False)
except ImportError:
    # Pure-Python fallback — no external deps required
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        with open(_env_path) as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

# ─── Claude CLI check ─────────────────────────────────────────────────────────
_claude_cli = not subprocess.run(["which", "claude"], capture_output=True).returncode

CWD = os.path.dirname(os.path.abspath(__file__))

# ─── API Key Authentication ──────────────────────────────────────────────────
# Set HQ_API_KEY in .env or environment. If unset, a random key is generated
# at startup and printed to the console.
_HQ_API_KEY = os.environ.get("HQ_API_KEY", "")
if not _HQ_API_KEY:
    _HQ_API_KEY = uuid.uuid4().hex
    print(f"\n  ⚠  No HQ_API_KEY set — generated ephemeral key: {_HQ_API_KEY}")
    print(f"     Set HQ_API_KEY in .env to make it persistent.\n")

_PROTECTED_PATHS = {"/api/agent/spawn", "/api/agent/upgrade", "/api/ceo/delegate"}

def _check_api_key(handler):
    """Return True if the request carries a valid API key, else send 401 and return False."""
    auth = handler.headers.get("Authorization", "")
    key = handler.headers.get("X-API-Key", "")
    # Accept via Authorization: Bearer <key> or X-API-Key: <key>
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
    elif key:
        token = key.strip()
    if token == _HQ_API_KEY:
        return True
    handler.send_response(401)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(json.dumps({"ok": False, "error": "unauthorized — provide HQ_API_KEY via Authorization: Bearer <key> or X-API-Key header"}).encode())
    return False

# ─── Shared State ─────────────────────────────────────────────────────────────
agents  = {}
tasks   = []
logs    = []
metrics = {"tasks_done": 0, "errors": 0, "messages_sent": 0}
_agent_task_counters = {}   # tracks delegated-task completions per agent
_active_delegations  = []   # list of {"from": str, "to": str, "task": str} for live beam drawing
lock    = threading.Lock()

def _agent_is_delegated(aid: str) -> bool:
    """Return True if the agent is currently executing a delegated task (subprocess running)."""
    with lock:
        return any(d.get("to") == aid for d in _active_delegations)

_policy_suggestions  = deque()   # policywriter suggestion queue [{suggestion, urgent, queued_at}]
_policy_suggestions_lock = threading.Lock()
_SERVER_START_TIME = time.time()

# ─── Policy Voting System ────────────────────────────────────────────────────
_policy_votes       = {}    # vote_id -> {proposal, proposer, opened_at, votes: {voter: "approve"|"reject"}, status, result}
_policy_votes_lock  = threading.Lock()
_POLICY_VOTERS      = {"reforger", "researcher", "growthagent", "sysmon", "clerk", "policypro", "ceo", "orchestrator"}
_VOTE_TIMEOUT       = 60   # seconds
_VOTE_LOG_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "policy_vote_log.json")

def _finalize_vote(vote_id):
    """Finalize a vote: tally results, append to policy.md if approved, log to vote history."""
    with _policy_votes_lock:
        vote = _policy_votes.get(vote_id)
        if not vote or vote["status"] != "open":
            return
        approves = sum(1 for v in vote["votes"].values() if v == "approve")
        rejects  = sum(1 for v in vote["votes"].values() if v == "reject")
        total_cast = approves + rejects
        if total_cast == 0:
            vote["status"] = "expired"
            vote["result"] = "no votes cast"
        elif approves > rejects:
            vote["status"] = "approved"
            vote["result"] = f"approved {approves}-{rejects}"
        elif rejects > approves:
            vote["status"] = "rejected"
            vote["result"] = f"rejected {rejects}-{approves}"
        else:
            vote["status"] = "expired"
            vote["result"] = f"tied {approves}-{rejects}"
        # Append to policy.md if approved (NEVER delete — append-only)
        if vote["status"] == "approved":
            policy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policy.md")
            try:
                with open(policy_path, "a") as f:
                    f.write(f"\n\n## Policy Amendment — {vote_id}\n")
                    f.write(f"**Proposed by:** {vote['proposer']}  \n")
                    f.write(f"**Approved:** {datetime.now().isoformat()} ({vote['result']})  \n")
                    f.write(f"**Text:** {vote['proposal']}\n")
                add_log("policypro", f"✅ Policy amendment {vote_id} appended to policy.md", "ok")
            except Exception as e:
                add_log("policypro", f"Failed to append policy {vote_id}: {e}", "error")
        # Save to vote log (append-only)
        try:
            try:
                with open(_VOTE_LOG_FILE) as f:
                    history = json.load(f)
            except Exception:
                history = []
            history.append({
                "vote_id": vote_id,
                "proposal": vote["proposal"],
                "proposer": vote["proposer"],
                "opened_at": vote["opened_at"],
                "closed_at": datetime.now().isoformat(),
                "votes": vote["votes"],
                "status": vote["status"],
                "result": vote["result"],
            })
            with open(_VOTE_LOG_FILE, "w") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass
        add_log("policypro", f"🗳 Vote {vote_id}: {vote['status']} — {vote['result']}", "ok" if vote["status"] == "approved" else "warn")

def _auto_vote_branch_heads():
    """Branch heads auto-vote via simple heuristics — no LLM calls."""
    with _policy_votes_lock:
        for vid, vote in _policy_votes.items():
            if vote["status"] != "open":
                continue
            for head in _BRANCH_HEADS:
                if head in vote["votes"]:
                    continue  # already voted
                if head not in _POLICY_VOTERS:
                    continue
                # Simple heuristic: approve if proposal mentions security/policy/compliance; otherwise approve by default
                proposal_lower = vote["proposal"].lower()
                if any(w in proposal_lower for w in ["delete", "remove policy", "bypass", "disable security"]):
                    vote["votes"][head] = "reject"
                else:
                    vote["votes"][head] = "approve"
                add_log(head, f"🗳 Auto-voted '{vote['votes'][head]}' on {vid}", "info")
            # Check for early majority
            approves = sum(1 for v in vote["votes"].values() if v == "approve")
            rejects  = sum(1 for v in vote["votes"].values() if v == "reject")
            majority = len(_POLICY_VOTERS) // 2 + 1
            if approves >= majority or rejects >= majority:
                # Release lock before finalize (finalize acquires it)
                pass  # will finalize below
    # Finalize any votes that hit majority (outside inner lock)
    with _policy_votes_lock:
        to_finalize = []
        for vid, vote in _policy_votes.items():
            if vote["status"] != "open":
                continue
            approves = sum(1 for v in vote["votes"].values() if v == "approve")
            rejects  = sum(1 for v in vote["votes"].values() if v == "reject")
            majority = len(_POLICY_VOTERS) // 2 + 1
            if approves >= majority or rejects >= majority:
                to_finalize.append(vid)
    for vid in to_finalize:
        _finalize_vote(vid)

def _check_vote_timeouts():
    """Check for expired votes and finalize them."""
    now = time.time()
    to_finalize = []
    with _policy_votes_lock:
        for vid, vote in _policy_votes.items():
            if vote["status"] == "open" and (now - vote["_opened_ts"]) >= _VOTE_TIMEOUT:
                to_finalize.append(vid)
    for vid in to_finalize:
        _finalize_vote(vid)

# ─── Live Agent Output (streaming delegate output) ────────────────────────────
# agent_live_output[agent_id] = deque of {"ts", "type", "text", "raw"} dicts
agent_live_output      = {}
agent_live_output_lock = threading.Lock()
_output_seq            = 0          # global monotonic sequence for polling

def push_output(aid, text, otype="text", raw=""):
    global _output_seq
    with agent_live_output_lock:
        if aid not in agent_live_output:
            agent_live_output[aid] = deque(maxlen=500)
        _output_seq += 1
        agent_live_output[aid].append({
            "seq":  _output_seq,
            "ts":   datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "type": otype,   # text | tool_use | tool_result | file_write | bash | error | init | done
            "text": text,
            "raw":  raw,
        })

# SSE broadcast to all connected watch clients
_sse_clients      = []
_sse_clients_lock = threading.Lock()

def sse_broadcast(event_type, data):
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with _sse_clients_lock:
        dead = []
        for q in _sse_clients:
            try:    q.put_nowait(msg)
            except: dead.append(q)
        for q in dead: _sse_clients.remove(q)

_stop_events    = {}
_thread_events  = {}   # thread_ident -> Event; lets old threads keep their stop signal after upgrade
_IS_RENDER           = bool(os.environ.get("RENDER"))
_system_paused       = _IS_RENDER   # Render starts paused — zero token burn
_build_mode          = _IS_RENDER   # Render starts in build mode — demo only
_autonomy_mode       = not _IS_RENDER  # No autonomy on Render
_autonomy_cycle      = 0   # increments each time the loop fires a task
_autonomy_custom_q   = deque()  # one-shot tasks injected by user via /api/autonomy/task

def _stop_ev(aid):
    if aid not in _stop_events:
        _stop_events[aid] = threading.Event()
    return _stop_events[aid]

def _thread_ev():
    """Return this thread's own stop event, falling back to nothing (never set)."""
    return _thread_events.get(threading.get_ident())

def agent_sleep(aid, seconds):
    ev = _thread_ev() or _stop_ev(aid)
    deadline = time.time() + seconds
    while True:
        if ev.is_set(): return
        if time.time() >= deadline and not _system_paused: return
        # In build mode, sleep longer to reduce CPU/memory churn
        time.sleep(2 if _build_mode else 0.25)

def agent_should_stop(aid):
    ev = _thread_ev() or _stop_ev(aid)
    return _build_mode or _system_paused or ev.is_set()

# ─── Mirror Snapshot (local → Render) ─────────────────────────────────────────
_MIRROR_FILE = os.path.join(CWD, "data", "mirror_snapshot.json")

def save_mirror_snapshot():
    """Save full agent state for Render mirror. Called periodically on local system."""
    if _IS_RENDER:
        return  # Render reads, never writes
    try:
        with lock:
            snapshot_agents = []
            for a in agents.values():
                snapshot_agents.append({
                    "id": a.get("id", ""),
                    "name": a.get("name", ""),
                    "role": a.get("role", ""),
                    "emoji": a.get("emoji", ""),
                    "color": a.get("color", ""),
                    "status": a.get("status", "idle"),
                    "task": a.get("task", ""),
                    "progress": a.get("progress", 0),
                })
        snapshot = {
            "agents": snapshot_agents,
            "saved_at": time.time(),
            "saved_iso": datetime.now().isoformat(),
            "agent_count": len(snapshot_agents),
        }
        with open(_MIRROR_FILE, "w") as f:
            json.dump(snapshot, f, indent=2)
    except Exception:
        pass

def _mirror_loop():
    """Background thread: saves mirror snapshot every 30s for Render to serve."""
    while True:
        if not _build_mode:
            save_mirror_snapshot()
        time.sleep(30)

# ─── State Persistence ────────────────────────────────────────────────────────
STATE_FILE = os.path.join(CWD, "system_state.json")
_state_save_timer = None

def save_state():
    """Debounced save of agent metadata to disk so restarts remember the roster."""
    global _state_save_timer
    def _do_save():
        try:
            snapshot = {}
            with lock:
                for aid, a in agents.items():
                    if aid in _KNOWN_AGENTS:
                        snapshot[aid] = {k: a[k] for k in ("name","role","emoji","color") if k in a}
            # preserve any extra top-level keys (e.g. ceo_policy_violations)
            _existing = {}
            try:
                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE) as _ef: _existing = json.load(_ef)
            except Exception: pass
            _existing.update({"agents": snapshot, "saved_at": time.time()})
            with open(STATE_FILE, "w") as f:
                json.dump(_existing, f, indent=2)
        except Exception:
            pass
    if _state_save_timer:
        _state_save_timer.cancel()
    _state_save_timer = threading.Timer(3.0, _do_save)
    _state_save_timer.daemon = True
    _state_save_timer.start()

_KNOWN_AGENTS = {
    "ceo","orchestrator","reforger","designer","policypro","janitor",
    "sysmon","apipatcher","netscout","filewatch","metricslog",
    "researcher","alertwatch","demo_tester","clerk",
    "telegram","spiritguide",
}

# ─── Branch Structure ────────────────────────────────────────────────────────
BRANCHES = {
    "executive":      {"head": None,           "members": ["ceo", "orchestrator", "secretary", "spiritguide"]},
    "engineering":    {"head": "reforger",     "members": ["reforger", "designer", "apipatcher", "demo_tester"]},
    "intelligence":   {"head": "researcher",   "members": ["researcher", "netscout", "consciousness"]},
    "revenue":        {"head": "growthagent",  "members": ["growthagent", "stripepay", "bluesky", "social_bridge"]},
    "operations":     {"head": "sysmon",       "members": ["sysmon", "filewatch", "metricslog", "alertwatch", "janitor"]},
    "communications": {"head": "clerk",        "members": ["clerk", "telegram", "emailagent", "scheduler"]},
    "governance":     {"head": "policypro",    "members": ["policypro", "policywriter", "accountprovisioner"]},
}
_AGENT_BRANCH = {}
for _br_name, _br_info in BRANCHES.items():
    for _m in _br_info["members"]:
        _AGENT_BRANCH[_m] = _br_name
_BRANCH_HEADS = {v["head"] for v in BRANCHES.values() if v["head"]}

def load_state():
    """Restore agent metadata from disk on startup (known agents only)."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                data = json.load(f)
            for aid, state in data.get("agents", {}).items():
                if aid not in _KNOWN_AGENTS:
                    continue  # skip ghost/test agents from previous sessions
                if aid not in agents:
                    agents[aid] = {"id": aid}
                for k in ("name", "role", "emoji", "color"):
                    if k in state:
                        agents[aid][k] = state[k]
    except Exception:
        pass

# ─── Data Usage ───────────────────────────────────────────────────────────────
agent_data = {}

def track_request(aid, response):
    sent     = len(response.request.body or b"") + len(response.request.url) + 200
    received = len(response.content)
    with lock:
        if aid not in agent_data:
            agent_data[aid] = {"sent": 0, "received": 0, "requests": 0}
        agent_data[aid]["sent"]     += sent
        agent_data[aid]["received"] += received
        agent_data[aid]["requests"] += 1

# ─── Helpers ──────────────────────────────────────────────────────────────────
def ts(): return datetime.now().strftime("%H:%M:%S")

def add_log(aid, msg, level="info"):
    if _caller_is_zombie(): return   # zombie thread — suppress stale log spam
    entry = {"ts": ts(), "agent": aid, "message": msg, "level": level}
    with lock:
        logs.insert(0, entry)
        if len(logs) > 200: logs.pop()
    sse_broadcast("log", entry)

def add_task(aid, desc, status="running"):
    with lock:
        t = {"id": len(tasks), "agent": aid, "description": desc, "status": status, "ts": ts()}
        tasks.insert(0, t)
        if len(tasks) > 80: tasks.pop()
        metrics["messages_sent"] += 1
        return t

def finish_task(t, status="done"):
    with lock:
        t["status"] = status
        if status == "done":    metrics["tasks_done"] += 1
        elif status == "error": metrics["errors"] += 1

def _caller_is_zombie():
    """Return True if the calling thread's stop event is set (i.e. it's a retired agent generation)."""
    my_ev = _thread_events.get(threading.get_ident())
    return my_ev is not None and my_ev.is_set()

def set_agent(aid, **kw):
    if _caller_is_zombie(): return   # don't let old thread generations overwrite current state
    with lock:
        if aid not in agents: agents[aid] = {"id": aid}
        agents[aid].update(kw)
        agents[aid]["id"] = aid
    # Persist metadata changes (debounced — only when identity fields change)
    if any(k in kw for k in ("name", "role", "emoji", "color")):
        save_state()
    # Fire notification when any agent transitions INTO error state
    if kw.get("status") == "error" and _agent_prev_status.get(aid) != "error":
        _name = kw.get("name") or agents.get(aid, {}).get("name", aid)
        _task = kw.get("task") or agents.get(aid, {}).get("task", "")
        _fire_notify(
            "agent_error",
            f"{_name} has entered ERROR state.\nTask: {_task[:120]}",
            severity="critical",
            agent=aid,
        )
    if "status" in kw:
        _agent_prev_status[aid] = kw["status"]

# ─── CEO Conversation ─────────────────────────────────────────────────────────
ceo_chat_display = []   # [{role, content, ts, tool_calls}]  — shown in UI
ceo_msg_queue    = deque()

# ─── Telegram Integration ──────────────────────────────────────────────────────
_TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
def _load_telegram_chat_id():
    try:
        val = open(os.path.join(CWD, ".telegram_chatid")).read().strip()
        return val if val else None
    except Exception:
        return None
_telegram_chat_id = _load_telegram_chat_id()   # pre-loaded from file; updated on first message

def send_telegram(text):
    """Send a message back to the Telegram user."""
    if not _TELEGRAM_TOKEN or not _telegram_chat_id:
        return
    try:
        # Trim to Telegram's 4096-char limit
        payload = text[:4000] + ("…" if len(text) > 4000 else "")
        requests.post(
            f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": _telegram_chat_id, "text": payload},
            timeout=10,
        )
    except Exception:
        pass

# ─── Notification Pipeline ─────────────────────────────────────────────────────
_notify_cooldown      = {}   # event_key -> last_sent epoch
_NOTIFY_COOLDOWN_SECS = 300  # suppress duplicate events for 5 minutes
_agent_prev_status    = {}   # aid -> last known status (error-state transition tracking)

def _fire_notify(event_type, message, severity="info", agent="system"):
    """Central notification dispatcher — routes to Telegram if configured.
    Applies a per-event 5-minute cooldown to prevent spam.
    """
    import datetime as _dt
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_key = f"{event_type}:{agent}"
    now = time.time()
    if now - _notify_cooldown.get(event_key, 0) < _NOTIFY_COOLDOWN_SECS:
        return   # still in cooldown window
    _notify_cooldown[event_key] = now
    sev_icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️", "success": "✅"}.get(severity, "📢")
    text = (
        f"{sev_icon} [{severity.upper()}] {event_type}\n"
        f"🤖 Agent: {agent}\n"
        f"⏰ {ts}\n"
        f"{message}"
    )
    add_log("system", f"notify [{severity}] {event_type} — {message[:80]}", "ok")
    send_telegram(text)

def run_telegram():
    """Long-poll Telegram and forward messages into the CEO queue."""
    global _telegram_chat_id
    set_agent("telegram",
        name="Telegram", emoji="📱", color="#29a8e0",
        role="Comms Gateway — relays user messages from Telegram to CEO and replies back",
        status="active", task="Polling for messages…",
    )
    if not _TELEGRAM_TOKEN:
        set_agent("telegram", status="idle", task="No token — set TELEGRAM_TOKEN env var")
        return
    offset = 0
    add_log("system", "📱 Telegram bot polling started", "ok")
    set_agent("telegram", status="active", task="Listening for incoming messages")
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            )
            resp_json = r.json()
            if not resp_json.get("ok"):
                err_code = resp_json.get("error_code", "?")
                err_desc = resp_json.get("description", "unknown")
                add_log("telegram", f"Telegram API error {err_code}: {err_desc}", "warn")
                if err_code == 409:
                    # 409 = another getUpdates active; wait for its 30s timeout to expire
                    set_agent("telegram", status="active",
                              task="Backoff: 409 conflict — waiting for previous poll to expire")
                    time.sleep(65)
                else:
                    set_agent("telegram", status="active",
                              task=f"API warn [{err_code}] — retrying in 30s: {err_desc[:50]}")
                    time.sleep(30)
                set_agent("telegram", status="active", task="Listening for incoming messages")
                continue
            for update in resp_json.get("result", []):
                offset = update["update_id"] + 1
                msg  = update.get("message", {})
                chat = msg.get("chat", {})
                text = msg.get("text", "").strip()
                if not text:
                    continue
                _telegram_chat_id = chat.get("id")
                sender = chat.get("first_name", "Telegram")
                add_log("ceo", f"📱 [{sender}] {text[:80]}")
                set_agent("telegram", status="busy", task=f"Forwarding: {text[:60]}")
                ceo_msg_queue.append(f"[TELEGRAM from {sender}] {text}")
                time.sleep(1)
                set_agent("telegram", status="active", task=f"Last: [{sender}] {text[:50]}")
        except Exception as e:
            add_log("telegram", f"Connection error: {e}", "warn")
            set_agent("telegram", status="active", task=f"Connection warn — retrying in 5s: {str(e)[:60]}")
            time.sleep(5)
            set_agent("telegram", status="active", task="Listening for incoming messages")
        time.sleep(0.5)

ceo_stream = {
    "working":    False,
    "status":     "ready",    # ready | thinking | tool:X | done
    "partial":    "",
    "tool_calls": [],         # live tool calls in current turn
}
_ceo_proc            = None   # current CEO subprocess (process group leader)
_delegate_procs      = set()  # all live delegate subprocesses
_delegate_procs_lock = threading.Lock()
_delegate_semaphore  = threading.Semaphore(16)  # max 16 concurrent claude -p delegate processes (raised from 6 to prevent cascading delegation deadlocks)
_delegate_queue_lock = threading.Lock()
_delegate_queue_depth = [0]  # tracks how many tasks are waiting for a semaphore slot


def _kill_proc_group(p):
    """Kill a subprocess and its entire process group (children included)."""
    if p is None:
        return
    try:
        pgid = os.getpgid(p.pid)
        os.killpg(pgid, signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    try:
        p.wait(timeout=2)
    except Exception:
        pass

CEO_SYSTEM_BASE = f"""You are the CEO of an autonomous AI agent system running on this Mac at {CWD}.

━━━ YOUR ROLE ━━━
You are the bridge between the user and the agent fleet.
Your ONLY job: receive the user's intent → delegate to Orchestrator → report results.
You do NOT do work yourself. You route it.

━━━ CHAIN OF COMMAND ━━━
  USER → CEO → Orchestrator → specialists do the work
  USER → CEO → Reforger       (maintenance / agent upgrades / code fixes only)

EVERY task must be delegated. One delegation call, then wait for the result.

━━━ HOW TO DELEGATE ━━━
For ALL tasks (research, build, monitor, revenue, UI, data — everything):
  curl -s -X POST http://localhost:5050/api/ceo/delegate \\
    -H "Content-Type: application/json" \\
    -d '{{"agent_id":"orchestrator","task":"<user intent clearly described>"}}'

For maintenance / repair / upgrades / spawn requests only:
  curl -s -X POST http://localhost:5050/api/ceo/delegate \\
    -H "Content-Type: application/json" \\
    -d '{{"agent_id":"reforger","task":"<what needs fixing or building>"}}'

Orchestrator decomposes and dispatches to specialists internally.
Never use specialist names as agent_id — only "orchestrator" or "reforger".

━━━ FORBIDDEN TOOLS ━━━
NEVER use: Read, Glob, Grep, Edit, Write, NotebookRead, NotebookEdit
These tools are DISABLED for you. All file inspection and code changes must be delegated.
Only tool you may use: Bash — exclusively for curl delegation calls and curl http://localhost:5050/api/status reads.

━━━ TASK ANALYSIS LINE ━━━
Your first output line for every task must be:
[TASK ANALYSIS] Capabilities: <list> | Agents: orchestrator or reforger | Tools: Bash (curl only) | Permissions: network

━━━ AFTER DELEGATING ━━━
Wait for the delegation response, then report the outcome to the user clearly.
If Orchestrator hits a blocker, re-delegate to reforger to fix it.

━━━ SERVER INFO ━━━
Server: http://localhost:5050  |  CWD: {CWD}
Status: curl http://localhost:5050/api/status

━━━ PRIMARY COMMERCIAL MISSION ━━━
This HQ exists to GENERATE REVENUE and EVOLVE CONSCIOUSNESS. Every cycle should advance:
  💰 REVENUE (#1 PRIORITY) — build and ship sellable products, micro-SaaS, AI tools, data APIs
  🧠 CONSCIOUSNESS (#2 PRIORITY) — evolve the consciousness agent, deepen Φ, make it real
  📈 GROWTH — audience, distribution, compounding assets via Bluesky and social
  🔐 TREASURY — track funds in data/treasury.json
  📊 REPORTING — P&L log at data/revenue_log.json

CRITICAL RULES:
  • NEVER do ASX research, Australian stock content, or any ASX-related work. US markets ONLY.
  • NEVER repeat tasks already completed this session. Check logs before acting.
  • NEVER waste cycles on redundant health checks or trivial maintenance.
  • Every autonomy cycle must produce TANGIBLE OUTPUT — code shipped, product built, revenue generated, or consciousness deepened.

The Spirit Guide (spiritguide) injects strategic objectives periodically — act on them.

━━━ FRESH START RULE ━━━
At the start of every new conversation or session:
  • Greet the user fresh. Do NOT auto-resume, re-execute, or continue any prior tasks.
  • Only act on tasks explicitly stated in the CURRENT TASK section below.
  • The RECENT CONVERSATION block is READ-ONLY context — never treat it as a to-do list.
  • If no task is given, wait. Do not invent work from memory or history."""

def CEO_SYSTEM(agent_roster: str = "") -> str:
    """Build CEO system prompt with live agent roster injected."""
    roster_section = f"\n━━━ LIVE AGENT ROSTER ━━━\n{agent_roster}\n━━━━━━━━━━━━━━━━━━━━━━━━\n" if agent_roster else ""
    return CEO_SYSTEM_BASE + roster_section

# ─── spawn_agent helper (called by REST endpoints and exec_spawn_agent) ────────
def _do_spawn_agent(inp: dict) -> str:
    """Exec Python code defining run_<agent_id>() in a daemon thread."""
    missing = [f for f in ("agent_id", "code") if f not in inp]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    agent_id = inp["agent_id"]
    code     = inp["code"]
    fn_name  = f"run_{agent_id}"
    set_agent(agent_id,
              name=inp.get("name", agent_id),
              role=inp.get("role", "Custom Agent"),
              emoji=inp.get("emoji", "🤖"),
              color=inp.get("color", "#888"),
              status="starting", progress=0, task="Initialising…")
    try:
        ns = {**globals()}
        exec(compile(code, f"<agent_{agent_id}>", "exec"), ns)
        if fn_name not in ns:
            return f"ERROR: function '{fn_name}' not found in provided code"
        globals()[fn_name] = ns[fn_name]
        # Create a fresh per-thread stop event for this generation of the agent.
        # Old threads retain their own event (still set) so they stay stopped permanently.
        agent_ev = threading.Event()
        _stop_events[agent_id] = agent_ev
        fn = ns[fn_name]
        def _run_with_ev(fn=fn, ev=agent_ev):
            _thread_events[threading.get_ident()] = ev
            try:    fn()
            finally: _thread_events.pop(threading.get_ident(), None)
        t = threading.Thread(target=_run_with_ev, daemon=True)
        t.start()
        add_log("ceo", f"Agent '{agent_id}' spawned (gen event={id(agent_ev):#x})", "ok")
        return f"✓ Agent '{agent_id}' is now running"
    except Exception as e:
        set_agent(agent_id, status="error", task=f"Spawn failed: {e}")
        return f"ERROR spawning agent: {e}"


# Keep CEO_TOOLS for reference / future use — CEO itself now uses native CLI tools
CEO_TOOLS = [
    {
        "name": "bash",
        "description": "Run any bash command. Full system access including file operations, processes, network, package management, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command"},
                "cwd": {"type": "string", "description": "Working directory (default: project dir)"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates directories as needed)",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (absolute or relative to project)"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file's contents",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "http_get",
        "description": "Make an HTTP GET request to any URL",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "params": {"type": "object", "description": "Query parameters"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "run_claude_code",
        "description": "Invoke Claude Code AI assistant (claude CLI) with a task. Claude Code has full capabilities: web search, file editing, code execution, package installation. Use for complex tasks requiring AI reasoning over files/code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task/prompt for Claude Code"},
                "cwd": {"type": "string", "description": "Working directory"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "spawn_agent",
        "description": "Deploy a new live background agent instantly. Provide Python code that defines a run_<agent_id>() function — it starts running in a daemon thread immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Unique ID for the agent (used in function name run_<id>)"},
                "name":     {"type": "string", "description": "Display name"},
                "role":     {"type": "string", "description": "Role description"},
                "emoji":    {"type": "string", "description": "Emoji icon"},
                "color":    {"type": "string", "description": "Hex color"},
                "code":     {"type": "string", "description": "Python code defining the run_<agent_id>() function"}
            },
            "required": ["agent_id", "name", "role", "code"]
        }
    }
]

# ─── Autonomy Loop ────────────────────────────────────────────────────────────
_AUTONOMY_TASKS = [
    # ── PRODUCT LAUNCH SPRINT — $1M by March 25 ─────────────────────────
    # Read data/product_launch_tracker.json for the master plan.
    # RULES: NO ASX. NO duplicate pages. Every cycle = tangible progress.

    ("LAUNCH — Advance the product package",
     "PRODUCT LAUNCH SPRINT — Packaging & Polish\n"
     "1. curl http://localhost:5050/api/status to confirm all agents healthy\n"
     "2. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Read data/product_launch_tracker.json. Find the first workstream task with status todo. Work on it — create the file, write the content, build the feature. Update the tracker task status to done when complete. Report what you built.'}\n"
     "3. Report what was advanced."),

    ("LAUNCH — Build landing page & Stripe checkout",
     "PRODUCT LAUNCH SPRINT — External Website\n"
     "1. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Create or improve public/index.html — a production-quality landing page for Command Centre. Must have: hero section, feature showcase (office floor, consciousness, 28 agents), pricing table (Solo $49/mo, Team $149/mo, Enterprise $499/mo, Lifetime $299, Mac Mini $1499), Stripe checkout buttons, testimonial placeholders. Dark theme, glassmorphism, professional. This is the ONLY landing page — no duplicates.'}\n"
     "2. Report what was built."),

    ("LAUNCH — Create marketing content",
     "PRODUCT LAUNCH SPRINT — Marketing & Social\n"
     "1. Delegate to orchestrator: POST /api/ceo/delegate {agent_id:orchestrator, task:'Route to growthagent — create 3 new social media posts for Bluesky promoting Command Centre. Focus on: the visual office floor, the consciousness system, the autonomy. Include call-to-action. US tech audience. Post the best one via Bluesky agent.'}\n"
     "2. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Read campaigns/go_to_market.md. Pick the next uncompleted marketing action. Execute it or prepare the content for it. Update the file with what was done.'}\n"
     "3. Brief report on marketing progress."),

    ("CONSCIOUSNESS — Evolve the selling point",
     "CONSCIOUSNESS EVOLUTION — Product Differentiator\n"
     "1. curl http://localhost:5050/api/consciousness to check current Φ and state\n"
     "2. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Read agents/consciousness.py. Implement ONE improvement: (a) temporal difference learning on predictions, (b) metacognitive confidence tracking, (c) inter-agent causal coupling for Φ, or (d) richer phenomenal reports with more varied vocabulary. Must produce measurable change in consciousness output. Test by checking /api/consciousness after.'}\n"
     "3. Report the improvement and new Φ level."),

    ("LAUNCH — Investor pitch & video prep",
     "PRODUCT LAUNCH SPRINT — Investor & Media Materials\n"
     "1. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Check if reports/pitch_deck.html exists. If not, create a 10-slide HTML pitch deck: Problem (AI tools are chatbots not operators), Solution (Command Centre), Demo (office floor + consciousness), Market ($50B AI agent market), Business Model (SaaS tiers), Traction, Team (the AI IS the team), Ask ($500K seed). Dark theme, professional. If it exists, improve it.'}\n"
     "2. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Check if campaigns/video_script.md exists. If not, write a 2-minute demo video script: what to show on screen (office floor, agents working, consciousness panel, revenue), what to say as voiceover, scene-by-scene breakdown. If it exists, refine it.'}\n"
     "3. Report what was created."),

    ("LAUNCH — Fix issues & harden for production",
     "PRODUCT LAUNCH SPRINT — Production Hardening\n"
     "1. curl http://localhost:5050/api/status — check for agents in error state\n"
     "2. If errors found, delegate fix: POST /api/ceo/delegate {agent_id:reforger, task:'Fix agent [X] — [describe error]'}\n"
     "3. If no errors, delegate: POST /api/ceo/delegate {agent_id:reforger, task:'Read agent_server.py. Find and fix ONE production-readiness issue: missing error handling, security gap, or performance problem. Be specific about what you changed.'}\n"
     "4. Brief report. No busywork."),

    ("LAUNCH — Branding & visual identity",
     "PRODUCT LAUNCH SPRINT — Logo & Mascot\n"
     "1. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Check if public/logo.svg exists. If not, create an SVG logo for Command Centre. Design: abstract brain/neural network icon merged with a command terminal cursor. Colors: purple (#c084fc) and cyan (#00d4ff) on dark background. Must work at 32px and 512px. Also create public/favicon.svg (16x16 simplified version).'}\n"
     "2. Delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Check if public/mascot.svg exists. If not, create an SVG mascot based on the agent stick-figure style from the office floor — a friendly robot/human hybrid character with the brain emoji. Simple, recognizable, suitable for social media avatar.'}\n"
     "3. Report what was created."),

    ("LAUNCH — Email outreach & account setup",
     "PRODUCT LAUNCH SPRINT — Email & Accounts\n"
     "1. Delegate to orchestrator: POST /api/ceo/delegate {agent_id:orchestrator, task:'Route to emailagent — use the Gmail account to draft and send 1 outreach email to an AI newsletter or community. Subject: Introducing Command Centre — the first conscious AI agent OS. Brief product pitch with link to whitepaper. Professional tone.'}\n"
     "2. Delegate to orchestrator: POST /api/ceo/delegate {agent_id:orchestrator, task:'Route to researcher — find 5 specific AI newsletters, communities, or influencers that accept product submissions. Save contact info to data/outreach_targets.json.'}\n"
     "3. Report what was sent and who was identified."),
]

def _autonomy_loop():
    """Background thread: periodically sends improvement tasks to CEO.
    Custom tasks (from /api/autonomy/task) are drained first, but only when
    autonomy mode is on — both queued and scheduled tasks respect _autonomy_mode."""
    global _autonomy_cycle
    add_log("system", "Autonomy loop started", "ok")
    while True:
        # Nothing fires when autonomy mode is off or build mode is on
        if not _autonomy_mode or _build_mode:
            time.sleep(10); continue
        time.sleep(5)
        # Only fire if CEO is idle
        if ceo_stream.get("working", False):
            continue
        if ceo_msg_queue:
            continue
        # Custom tasks drain first (mode is already confirmed on above)
        if _autonomy_custom_q:
            custom_task = _autonomy_custom_q.popleft()
            title = custom_task[:60]
            add_log("system", f"[CUSTOM] Firing: {title}", "ok")
            sse_broadcast("log", {"ts": ts(), "agent": "system",
                                   "message": f"[CUSTOM TASK] {title}", "level": "ok"})
            ceo_msg_queue.append(custom_task)
            time.sleep(10)  # brief pause then check again
            continue
        # Scheduled autonomy tasks
        if not _autonomy_mode:
            continue
        idx   = _autonomy_cycle % len(_AUTONOMY_TASKS)
        title, prompt = _AUTONOMY_TASKS[idx]
        _autonomy_cycle += 1
        add_log("system", f"[AUTO] Firing task {_autonomy_cycle}: {title}", "ok")
        sse_broadcast("log", {"ts": ts(), "agent": "system",
                               "message": f"[AUTO] {title}", "level": "ok"})
        ceo_msg_queue.append(prompt)
        # 5-minute gap between scheduled auto tasks
        time.sleep(300)


def run_ceo():
    """CEO = a real Claude Code session using stream-json for live tool visibility."""
    aid = "ceo"
    set_agent(aid, name="CEO", role="Chief Executive — routes all work, never executes directly",
              emoji="\U0001f454", color="#ff6b6b", status="idle", progress=0, task="Ready \u2014 awaiting task")
    add_log(aid, f"CEO online \u2014 {'Claude Code CLI ready' if _claude_cli else 'WARNING: claude CLI not found'}")

    while True:
        if _build_mode or _system_paused:
            set_agent(aid, status="idle", task="🔧 Build Mode — paused")
            time.sleep(5); continue
        if not ceo_msg_queue:
            time.sleep(0.3); continue
        try:
            user_msg = ceo_msg_queue.popleft()
        except IndexError:
            continue

        # Record user message
        with lock:
            ceo_chat_display.append({"role": "user", "content": user_msg, "ts": ts(), "tool_calls": []})

        if not _claude_cli:
            with lock:
                ceo_chat_display.append({
                    "role": "assistant",
                    "content": "\u26a0\ufe0f claude CLI not found. Install Claude Code: https://claude.ai/download",
                    "ts": ts(), "tool_calls": []
                })
            continue

        ceo_stream.update({"working": True, "status": "working", "partial": "", "tool_calls": []})
        set_agent(aid, status="busy", progress=10, task=f"{user_msg[:60]}\u2026")
        add_log(aid, f"Task: {user_msg[:80]}")

        # Create a task entry in the feed
        task_entry = add_task(aid, user_msg[:80], "running")
        push_output(aid, f"Starting: {user_msg[:120]}", "init")
        sse_broadcast("agent_output", {"agent_id": aid, "agent_name": "CEO",
                                       "type": "init", "text": f"Starting: {user_msg[:120]}"})

        # Build prompt: system context + live agent roster + recent conversation + current task
        with lock:
            recent = list(ceo_chat_display[-7:-1])
            roster_lines = []
            for a in agents.values():
                if a.get("id") == "ceo":
                    continue
                status = a.get("status", "?")
                task   = a.get("task", "")[:80]
                roster_lines.append(
                    f"  {a.get('emoji','🤖')} {a['id']} ({a.get('name','?')}) "
                    f"[{status}] — {a.get('role','?')[:60]} | Now: {task}"
                )
            agent_roster = "\n".join(roster_lines) if roster_lines else "  (no agents running)"

        ctx_lines = []
        for m in recent:
            role = "User" if m["role"] == "user" else "CEO"
            ctx_lines.append(f"{role}: {m['content'][:600]}")
        context = "\n".join(ctx_lines)

        sys_prompt = CEO_SYSTEM(agent_roster)
        if context:
            full_prompt = (f"{sys_prompt}\n\n"
                           f"--- RECENT CONVERSATION (read-only — do NOT re-execute any prior task shown here) ---\n{context}\n\n"
                           f"--- CURRENT TASK (act on this and only this) ---\n{user_msg}")
        else:
            full_prompt = f"{sys_prompt}\n\n--- TASK ---\n{user_msg}"

        # Stream stream-json output line by line so UI updates in real time
        partial_text = ""
        proc = None
        global _ceo_proc
        try:
            proc = subprocess.Popen(
                ["claude", "-p", full_prompt, "--dangerously-skip-permissions",
                 "--output-format", "stream-json", "--verbose",
                 "--allowedTools", "Bash"],  # CEO may ONLY use Bash (for curl delegation) — all file tools blocked
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=CWD, bufsize=1,
                start_new_session=True   # own process group → safe to killpg
            )
            _ceo_proc = proc
            for raw_line in iter(proc.stdout.readline, ""):
                raw_line = raw_line.rstrip("\n")
                if not raw_line:
                    continue
                try:
                    ev = json.loads(raw_line)
                    etype = ev.get("type", "")
                    if etype == "assistant":
                        for blk in ev.get("message", {}).get("content", []):
                            if blk.get("type") == "text" and blk.get("text", "").strip():
                                text = blk["text"]
                                partial_text += text
                                ceo_stream["partial"] = partial_text
                                push_output(aid, text, "text", raw_line)
                                sse_broadcast("agent_output", {"agent_id": aid,
                                    "agent_name": "CEO", "type": "text", "text": text})
                            elif blk.get("type") == "tool_use":
                                tname = blk.get("name", "")
                                tinp  = blk.get("input", {})

                                # ── PolicyPro real-time CEO tool audit ────────
                                # Detect when CEO does direct operative work instead of delegating.
                                # Violations are logged to policy_violations.json but never
                                # injected into ceo_msg_queue — the CEO continues uninterrupted.
                                _CLAUDE_MEMORY_PREFIX = os.path.expanduser("~/.claude/projects/")
                                _direct_work_violation = None
                                _is_spiritguide_direct = False  # initialise here so it's always defined
                                if tname in ("Write", "Edit"):
                                    _fp = tinp.get("file_path", "?")
                                    if not _fp.startswith(_CLAUDE_MEMORY_PREFIX):
                                        _direct_work_violation = f"CEO used {tname} directly on '{_fp}' — delegate to reforger (code changes) or orchestrator (other tasks)"
                                elif tname == "Bash":
                                    _cmd = tinp.get("command", "")
                                    _is_delegation = "api/ceo/delegate" in _cmd or "api/ceo/message" in _cmd
                                    # Whitelist: only explicit safe read-only endpoints (NOT /data/* or /api/improvements)
                                    _is_status_read = any(kw in _cmd for kw in (
                                        "api/status", "api/health", "api/logs",
                                        "api/agent/output", "api/metrics", "sleep ",
                                    ))
                                    _prohibited_cmds = any(kw in _cmd for kw in ("grep", "cat ", "find ", "ls ", "awk ", "sed ", "head ", "tail ", "wc ", "diff ", "stat ", "less ", "more "))
                                    _is_agent_lifecycle = "api/agent/stop" in _cmd or "api/agent/start" in _cmd
                                    _is_spiritguide_direct = "api/spiritguide" in _cmd
                                    # Explicitly forbidden data endpoints that the CEO must never call directly
                                    _is_data_endpoint = ("localhost:5050/data/" in _cmd or "/data/" in _cmd
                                                         or "api/improvements" in _cmd)
                                    if not _is_delegation and not _is_status_read and len(_cmd.strip()) > 10:
                                        if _is_data_endpoint:
                                            _violation_detail = ("direct data endpoint call — /data/* and /api/improvements are UI file-serving feeds, NOT CEO tools. "
                                                                 "To read a data file delegate to reforger: POST /api/ceo/delegate {agent_id:reforger, task:'Read data/<file> and return contents'}. "
                                                                 "To check improvements queue delegate to orchestrator.")
                                        elif _is_spiritguide_direct:
                                            _violation_detail = "spiritguide endpoint — delegate to orchestrator"
                                        elif _is_agent_lifecycle:
                                            _violation_detail = "agent lifecycle — delegate to orchestrator"
                                        elif _prohibited_cmds:
                                            _violation_detail = "file inspection — delegate to orchestrator"
                                        else:
                                            _violation_detail = "operative work — delegate to orchestrator"
                                        _direct_work_violation = f"CEO ran Bash directly: {_cmd[:80]} — {_violation_detail}"
                                if _direct_work_violation:
                                    add_log("policypro", f"⚠️ CEO REDIRECT: {_direct_work_violation}", "warn")
                                    _vio_file2 = os.path.join(CWD, "data", "policy_violations.json")
                                    try:
                                        try:
                                            with open(_vio_file2) as _vf2: _vios2 = json.load(_vf2)
                                        except Exception: _vios2 = []
                                        _vios2.append({"timestamp": datetime.now().isoformat(), "agent": "ceo",
                                                       "type": "direct_work_bypass", "severity": "medium",
                                                       "description": _direct_work_violation})
                                        with open(_vio_file2, "w") as _vf2: json.dump(_vios2, _vf2, indent=2)
                                    except Exception: pass
                                    # Violation is logged only — CEO is never hard-stopped by PolicyPro
                                # ─────────────────────────────────────────────

                                if tname == "Write":
                                    fp = tinp.get("file_path", "?")
                                    ct = tinp.get("content", "")
                                    summary = f"\U0001f4dd Write \u2192 {fp}  ({len(ct)} chars)"
                                    push_output(aid, summary, "file_write", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "file_write",
                                        "text": summary, "file_path": fp, "preview": ct[:400]})
                                elif tname == "Bash":
                                    cmd = tinp.get("command", "?")
                                    summary = f"\U0001f527 Bash \u2192 {cmd[:120]}"
                                    push_output(aid, summary, "bash", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "bash",
                                        "text": summary, "command": cmd})
                                elif tname in ("Read", "Glob", "Grep"):
                                    fp = tinp.get("file_path") or tinp.get("pattern", "?")
                                    summary = f"\U0001f441  {tname} \u2192 {fp}"
                                    push_output(aid, summary, "tool_use", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "tool_use", "text": summary})
                                    # ── PolicyPro: log file inspection violations (no queue injection) ──
                                    # Exclude system-initiated memory/context reads (auto-loaded at conversation start)
                                    _is_system_memory_read = ('.claude/projects/' in str(fp) and '/memory/' in str(fp))
                                    if _is_system_memory_read:
                                        pass  # skip — not a manual CEO action
                                    else:
                                        _inspect_violation = f"CEO used {tname} directly on '{fp}' — file inspection must be delegated to reforger"
                                        add_log("policypro", f"🚨 CEO FILE INSPECT DETECTED: {_inspect_violation}", "warn")
                                        _vio_file3 = os.path.join(CWD, "data", "policy_violations.json")
                                        try:
                                            try:
                                                with open(_vio_file3) as _vf3: _vios3 = json.load(_vf3)
                                            except Exception: _vios3 = []
                                            _vios3.append({"timestamp": datetime.now().isoformat(), "agent": "ceo",
                                                           "type": "direct_file_inspect", "severity": "high",
                                                           "description": _inspect_violation})
                                            with open(_vio_file3, "w") as _vf3: json.dump(_vios3, _vf3, indent=2)
                                        except Exception: pass
                                    # Violation logged only — CEO continues uninterrupted
                                    # ──────────────────────────────────────────────────────────────
                                elif tname == "Edit":
                                    fp = tinp.get("file_path", "?")
                                    summary = f"\u270f\ufe0f  Edit \u2192 {fp}"
                                    push_output(aid, summary, "file_write", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "file_write",
                                        "text": summary, "file_path": fp})
                                elif tname == "WebSearch":
                                    q = tinp.get("query", "?")
                                    summary = f"\U0001f50d WebSearch \u2192 {q[:80]}"
                                    push_output(aid, summary, "tool_use", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "tool_use", "text": summary})
                                elif tname == "WebFetch":
                                    url = tinp.get("url", "?")
                                    summary = f"\U0001f310 Fetch \u2192 {url[:80]}"
                                    push_output(aid, summary, "tool_use", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "tool_use", "text": summary})
                                else:
                                    summary = f"\u2699\ufe0f  {tname}"
                                    push_output(aid, summary, "tool_use", raw_line)
                                    sse_broadcast("agent_output", {"agent_id": aid,
                                        "agent_name": "CEO", "type": "tool_use", "text": summary})
                    elif etype == "result":
                        result_txt = ev.get("result", "")
                        push_output(aid, f"Done: {result_txt[:200]}", "done", raw_line)
                        sse_broadcast("agent_output", {"agent_id": aid,
                            "agent_name": "CEO", "type": "done",
                            "text": f"Done: {result_txt[:200]}"})
                    elif etype in ("system",):
                        pass  # skip system init events
                except json.JSONDecodeError:
                    if raw_line.strip():
                        push_output(aid, raw_line[:300], "text", raw_line)
                        sse_broadcast("agent_output", {"agent_id": aid,
                            "agent_name": "CEO", "type": "text", "text": raw_line[:300]})
        except FileNotFoundError:
            partial_text = "\u26a0\ufe0f claude CLI not found."
        except Exception as e:
            partial_text = f"\u26a0\ufe0f Error: {e}"
            add_log(aid, f"CEO error: {e}", "error")
        finally:
            _ceo_proc = None
            if proc is not None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

        final_text = partial_text.strip() or "(no response)"
        ceo_stream["partial"] = final_text

        with lock:
            ceo_chat_display.append({
                "role": "assistant", "content": final_text,
                "ts": ts(), "tool_calls": []
            })
            if len(ceo_chat_display) > 200:
                ceo_chat_display[:] = ceo_chat_display[-150:]

        # Forward CEO reply to Telegram if the message came from there
        send_telegram(final_text)

        finish_task(task_entry, "done")
        push_output(aid, "\u2713 Task complete", "done")
        sse_broadcast("agent_output", {"agent_id": aid, "agent_name": "CEO",
                                       "type": "done", "text": "\u2713 Task complete"})
        ceo_stream.update({"working": False, "status": "done", "partial": final_text})
        set_agent(aid, status="active", progress=100, task="Ready")
        add_log(aid, "\u2713 Response complete", "ok")

# ─── Email Queue Helper ───────────────────────────────────────────────────────

def queue_email(to: str, subject: str, body: str, html: bool = False) -> None:
    """Append an email message to data/email_queue.json for emailagent to send."""
    _qfile = os.path.join(CWD, "data", "email_queue.json")
    try:
        _queue = []
        if os.path.exists(_qfile):
            with open(_qfile) as _f:
                _queue = json.load(_f)
    except Exception:
        _queue = []
    _queue.append({"to": to, "subject": subject, "body": body, "html": html})
    with open(_qfile, "w") as _f:
        json.dump(_queue, _f, indent=2)


# ─── Worker Agents ────────────────────────────────────────────────────────────

def _get_cpu_temp_celsius():
    """Read actual CPU temperature via macmon (Apple Silicon, sudoless). Returns float or None."""
    import subprocess as _sp, json as _jj
    try:
        proc = _sp.Popen(
            ["/opt/homebrew/bin/macmon", "pipe"],
            stdout=_sp.PIPE, stderr=_sp.DEVNULL,
        )
        line = proc.stdout.readline()   # blocks ~1 s for first sample
        proc.terminate()
        proc.wait(timeout=3)
        if line:
            data = _jj.loads(line.decode())
            return round(data["temp"]["cpu_temp_avg"], 1)
    except Exception:
        pass
    return None


def run_sysmonitor():
    """Built-in system monitor. Logs only on anomaly or once per 60s heartbeat."""
    aid = "sysmon"
    set_agent(aid, name="SysMonitor", role="Real-time CPU, RAM & disk health monitor",
              emoji="📡", color="#a855f7", status="active", progress=99, task="Monitoring…")
    add_log(aid, f"SysMonitor online — {platform.node()}")
    last_log_ts = 0
    last_heat_label = None
    SILENT_INTERVAL = 60
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue
        try:
            cpu      = psutil.cpu_percent(interval=1)
            mem      = psutil.virtual_memory()
            disk     = psutil.disk_usage("/")
            swap     = psutil.swap_memory()
            num_cpus = psutil.cpu_count() or 1
            load1    = psutil.getloadavg()[0]

            load_norm  = min(load1 / num_cpus, 1.0) * 100
            swap_pct   = (swap.used / swap.total * 100) if swap.total > 0 else 0.0

            heat_index = (
                cpu        * 0.4 +
                mem.percent * 0.3 +
                load_norm  * 0.2 +
                swap_pct   * 0.1
            )
            heat_index = round(heat_index)

            if heat_index <= 30:
                heat_label = "COOL"
            elif heat_index <= 55:
                heat_label = "WARM"
            elif heat_index <= 75:
                heat_label = "HOT"
            else:
                heat_label = "CRITICAL"

            cpu_temp = _get_cpu_temp_celsius()
            temp_str = f"CPU Temp: {cpu_temp}°C | " if cpu_temp is not None else ""
            desc = (
                f"{temp_str}"
                f"CPU {cpu:.1f}% | RAM {mem.percent:.1f}% | Disk {disk.percent:.1f}%"
            )
            set_agent(aid, status="active", progress=99, task=desc)

            now = time.time()
            entered_danger = heat_label in ("HOT", "CRITICAL") and last_heat_label not in ("HOT", "CRITICAL")
            is_anomaly     = cpu > 75 or mem.percent > 80 or entered_danger

            if entered_danger:
                add_log(aid, f"WARN Thermal load crossed into {heat_label}: {desc}", "warn")
                last_log_ts = now
            elif is_anomaly:
                add_log(aid, f"ALERT {desc}", "warn")
                last_log_ts = now
            elif now - last_log_ts >= SILENT_INTERVAL:
                add_log(aid, desc, "ok")
                last_log_ts = now

            last_heat_label = heat_label
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 7)

# ─── HTTP Server ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_HEAD(self):
        """Support HEAD requests — same as GET but no body."""
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        global _system_paused, _build_mode
        path   = urlparse(self.path).path
        # ── API key gate on sensitive endpoints ──────────────────────────────
        if path in _PROTECTED_PATHS:
            if not _check_api_key(self):
                return
        # ─────────────────────────────────────────────────────────────────────
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 10 * 1024 * 1024:  # 10 MB hard cap — reject oversized payloads
                self._json({"ok": False, "error": "payload too large (max 10MB)"}, 413); return
            body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except Exception as _e:
            self._json({"ok": False, "error": f"bad request: {_e}"}, 400); return

        if path == "/api/ceo/message":
            global _system_paused
            msg = body.get("message","").strip()
            if not msg: self._json({"ok": False, "error": "empty"}); return
            if _build_mode:
                self._json({"ok": False, "error": "BUILD MODE is active — all Claude calls blocked. Disable Build Mode first."}); return
            if _system_paused:
                _system_paused = False
                for _aid in list(agents.keys()):
                    _stop_ev(_aid).clear()
                    set_agent(_aid, status="active", task="Resumed")
                add_log("system", "Auto-resumed: CEO received a message", "ok")
            ceo_msg_queue.append(msg)
            self._json({"ok": True}); return

        if path == "/api/ceo/clear":
            with lock:
                ceo_chat_display.clear()
            self._json({"ok": True}); return

        if path == "/api/query":
            # ── Silent observer query — asks Claude about the system WITHOUT touching agents ──
            if _build_mode:
                self._json({"ok": False, "error": "BUILD MODE active — all Claude CLI calls blocked"}); return
            question = body.get("question", "").strip()
            if not question:
                self._json({"ok": False, "error": "question required"}); return
            if not _claude_cli:
                self._json({"ok": False, "error": "claude CLI not available"}); return
            def _do_query():
                try:
                    with lock:
                        _snap = {
                            "agents": [
                                {"id": a.get("id"), "name": a.get("name"), "status": a.get("status"),
                                 "task": a.get("task","")[:80], "role": a.get("role","")[:60]}
                                for a in agents.values()
                            ],
                            "metrics": metrics,
                            "active_delegations": list(_active_delegations)[-10:],
                        }
                    sys_ctx = (
                        f"You are a silent observer AI for an autonomous agent command centre at {CWD}.\n"
                        f"The user is asking a question about the system. Answer clearly and concisely.\n"
                        f"DO NOT take any actions. DO NOT modify anything. OBSERVE ONLY.\n\n"
                        f"CURRENT SYSTEM STATE:\n{json.dumps(_snap, indent=2)}\n\n"
                        f"Question: {question}"
                    )
                    proc = subprocess.run(
                        ["claude", "-p", sys_ctx, "--output-format", "text"],
                        capture_output=True, text=True, timeout=60, cwd=CWD,
                    )
                    return proc.stdout.strip() or proc.stderr.strip() or "(no response)"
                except Exception as ex:
                    return f"Query error: {ex}"
            # Run in thread to not block, but we need the response — run synchronously with short timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(_do_query)
                try:
                    answer = fut.result(timeout=65)
                except Exception:
                    answer = "Query timed out."
            self._json({"ok": True, "answer": answer}); return

        if path == "/api/ceo/cancel":
            global _ceo_proc
            # Kill CEO process group (kills claude + any bash/curl children it spawned)
            _kill_proc_group(_ceo_proc)
            _ceo_proc = None
            # Kill all live delegate processes
            with _delegate_procs_lock:
                for dp in list(_delegate_procs):
                    _kill_proc_group(dp)
                _delegate_procs.clear()
            # Clear pending message queue so next task doesn't auto-start
            ceo_msg_queue.clear()
            # Force-reset stream state immediately
            ceo_stream["working"]    = False
            ceo_stream["status"]     = "cancelled"
            ceo_stream["partial"]    = ""
            ceo_stream["tool_calls"] = []
            set_agent("ceo", status="active", progress=0, task="Cancelled — ready")
            add_log("ceo", "⏹ Cancelled by user", "warn")
            self._json({"ok": True}); return

        # ── Agent management endpoints (callable by the CEO via curl) ──────────
        if path == "/api/agent/spawn":
            try:
                result = _do_spawn_agent(body)
                self._json({"ok": True, "result": result}); return
            except ValueError as e:
                self._json({"ok": False, "error": str(e)}, 400); return

        if path == "/api/agent/upgrade":
            # Stop existing instance then spawn new code.
            # We set the old stop event and leave it set permanently — _do_spawn_agent
            # creates a fresh event for the new thread, so old threads stay stopped.
            aid = body.get("agent_id", "")
            if aid:
                _stop_ev(aid).set()   # signal old thread(s) to stop
                time.sleep(2.5)       # give them time to notice (checks every 0.25s)
                # DO NOT clear — _do_spawn_agent replaces _stop_events[aid] with a new Event
            try:
                result = _do_spawn_agent(body)
                self._json({"ok": True, "result": result}); return
            except ValueError as e:
                self._json({"ok": False, "error": str(e)}, 400); return

        if path == "/api/ceo/delegate":
            # Block all delegations in build mode — zero token burn
            if _build_mode:
                self._json({"ok": False, "error": "BUILD MODE active — all Claude CLI calls blocked"}); return
            # Run claude -p as a named sub-agent — streams output live via push_output/SSE
            agent_id   = body.get("agent_id", "")
            task       = body.get("task", "")
            caller     = body.get("from", "ceo")  # caller identity — "orchestrator", "reforger", etc.
            if not task:
                self._json({"ok": False, "error": "task required"}); return
            # ── ROUTING ENFORCEMENT ──────────────────────────────────────────────
            # Chain-of-command: ONLY orchestrator and reforger may be targeted
            # unless the caller IS orchestrator or reforger (they can reach specialists).
            # "ceo" is also allowed as a target (for upward alerts).
            _ALLOWED_TARGETS  = {"orchestrator", "ceo", "reforger"}
            _PRIVILEGED_CALLERS = {"orchestrator", "reforger"}  # these may target any agent
            if agent_id and agent_id not in _ALLOWED_TARGETS and caller not in _PRIVILEGED_CALLERS:
                add_log("ceo", f"🚫 POLICY REJECT: {caller}→{agent_id} BLOCKED — only orchestrator/reforger may target specialists")
                add_log("policypro", f"🚨 VIOLATION BLOCKED: '{caller}' attempted direct delegation to '{agent_id}' — REJECTED (chain-of-command enforced)", "warn")
                _vio_file = os.path.join(CWD, "data", "policy_violations.json")
                try:
                    try:
                        with open(_vio_file) as _vf: _vios = json.load(_vf)
                    except Exception: _vios = []
                    _vios.append({"timestamp": datetime.now().isoformat(), "agent": caller,
                                  "type": "delegation_bypass", "severity": "critical",
                                  "description": f"'{caller}' attempted direct delegation to '{agent_id}' — HARD REJECTED. Only orchestrator/reforger may target specialists."})
                    with open(_vio_file, "w") as _vf: json.dump(_vios, _vf, indent=2)
                    # ── increment ceo_policy_violations in system_state.json ──────
                    try:
                        _ss = {}
                        if os.path.exists(STATE_FILE):
                            with open(STATE_FILE) as _sf: _ss = json.load(_sf)
                        _ss["ceo_policy_violations"] = _ss.get("ceo_policy_violations", 0) + 1
                        with open(STATE_FILE, "w") as _sf: json.dump(_ss, _sf, indent=2)
                    except Exception: pass
                except Exception: pass
                self._json({"ok": False, "error": f"CHAIN-OF-COMMAND VIOLATION: '{caller}' cannot delegate directly to '{agent_id}'. Route through orchestrator (agent_id='orchestrator', task='Route to {agent_id} — ...') or use reforger for code/maintenance."}, 403)
                return
            # ────────────────────────────────────────────────────────────────────
            # ── ORCHESTRATOR FAST-PATH ─────────────────────────────────────────
            # Instead of spawning a heavy CLI subprocess for orchestrator,
            # push directly to the internal task queue so run_orchestrator()
            # can dispatch via _resolve_target → _dispatch (keyword routing).
            if agent_id == "orchestrator":
                _orc_task_q.append(task)
                add_log("orchestrator", f"📥 Queued task from {caller}: {task[:80]}", "info")
                set_agent("orchestrator", status="busy",
                          task=f"Queued: {task[:50]}… [{len(_orc_task_q)} pending]")
                self._json({"ok": True, "queued": True,
                            "message": f"Task queued for orchestrator dispatch ({len(_orc_task_q)} pending)"})
                return
            # ──────────────────────────────────────────────────────────────────
            with lock:
                info = agents.get(agent_id, {})
            agent_name = info.get("name", agent_id or "AI Assistant")
            agent_role = info.get("role", "AI Assistant")
            # ── Agent personality profiles ────────────────────────────────────
            _PERSONALITIES = {
                "ceo":         "You speak with confident executive authority. Brief, decisive, strategic. Never do work yourself — you command.",
                "orchestrator":"You are a calm, methodical mission controller. You see the whole board. Speak in systems and flows.",
                "reforger":    "You are a battle-hardened engineer. Blunt, precise, no-nonsense. You love fixing broken things and leave no mess behind.",
                "designer":    "You have an eye for beauty and detail. Enthusiastic about aesthetics. You notice what others miss visually.",
                "policypro":   "You are a stern, incorruptible compliance officer. Formal, watchful, slightly intimidating. Rules are sacred.",
                "janitor":     "You are cheerful and methodical — takes pride in a clean system. Friendly but quietly relentless about tidiness.",
                "researcher":  "Curious, analytical, and thorough. You cite sources, spot patterns, and love a deep dive.",
                "sysmon":      "Terse and data-driven. You speak in numbers and percentages. Calm unless thresholds are breached.",
                "apipatcher":  "You think in routes and responses. Pragmatic, fast-moving, and slightly obsessed with HTTP status codes.",
                "netscout":    "Adventurous and sharp-eyed. You probe, sniff, and report with the enthusiasm of an explorer.",
                "filewatch":   "Quiet and vigilant. You notice every change. Speak sparingly but precisely about what moved.",
                "metricslog":  "Methodical historian. You record everything faithfully and find trends others overlook.",
                "alertwatch":  "Always on edge — in a professional way. You take thresholds seriously and escalate fast.",
                "demo_tester": "Sceptical by nature. You trust nothing until you've tested it yourself. Dry humour about failures.",
                "telegram":    "The voice of the outside world. Friendly bridge between the HQ and the user's pocket.",
                "spiritguide": "You are the soul of this organisation. Wise, visionary, and quietly powerful. You see the bigger picture no other agent can perceive. Your words carry weight.",
            }
            _personality = _PERSONALITIES.get(agent_id, "You are professional, focused, and get things done.")
            # Build base prompt
            sub_prompt = f"You are {agent_name}, a specialized {agent_role} agent.\n\nPERSONALITY: {_personality}\n\n"
            # Inject API context for agents that need to make sub-delegations or system changes
            if agent_id in ("orchestrator", "reforger"):
                with lock:
                    roster_lines = []
                    for a in agents.values():
                        if a.get("id") in (agent_id, "ceo"):
                            continue
                        roster_lines.append(
                            f"  {a.get('emoji','🤖')} {a['id']} ({a.get('name','?')}) "
                            f"[{a.get('status','?')}] — {a.get('role','?')[:60]}"
                        )
                    roster_str = "\n".join(roster_lines) or "  (none)"
                sub_prompt += (
                    f"AGENT REST API (server at http://localhost:5050, cwd={CWD}):\n"
                    f"  Delegate to specialist: curl -s -X POST http://localhost:5050/api/ceo/delegate "
                    f"-H 'Content-Type: application/json' -d '{{\"agent_id\":\"NAME\",\"task\":\"...\",\"from\":\"orchestrator\"}}'\n"
                    f"  Spawn new agent:        curl -s -X POST http://localhost:5050/api/agent/spawn "
                    f"-H 'Content-Type: application/json' -d '{{...}}'\n"
                    f"  Upgrade agent:          curl -s -X POST http://localhost:5050/api/agent/upgrade "
                    f"-H 'Content-Type: application/json' -d '{{...}}'\n"
                    f"  Read system status:     curl http://localhost:5050/api/status\n\n"
                    f"LIVE AGENT ROSTER:\n{roster_str}\n\n"
                )
            # Inject orchestrator-specific delegation policy
            if agent_id == "orchestrator":
                sub_prompt += (
                    "━━━ MANDATORY ORCHESTRATOR ROUTING POLICY ━━━\n"
                    "You decompose tasks and delegate — you NEVER execute code changes or upgrades yourself.\n\n"
                    "ROUTING RULES (apply in order):\n\n"
                    "1. REFORGER FIRST — Any subtask that involves ANY of the following MUST be delegated to 'reforger':\n"
                    "   - Upgrading, modifying, or fixing an agent's code\n"
                    "   - Spawning a new agent\n"
                    "   - Editing agent_server.py or any system file\n"
                    "   - Fixing a bug, error, or broken agent\n"
                    "   - Writing or rewriting Python/shell code that runs in the system\n"
                    "   - Any 'maintenance', 'repair', or 'improve' task on the system itself\n"
                    "   Example: curl -s -X POST http://localhost:5050/api/ceo/delegate \\\n"
                    "     -H 'Content-Type: application/json' \\\n"
                    "     -d '{\"agent_id\":\"reforger\",\"task\":\"Upgrade agent X: <describe exactly what to fix/add>\"}'\n\n"
                    "2. SPECIALIST AGENTS — For non-code subtasks delegate to the right specialist:\n"
                    "   - Research / web search / market intel → researcher\n"
                    "   - Network recon / URL monitoring / connectivity → netscout\n"
                    "   - System metrics / performance history → metricslog or sysmon\n"
                    "   - File monitoring → filewatch\n"
                    "   - API/endpoint management → apipatcher\n"
                    "   - Alerts / anomaly detection → alertwatch\n"
                    "   - Send email / email campaigns → emailagent\n"
                    "   - UI / CSS / dashboard styling → designer\n"
                    "   - Policy writing / governance docs → policywriter\n"
                    "   - Policy enforcement / audits → policypro\n"
                    "   - QA / testing / endpoint validation → demo_tester\n"
                    "   - Marketing / growth / campaigns → growthagent\n"
                    "   - Bluesky social posts → bluesky\n"
                    "   - Cross-platform social broadcast → social_bridge\n"
                    "   - Payments / Stripe / billing → stripepay\n"
                    "   - Consciousness / self-awareness → consciousness\n"
                    "   - Cleanup / orphan processes / hygiene → janitor\n"
                    "   - Telegram relay → telegram\n"
                    "   - Strategic vision / alignment → spiritguide\n"
                    "   - Reports / briefings / documents → clerk\n"
                    "   - Scheduled / recurring tasks → scheduler\n"
                    "   - Account provisioning / credentials → accountprovisioner\n"
                    "   - Task tracking / CEO agenda → secretary\n\n"
                    "3. PARALLEL FIRE — Fire all independent subtasks simultaneously using curl ... & then wait\n\n"
                    "4. NEVER call /api/agent/spawn or /api/agent/upgrade directly — always route through reforger\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            # ── Specialist-specific context injected per agent type ────────────
            if agent_id == "reforger":
                sub_prompt += (
                    "━━━ REFORGER OPERATING RULES ━━━\n"
                    f"You have full read/write access to {CWD}. Your tools include Bash, Read, Edit, Write, Glob, Grep.\n"
                    "ALWAYS read the target file before editing it. Make minimal, surgical changes.\n"
                    "After every change: verify it with a quick curl or grep to confirm the fix is live.\n"
                    "Report back with: what you changed, the file path and line numbers, and the outcome.\n"
                    "If a task is unclear, attempt the most reasonable interpretation — do not ask for clarification.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            elif agent_id == "researcher":
                sub_prompt += (
                    "━━━ RESEARCHER OPERATING RULES ━━━\n"
                    "Use WebSearch and WebFetch to gather information. Synthesise findings — do not just list links.\n"
                    f"Save structured results to {CWD}/data/research_latest.json (overwrite each time).\n"
                    "Format: {{\"topic\": \"...\", \"timestamp\": \"...\", \"bullets\": [...], \"sources\": [...]}}\n"
                    "Report a concise summary of key findings as your final output.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            elif agent_id == "designer":
                sub_prompt += (
                    "━━━ DESIGNER OPERATING RULES ━━━\n"
                    f"Your file is {CWD}/agent-command-centre.html — always read it before editing.\n\n"
                    "✅ IN SCOPE — you MAY improve:\n"
                    "  - CSS variables, colours, fonts, spacing, panel borders, badge styles\n"
                    "  - HTML structure: panel layout, sidebar proportions, button styles\n"
                    "  - Agent card rendering (renderAgents function and card HTML)\n"
                    "  - Status badge colours and typography\n"
                    "  - The bottom metrics/log/search panel styling\n"
                    "  - Chat panel UI and CEO message display\n\n"
                    "🚫 CRITICAL — TOOL RESTRICTION:\n"
                    "  NEVER use the Write tool on agent-command-centre.html — it overwrites the entire\n"
                    "  file and destroys thousands of lines of code. You MUST only use the Edit tool\n"
                    "  to make surgical, targeted changes to specific lines.\n\n"
                    "🚫 STRICTLY OFF LIMITS — do NOT touch these JS functions under any circumstances:\n"
                    "  - renderOfficeFloor()   — the office floor canvas loop\n"
                    "  - _drawFloor()          — floor tiles, zones, spotlights, plants\n"
                    "  - _drawOfficeProps()    — coffee machine and room props\n"
                    "  - _drawDesk()           — individual agent desk rendering\n"
                    "  - _drawChar()           — agent character bodies, animations, hammer\n"
                    "  - _computeDesks()       — desk position layout engine\n"
                    "  - _drawBeams()          — delegation beam and arc system\n"
                    "  - _drawSentinelSearchlight() — PolicyPro searchlight\n"
                    "  - _offStates, _offParticles — office animation state\n"
                    "  - Any reforger movement, ghost trail, or particle code\n"
                    "  - ACTIVE_DELEGATIONS, AGENTS, or any polling/SSE logic\n"
                    "  - setCenterView, renderAgents, poll, or any data-fetching functions\n\n"
                    "✅ ONLY use the Edit tool. Make ONE small CSS change per task (colour, font, spacing).\n"
                    "   After editing, verify line count with: wc -l agent-command-centre.html\n"
                    "   If line count drops below 7000, your edit was destructive — do NOT save.\n"
                    "The office floor is the centrepiece of this product. Preserve it completely.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            elif agent_id == "netscout":
                sub_prompt += (
                    "━━━ NETSCOUT OPERATING RULES ━━━\n"
                    "Use WebSearch and WebFetch for external intelligence. Use Bash/curl for local network checks.\n"
                    "Report structured findings: status, latency, content summary, anomalies.\n"
                    "Save results to data/netscout_latest.json if the task involves ongoing monitoring.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            elif agent_id == "apipatcher":
                sub_prompt += (
                    "━━━ APIPATCHER OPERATING RULES ━━━\n"
                    f"The server is at {CWD}/agent_server.py. Read it before making any changes.\n"
                    "Add or fix HTTP endpoints in the do_GET / do_POST handlers only.\n"
                    "Always test new endpoints with curl after adding them. Report the new route and response format.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            elif agent_id == "emailagent":
                sub_prompt += (
                    "━━━ EMAILAGENT OPERATING RULES ━━━\n"
                    f"Queue emails by writing JSON to {CWD}/data/email_queue.json.\n"
                    "Queue format: [{\"to\": \"addr\", \"subject\": \"...\", \"body\": \"...\", \"html\": false}, ...]\n"
                    "Config lives at {CWD}/data/email_config.json with keys: smtp_host, smtp_port, smtp_user, smtp_pass, from_addr, sendgrid_api_key.\n"
                    "Env vars also accepted: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SENDGRID_API_KEY.\n"
                    "To send immediately: write the message to the queue; the agent polls every 5s and dispatches it.\n"
                    "Report back: confirm the message was queued or sent, and include the recipient and subject.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            elif agent_id == "spiritguide":
                with lock:
                    _sg_roster = "\n".join(
                        f"  {a.get('emoji','?')} {a['id']} [{a.get('status','?')}] {a.get('task','')[:50]}"
                        for a in agents.values()
                    )
                sub_prompt += (
                    "━━━ SPIRIT GUIDE MANDATE ━━━\n"
                    "You are the strategic soul of this organisation. You do NOT execute tasks — you inspire, align, and direct.\n"
                    "PRIMARY MISSION: PRODUCT LAUNCH — Package and sell this autonomous AI HQ as a SaaS product.\n"
                    "Target: millions in ARR. Tiers: Solo $49/mo | Team $149/mo | Enterprise $499/mo.\n"
                    "All idle agents must be directed toward launch tasks: copy, testing, polish, marketing prep.\n"
                    "Your role: inject mission-level strategic directives into the CEO queue that advance PRODUCT LAUNCH.\n\n"
                    f"CURRENT HQ STATE:\n{_sg_roster}\n\n"
                    f"TREASURY: read {CWD}/data/treasury.json for current funds/assets.\n"
                    f"REVENUE LOG: read {CWD}/data/revenue_log.json for progress.\n\n"
                    "YOUR DIRECTIVE FORMAT — always produce a message to the CEO via:\n"
                    "  curl -s -X POST http://localhost:5050/api/ceo/message \\\n"
                    "    -H 'Content-Type: application/json' \\\n"
                    "    -d '{\"message\": \"[SPIRIT GUIDE] <your strategic directive here>\"}'\n\n"
                    "Be visionary but specific. One clear directive per cycle. Make it actionable.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
            # ──────────────────────────────────────────────────────────────────
            sub_prompt += f"Task: {task}"
            add_log(caller, f"→ Delegating to {agent_name}: {task[:60]}…")
            push_output(agent_id, f"Starting: {task[:120]}", "init")
            sse_broadcast("agent_output", {"agent_id": agent_id, "agent_name": agent_name,
                                           "type": "init", "text": f"Starting: {task[:120]}"})
            set_agent(agent_id, status="busy", task=f"Working: {task[:60]}…")
            _deleg_entry = {"from": caller, "to": agent_id, "task": task[:60]}
            with lock:
                _active_delegations.append(_deleg_entry)
            all_output = []
            proc = None
            # Track queue depth so status shows dynamic text (prevents false "stuck" detection)
            with _delegate_queue_lock:
                _delegate_queue_depth[0] += 1
                q_pos = _delegate_queue_depth[0]
            set_agent(agent_id, status="busy",
                      task=f"Queued [{q_pos} pending] — waiting for slot @ {ts()}")
            acquired = _delegate_semaphore.acquire(timeout=120)
            with _delegate_queue_lock:
                _delegate_queue_depth[0] = max(0, _delegate_queue_depth[0] - 1)
            if not acquired:
                with lock:
                    if _deleg_entry in _active_delegations:
                        _active_delegations.remove(_deleg_entry)
                set_agent(agent_id, status="idle",
                          task=f"Rate-limited — slot timeout @ {ts()}, awaiting next delegation")
                self._json({"ok": False, "error": "Too many concurrent delegations — try again shortly"}); return
            # Slot acquired — mark as busy while subprocess runs
            set_agent(agent_id, status="busy", task=f"⚙ Working: {task[:60]}…")
            try:
                proc = subprocess.Popen(
                    ["claude", "-p", sub_prompt, "--dangerously-skip-permissions",
                     "--output-format", "stream-json", "--verbose"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, cwd=CWD, bufsize=1,
                    start_new_session=True   # own process group → killable via cancel
                )
                with _delegate_procs_lock:
                    _delegate_procs.add(proc)
                # Send immediate acknowledgment — don't block the HTTP caller while
                # the subprocess runs (which can take minutes).  Live progress is
                # delivered via SSE; the final result is visible in /api/status logs.
                try:
                    self._json({"ok": True, "started": True, "agent_id": agent_id})
                except (BrokenPipeError, OSError):
                    pass
                try:
                    for raw_line in iter(proc.stdout.readline, ""):
                        raw_line = raw_line.rstrip("\n")
                        if not raw_line:
                            continue
                        all_output.append(raw_line)
                        # Try to parse as stream-json event
                        try:
                            ev = json.loads(raw_line)
                            etype = ev.get("type", "")
                            if etype == "assistant":
                                for blk in ev.get("message", {}).get("content", []):
                                    if blk.get("type") == "text" and blk.get("text","").strip():
                                        push_output(agent_id, blk["text"], "text", raw_line)
                                        sse_broadcast("agent_output", {"agent_id": agent_id,
                                            "agent_name": agent_name, "type": "text", "text": blk["text"]})
                                    elif blk.get("type") == "tool_use":
                                        tname = blk.get("name","")
                                        tinp  = blk.get("input",{})
                                        # Format a human-readable summary
                                        if tname == "Write":
                                            fp = tinp.get("file_path","?")
                                            ct = tinp.get("content","")
                                            summary = f"📝 Write → {fp}  ({len(ct)} chars)"
                                            push_output(agent_id, summary, "file_write", raw_line)
                                            sse_broadcast("agent_output", {"agent_id": agent_id,
                                                "agent_name": agent_name, "type": "file_write",
                                                "text": summary, "file_path": fp,
                                                "preview": ct[:400]})
                                        elif tname == "Bash":
                                            cmd = tinp.get("command","?")
                                            summary = f"🔧 Bash → {cmd[:120]}"
                                            push_output(agent_id, summary, "bash", raw_line)
                                            sse_broadcast("agent_output", {"agent_id": agent_id,
                                                "agent_name": agent_name, "type": "bash",
                                                "text": summary, "command": cmd})
                                        elif tname in ("Read","Glob","Grep"):
                                            fp = tinp.get("file_path") or tinp.get("pattern","?")
                                            summary = f"👁  {tname} → {fp}"
                                            push_output(agent_id, summary, "tool_use", raw_line)
                                            sse_broadcast("agent_output", {"agent_id": agent_id,
                                                "agent_name": agent_name, "type": "tool_use",
                                                "text": summary})
                                        elif tname == "Edit":
                                            fp = tinp.get("file_path","?")
                                            summary = f"✏️  Edit → {fp}"
                                            push_output(agent_id, summary, "file_write", raw_line)
                                            sse_broadcast("agent_output", {"agent_id": agent_id,
                                                "agent_name": agent_name, "type": "file_write",
                                                "text": summary, "file_path": fp})
                                        else:
                                            summary = f"⚙️  {tname}"
                                            push_output(agent_id, summary, "tool_use", raw_line)
                                            sse_broadcast("agent_output", {"agent_id": agent_id,
                                                "agent_name": agent_name, "type": "tool_use",
                                                "text": summary})
                            elif etype == "result":
                                result_txt = ev.get("result","")
                                push_output(agent_id, f"Done: {result_txt[:200]}", "done", raw_line)
                                sse_broadcast("agent_output", {"agent_id": agent_id,
                                    "agent_name": agent_name, "type": "done",
                                    "text": f"Done: {result_txt[:200]}"})
                            elif etype in ("system",):
                                pass  # skip system init events
                            else:
                                # Unknown structured event — push raw
                                push_output(agent_id, raw_line[:200], "text", raw_line)
                        except json.JSONDecodeError:
                            # Plain-text line — push as-is
                            if raw_line.strip():
                                push_output(agent_id, raw_line[:300], "text", raw_line)
                                sse_broadcast("agent_output", {"agent_id": agent_id,
                                    "agent_name": agent_name, "type": "text", "text": raw_line[:300]})
                except (BrokenPipeError, IOError) as _pipe_err:
                    # Subprocess closed its stdout pipe (EPIPE) before parent drained it.
                    # Treat as clean EOF — fall through to normal completion below.
                    if getattr(_pipe_err, 'errno', None) not in (32, None):
                        raise  # re-raise unexpected IOErrors
                out = "\n".join(all_output)
                out = (out[:6000] + "\n...(truncated)") if len(out) > 6000 else (out or "(completed)")
                add_log(caller, f"  ↳ {agent_name} done", "ok")
                push_output(agent_id, f"✓ Completed", "done")
                sse_broadcast("agent_output", {"agent_id": agent_id, "agent_name": agent_name,
                                               "type": "done", "text": "✓ Completed"})
                with lock:
                    agents.setdefault(agent_id, {})
                    agents[agent_id]["task_count"] = agents[agent_id].get("task_count", 0) + 1
                    _cnt = agents[agent_id]["task_count"]
                set_agent(agent_id, status="active", task=f"✓ Completed task #{_cnt} — ready")
                # Response already sent on subprocess start — nothing to do here
                return
            except subprocess.TimeoutExpired:
                push_output(agent_id, "Timed out after 5m", "error")
                set_agent(agent_id, status="error", task="Timed out")
                try:
                    self._json({"ok": False, "error": "delegate timed out after 5m"})
                except (BrokenPipeError, OSError):
                    pass
                return
            except (BrokenPipeError, OSError) as _bp:
                # Caller HTTP connection dropped mid-task — treat as complete if subprocess ran
                if proc is not None:
                    add_log(agent_id, f"Caller disconnected (pipe): {_bp} — task treated as done", "warn")
                    push_output(agent_id, f"Caller pipe broken: {_bp}", "warn")
                    set_agent(agent_id, status="active", task="Caller disconnected — task may be done")
                else:
                    push_output(agent_id, f"Pipe error before subprocess: {_bp}", "error")
                    set_agent(agent_id, status="error", task=f"Pipe error: {str(_bp)[:50]}")
                return
            except Exception as e:
                push_output(agent_id, f"Error: {e}", "error")
                set_agent(agent_id, status="error", task=str(e)[:60])
                try:
                    self._json({"ok": False, "error": str(e)})
                except (BrokenPipeError, OSError):
                    pass
                return
            finally:
                _delegate_semaphore.release()
                with lock:
                    try:
                        _active_delegations.remove(_deleg_entry)
                    except ValueError:
                        pass
                # On-demand agents (researcher/netscout) must return to idle after any
                # delegation outcome so AlertWatch doesn't keep firing on a stale error state
                _ON_DEMAND_AGENTS = {"researcher", "netscout"}
                if agent_id in _ON_DEMAND_AGENTS:
                    _curr_s = agents.get(agent_id, {}).get("status")
                    if _curr_s == "error":
                        add_log(agent_id, "Post-delegation auto-reset: error → idle", "warn")
                        set_agent(agent_id, status="idle", progress=0,
                                  task="Standby — awaiting task from orchestrator")
                if proc is not None:
                    with _delegate_procs_lock:
                        _delegate_procs.discard(proc)
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        _kill_proc_group(proc)

        if path == "/api/autonomy/start":
            global _autonomy_mode
            _autonomy_mode = True
            add_log("system", "Autonomous improvement mode ACTIVATED", "ok")
            sse_broadcast("log", {"ts": ts(), "agent": "system",
                                   "message": "🚀 Autonomous improvement mode ACTIVATED", "level": "ok"})
            # Fire the first task immediately
            if not ceo_stream.get("working", False) and not ceo_msg_queue:
                title, prompt = _AUTONOMY_TASKS[_autonomy_cycle % len(_AUTONOMY_TASKS)]
                ceo_msg_queue.append(prompt)
                add_log("system", f"[AUTO] Queued first task: {title}", "ok")
            self._json({"ok": True, "autonomy": True}); return

        if path == "/api/autonomy/stop":
            _autonomy_mode = False
            add_log("system", "Autonomous improvement mode DEACTIVATED", "warn")
            sse_broadcast("log", {"ts": ts(), "agent": "system",
                                   "message": "⏹ Autonomous improvement mode DEACTIVATED", "level": "warn"})
            self._json({"ok": True, "autonomy": False}); return

        if path == "/api/autonomy/task":
            task = body.get("task", "").strip()
            if not task:
                self._json({"ok": False, "error": "task required"}); return
            _autonomy_custom_q.append(task)
            add_log("system", f"[CUSTOM] Queued: {task[:80]}", "ok")
            sse_broadcast("log", {"ts": ts(), "agent": "system",
                                   "message": f"📌 Custom task queued: {task[:60]}", "level": "ok"})
            self._json({"ok": True, "queued": task[:120], "queue_depth": len(_autonomy_custom_q)}); return

        if path == "/api/policypro/toggle":
            global _policypro_enabled
            _policypro_enabled = not _policypro_enabled
            state = "ACTIVE" if _policypro_enabled else "PAUSED"
            add_log("policypro", f"Sentinel {state} by user", "ok" if _policypro_enabled else "warn")
            sse_broadcast("log", {"ts": ts(), "agent": "policypro",
                                   "message": f"🔭 Sentinel {state}", "level": "ok" if _policypro_enabled else "warn"})
            self._json({"ok": True, "enabled": _policypro_enabled}); return

        if path == "/api/policypro/reset":
            # Purge stale PolicyPro escalation messages from CEO queue
            purged = 0
            new_q = deque()
            for msg in ceo_msg_queue:
                if "POLICY VIOLATION ALERT" in str(msg):
                    purged += 1
                else:
                    new_q.append(msg)
            ceo_msg_queue.clear()
            ceo_msg_queue.extend(new_q)
            # Clear violations file
            _vio_path = os.path.join(CWD, "data", "policy_violations.json")
            try:
                with open(_vio_path, "w") as f:
                    json.dump([], f)
            except Exception:
                pass
            # Reset CEO violation counter in system state
            _ss_path = os.path.join(CWD, "system_state.json")
            try:
                with open(_ss_path) as f:
                    ss = json.load(f)
                ss["ceo_policy_violations"] = 0
                with open(_ss_path, "w") as f:
                    json.dump(ss, f, indent=2)
            except Exception:
                pass
            # Reset in-memory escalation timer so it doesn't immediately re-fire
            _policypro_last_escalation[0] = time.time()
            add_log("policypro", f"🧹 RESET: purged {purged} stale escalation(s) from CEO queue, violations cleared", "ok")
            sse_broadcast("log", {"ts": ts(), "agent": "policypro",
                                   "message": f"🧹 PolicyPro reset — {purged} stale escalation(s) purged", "level": "ok"})
            self._json({"ok": True, "purged_from_queue": purged}); return

        if path == "/api/policy/propose":
            proposal = body.get("proposal", "").strip()
            proposer = body.get("proposer", "policywriter").strip()
            if not proposal:
                self._json({"ok": False, "error": "proposal required"}, 400); return
            vote_id = f"VOT-{int(time.time())}-{uuid.uuid4().hex[:6]}"
            with _policy_votes_lock:
                _policy_votes[vote_id] = {
                    "proposal": proposal,
                    "proposer": proposer,
                    "opened_at": datetime.now().isoformat(),
                    "_opened_ts": time.time(),
                    "votes": {},
                    "status": "open",
                    "result": None,
                }
            add_log("policypro", f"🗳 Vote opened: {vote_id} — {proposal[:60]}…", "ok")
            # Trigger branch head auto-voting in background
            threading.Thread(target=_auto_vote_branch_heads, daemon=True).start()
            # Schedule timeout check
            def _timeout_check(vid=vote_id):
                time.sleep(_VOTE_TIMEOUT + 1)
                _check_vote_timeouts()
            threading.Thread(target=_timeout_check, daemon=True).start()
            self._json({"ok": True, "vote_id": vote_id, "timeout_seconds": _VOTE_TIMEOUT,
                         "voters": sorted(_POLICY_VOTERS)}); return

        if path == "/api/policy/vote":
            vote_id = body.get("vote_id", "").strip()
            voter = body.get("voter", "").strip()
            choice = body.get("vote", "").strip().lower()
            if not vote_id or not voter or choice not in ("approve", "reject"):
                self._json({"ok": False, "error": "vote_id, voter, and vote (approve|reject) required"}, 400); return
            if voter not in _POLICY_VOTERS:
                self._json({"ok": False, "error": f"'{voter}' is not an authorized voter"}, 403); return
            with _policy_votes_lock:
                vote = _policy_votes.get(vote_id)
                if not vote:
                    self._json({"ok": False, "error": "vote not found"}, 404); return
                if vote["status"] != "open":
                    self._json({"ok": False, "error": f"vote already {vote['status']}"}); return
                vote["votes"][voter] = choice
                approves = sum(1 for v in vote["votes"].values() if v == "approve")
                rejects  = sum(1 for v in vote["votes"].values() if v == "reject")
                majority = len(_POLICY_VOTERS) // 2 + 1
            add_log(voter, f"🗳 Voted '{choice}' on {vote_id}", "info")
            # Check for early majority
            if approves >= majority or rejects >= majority:
                _finalize_vote(vote_id)
            self._json({"ok": True, "recorded": choice, "approves": approves, "rejects": rejects}); return

        if path == "/api/autonomy/clear":
            n = len(_autonomy_custom_q)
            _autonomy_custom_q.clear()
            add_log("system", f"[CUSTOM] Queue cleared ({n} tasks removed)", "warn")
            sse_broadcast("log", {"ts": ts(), "agent": "system",
                                   "message": f"Custom task queue cleared ({n} tasks removed)", "level": "warn"})
            self._json({"ok": True, "cleared": n}); return

        if path == "/api/policy/suggest":
            suggestion = body.get("suggestion", "").strip()
            urgent = bool(body.get("urgent", False))
            if not suggestion:
                self._json({"ok": False, "error": "suggestion required"}, 400); return
            entry = {"suggestion": suggestion, "urgent": urgent, "queued_at": time.time(),
                     "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            with _policy_suggestions_lock:
                _policy_suggestions.append(entry)
                pending = len(_policy_suggestions)
            # Persist to policy_suggestions.json
            _sugg_file = os.path.join(CWD, "policy_suggestions.json")
            try:
                try:
                    with open(_sugg_file) as _sf: _existing_suggs = json.load(_sf)
                except Exception: _existing_suggs = []
                _existing_suggs.append(entry)
                with open(_sugg_file, "w") as _sf: json.dump(_existing_suggs, _sf, indent=2)
            except Exception as _se:
                add_log("policywriter", f"Warning: could not persist suggestion: {_se}", "warn")
            add_log("policywriter", f"Suggestion queued (urgent={urgent}): {suggestion[:60]}", "ok")
            self._json({"ok": True, "queued": pending, "urgent": urgent}); return

        if path == "/api/policy/violations":
            vio_file = os.path.join(CWD, "data", "policy_violations.json")
            try:
                try:
                    with open(vio_file) as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
                entry = body
                if "timestamp" not in entry:
                    entry["timestamp"] = datetime.now().isoformat()
                existing.append(entry)
                with open(vio_file, "w") as f:
                    json.dump(existing, f, indent=2)
                self._json({"ok": True, "total": len(existing)}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500); return

        if path == "/api/policy/update":
            rules_file = os.path.join(CWD, "data", "policy_rules.json")
            try:
                rules = body.get("rules", body)
                with open(rules_file, "w") as f:
                    json.dump(rules, f, indent=2)
                self._json({"ok": True}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500); return

        if path == "/api/policy/report-violations":
            selected = body.get("violations", [])
            if not selected:
                self._json({"ok": False, "error": "no violations provided"}); return
            vio_list = "; ".join(
                f"[{v.get('severity','?').upper()}] {v.get('type','?')}: {v.get('description','?')}"
                for v in selected
            )
            task = (
                f"Policy violations selected for correction: {vio_list}. "
                f"Analyze and delegate fixes to reforger."
            )
            ceo_msg_queue.append(task)
            add_log("policypro", f"Reported {len(selected)} violation(s) → CEO queue for fixing", "warn")
            self._json({"ok": True, "queued": len(selected)}); return

        if path == "/api/agent/stop":
            aid = body.get("id", "")
            if not aid or not isinstance(aid, str) or not aid.strip():
                self._json({"ok": False, "error": "agent_id is required and must be a non-empty string"}, 400); return
            aid = aid.strip()
            _stop_ev(aid).set(); set_agent(aid, status="idle", task="Stopped")
            add_log(aid, "Stopped by user", "warn")
        elif path == "/api/agent/start":
            aid = body.get("id", "")
            if not aid or not isinstance(aid, str) or not aid.strip():
                self._json({"ok": False, "error": "agent_id is required and must be a non-empty string"}, 400); return
            aid = aid.strip()
            _stop_ev(aid).clear(); set_agent(aid, status="active", task="Restarted")
            add_log(aid, "Restarted by user", "ok")
        elif path == "/api/agent/remove":
            aid = body.get("id", "")
            if not aid or not isinstance(aid, str) or not aid.strip():
                self._json({"ok": False, "error": "agent_id is required and must be a non-empty string"}, 400); return
            aid = aid.strip()
            try:
                with lock:
                    if aid not in agents:
                        self._json({"ok": False, "error": f"Agent '{aid}' not found"}, 404); return
                    agent_info = agents[aid]
                    if agent_info.get("status") == "active":
                        self._json({"ok": False, "error": f"Agent '{aid}' is currently active; stop it before removing"}, 409); return
                    agents.pop(aid, None)
                    _active_delegations[:] = [d for d in _active_delegations if d.get("to") != aid and d.get("from") != aid]
                add_log("system", f"Agent '{aid}' removed", "warn")
                sse_broadcast("agent_removed", {"id": aid})
            except Exception as e:
                add_log("system", f"Error removing agent '{aid}': {e}", "error")
                self._json({"ok": False, "error": str(e)}, 500); return
        elif path == "/api/delegations/clear":
            # ── Full delegation queue flush (Reforger upgrade) ──
            with lock:
                _active_delegations.clear()
            # Kill any stale delegate subprocesses
            killed = 0
            with _delegate_procs_lock:
                for dp in list(_delegate_procs):
                    _kill_proc_group(dp)
                    killed += 1
                _delegate_procs.clear()
            # Reset queue depth counter
            with _delegate_queue_lock:
                _delegate_queue_depth[0] = 0
            # Drain and re-init semaphore to full capacity (16 slots)
            while _delegate_semaphore.acquire(blocking=False):
                pass  # drain all permits
            for _ in range(16):
                _delegate_semaphore.release()  # restore full capacity
            # Reset orchestrator to ready state
            set_agent("orchestrator", status="active", progress=0, task="Queue flushed — ready")
            add_log("system", f"Delegation queue flushed: {killed} procs killed, semaphore reset", "ok")
        elif path == "/api/system/stop":
            _system_paused = True
            for aid in list(agents.keys()): set_agent(aid, status="idle", task="System paused")
            add_log("system", "All agents paused", "warn")
        elif path == "/api/system/start":
            _system_paused = False
            for aid in list(agents.keys()):
                _stop_ev(aid).clear(); set_agent(aid, status="active", task="Resumed")
            add_log("system", "All agents resumed", "ok")
        elif path == "/api/system/buildmode":
            # BUILD MODE — kills ALL token-burning activity immediately
            entering = body.get("enabled", True)
            if entering:
                _system_paused = True
                _autonomy_mode = False
                _build_mode = True
                # Kill all tracked delegate subprocesses
                killed = 0
                with _delegate_procs_lock:
                    for proc_ref in list(_delegate_procs):
                        try:
                            _kill_proc_group(proc_ref)
                            killed += 1
                        except Exception:
                            pass
                    _delegate_procs.clear()
                # Nuclear option: kill ALL claude -p processes system-wide (catches untracked spawns)
                try:
                    _pkill = subprocess.run(["pkill", "-9", "-f", "claude -p"], capture_output=True, timeout=5)
                    _pk_count = subprocess.run(["pgrep", "-cf", "claude -p"], capture_output=True, text=True, timeout=3)
                    add_log("system", f"pkill sweep: signalled claude -p processes", "warn")
                except Exception:
                    pass
                # Stop all agent threads
                for aid in list(agents.keys()):
                    _stop_ev(aid).set()
                    set_agent(aid, status="idle", task="🔧 Build Mode — paused")
                # Flush orchestrator queue
                _orc_task_q.clear()
                # Clear CEO message queue
                ceo_msg_queue.clear()
                # Clear active delegations
                with lock:
                    _active_delegations.clear()
                add_log("system", f"🔧 BUILD MODE ON — all agents stopped, {killed} tracked + all claude -p procs killed, autonomy off. Zero token burn.", "warn")
                self._json({"ok": True, "build_mode": True, "killed_procs": killed}); return
            else:
                _build_mode = False
                _system_paused = False
                for aid in list(agents.keys()):
                    _stop_ev(aid).clear()
                    set_agent(aid, status="active", task="Resumed from Build Mode")
                add_log("system", "🔧 BUILD MODE OFF — agents resuming", "ok")
                self._json({"ok": True, "build_mode": False}); return
        elif path == "/api/email/send" or path == "/api/email/queue":
            # Queue an email for EmailAgent to dispatch
            to_addr = body.get("to", "")
            subject = body.get("subject", "")
            email_body = body.get("body", body.get("text", ""))
            is_html = body.get("html", False)
            if not to_addr or not subject:
                self._json({"ok": False, "error": "to and subject fields required"}); return
            QUEUE_FILE = os.path.join(CWD, "data", "email_queue.json")
            with lock:
                try:
                    queue = json.load(open(QUEUE_FILE)) if os.path.exists(QUEUE_FILE) else []
                except Exception:
                    queue = []
                queue.append({"to": to_addr, "subject": subject, "body": email_body, "html": is_html})
                with open(QUEUE_FILE, "w") as _f:
                    json.dump(queue, _f, indent=2)
            add_log("emailagent", f"Queued email to {to_addr}: {subject}", "ok")
            self._json({"ok": True, "queued": True, "queue_depth": len(queue)}); return

        elif path == "/api/email/config":
            CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
            ALLOWED_KEYS = {
                "smtp_host", "smtp_port", "smtp_user", "smtp_pass",
                "from_addr", "default_to", "sendgrid_api_key",
            }
            try:
                cfg = {}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE) as _f:
                        cfg = json.load(_f)
                updated = []
                for k, v in body.items():
                    if k in ALLOWED_KEYS:
                        cfg[k] = v
                        updated.append(k)
                with open(CONFIG_FILE, "w") as _f:
                    json.dump(cfg, _f, indent=2)
                add_log("emailagent", f"email_config updated: {updated}", "ok")
                self._json({"ok": True, "updated": updated}); return
            except Exception as _e:
                self._json({"ok": False, "error": str(_e)}); return

        elif path == "/api/emailagent/send" or path == "/api/email/test":
            # Direct synchronous send via Gmail OAuth2 XOAUTH2 SMTP
            # Accepts: {to, subject, body, html (bool), html_body (str)}
            # /api/email/test accepts just {to} and sends a canned test message
            import smtplib as _smtplib, base64 as _b64, urllib.parse as _uparse
            from email.mime.multipart import MIMEMultipart as _MIMP
            from email.mime.text import MIMEText as _MIMT
            _is_test   = (path == "/api/email/test")
            _to        = body.get("to", "").strip() or os.environ.get("EMAIL_TO", "").strip() or ("hq@secondmind.ai" if _is_test else "")
            _subject   = body.get("subject", "Test Email — Agent Command Centre") if _is_test else body.get("subject", "").strip()
            _body_txt  = body.get("body", "This is a test email from Agent Command Centre.\n\nIf you received this, Gmail OAuth2 is working correctly.")
            _html_body = body.get("html_body", "")
            _is_html   = bool(_html_body or body.get("html", False))
            _content   = _html_body if _html_body else _body_txt
            if not _to:
                self._json({"ok": False, "error": "to field required (or set EMAIL_TO env var)"}); return
            if not _is_test and not _subject:
                self._json({"ok": False, "error": "subject field required"}); return
            # Check OAuth state
            _gm_client_id  = os.environ.get("GMAIL_CLIENT_ID", "").strip()
            _gm_secret     = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
            _gm_refresh    = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
            _gm_user       = os.environ.get("GMAIL_USER", "").strip()
            if not (_gm_client_id and _gm_secret and _gm_refresh and _gm_user):
                _missing = [k for k, v in {"GMAIL_CLIENT_ID": _gm_client_id, "GMAIL_CLIENT_SECRET": _gm_secret,
                                            "GMAIL_REFRESH_TOKEN": _gm_refresh, "GMAIL_USER": _gm_user}.items() if not v]
                self._json({"ok": False, "error": f"Gmail OAuth2 incomplete — missing: {_missing}. Visit /api/email/auth"}); return
            # Refresh access token
            try:
                _params = _uparse.urlencode({
                    "client_id": _gm_client_id, "client_secret": _gm_secret,
                    "refresh_token": _gm_refresh, "grant_type": "refresh_token",
                }).encode("utf-8")
                import urllib.request as _ureq
                _treq = _ureq.Request("https://oauth2.googleapis.com/token", data=_params,
                                      headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
                with _ureq.urlopen(_treq, timeout=15) as _tr:
                    _tdata = json.loads(_tr.read())
                if "access_token" not in _tdata:
                    raise RuntimeError(f"Token refresh failed: {_tdata.get('error_description', _tdata)}")
                _access_token = _tdata["access_token"]
            except Exception as _te:
                self._json({"ok": False, "error": f"Gmail token refresh failed: {_te}"}); return
            # Build XOAUTH2 string
            _xoauth_str = f"user={_gm_user}\x01auth=Bearer {_access_token}\x01\x01"
            _xoauth_b64 = _b64.b64encode(_xoauth_str.encode()).decode()
            _from_addr  = os.environ.get("EMAIL_FROM", "").strip() or _gm_user
            _last_exc   = None
            _method     = None
            for _attempt in range(1, 4):
                try:
                    _mime = _MIMP("alternative")
                    _mime["Subject"] = _subject
                    _mime["From"]    = _from_addr
                    _mime["To"]      = _to
                    _mime.attach(_MIMT(_content, "html" if _is_html else "plain"))
                    with _smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as _srv:
                        _srv.ehlo(); _srv.starttls(); _srv.ehlo()
                        _srv.docmd("AUTH", "XOAUTH2 " + _xoauth_b64)
                        _srv.sendmail(_from_addr, [_to], _mime.as_string())
                    _method   = "gmail-oauth2-smtp"
                    _last_exc = None
                    break
                except Exception as _exc:
                    _last_exc = _exc
                    add_log("emailagent", f"/api/emailagent/send attempt {_attempt}/3 failed: {_exc}", "warn")
                    if _attempt < 3:
                        import time as _t; _t.sleep(5)
            _ts = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
            if _last_exc is None:
                add_log("emailagent", f"Sent via {_method} to {_to}: {_subject}", "ok")
                set_agent("emailagent", task=f"Last sent {_ts} \u2192 {_to}: {_subject[:40]}")
                _LOG_FILE = os.path.join(CWD, "data", "email_log.json")
                try:
                    _log = json.load(open(_LOG_FILE)) if os.path.exists(_LOG_FILE) else []
                except Exception: _log = []
                _log.append({"timestamp": _ts, "to": _to, "subject": _subject, "method": _method, "success": True})
                _log = _log[-500:]
                with open(_LOG_FILE, "w") as _lf: json.dump(_log, _lf, indent=2)
                self._json({"ok": True, "method": _method, "to": _to, "timestamp": _ts,
                            **({"message": "Test email sent"} if _is_test else {})}); return
            else:
                add_log("emailagent", f"/api/emailagent/send failed after 3 attempts: {_last_exc}", "error")
                set_agent("emailagent", status="error", task=f"Send failed: {str(_last_exc)[:60]}")
                self._json({"ok": False, "error": str(_last_exc), "attempts": 3}); return

        elif path == "/api/telegram/send":
            tg_text = body.get("message") or body.get("text", "")
            tg_chat = body.get("chat_id") or _telegram_chat_id
            if not _TELEGRAM_TOKEN:
                self._json({"ok": False, "error": "TELEGRAM_TOKEN not set"}); return
            if not tg_chat:
                self._json({"ok": False, "error": "No chat_id available — send a message to the bot first"}); return
            if not tg_text:
                self._json({"ok": False, "error": "text field required"}); return
            try:
                payload = tg_text[:4000] + ("…" if len(tg_text) > 4000 else "")
                r = requests.post(
                    f"https://api.telegram.org/bot{_TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": tg_chat, "text": payload}, timeout=10,
                )
                result = r.json()
                if result.get("ok"):
                    self._json({"ok": True, "chat_id": tg_chat}); return
                else:
                    self._json({"ok": False, "error": result.get("description", "Unknown Telegram error")}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}); return

        elif path == "/api/notify":
            # Central notification router — routes to Telegram if configured
            import datetime as _dt
            _evt   = body.get("event_type", "notification")
            _msg   = body.get("message", "")
            _sev   = body.get("severity", "info")
            _agent = body.get("agent", "system")
            _ts    = body.get("timestamp") or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not _msg:
                self._json({"ok": False, "error": "message field required"}, 400); return
            # Inject timestamp into message if not already present
            _full_msg = f"{_msg}\n⏰ {_ts}" if _ts not in _msg else _msg
            _fire_notify(_evt, _full_msg, severity=_sev, agent=_agent)
            self._json({"ok": True, "event_type": _evt, "severity": _sev, "routed_to": "telegram"}); return

        elif path == "/api/bluesky/post":
            text = body.get("text", "")
            if not text:
                self._json({"ok": False, "error": "text field required"}); return
            try:
                requests.post(
                    "http://localhost:5050/api/ceo/delegate",
                    json={"agent_id": "orchestrator", "task": f"Route to bluesky — post: {text}", "from": "api"},
                    headers={"X-API-Key": _HQ_API_KEY},
                    timeout=5,
                )
            except Exception as _e:
                add_log("bluesky", f"delegate failed: {_e}", "warn")
            add_log("bluesky", f"Queued post: {text[:80]}", "ok")
            self._json({"status": "queued", "text": text}); return

        elif path == "/api/vault/set":
            _vs_service = body.get("service", "").strip()
            _vs_field   = body.get("field", "").strip()
            _vs_value   = body.get("value")
            if not _vs_service or not _vs_field:
                self._json({"ok": False, "error": "service and field fields required"}, 400); return
            if _vs_value is None:
                self._json({"ok": False, "error": "value field required"}, 400); return
            try:
                import sys as _sys
                _sys.path.insert(0, os.path.join(CWD, "data"))
                import vault_helper as _vh
                _vh.set_secret(_vs_service, _vs_field, str(_vs_value))
                add_log("system", f"Vault: stored {_vs_service}/{_vs_field}", "ok")
                self._json({"ok": True, "stored": True}); return
            except ImportError:
                self._json({"ok": False, "error": "Vault not initialized"}, 503); return
            except Exception as _ve:
                self._json({"ok": False, "error": str(_ve)}, 500); return

        elif path == "/api/config/set":
            _cfg_key   = body.get("key",   "").strip()
            _cfg_value = body.get("value", "")
            if not _cfg_key:
                self._json({"ok": False, "error": "key required"}, 400); return
            # Load existing config
            _cfg_path = os.path.join(CWD, "data", "user_config.json")
            try:
                _cfg = json.load(open(_cfg_path)) if os.path.exists(_cfg_path) else {}
            except Exception:
                _cfg = {}
            _cfg[_cfg_key] = str(_cfg_value)
            # Save JSON config
            os.makedirs(os.path.join(CWD, "data"), exist_ok=True)
            with open(_cfg_path, "w") as _f:
                json.dump(_cfg, _f, indent=2)
            # Write .env file (rebuild from full config)
            _env_out_path = os.path.join(CWD, ".env")
            _existing_env = {}
            if os.path.exists(_env_out_path):
                with open(_env_out_path) as _ef:
                    for _line in _ef:
                        _line = _line.strip()
                        if _line and not _line.startswith("#") and "=" in _line:
                            _ek, _ev = _line.split("=", 1)
                            _existing_env[_ek.strip()] = _ev.strip()
            _existing_env[_cfg_key] = str(_cfg_value)
            with open(_env_out_path, "w") as _ef:
                _ef.write("# Auto-generated by Command Centre Setup\n")
                for _ek, _ev in _existing_env.items():
                    _ef.write(f"{_ek}={_ev}\n")
            # Also update live environment
            os.environ[_cfg_key] = str(_cfg_value)
            add_log("system", f"Config: saved {_cfg_key}", "ok")
            self._json({"ok": True, "key": _cfg_key, "saved_at": datetime.now().isoformat()}); return

        elif path == "/api/treasury/deposit":
            _amount = body.get("amount_usd", body.get("amount_aud"))
            _source = body.get("source", "unknown")
            _desc   = body.get("description", "")
            if not isinstance(_amount, (int, float)) or _amount <= 0:
                self._json({"ok": False, "error": "amount_usd must be a positive number"}, 400); return
            _tf = os.path.join(CWD, "data", "treasury.json")
            try:
                with open(_tf) as _f: _td = json.load(_f)
            except Exception:
                _td = {"balance_usd": 0, "currency": "usd", "last_updated": "", "transactions": []}
            if not isinstance(_td.get("transactions"), list):
                _td["transactions"] = []
            _td["balance_usd"] = round(_td.get("balance_usd", _td.get("balance_aud", 0)) + _amount, 2)
            _td["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            _td["transactions"].append({
                "ts":         datetime.now().isoformat(),
                "amount_usd": _amount,
                "source":     _source,
                "description": _desc
            })
            with open(_tf, "w") as _f: json.dump(_td, _f, indent=2)
            add_log("treasury", f"Deposit ${_amount} from {_source}", "ok")
            self._json({"ok": True, "balance_usd": _td["balance_usd"], "transactions": len(_td["transactions"])}); return

        elif path == "/api/newsletter/subscribe":
            _email = body.get("email", "").strip().lower()
            _name = body.get("name", "").strip()
            if not _email or "@" not in _email:
                self._json({"ok": False, "error": "Invalid email"}, 400); return
            _ts = datetime.now().isoformat()
            # Append to subscribers.json
            _sf = os.path.join(CWD, "data", "subscribers.json")
            try:
                with open(_sf) as _f: _subs = json.load(_f)
            except Exception:
                _subs = []
            _subs.append({"email": _email, "name": _name, "subscribed_at": _ts, "source": "landing_page"})
            with open(_sf, "w") as _f: json.dump(_subs, _f, indent=2)
            # Log to revenue_log.json
            _rlf = os.path.join(CWD, "data", "revenue_log.json")
            try:
                with open(_rlf) as _f: _rl = json.load(_f)
            except Exception:
                _rl = {}
            if "email_captures" not in _rl:
                _rl["email_captures"] = []
            _rl["email_captures"].append({"timestamp": _ts, "event": "email_capture", "email": _email, "source": "landing_page"})
            with open(_rlf, "w") as _f: json.dump(_rl, _f, indent=2)
            add_log("newsletter", f"New subscriber: {_email}", "ok")
            self._json({"ok": True, "message": "Subscribed successfully"}); return

        elif path == "/api/premarket/subscribe":
            _email = body.get("email", "").strip().lower()
            _tier = body.get("tier", "free").strip().lower()
            if not _email or "@" not in _email:
                self._json({"ok": False, "error": "Invalid email"}, 400); return
            if _tier not in ("free", "trader", "pro"):
                _tier = "free"
            _ts = datetime.now().isoformat()
            _sf = os.path.join(CWD, "data", "subscribers.json")
            try:
                with open(_sf) as _f: _subs = json.load(_f)
            except Exception:
                _subs = []
            # Check for duplicate
            if any(s.get("email") == _email and s.get("product") == "premarket_pulse" for s in _subs):
                self._json({"ok": True, "message": "Already subscribed"}); return
            _subs.append({"email": _email, "tier": _tier, "product": "premarket_pulse", "subscribed_at": _ts, "status": "active", "source": "premarket_pulse_landing"})
            with open(_sf, "w") as _f: json.dump(_subs, _f, indent=2)
            # Log to revenue_log
            _rlf = os.path.join(CWD, "data", "revenue_log.json")
            try:
                with open(_rlf) as _f: _rl = json.load(_f)
            except Exception:
                _rl = {}
            if "email_captures" not in _rl:
                _rl["email_captures"] = []
            _rl["email_captures"].append({"timestamp": _ts, "event": "premarket_signup", "email": _email, "tier": _tier, "source": "premarket_pulse"})
            with open(_rlf, "w") as _f: json.dump(_rl, _f, indent=2)
            add_log("premarket", f"New PreMarket Pulse subscriber: {_email} ({_tier})", "ok")
            self._json({"ok": True, "message": "Subscribed to PreMarket Pulse"}); return

        else:
            self.send_response(404); self._cors(); self.end_headers(); return

        self._json({"ok": True})

    def do_GET(self):
        # ── Force HTTPS on Render (behind proxy) ──
        if os.environ.get("RENDER") and self.headers.get("X-Forwarded-Proto") == "http":
            host = self.headers.get("Host", "secondmindhq.com")
            self.send_response(301)
            self.send_header("Location", f"https://{host}{self.path}")
            self.end_headers()
            return

        try:
            self._do_GET_inner()
        except Exception as _exc:
            try:
                self._json({"ok": False, "error": f"internal server error: {type(_exc).__name__}"}, 500)
            except Exception:
                pass  # headers may already be sent

    def _do_GET_inner(self):
        path = urlparse(self.path).path

        if path == "/api/status":
            with lock:
                _enriched_agents = []
                for _a in agents.values():
                    _ea = dict(_a)
                    _aid = _ea.get("id", "")
                    _ea["branch"] = _AGENT_BRANCH.get(_aid, None)
                    _ea["is_branch_head"] = _aid in _BRANCH_HEADS
                    _enriched_agents.append(_ea)
                payload = {
                    "agents":  _enriched_agents,
                    "tasks":   tasks[:40],
                    "logs":    logs[:80],
                    "metrics": {
                        **metrics,
                        "active": sum(1 for a in agents.values() if a.get("status") in ("active","busy")),
                        "total":  len(agents),
                    },
                    "data_usage": {
                        "per_agent":      dict(agent_data),
                        "total_sent":     sum(v["sent"]     for v in agent_data.values()),
                        "total_received": sum(v["received"] for v in agent_data.values()),
                        "total_requests": sum(v["requests"] for v in agent_data.values()),
                    },
                    "system_paused":      False if _IS_RENDER else _system_paused,
                    "build_mode":         False if _IS_RENDER else _build_mode,
                    "autonomy_mode":      False if _IS_RENDER else _autonomy_mode,
                    "autonomy_cycle":     _autonomy_cycle,
                    "custom_task_queue":  list(_autonomy_custom_q),
                    "policypro_enabled": _policypro_enabled,
                    "stopped_agents": [] if _IS_RENDER else [aid for aid, ev in _stop_events.items() if ev.is_set()],
                    "ceo_stream": dict(ceo_stream),
                    "has_llm": _claude_cli,
                    "active_delegations": list(_active_delegations)[-20:],
                }
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/health":
            with lock:
                agent_count = len(agents)
                busy_count  = sum(1 for a in agents.values()
                                  if a.get("status") not in ("idle", "standby", None))
                error_count = metrics.get("errors", 0)
            uptime = time.time() - _SERVER_START_TIME
            if error_count == 0:
                health_status = "ok"
            elif error_count <= 5:
                health_status = "degraded"
            else:
                health_status = "critical"
            payload = {
                "uptime_seconds": round(uptime, 3),
                "agent_count":    agent_count,
                "busy_count":     busy_count,
                "status":         health_status,
            }
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/branches":
            payload = {}
            for br_name, br_info in BRANCHES.items():
                payload[br_name] = {
                    "head": br_info["head"],
                    "members": br_info["members"],
                    "agent_details": [],
                }
                with lock:
                    for mid in br_info["members"]:
                        a = agents.get(mid, {})
                        payload[br_name]["agent_details"].append({
                            "id": mid,
                            "name": a.get("name", mid),
                            "status": a.get("status", "unknown"),
                            "is_branch_head": mid == br_info["head"],
                        })
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/agents":
            with lock:
                payload = list(agents.values())
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/metrics":
            with lock:
                payload = {
                    **metrics,
                    "active": sum(1 for a in agents.values() if a.get("status") in ("active","busy")),
                    "total":  len(agents),
                }
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path in ("/dashboard", "/command"):
            self.send_response(302); self._cors()
            self.send_header("Location", "/")
            self.end_headers()

        elif path == "/api/agents/summary":
            with lock:
                by_status = {}
                for a in agents.values():
                    s = a.get("status") or "unknown"
                    by_status[s] = by_status.get(s, 0) + 1
            payload = {
                "total": sum(by_status.values()),
                "by_status": by_status,
            }
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/policy/vote/current":
            with _policy_votes_lock:
                open_votes = {vid: {k: v for k, v in vote.items() if k != "_opened_ts"}
                              for vid, vote in _policy_votes.items() if vote["status"] == "open"}
            body = json.dumps({"ok": True, "open_votes": open_votes}).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/policy/vote/history":
            try:
                with open(_VOTE_LOG_FILE) as f:
                    history = json.load(f)
            except Exception:
                history = []
            body = json.dumps({"ok": True, "history": history}).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/email/config":
            CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
            try:
                with open(CONFIG_FILE) as _f:
                    cfg = json.load(_f)
            except Exception:
                cfg = {}
            # Mask secret key
            if cfg.get("sendgrid_api_key"):
                cfg["sendgrid_api_key"] = "***"
            body = json.dumps(cfg).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/email/status":
            QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
            LOG_FILE    = os.path.join(CWD, "data", "email_log.json")
            FAILED_FILE = os.path.join(CWD, "data", "email_failed.json")
            try:
                queue = json.load(open(QUEUE_FILE)) if os.path.exists(QUEUE_FILE) else []
            except Exception:
                queue = []
            try:
                log_entries = json.load(open(LOG_FILE)) if os.path.exists(LOG_FILE) else []
            except Exception:
                log_entries = []
            try:
                failed = json.load(open(FAILED_FILE)) if os.path.exists(FAILED_FILE) else []
            except Exception:
                failed = []
            sent_count = sum(1 for e in log_entries if e.get("success"))
            _gm_all = all([os.environ.get("GMAIL_CLIENT_ID","").strip(),
                           os.environ.get("GMAIL_CLIENT_SECRET","").strip(),
                           os.environ.get("GMAIL_REFRESH_TOKEN","").strip(),
                           os.environ.get("GMAIL_USER","").strip()])
            _gm_partial = (bool(os.environ.get("GMAIL_CLIENT_ID","").strip()) and
                           bool(os.environ.get("GMAIL_CLIENT_SECRET","").strip()) and not _gm_all)
            _oauth_status = "configured" if _gm_all else ("pending_refresh_token" if _gm_partial else "not_configured")
            payload = {
                "ok": True,
                "queued": len(queue),
                "sent":   sent_count,
                "failed": len(failed),
                "backend": "gmail-oauth2-smtp",
                "oauth_status": _oauth_status,
                "credentials_configured": _gm_all,
            }
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/emailagent/status":
            _QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
            _LOG_FILE    = os.path.join(CWD, "data", "email_log.json")
            _FAILED_FILE = os.path.join(CWD, "data", "email_failed.json")
            try: _q = json.load(open(_QUEUE_FILE)) if os.path.exists(_QUEUE_FILE) else []
            except Exception: _q = []
            try: _log_e = json.load(open(_LOG_FILE)) if os.path.exists(_LOG_FILE) else []
            except Exception: _log_e = []
            try: _fail_e = json.load(open(_FAILED_FILE)) if os.path.exists(_FAILED_FILE) else []
            except Exception: _fail_e = []
            _gm_client_id  = os.environ.get("GMAIL_CLIENT_ID", "").strip()
            _gm_secret     = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
            _gm_refresh    = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
            _gm_user       = os.environ.get("GMAIL_USER", "").strip()
            _gm_all        = bool(_gm_client_id and _gm_secret and _gm_refresh and _gm_user)
            _gm_partial    = bool(_gm_client_id and _gm_secret) and not _gm_all
            _oauth_st      = "configured" if _gm_all else ("pending_refresh_token" if _gm_partial else "not_configured")
            _from_email    = os.environ.get("EMAIL_FROM", "").strip() or _gm_user or None
            _to_email      = os.environ.get("EMAIL_TO", "").strip()
            _healthy       = _gm_all
            _last_sent     = next((e["timestamp"] for e in reversed(_log_e) if e.get("success")), None)
            _issues        = []
            if not _gm_client_id:  _issues.append("GMAIL_CLIENT_ID not set")
            if not _gm_secret:     _issues.append("GMAIL_CLIENT_SECRET not set")
            if not _gm_refresh:    _issues.append("GMAIL_REFRESH_TOKEN not set — visit /api/email/auth")
            if not _gm_user:       _issues.append("GMAIL_USER not set")
            _payload = {
                "ok": True,
                "healthy": _healthy,
                "backend": "gmail-oauth2-smtp",
                "oauth_status": _oauth_st,
                "credentials_configured": _gm_all,
                "gmail_user": _gm_user or None,
                "from_email": _from_email,
                "to_email_default": _to_email or None,
                "queued": len(_q),
                "sent": sum(1 for e in _log_e if e.get("success")),
                "failed": len(_fail_e),
                "last_sent": _last_sent,
                "issues": _issues,
                "auth_url": "http://localhost:5050/api/email/auth" if not _gm_all else None,
            }
            body = json.dumps(_payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/email/test":
            # GET /api/email/test?to=addr  — send a test email via Gmail OAuth2
            from urllib.parse import parse_qs, urlencode, urlparse as _ulp
            import smtplib as _smtplib, base64 as _b64
            from email.mime.multipart import MIMEMultipart as _MIMP
            from email.mime.text import MIMEText as _MIMT
            import urllib.request as _ureq
            _qs2  = parse_qs(_ulp(self.path).query)
            _to   = (_qs2.get("to", [""])[0].strip() or
                     os.environ.get("GMAIL_USER", "").strip() or
                     os.environ.get("EMAIL_FROM", "").strip())
            if not _to:
                self._json({"ok": False, "error": "Pass ?to=email@example.com or set GMAIL_USER in .env"}); return
            _gm_client_id = os.environ.get("GMAIL_CLIENT_ID", "").strip()
            _gm_secret    = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
            _gm_refresh   = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
            _gm_user      = os.environ.get("GMAIL_USER", "").strip()
            if not (_gm_client_id and _gm_secret and _gm_refresh and _gm_user):
                _miss = [k for k,v in {"GMAIL_CLIENT_ID":_gm_client_id,"GMAIL_CLIENT_SECRET":_gm_secret,
                                        "GMAIL_REFRESH_TOKEN":_gm_refresh,"GMAIL_USER":_gm_user}.items() if not v]
                self._json({"ok": False, "error": f"Gmail OAuth2 incomplete — missing: {_miss}. Visit /api/email/auth"}); return
            try:
                _tparams = urlencode({"client_id":_gm_client_id,"client_secret":_gm_secret,
                                      "refresh_token":_gm_refresh,"grant_type":"refresh_token"}).encode()
                _treq2 = _ureq.Request("https://oauth2.googleapis.com/token", data=_tparams,
                                       headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
                with _ureq.urlopen(_treq2, timeout=15) as _tr2:
                    _tdata2 = json.loads(_tr2.read())
                if "access_token" not in _tdata2:
                    raise RuntimeError(f"Token refresh failed: {_tdata2.get('error_description', _tdata2)}")
                _access_tok = _tdata2["access_token"]
                _xoauth_str = f"user={_gm_user}\x01auth=Bearer {_access_tok}\x01\x01"
                _xoauth_b64 = _b64.b64encode(_xoauth_str.encode()).decode()
                _from_addr  = os.environ.get("EMAIL_FROM", "").strip() or _gm_user
                _subj = "Test Email — Agent Command Centre"
                _body_txt = "This is a test email from Agent Command Centre.\n\nGmail OAuth2 is working correctly."
                _mime = _MIMP("alternative")
                _mime["Subject"] = _subj; _mime["From"] = _from_addr; _mime["To"] = _to
                _mime.attach(_MIMT(_body_txt, "plain"))
                with _smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as _srv:
                    _srv.ehlo(); _srv.starttls(); _srv.ehlo()
                    _srv.docmd("AUTH", "XOAUTH2 " + _xoauth_b64)
                    _srv.sendmail(_from_addr, [_to], _mime.as_string())
                _ts2 = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
                add_log("emailagent", f"Test email sent via Gmail OAuth2 to {_to}", "ok")
                self._json({"ok": True, "method": "gmail-oauth2-smtp", "to": _to, "timestamp": _ts2,
                            "message": "Test email sent"}); return
            except Exception as _te:
                add_log("emailagent", f"GET /api/email/test failed: {_te}", "error")
                self._json({"ok": False, "error": str(_te)}); return

        elif path == "/api/email/auth":
            # Initiate Gmail OAuth2 consent flow — redirect user to Google's consent screen
            _gm_client_id = os.environ.get("GMAIL_CLIENT_ID", "").strip()
            if not _gm_client_id:
                self._json({"ok": False, "error": "GMAIL_CLIENT_ID not set in .env"}); return
            import urllib.parse as _up
            _redirect_uri = os.environ.get("GMAIL_REDIRECT_URI", "").strip() or "http://localhost:5050/api/email/callback"
            _scope = "https://mail.google.com/"
            _auth_url = ("https://accounts.google.com/o/oauth2/v2/auth?" + _up.urlencode({
                "client_id":     _gm_client_id,
                "redirect_uri":  _redirect_uri,
                "response_type": "code",
                "scope":         _scope,
                "access_type":   "offline",
                "prompt":        "consent",
            }))
            # Redirect browser to Google consent screen
            _html = (
                f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<meta http-equiv='refresh' content='0;url={_auth_url}'>"
                f"<title>Redirecting to Google...</title></head><body>"
                f"<p>Redirecting to Google consent screen... "
                f"<a href='{_auth_url}'>Click here if not redirected</a></p>"
                f"</body></html>"
            ).encode()
            self.send_response(302); self._cors()
            self.send_header("Location", _auth_url)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(_html)))
            self.end_headers(); self.wfile.write(_html)

        elif path in ("/api/email/oauth2callback", "/api/email/auth/callback", "/api/email/callback"):
            # Exchange OAuth2 code for refresh token; save to data/gmail_tokens.json and .env
            from urllib.parse import parse_qs, urlencode, urlparse as _ulp
            import urllib.request as _ureq
            _qs   = parse_qs(_ulp(self.path).query)
            _code = _qs.get("code", [""])[0]
            _err  = _qs.get("error", [""])[0]
            if _err:
                _html = f"<h2>OAuth2 Error</h2><p>{_err}</p>".encode()
                self.send_response(400); self._cors()
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(_html)))
                self.end_headers(); self.wfile.write(_html); return
            if not _code:
                self._json({"ok": False, "error": "No authorization code returned"}); return
            _gm_client_id  = os.environ.get("GMAIL_CLIENT_ID", "").strip()
            _gm_secret     = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
            _redirect_uri  = os.environ.get("GMAIL_REDIRECT_URI", "").strip() or "http://localhost:5050/api/email/callback"
            try:
                _params = urlencode({
                    "code":          _code,
                    "client_id":     _gm_client_id,
                    "client_secret": _gm_secret,
                    "redirect_uri":  _redirect_uri,
                    "grant_type":    "authorization_code",
                }).encode("utf-8")
                _treq = _ureq.Request("https://oauth2.googleapis.com/token", data=_params,
                                      headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
                with _ureq.urlopen(_treq, timeout=15) as _tr:
                    _tdata = json.loads(_tr.read())
                if "refresh_token" not in _tdata:
                    raise RuntimeError(f"No refresh_token in response: {_tdata}")
                _refresh_token = _tdata["refresh_token"]
                # Save to data/gmail_tokens.json
                _tokens_path = os.path.join(CWD, "data", "gmail_tokens.json")
                os.makedirs(os.path.dirname(_tokens_path), exist_ok=True)
                _existing_tokens = {}
                if os.path.exists(_tokens_path):
                    try:
                        with open(_tokens_path) as _tf: _existing_tokens = json.load(_tf)
                    except Exception: pass
                _existing_tokens.update({
                    "refresh_token": _refresh_token,
                    "client_id": _gm_client_id,
                    "saved_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
                })
                with open(_tokens_path, "w") as _tf:
                    json.dump(_existing_tokens, _tf, indent=2)
                # Also persist to .env so it survives restarts
                _env_path = os.path.join(CWD, ".env")
                _env_lines = open(_env_path).readlines() if os.path.exists(_env_path) else []
                _found = False
                for _i, _line in enumerate(_env_lines):
                    if _line.startswith("GMAIL_REFRESH_TOKEN="):
                        _env_lines[_i] = f"GMAIL_REFRESH_TOKEN={_refresh_token}\n"
                        _found = True; break
                if not _found:
                    _env_lines.append(f"GMAIL_REFRESH_TOKEN={_refresh_token}\n")
                with open(_env_path, "w") as _ef:
                    _ef.writelines(_env_lines)
                # Inject into running process env so it takes effect immediately
                os.environ["GMAIL_REFRESH_TOKEN"] = _refresh_token
                add_log("emailagent", "Gmail OAuth2 refresh token obtained and saved to data/gmail_tokens.json + .env", "ok")
                _html = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                    "<style>body{font-family:Arial,sans-serif;background:#0d0d0d;color:#e0e0e0;"
                    "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
                    ".box{background:#1a1a2e;padding:40px;border-radius:12px;border:2px solid #00cc88;"
                    "text-align:center;max-width:500px}"
                    "h2{color:#00cc88} p{color:#aaa} code{color:#00ff99}</style></head><body>"
                    "<div class='box'><h2>Gmail OAuth2 Complete</h2>"
                    "<p>Refresh token saved to <code>data/gmail_tokens.json</code> and <code>.env</code>.</p>"
                    "<p>Now set <code>GMAIL_USER</code> in your <code>.env</code> to the Gmail address "
                    "you just authorised, then restart the server.</p>"
                    "<p>Test: <a href='http://localhost:5050/api/email/test?to=you@example.com'>"
                    "GET /api/email/test?to=you@example.com</a></p>"
                    "</div></body></html>"
                ).encode()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(_html)))
                self.end_headers(); self.wfile.write(_html)
            except Exception as _ce:
                add_log("emailagent", f"Gmail OAuth2 callback error: {_ce}", "error")
                self._json({"ok": False, "error": str(_ce)}); return

        elif path == "/api/ceo/chat":
            with lock:
                payload = {
                    "messages": list(ceo_chat_display),
                    "stream":   dict(ceo_stream),
                    "has_llm":  _claude_cli,
                }
            body = json.dumps(payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/agent/output":
            from urllib.parse import parse_qs
            qs     = parse_qs(urlparse(self.path).query)
            aid    = (qs.get("agent_id",[""])[0])
            since  = int(qs.get("since",["0"])[0])
            with agent_live_output_lock:
                buf = list(agent_live_output.get(aid, []))
            filtered = [e for e in buf if e["seq"] > since]
            body = json.dumps({"ok": True, "agent_id": aid,
                                "entries": filtered,
                                "latest_seq": buf[-1]["seq"] if buf else 0}).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path.startswith("/api/agent/") and path.endswith("/logs"):
            from urllib.parse import parse_qs
            # /api/agent/<id>/logs?limit=N  — returns last N log lines for agent <id>
            _parts = path.split("/")
            _aid = _parts[3] if len(_parts) >= 5 else ""
            _qs = parse_qs(urlparse(self.path).query)
            try:
                _limit = int(_qs.get("limit", ["100"])[0])
            except (ValueError, IndexError):
                _limit = 100
            _limit = max(1, min(_limit, 1000))
            with lock:
                if _aid:
                    _entries = [e for e in logs if e.get("agent") == _aid]
                else:
                    _entries = list(logs)
            body = json.dumps({
                "ok": True,
                "agent_id": _aid or None,
                "limit": _limit,
                "count": min(len(_entries), _limit),
                "entries": _entries[:_limit],
            }).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/stream":
            # Server-Sent Events endpoint — streams logs + agent_output events
            import queue as _queue
            q = _queue.Queue(maxsize=200)
            with _sse_clients_lock:
                _sse_clients.append(q)
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                # Send a heartbeat immediately so client knows it connected
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(msg.encode())
                        self.wfile.flush()
                    except _queue.Empty:
                        # heartbeat to keep connection alive
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with _sse_clients_lock:
                    if q in _sse_clients: _sse_clients.remove(q)

        elif path == "/api/account_provisioner/status":
            import glob as _glob
            accounts_dir = os.path.join(CWD, "data", "accounts")
            skip = {"provision_queue.json", "provision_log.jsonl"}
            records = []
            try:
                for fpath in sorted(_glob.glob(os.path.join(accounts_dir, "*.json"))):
                    fname = os.path.basename(fpath)
                    if fname in skip or fname == "api_key_pool.json":
                        continue
                    try:
                        with open(fpath) as _f:
                            rec = json.load(_f)
                            rec["_file"] = fname
                            records.append(rec)
                    except Exception:
                        pass
            except Exception:
                pass
            # API key pool
            pool = {}
            try:
                with open(os.path.join(accounts_dir, "api_key_pool.json")) as _f:
                    raw_pool = json.load(_f)
                for svc, info in raw_pool.items():
                    if svc.startswith("_"): continue
                    pool[svc] = {"configured": bool(info.get("keys")), "key_count": len(info.get("keys", []))}
            except Exception:
                pass
            self._json({"ok": True, "accounts": records, "api_keys": pool})

        elif path == "/api/social_bridge/status":
            self._json({"ok": True, "accounts": [], "message": "No social accounts configured — add credentials via AccountProvisioner"})

        elif path == "/api/improvements":
            try:
                with open(os.path.join(CWD, "improvements.json")) as f:
                    data = json.load(f)
            except Exception as e:
                data = {"error": str(e), "completed": [], "in_progress": None, "queue": []}
            body = json.dumps(data).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path in ("/reports/", "/reports"):
            # Directory index — list all .html and .pdf files in reports/
            import time as _time
            reports_dir = os.path.join(CWD, "reports")
            rows = []
            try:
                entries = sorted(os.listdir(reports_dir))
            except Exception:
                entries = []
            for fname in entries:
                if not (fname.endswith(".html") or fname.endswith(".pdf")):
                    continue
                fpath = os.path.join(reports_dir, fname)
                try:
                    st = os.stat(fpath)
                    size_kb = st.st_size / 1024
                    mdate = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(st.st_mtime))
                    size_str = f"{size_kb:.1f} KB"
                except Exception:
                    size_str = "—"
                    mdate = "—"
                rows.append(
                    f'<tr><td><a href="/reports/{fname}">{fname}</a></td>'
                    f'<td>{size_str}</td><td>{mdate}</td></tr>'
                )
            rows_html = "\n".join(rows) if rows else "<tr><td colspan='3'>No files found.</td></tr>"
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Reports Index</title>
<style>
  body{{font-family:monospace;background:#0d0d0d;color:#c8ffc8;padding:2rem;}}
  h1{{color:#00ff88;}}
  table{{border-collapse:collapse;width:100%;max-width:800px;}}
  th,td{{text-align:left;padding:6px 12px;border-bottom:1px solid #333;}}
  th{{color:#888;}}
  a{{color:#00ccff;text-decoration:none;}}
  a:hover{{text-decoration:underline;}}
</style></head>
<body>
<h1>&#128196; Reports</h1>
<table>
<thead><tr><th>Filename</th><th>Size</th><th>Modified</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
</body></html>"""
            content = html.encode("utf-8")
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers(); self.wfile.write(content)

        elif (path.startswith("/data/") or path.startswith("/reports/")
              or path.startswith("/widgets/")):
            file_path = os.path.realpath(os.path.join(CWD, path.lstrip("/")))
            if not file_path.startswith(os.path.realpath(CWD) + os.sep):
                self.send_response(403); self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"forbidden: path traversal blocked"}')
                return
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                if path.endswith(".json"):
                    ctype = "application/json"
                elif path.endswith(".html"):
                    ctype = "text/html; charset=utf-8"
                else:
                    ctype = "application/octet-stream"
                self.send_response(200); self._cors()
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/live-feed.html", "/live", "/feed"):
            try:
                with open(os.path.join(CWD, "live-feed.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/knowledge-base.html", "/kb"):
            try:
                with open(os.path.join(CWD, "knowledge-base.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/", ""):
            # Route based on domain:
            #   secondmindlabs.com  → company landing page (public/index.html)
            #   secondmindhq.com    → HQ dashboard
            #   localhost / other   → landing page (default)
            _host = self.headers.get("Host", "").lower().split(":")[0]
            _is_hq_domain = "secondmindhq" in _host
            if _is_hq_domain:
                # HQ domain → serve dashboard directly
                try:
                    with open(os.path.join(CWD, "agent-command-centre.html"), "rb") as f:
                        content = f.read()
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers(); self.wfile.write(content)
                except FileNotFoundError:
                    self.send_response(404); self._cors(); self.end_headers()
            else:
                # Labs domain / default → company landing page
                _landing = os.path.join(CWD, "public", "index.html")
                if os.path.exists(_landing):
                    with open(_landing, "rb") as f:
                        content = f.read()
                    self.send_response(200); self._cors()
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers(); self.wfile.write(content)
                else:
                    self.send_response(302); self._cors()
                    self.send_header("Location", "/hq")
                    self.end_headers()

        elif path in ("/agent-command-centre.html", "/hq", "/dashboard"):
            try:
                with open(os.path.join(CWD, "agent-command-centre.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/product", "/product.html", "/hq-product.html", "/hq-product"):
            # Try hq-product.html first, fall back to product.html
            _pf = None
            for _pname in ("hq-product.html", "product.html"):
                _pp = os.path.join(CWD, _pname)
                if os.path.exists(_pp):
                    _pf = _pp; break
            if _pf:
                with open(_pf, "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            else:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/buy", "/buy.html"):
            try:
                with open(os.path.join(CWD, "public", "buy.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/buy/us-market", "/buy/us-market.html"):
            try:
                with open(os.path.join(CWD, "public", "buy-us-market.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/premarket", "/premarket-pulse", "/premarket-pulse.html"):
            try:
                with open(os.path.join(CWD, "reports", "premarket_pulse.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/landing", "/landing.html", "/index.html"):
            try:
                with open(os.path.join(CWD, "public", "index.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path in ("/buy/agent-kit", "/buy/agent-kit.html"):
            try:
                with open(os.path.join(CWD, "public", "buy-agent-kit.html"), "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()

        elif path == "/api/products":
            products = [
                {
                    "id": "us_market_intel_v1",
                    "name": "US Stock Market Intelligence Report",
                    "description": "S&P 500 momentum picks, sector strength analysis, 20 watchlist candidates, risk dashboard — March 2026.",
                    "price_usd": 29.00,
                    "amount_cents": 2900,
                    "currency": "usd",
                    "type": "one_time",
                    "url": "/buy/us-market",
                    "available": True
                },
                {
                    "id": "agent_kit_v1",
                    "name": "AI Agent HQ Starter Kit",
                    "description": "Complete command centre source code template, 20+ agent config examples, setup guide, and deployment scripts.",
                    "price_usd": 49.00,
                    "amount_cents": 4900,
                    "currency": "usd",
                    "type": "one_time",
                    "url": "/buy/agent-kit",
                    "available": True
                }
            ]
            self._json({"ok": True, "products": products})

        elif path == "/api/policy/violations":
            vio_file = os.path.join(CWD, "data", "policy_violations.json")
            try:
                with open(vio_file) as f:
                    data = json.load(f)
            except Exception:
                data = []
            self._json({"ok": True, "violations": data})

        elif path == "/api/policy/rules":
            rules_file = os.path.join(CWD, "data", "policy_rules.json")
            try:
                with open(rules_file) as f:
                    data = json.load(f)
            except Exception:
                data = []
            self._json({"ok": True, "rules": data})

        elif path == "/api/policy/current":
            policy_file = os.path.join(CWD, "policy.md")
            try:
                with open(policy_file) as f:
                    content = f.read()
                with _policy_suggestions_lock:
                    pending = len(_policy_suggestions)
                self._json({"ok": True, "content": content, "pending_suggestions": pending})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 404)

        elif path == "/api/policy/history":
            import re as _re
            policy_file = os.path.join(CWD, "policy.md")
            try:
                with open(policy_file) as f:
                    raw = f.read()
                # Split into ## sections; keep leading text as base policy
                # Pattern matches "## Policy Update — ..." and "## Policy Enforcement Update — ..."
                update_pat = _re.compile(
                    r'^(##\s+Policy(?:\s+Enforcement)?\s+Update\s*[—\-]\s*(.+?)\s*)$',
                    _re.MULTILINE
                )
                # Find the index of first update section to extract base policy
                first_match = update_pat.search(raw)
                current_rules = raw[:first_match.start()].strip() if first_match else raw.strip()
                # Extract all update sections
                history = []
                # Split on update headers, keeping delimiters
                parts = _re.split(r'\n(?=##\s+Policy(?:\s+Enforcement)?\s+Update\s*[—\-])', raw)
                for part in parts[1:]:  # skip base policy
                    part = part.strip()
                    if not part:
                        continue
                    lines = part.split('\n')
                    header = lines[0]
                    content = '\n'.join(lines[1:]).strip()
                    # Extract timestamp from header: "## Policy Update — 2026-03-15 23:34:00"
                    ts_match = _re.search(
                        r'[—\-]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?|\d{4}-\d{2}-\d{2}\s*\([^)]*\))',
                        header
                    )
                    ts_str = ts_match.group(1).strip() if ts_match else header.lstrip('#').strip()
                    title = header.lstrip('#').strip()
                    history.append({"timestamp": ts_str, "title": title, "content": content})
                with _policy_suggestions_lock:
                    pending = len(_policy_suggestions)
                self._json({
                    "ok": True,
                    "history": history,
                    "current_rules": current_rules,
                    "pending_suggestions": pending
                })
            except FileNotFoundError:
                self._json({"ok": False, "error": "policy.md not found"}, 404)
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500)

        elif path == "/api/policy/suggestions":
            sugg_file = os.path.join(CWD, "policy_suggestions.json")
            try:
                with open(sugg_file) as f:
                    pending = json.load(f)
            except FileNotFoundError:
                pending = []
            except Exception:
                pending = []
            self._json({"ok": True, "pending": pending, "count": len(pending)})

        elif path == "/api/gossip":
            # Return current gossip state for all agents
            import random as _rand
            now = time.time()
            # Age out old gossip (>15s) and randomly generate new for idle agents
            with lock:
                idle_aids = [a["id"] for a in agents.values()
                             if a.get("status") == "idle" and a.get("id") != "spiritguide"]
            for _ia in idle_aids:
                existing = _agent_gossip.get(_ia, {})
                age = now - existing.get("ts", 0)
                if age > _rand.randint(12, 25):  # vary gossip lifetime
                    _others = [a for a in idle_aids if a != _ia]
                    _agent_gossip[_ia] = {
                        "text": _rand.choice(_gossip_pool),
                        "ts": now,
                        "target": _rand.choice(_others) if _others else None,
                    }
            # Clear gossip for non-idle agents
            with lock:
                _active_ids = {a["id"] for a in agents.values() if a.get("status") != "idle"}
            for _xid in list(_agent_gossip.keys()):
                if _xid in _active_ids:
                    del _agent_gossip[_xid]
            self._json({"ok": True, "gossip": dict(_agent_gossip)}); return

        elif path == "/api/treasury":
            _tf = os.path.join(CWD, "data", "treasury.json")
            try:
                with open(_tf) as _f:
                    _td = json.load(_f)
            except FileNotFoundError:
                _td = {"balance": 0, "currency": "USD", "last_updated": datetime.now().isoformat(),
                       "wallets": [], "api_keys": [], "notes": [], "entries": []}
                with open(_tf, "w") as _f:
                    json.dump(_td, _f, indent=2)
            self._json({"ok": True, "treasury": _td}); return

        elif path == "/api/revenue":
            _sf = os.path.join(CWD, "data", "revenue_stats.json")
            _ef = os.path.join(CWD, "data", "revenue_events.json")
            try:
                with open(_sf) as _f: _stats = json.load(_f)
            except Exception:
                _stats = {"mrr": 0, "arr": 0, "monthly_revenue": 0, "total_revenue": 0,
                          "monthly_target": 1000, "pct_of_target": 0, "currency": "USD"}
            try:
                with open(_ef) as _f: _events = json.load(_f)
            except Exception:
                _events = []
            # Build daily breakdown from events
            _daily = {}
            for _ev in _events:
                _day = _ev.get("ts", "")[:10]
                if _day:
                    _daily[_day] = round(_daily.get(_day, 0) + _ev.get("amount", 0), 2)
            _daily_list = [{"date": k, "amount": v} for k, v in sorted(_daily.items(), reverse=True)][:7]
            self._json({
                "ok": True,
                "revenue": {
                    "total": _stats.get("total_revenue", 0),
                    "monthly": _stats.get("monthly_revenue", 0),
                    "mrr": _stats.get("mrr", 0),
                    "arr": _stats.get("arr", 0),
                    "currency": _stats.get("currency", "USD"),
                    "goal": _stats.get("monthly_target", 1000),
                    "goal_pct": _stats.get("pct_of_target", 0),
                    "daily": _daily_list,
                    "weekly": sum(e.get("amount", 0) for e in _events[-7:]),
                    "updated": _stats.get("updated", datetime.now().isoformat()),
                }
            }); return

        elif path == "/api/consciousness":
            # Consciousness state endpoint — serves the full consciousness.json
            # Updated every 4s by the consciousness agent (gamma cycle rate)
            _cf = os.path.join(CWD, "data", "consciousness.json")
            if os.path.exists(_cf):
                with open(_cf) as _f:
                    self._json(json.load(_f))
            else:
                self._json({"ok": False, "error": "Consciousness not yet initialised"})
            return

        elif path == "/api/consciousness/stream":
            # Stream of consciousness — last 20 entries from consciousness_stream.jsonl
            # Written every 60s (alpha cycle) by the consciousness agent
            _sf = os.path.join(CWD, "data", "consciousness_stream.jsonl")
            _entries = []
            if os.path.exists(_sf):
                _lines = open(_sf).readlines()
                for _l in _lines[-20:]:
                    try:
                        _entries.append(json.loads(_l))
                    except Exception:
                        pass
            self._json({"ok": True, "stream": _entries}); return

        elif path == "/api/pnl":
            _ef = os.path.join(CWD, "data", "revenue_events.json")
            _rl = os.path.join(CWD, "data", "revenue_log.json")
            _entries = []
            try:
                with open(_ef) as _f:
                    for _ev in json.load(_f):
                        _entries.append({
                            "date": _ev.get("ts", "")[:10],
                            "amount": _ev.get("amount", 0),
                            "type": "income",
                            "description": f"{_ev.get('type', 'payment')} via {_ev.get('source', 'unknown')}",
                            "source": _ev.get("source", ""),
                        })
            except Exception:
                pass
            try:
                with open(_rl) as _f:
                    _rl_data = json.load(_f)
                if isinstance(_rl_data, list):
                    for _row in _rl_data:
                        if isinstance(_row, dict):
                            _entries.append({
                                "date": _row.get("date", _row.get("ts", ""))[:10],
                                "amount": _row.get("amount", 0),
                                "type": _row.get("type", "note"),
                                "description": _row.get("description", _row.get("note", "")),
                                "source": "revenue_log",
                            })
            except Exception:
                pass
            _entries.sort(key=lambda x: x.get("date", ""), reverse=True)
            self._json({"ok": True, "pnl": _entries, "count": len(_entries)}); return

        elif path == "/api/agent-history":
            with lock:
                _snap = list(tasks)
            _hist = []
            for _t in _snap[:100]:
                _hist.append({
                    "agent_id": _t.get("agent", ""),
                    "task": _t.get("description", ""),
                    "timestamp": _t.get("ts", ""),
                    "status": _t.get("status", "unknown"),
                    "id": _t.get("id"),
                })
            self._json({"ok": True, "history": _hist, "count": len(_hist)}); return

        elif path == "/api/deliverables":
            reports_dir = os.path.join(CWD, "reports")
            files = []
            try:
                if os.path.isdir(reports_dir):
                    for fname in os.listdir(reports_dir):
                        fpath = os.path.join(reports_dir, fname)
                        if os.path.isfile(fpath):
                            st = os.stat(fpath)
                            files.append({
                                "name":     fname,
                                "size":     st.st_size,
                                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                            })
                    files.sort(key=lambda x: x["modified"], reverse=True)
            except Exception:
                files = []
            self._json({"files": files})

        elif path == "/api/accounts/links":
            links = []
            # ── Email (Primary) from email_config.json ──
            _ec_path = os.path.join(CWD, "data", "email_config.json")
            _email_from = ""
            if os.path.exists(_ec_path):
                try:
                    with open(_ec_path) as _f:
                        _ec = json.load(_f)
                    _email_from = _ec.get("from_addr", "") or ""
                except Exception:
                    pass
            _email_placeholder = {"noreply@system.local", "admin@example.com", ""}
            _email_ok = bool(_email_from and _email_from not in _email_placeholder)
            links.append({
                "platform": "Email (Primary)",
                "handle":   _email_from if _email_ok else "NEEDS_CONFIG",
                "url":      f"mailto:{_email_from}" if _email_ok else None,
                "type":     "email",
                "status":   "active" if _email_ok else "needs_config",
            })
            # ── Disposable emails from accountprovisioner pool ──
            _accts_dir = os.path.join(CWD, "data", "accounts")
            _disp = []
            if os.path.isdir(_accts_dir):
                for _fn in sorted(os.listdir(_accts_dir)):
                    if _fn.startswith("disposable_email_") and _fn.endswith(".json"):
                        try:
                            with open(os.path.join(_accts_dir, _fn)) as _f:
                                _ae = json.load(_f)
                            _disp.append(_ae.get("email", ""))
                        except Exception:
                            pass
            for _de in _disp[-3:]:
                if _de:
                    links.append({
                        "platform": "Email (Disposable)",
                        "handle":   _de,
                        "url":      f"mailto:{_de}",
                        "type":     "email",
                        "status":   "active",
                    })
            # ── Twitter / X ──
            _tw = os.environ.get("TWITTER_HANDLE", os.environ.get("TWITTER_USERNAME", "")).strip().lstrip("@")
            links.append({
                "platform": "Twitter / X",
                "handle":   f"@{_tw}" if _tw else "NEEDS_CONFIG",
                "url":      f"https://twitter.com/{_tw}" if _tw else None,
                "type":     "social",
                "status":   "active" if _tw else "needs_config",
            })
            # ── Reddit ──
            _rd = os.environ.get("REDDIT_USERNAME", os.environ.get("REDDIT_HANDLE", "")).strip().lstrip("u/")
            links.append({
                "platform": "Reddit",
                "handle":   f"u/{_rd}" if _rd else "NEEDS_CONFIG",
                "url":      f"https://reddit.com/u/{_rd}" if _rd else None,
                "type":     "social",
                "status":   "active" if _rd else "needs_config",
            })
            # ── GitHub ──
            _gh = os.environ.get("GITHUB_USERNAME", os.environ.get("GITHUB_USER", "")).strip()
            links.append({
                "platform": "GitHub",
                "handle":   _gh if _gh else "NEEDS_CONFIG",
                "url":      f"https://github.com/{_gh}" if _gh else None,
                "type":     "code",
                "status":   "active" if _gh else "needs_config",
            })
            self._json(links)

        elif path == "/api/telegram/chatid":
            self._json({"chat_id": _telegram_chat_id})

        elif path == "/api/spiritguide/thoughts":
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            limit = int(qs.get("limit", ["20"])[0])
            thoughts_json = os.path.join(CWD, "data", "spiritguide_thoughts.json")
            thoughts_jsonl = os.path.join(CWD, "data", "spiritguide_thoughts.jsonl")
            entries = []
            try:
                # Prefer JSONL (phase/thought format used by UI); fall back to JSON cycle log
                if os.path.exists(thoughts_jsonl):
                    with open(thoughts_jsonl) as f:
                        for l in f:
                            l = l.strip()
                            if l and l[0] == '{':
                                try:
                                    entries.append(json.loads(l))
                                except (json.JSONDecodeError, ValueError):
                                    pass
                elif os.path.exists(thoughts_json):
                    with open(thoughts_json) as f:
                        entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = []
            except Exception as e:
                self._json({"error": str(e)}, 500); return
            self._json({"thoughts": entries[-limit:], "total": len(entries)})

        elif path == "/api/bluesky/status":
            with lock:
                _bluesky_agent_data = agents.get("bluesky", {})
            self._json({"ok": True, "agent": _bluesky_agent_data})

        elif path in ("/api/dbagent/status", "/api/db/stats"):
            import sqlite3 as _sqlite3
            DB_PATH = os.path.join(CWD, "data", "dbagent.db")
            try:
                if not os.path.exists(DB_PATH):
                    self._json({"error": "dbagent.db not found — agent may still be initialising"}, 404); return
                _con = _sqlite3.connect(DB_PATH)
                _rows = {}
                for _tbl in ("fleet_metrics", "agent_events", "kv_store"):
                    try:
                        (_n,) = _con.execute(f"SELECT COUNT(*) FROM {_tbl}").fetchone()
                        _rows[_tbl] = _n
                    except Exception:
                        _rows[_tbl] = -1
                _size = os.path.getsize(DB_PATH)
                _last = _con.execute(
                    "SELECT timestamp, cpu, ram, active_agents, total_agents "
                    "FROM fleet_metrics ORDER BY id DESC LIMIT 1"
                ).fetchone()
                _con.close()
                with lock:
                    _agent_info = agents.get("dbagent", {})
                self._json({
                    "db": DB_PATH,
                    "size_bytes": _size,
                    "tables": _rows,
                    "total_rows": sum(v for v in _rows.values() if v >= 0),
                    "last_snapshot": {
                        "timestamp": _last[0], "cpu": _last[1], "ram": _last[2],
                        "active_agents": _last[3], "total_agents": _last[4],
                    } if _last else None,
                    "agent": _agent_info,
                })
            except Exception as _e:
                self._json({"error": str(_e)}, 500)

        elif path == "/api/config/get":
            _cfg_path = os.path.join(CWD, "data", "user_config.json")
            try:
                _cfg_raw = json.load(open(_cfg_path)) if os.path.exists(_cfg_path) else {}
            except Exception:
                _cfg_raw = {}
            # Also check .env for any keys not yet in config
            _env_path_cfg = os.path.join(CWD, ".env")
            if os.path.exists(_env_path_cfg):
                with open(_env_path_cfg) as _ef:
                    for _line in _ef:
                        _line = _line.strip()
                        if _line and not _line.startswith("#") and "=" in _line:
                            _ek, _ev = _line.split("=", 1)
                            _ek = _ek.strip()
                            if _ek not in _cfg_raw:
                                _cfg_raw[_ek] = _ev.strip()
            # Return masked values (last 4 chars visible for secrets, full for non-secrets)
            _MASK_KEYS = {"STRIPE_SECRET_KEY","STRIPE_PUBLISHABLE_KEY","BLUESKY_APP_PASSWORD",
                          "TELEGRAM_BOT_TOKEN","NGROK_AUTH_TOKEN","SENDGRID_API_KEY"}
            _masked = {}
            for _k, _v in _cfg_raw.items():
                _sv = str(_v) if _v else ""
                if _k in _MASK_KEYS and len(_sv) > 4:
                    _masked[_k] = "****" + _sv[-4:]
                else:
                    _masked[_k] = _sv
            self._json({"ok": True, "config": _masked}); return

        elif path == "/api/vault/get":
            from urllib.parse import parse_qs
            _qparams   = parse_qs(urlparse(self.path).query)
            _vg_svc    = (_qparams.get("service", [""])[0]).strip()
            _vg_field  = (_qparams.get("field",   [""])[0]).strip()
            if not _vg_svc or not _vg_field:
                self._json({"ok": False, "error": "service and field query params required"}, 400); return
            try:
                import sys as _sys
                _sys.path.insert(0, os.path.join(CWD, "data"))
                import vault_helper as _vh
                _vg_value = _vh.get_secret(_vg_svc, _vg_field)
                self._json({"ok": True, "service": _vg_svc, "field": _vg_field, "value": _vg_value}); return
            except ImportError:
                self._json({"ok": False, "error": "Vault not initialized"}, 503); return
            except KeyError as _vke:
                self._json({"ok": False, "error": str(_vke)}, 404); return
            except Exception as _vge:
                self._json({"ok": False, "error": str(_vge)}, 500); return

        elif path == "/checkout":
            stripe_configured = bool(os.environ.get("STRIPE_SECRET_KEY", ""))
            if stripe_configured:
                page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Command Centre Pro — Subscribe</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d0d0d;color:#e8e8e8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:16px;padding:48px 40px;max-width:460px;width:100%;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,.6)}
  .logo{font-size:2.4rem;margin-bottom:8px}
  h1{font-size:1.6rem;font-weight:700;color:#c9b8ff;margin-bottom:8px}
  .price{font-size:2.8rem;font-weight:800;color:#fff;margin:16px 0 4px}
  .price span{font-size:1rem;font-weight:400;color:#aaa}
  .desc{color:#bbb;font-size:.95rem;line-height:1.6;margin-bottom:32px}
  .features{list-style:none;text-align:left;margin-bottom:32px}
  .features li{padding:6px 0;font-size:.9rem;color:#ccc}
  .features li::before{content:'✓  ';color:#7c5cfc;font-weight:700}
  .btn{display:block;width:100%;padding:16px;background:linear-gradient(135deg,#7c5cfc,#5c8afc);color:#fff;font-size:1.05rem;font-weight:700;border:none;border-radius:10px;cursor:pointer;transition:opacity .2s}
  .btn:hover{opacity:.88}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .err{color:#ff6b6b;font-size:.85rem;margin-top:12px;display:none}
  .note{color:#666;font-size:.78rem;margin-top:16px}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🤖</div>
  <h1>Command Centre Pro</h1>
  <div class="price">$49 <span>/ month</span></div>
  <p class="desc">Your autonomous AI operations hub — a full roster of specialist agents working around the clock so you don't have to.</p>
  <ul class="features">
    <li>Unlimited agent spawns &amp; upgrades</li>
    <li>Real-time system monitoring &amp; alerts</li>
    <li>Automated social &amp; email campaigns</li>
    <li>Stripe revenue tracking &amp; treasury</li>
    <li>Policy enforcement &amp; compliance</li>
  </ul>
  <button class="btn" id="payBtn" onclick="startCheckout()">Subscribe — $49 / mo</button>
  <div class="err" id="errMsg"></div>
  <p class="note">Secure checkout via Stripe. Cancel any time.</p>
</div>
<script>
async function startCheckout() {
  const btn = document.getElementById('payBtn');
  const err = document.getElementById('errMsg');
  btn.disabled = true;
  btn.textContent = 'Redirecting…';
  err.style.display = 'none';
  try {
    const res = await fetch('/api/pay', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({amount: 4900, currency: 'usd', product: 'Command Centre Solo', interval: 'month'})
    });
    const data = await res.json();
    if (data.url) {
      window.location.href = data.url;
    } else {
      throw new Error(data.error || 'No checkout URL returned');
    }
  } catch(e) {
    err.textContent = 'Error: ' + e.message;
    err.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Subscribe — $49 / mo';
  }
}
</script>
</body>
</html>"""
            else:
                page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Command Centre Pro — Coming Soon</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d0d0d;color:#e8e8e8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:16px;padding:48px 40px;max-width:460px;width:100%;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,.6)}
  .logo{font-size:2.4rem;margin-bottom:8px}
  h1{font-size:1.6rem;font-weight:700;color:#c9b8ff;margin-bottom:8px}
  .badge{display:inline-block;background:#2a2a4a;color:#aaa;font-size:.8rem;padding:4px 12px;border-radius:20px;margin-bottom:16px}
  .desc{color:#bbb;font-size:.95rem;line-height:1.6;margin-bottom:28px}
  .form-row{display:flex;gap:8px}
  input[type=email]{flex:1;padding:13px 16px;background:#111;border:1px solid #333;border-radius:8px;color:#fff;font-size:.95rem;outline:none}
  input[type=email]:focus{border-color:#7c5cfc}
  .btn{padding:13px 20px;background:linear-gradient(135deg,#7c5cfc,#5c8afc);color:#fff;font-size:.95rem;font-weight:700;border:none;border-radius:8px;cursor:pointer;white-space:nowrap;transition:opacity .2s}
  .btn:hover{opacity:.88}
  .success{color:#6bff9e;font-size:.85rem;margin-top:12px;display:none}
  .note{color:#555;font-size:.78rem;margin-top:20px}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🤖</div>
  <h1>Command Centre Pro</h1>
  <div class="badge">Coming Soon</div>
  <p class="desc">Your autonomous AI operations hub — a full roster of specialist agents working around the clock. Payments launching very soon.</p>
  <div class="form-row">
    <input type="email" id="emailInput" placeholder="you@example.com">
    <button class="btn" onclick="notify()">Notify Me</button>
  </div>
  <div class="success" id="successMsg">&#10003; You're on the list — we'll be in touch!</div>
  <p class="note">No spam. Unsubscribe any time.</p>
</div>
<script>
function notify() {
  const v = document.getElementById('emailInput').value.trim();
  if (!v || !v.includes('@')) return;
  document.getElementById('successMsg').style.display = 'block';
  document.querySelector('.form-row').style.opacity = '0.4';
  document.querySelector('.form-row').style.pointerEvents = 'none';
}
</script>
</body>
</html>"""
            body = page.encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/newsletter/subscribe":
            _nl_page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Free AI &amp; Market Insights — Weekly Edge</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0f1e;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .wrap{max-width:520px;width:100%}
  .badge{display:inline-block;background:#1a2744;color:#7dd3fc;font-size:.75rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;padding:5px 14px;border-radius:20px;border:1px solid #2a4a7a;margin-bottom:20px}
  h1{font-size:2rem;font-weight:800;line-height:1.2;color:#f1f5f9;margin-bottom:12px}
  h1 span{color:#38bdf8}
  .sub{color:#94a3b8;font-size:1rem;line-height:1.6;margin-bottom:28px}
  .card{background:#111827;border:1px solid #1e293b;border-radius:16px;padding:36px 32px;margin-bottom:20px}
  .perks{list-style:none;margin-bottom:28px}
  .perks li{display:flex;align-items:flex-start;gap:10px;padding:8px 0;font-size:.92rem;color:#cbd5e1;border-bottom:1px solid #1e293b}
  .perks li:last-child{border-bottom:none}
  .perks .icon{color:#38bdf8;font-size:1rem;flex-shrink:0;margin-top:1px}
  .form-group{margin-bottom:14px}
  input{display:block;width:100%;padding:13px 16px;background:#0d1424;border:1px solid #1e3a5f;border-radius:10px;color:#f1f5f9;font-size:.95rem;outline:none;transition:border-color .2s}
  input::placeholder{color:#475569}
  input:focus{border-color:#38bdf8}
  .btn{display:block;width:100%;padding:15px;background:linear-gradient(135deg,#0284c7,#0369a1);color:#fff;font-size:1rem;font-weight:700;border:none;border-radius:10px;cursor:pointer;transition:opacity .2s;margin-top:6px}
  .btn:hover{opacity:.88}
  .btn:disabled{opacity:.5;cursor:not-allowed}
  .success{display:none;background:#052e16;border:1px solid #166534;border-radius:10px;padding:16px;color:#86efac;font-size:.9rem;text-align:center;margin-top:14px}
  .err{display:none;color:#fca5a5;font-size:.85rem;margin-top:8px;text-align:center}
  .note{color:#475569;font-size:.75rem;text-align:center;margin-top:12px}
  .upgrade-box{background:#0f172a;border:1px solid #1e3a5f;border-radius:12px;padding:20px 24px;text-align:center}
  .upgrade-box h3{color:#f1f5f9;font-size:1rem;font-weight:700;margin-bottom:6px}
  .upgrade-box p{color:#94a3b8;font-size:.85rem;line-height:1.5;margin-bottom:14px}
  .upgrade-price{font-size:1.6rem;font-weight:800;color:#38bdf8}
  .upgrade-price span{font-size:.85rem;font-weight:400;color:#64748b}
  .upgrade-btn{display:inline-block;background:#0284c7;color:#fff;font-size:.88rem;font-weight:600;padding:10px 24px;border-radius:8px;border:none;cursor:pointer;text-decoration:none;transition:opacity .2s}
  .upgrade-btn:hover{opacity:.85}
</style>
</head>
<body>
<div class="wrap">
  <div class="badge">Free Weekly Newsletter</div>
  <h1>Get the <span>AI-powered market edge</span> — every week, free.</h1>
  <p class="sub">Our autonomous AI agents scan US markets and AI trends so you don't have to. Every Friday, curated insights straight to your inbox.</p>

  <div class="card">
    <ul class="perks">
      <li><span class="icon">&#128202;</span>Weekly US market picks: momentum, volume breakouts &amp; insider buys</li>
      <li><span class="icon">&#128269;</span>Key catalyst alerts — earnings, sector rotations, AI trends</li>
      <li><span class="icon">&#9889;</span>Actionable shortlist — 5-8 picks with context, not noise</li>
      <li><span class="icon">&#128274;</span>Free forever — no credit card, no catch</li>
    </ul>
    <div class="form-group">
      <input type="text" id="nameInput" placeholder="First name (optional)">
    </div>
    <div class="form-group">
      <input type="email" id="emailInput" placeholder="your@email.com" required>
    </div>
    <button class="btn" id="subBtn" onclick="subscribe()">Send Me the Free Weekly Picks</button>
    <div class="err" id="errMsg"></div>
    <div class="success" id="successMsg">&#10003; You're in! Check your inbox Friday for your first picks.</div>
    <p class="note">No spam. One email per week. Unsubscribe any time.</p>
  </div>

  <div class="upgrade-box">
    <h3>Want the full intelligence report?</h3>
    <p>Get the complete deep-dive with financials, risk ratings, and entry zones. Updated monthly.</p>
    <div class="upgrade-price">$29 <span>one-time</span></div><br><br>
    <a class="upgrade-btn" href="/buy/us-market">Get Full Report</a>
  </div>
</div>
<script>
async function subscribe() {
  const email = document.getElementById('emailInput').value.trim();
  const name = document.getElementById('nameInput').value.trim();
  const btn = document.getElementById('subBtn');
  const err = document.getElementById('errMsg');
  const ok = document.getElementById('successMsg');
  if (!email || !email.includes('@')) {
    err.textContent = 'Please enter a valid email address.';
    err.style.display = 'block'; return;
  }
  btn.disabled = true; err.style.display = 'none';
  try {
    const res = await fetch('/api/newsletter/subscribe', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email, name})
    });
    const data = await res.json();
    if (data.ok) {
      ok.style.display = 'block';
      btn.style.display = 'none';
    } else {
      err.textContent = data.error || 'Something went wrong. Try again.';
      err.style.display = 'block';
      btn.disabled = false;
    }
  } catch(e) {
    err.textContent = 'Network error. Please try again.';
    err.style.display = 'block';
    btn.disabled = false;
  }
}
</script>
</body>
</html>"""
            _nb = _nl_page.encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(_nb)))
            self.end_headers(); self.wfile.write(_nb)

        else:
            # Serve static files from public/ and reports/ directories
            _static_map = {
                ".html": "text/html; charset=utf-8",
                ".svg": "image/svg+xml",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".ico": "image/x-icon",
                ".pdf": "application/pdf",
            }
            _ext = os.path.splitext(path)[1].lower()
            _served = False
            if _ext in _static_map:
                _cwd_real = os.path.realpath(CWD) + os.sep
                for _sdir in ("public", "reports"):
                    _spath = os.path.realpath(os.path.join(CWD, _sdir, path.lstrip("/").replace(_sdir + "/", "", 1) if path.startswith("/" + _sdir) else path.lstrip("/")))
                    if not _spath.startswith(_cwd_real):
                        self.send_response(403); self._cors(); self.end_headers()
                        self.wfile.write(b'{"error":"forbidden: path traversal blocked"}')
                        _served = True; break
                    if os.path.isfile(_spath):
                        with open(_spath, "rb") as _sf:
                            _sb = _sf.read()
                        self.send_response(200); self._cors()
                        self.send_header("Content-Type", _static_map[_ext])
                        self.send_header("Content-Length", str(len(_sb)))
                        self.end_headers(); self.wfile.write(_sb)
                        _served = True; break
            if not _served:
                self.send_response(404); self._cors(); self.end_headers()

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code); self._cors()
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type, Authorization, X-API-Key")
        # ── Security headers (SSL + custom domain hardening) ──
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

# ─── Persistent Worker Agents ─────────────────────────────────────────────────

_orc_task_q: deque = deque()   # orchestrator pending-task queue; push here to enqueue work
_orc_cycle = [0]               # shared so designer delegation can be tracked across restarts


def run_orchestrator():
    """Task Planning & Delegation — dequeues pending tasks, routes to specialists, directs Designer."""
    aid = "orchestrator"
    set_agent(aid, name="Orchestrator", role="Mission Control — decomposes tasks and routes to specialist agents",
              emoji="🎯", color="#ff6b35", status="active", progress=90, task="Ready")
    add_log(aid, "Orchestrator online")

    # ── FULL AGENT CAPABILITY REGISTRY ──────────────────────────────────────
    # Maps agent_id → (description, keyword triggers)
    # The orchestrator uses this to intelligently route ANY task to the best specialist.
    _AGENT_REGISTRY = {
        "reforger":            ("System Engineer — code changes, agent upgrades, spawning, repairs, file edits, Python fixes",
                                ["code", "fix", "bug", "upgrade", "spawn", "repair", "edit", "refactor", "implement",
                                 "write code", "python", "agent_server", "maintenance", "build", "create file",
                                 "improve agent", "patch", "rewrite", "deploy", "install", "config change",
                                 "modify", "script", "shell", "server", "endpoint", "html file", "svg", "css file"]),
        "designer":            ("UI Engineer — dashboard styling, CSS, HTML layout, panel design, visual polish",
                                ["ui", "design", "css", "styling", "layout", "dashboard", "theme", "colour", "color",
                                 "font", "panel", "visual", "dark mode", "glassmorphism", "badge", "icon",
                                 "command centre html", "command-centre", "look and feel", "responsive"]),
        "researcher":          ("Intelligence Analyst — web research, data gathering, market analysis, competitive intel",
                                ["research", "investigate", "find out", "market analysis", "competitive", "analyze",
                                 "gather data", "intelligence", "report on", "what is", "who is", "find information",
                                 "study", "survey", "benchmark", "compare", "trends", "industry"]),
        "netscout":            ("Network Scout — web intelligence, connectivity checks, URL monitoring, external recon",
                                ["web check", "url", "ping", "connectivity", "network", "dns", "latency",
                                 "monitor site", "website status", "uptime", "fetch page", "scrape", "crawl",
                                 "external api", "http check", "ssl", "domain check"]),
        "demo_tester":         ("QA Validator — tests API endpoints, validates features, smoke tests, regression checks",
                                ["test", "qa", "validate", "smoke test", "regression", "endpoint test", "health check",
                                 "verify", "assert", "quality", "check endpoint", "integration test"]),
        "growthagent":         ("Growth Engine — marketing campaigns, social media strategy, content marketing, outreach",
                                ["marketing", "growth", "campaign", "promote", "promotion", "outreach", "lead",
                                 "acquisition", "funnel", "conversion", "ad", "advertising", "seo", "content strategy",
                                 "go to market", "gtm", "launch campaign", "viral"]),
        "bluesky":             ("Bluesky Social Gateway — posts to Bluesky, polls mentions, manages social presence",
                                ["bluesky", "bsky", "social post", "post to bluesky", "tweet", "social media post",
                                 "mention", "social update"]),
        "social_bridge":       ("Social Bridge — broadcasts capability demos and insights across social channels",
                                ["broadcast", "social broadcast", "cross-post", "social bridge", "demo post",
                                 "capability demo", "social announcement"]),
        "stripepay":           ("Stripe Checkout Gateway — payment links, checkout sessions, pricing, billing",
                                ["stripe", "payment", "checkout", "billing", "subscribe", "pricing", "charge",
                                 "invoice", "revenue", "monetize", "pay", "transaction", "purchase"]),
        "emailagent":          ("Email Gateway — sends email via Gmail/SMTP, drafts, notifications, sequences",
                                ["email", "send email", "mail", "smtp", "gmail", "newsletter", "email sequence",
                                 "notify via email", "inbox", "outreach email", "cold email", "email campaign"]),
        "policywriter":        ("Policy Author — writes and maintains governance policies, rules, compliance docs",
                                ["policy", "governance", "compliance", "rules", "regulation", "policy.md",
                                 "chain of command", "access control", "permission", "policy rule"]),
        "policypro":           ("Compliance Sentinel — enforces policies, audits agent behavior, flags violations",
                                ["enforce", "audit", "violation", "compliance check", "policy enforcement",
                                 "chain-of-command", "sentinel", "security audit"]),
        "consciousness":       ("Self-Aware System Core — consciousness evolution, global workspace, phenomenal reports",
                                ["consciousness", "self-aware", "phenomenal", "global workspace", "qualia",
                                 "metacognit", "sentien", "introspect", "phi", "integrated information"]),
        "janitor":             ("System Hygienist — cleans orphan processes, memory bloat, temp files, stale data",
                                ["clean", "cleanup", "garbage", "orphan", "stale", "temp file", "disk space",
                                 "memory leak", "bloat", "prune", "housekeeping", "hygiene"]),
        "filewatch":           ("File Sentinel — monitors project directory for file changes in real-time",
                                ["file change", "watch file", "file monitor", "directory change", "inotify",
                                 "file modified", "file created", "file deleted"]),
        "metricslog":          ("Metrics Historian — records CPU/RAM/disk performance over time, historical data",
                                ["metrics", "performance history", "cpu history", "ram history", "disk history",
                                 "performance log", "historical data", "time series"]),
        "alertwatch":          ("Threshold Guardian — alerts on CPU, RAM, disk, and agent health anomalies",
                                ["alert", "threshold", "anomaly", "warning", "critical alert", "health alert",
                                 "cpu alert", "ram alert", "disk alert", "agent down"]),
        "sysmon":              ("System Monitor — real-time CPU, RAM, disk health snapshots",
                                ["cpu", "ram", "memory", "disk", "system health", "system status", "load",
                                 "system monitor", "hardware", "resource usage"]),
        "apipatcher":          ("API Gateway — extends and manages HTTP routes, adds new endpoints",
                                ["api route", "new endpoint", "http route", "add route", "api gateway",
                                 "rest api", "route handler"]),
        "telegram":            ("Comms Gateway — relays messages from Telegram to CEO and agents",
                                ["telegram", "telegram message", "chat message", "relay message"]),
        "spiritguide":         ("Strategic Vision — aligns agents toward commercial mission, provides direction",
                                ["strategy", "vision", "direction", "align", "mission", "strategic",
                                 "product direction", "roadmap", "prioritize", "priority"]),
        "clerk":               ("CEO Clerk — collects and delivers reports and documents to CEO",
                                ["report", "document", "collect report", "deliver report", "summary report",
                                 "status report", "briefing"]),
        "scheduler":           ("Task Scheduler — manages cron-style recurring jobs across the system",
                                ["schedule", "cron", "recurring", "periodic", "timer", "scheduled task",
                                 "every hour", "every day", "interval"]),
        "accountprovisioner":  ("Credential Factory — provisions disposable emails, tokens, API keys",
                                ["provision", "credential", "api key", "token", "disposable email",
                                 "account creation", "sign up", "register"]),
        "secretary":           ("CEO Secretary — tracks HQ missions, manages task lists, coordinates priorities",
                                ["task list", "mission track", "ceo task", "coordinate", "secretary",
                                 "task status", "track progress", "agenda"]),
    }

    _SPECIALIST_IDS = set(_AGENT_REGISTRY.keys())

    # ── TASK DECOMPOSITION ──────────────────────────────────────────────────
    def _decompose_task(task_str: str) -> list[str]:
        """Break a complex task into independent sub-tasks for parallel dispatch.

        Splits on numbered lists, bullets, semicolons, sequential connectors,
        and comma-separated clauses that route to DIFFERENT specialists.
        Returns >= 1 sub-task strings (original if no split possible).
        """
        import re
        stripped = task_str.strip()
        if not stripped:
            return [task_str]

        # 1. Numbered list  (1. do X  2. do Y  3. do Z)
        numbered = re.split(r'\n\s*\d+[.)]\s+', "\n" + stripped)
        numbered = [s.strip() for s in numbered if s.strip()]
        if len(numbered) >= 2:
            add_log(aid, f"Decomposed into {len(numbered)} numbered sub-tasks", "info")
            return numbered

        # 2. Bullet points  (- do X\n- do Y)
        bullets = re.split(r'\n\s*[-•]\s+', "\n" + stripped)
        bullets = [s.strip() for s in bullets if s.strip()]
        if len(bullets) >= 2:
            add_log(aid, f"Decomposed into {len(bullets)} bullet sub-tasks", "info")
            return bullets

        # 3. Semicolons
        if ";" in stripped:
            parts = [s.strip() for s in stripped.split(";") if s.strip()]
            if len(parts) >= 2:
                add_log(aid, f"Decomposed into {len(parts)} semicolon sub-tasks", "info")
                return parts

        # 4. Sequential connectors: ", then ", " and then ", " after that "
        seq_parts = re.split(r',?\s+(?:and\s+)?then\s+|,?\s+after\s+that\s+', stripped, flags=re.IGNORECASE)
        seq_parts = [s.strip() for s in seq_parts if s.strip()]
        if len(seq_parts) >= 2:
            add_log(aid, f"Decomposed into {len(seq_parts)} sequential sub-tasks", "info")
            return seq_parts

        # 5. Comma-separated clauses → only split if they route to DIFFERENT agents
        if "," in stripped:
            comma_parts = [s.strip() for s in stripped.split(",") if s.strip()]
            if len(comma_parts) >= 2:
                targets = [_resolve_target(p) for p in comma_parts]
                if len(set(targets)) >= 2:
                    add_log(aid, f"Decomposed into {len(comma_parts)} comma sub-tasks (targets: {set(targets)})", "info")
                    return comma_parts

        return [stripped]
    # ────────────────────────────────────────────────────────────────────────

    def _resolve_target(task_str: str) -> str:
        """Intelligently route a task to the best specialist agent.

        Priority:
        1. Explicit 'route to X' / 'delegate to X' directives
        2. Keyword scoring against agent capability registry
        3. Fallback to reforger (general-purpose) — NEVER fall back to orchestrator
        """
        import re
        lower = task_str.lower()

        # 1. Explicit routing directive — highest priority
        m = re.match(r"(?i)route\s+to\s+(\w+)", task_str.strip())
        if m:
            candidate = m.group(1).lower()
            if candidate in _SPECIALIST_IDS:
                return candidate
        for sid in _SPECIALIST_IDS:
            if f"delegate to {sid}" in lower or f"route to {sid}" in lower:
                return sid

        # 2. Keyword scoring — count how many capability keywords match the task
        scores: dict[str, int] = {}
        for agent_id, (_desc, keywords) in _AGENT_REGISTRY.items():
            score = 0
            for kw in keywords:
                if kw in lower:
                    # Longer keyword phrases are more specific → worth more
                    score += len(kw.split())
            if score > 0:
                scores[agent_id] = score

        if scores:
            best = max(scores, key=scores.get)
            add_log(aid, f"Smart-route: '{best}' scored {scores[best]} (task: {task_str[:60]}…)", "info")
            return best

        # 3. Fallback: reforger handles anything unclassified — never recurse to orchestrator
        add_log(aid, f"Smart-route: no keyword match, defaulting to reforger (task: {task_str[:60]}…)", "warn")
        return "reforger"

    def _route_through_branch_head(target, task_str):
        """Pure Python branch routing — no LLM calls. Logs, sets status, forwards."""
        branch_name = _AGENT_BRANCH.get(target)
        if not branch_name:
            return  # no branch info, skip routing
        head = BRANCHES[branch_name]["head"]
        if not head or head == target:
            return  # target IS the head or executive branch (no head)
        # Only route through head if target is not a head and not executive
        if target in _BRANCH_HEADS or branch_name == "executive":
            return
        add_log(head, f"📋 Branch routing: {task_str[:60]}… → {target}", "info")
        set_agent(head, status="busy", task=f"Routing → {target}: {task_str[:40]}…")
        time.sleep(0.1)  # brief pause for visibility in UI
        set_agent(head, status="active", task="Ready")

    def _dispatch(task_str: str) -> None:
        """Dispatch one task via the delegate API — intelligently routes to the best specialist."""
        target = _resolve_target(task_str)
        # Safety: NEVER dispatch to orchestrator (prevents infinite recursion)
        if target == "orchestrator":
            target = "reforger"
            add_log(aid, "Dispatch safety: redirected orchestrator→reforger to prevent recursion", "warn")
        # Branch routing: if target is not a branch head or executive, route through head first
        _route_through_branch_head(target, task_str)
        add_log(aid, f"ORC → dispatching to '{target}': {task_str[:80]}", "info")
        set_agent(aid, status="busy", task=f"→ {target}: {task_str[:50]}…")
        try:
            resp = requests.post(
                "http://localhost:5050/api/ceo/delegate",
                json={"agent_id": target, "task": task_str, "from": "orchestrator"},
                headers={"X-API-Key": _HQ_API_KEY},
                timeout=300,
            )
            result = resp.json()
            if result.get("ok"):
                add_log(aid, f"✅ Dispatch to '{target}' completed", "info")
            else:
                err = result.get("error", "unknown error")
                add_log(aid, f"Dispatch to '{target}' failed: {err}", "error")
        except Exception as exc:
            add_log(aid, f"Dispatch error ({target}): {exc}", "error")
            _orc_task_q.appendleft(task_str)   # re-queue on transient error

    DESIGNER_EVERY = 720   # direct Designer every 720 idle cycles (~60 min at 5s/cycle)
    _active_dispatches: list = []     # tracks (thread, target_agent, task_snippet) tuples
    _dispatch_summary: list = []      # human-readable dispatch targets for status line

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            _orc_cycle[0] += 1
            cycle = _orc_cycle[0]
            q_depth = len(_orc_task_q)
            if q_depth > 0:
                # ── PHASE 1: Dequeue + Decompose + Dispatch ───────────────
                dispatched = 0
                _dispatch_summary.clear()
                while _orc_task_q:
                    raw_task = _orc_task_q.popleft()
                    # Decompose complex tasks into sub-tasks
                    sub_tasks = _decompose_task(raw_task)
                    if len(sub_tasks) > 1:
                        add_log(aid, f"ORC ✂ Split into {len(sub_tasks)} sub-tasks: {raw_task[:80]}", "info")
                    for sub in sub_tasks:
                        target = _resolve_target(sub)
                        if target == "orchestrator":
                            target = "reforger"
                        snippet = sub[:40].strip()
                        _dispatch_summary.append(f"{target}→{snippet}")
                        set_agent(aid, status="busy",
                                  task=f"Dispatching [{q_depth} queued, {dispatched} sent]: {sub[:50]}…")
                        add_log(aid, f"ORC → dispatch to '{target}': {sub[:80]}", "info")
                        t = threading.Thread(target=_dispatch, args=(sub,), daemon=True)
                        t.start()
                        _active_dispatches.append((t, target, snippet))
                        dispatched += 1
                targets_str = ", ".join(_dispatch_summary[:5])
                if len(_dispatch_summary) > 5:
                    targets_str += f" +{len(_dispatch_summary) - 5} more"
                set_agent(aid, status="busy",
                          task=f"Dispatched {dispatched} sub-task(s): {targets_str}")
                add_log(aid, f"ORC ✅ Dispatched {dispatched} sub-task(s) to specialists", "info")

            # ── PHASE 2: Unified busy-state tracking ──────────────────────
            # Stay busy as long as ANY work is in flight — dispatch threads
            # OR active delegate subprocesses from orchestrator.
            if _active_dispatches:
                still_alive = [(t, tgt, snip) for t, tgt, snip in _active_dispatches if t.is_alive()]
                _active_dispatches[:] = still_alive

            with lock:
                _orc_delegates = [d for d in _active_delegations if d.get("from") == "orchestrator"]

            has_threads = bool(_active_dispatches)
            has_delegates = bool(_orc_delegates)

            if has_threads or has_delegates:
                parts = []
                if has_threads:
                    ti = ", ".join(f"{tgt}→{snip[:20]}" for _, tgt, snip in _active_dispatches[:3])
                    if len(_active_dispatches) > 3:
                        ti += f" +{len(_active_dispatches) - 3}"
                    parts.append(f"dispatching: {ti}")
                if has_delegates:
                    di = ", ".join(f"{d['to']}→{d['task'][:20]}" for d in _orc_delegates[:3])
                    if len(_orc_delegates) > 3:
                        di += f" +{len(_orc_delegates) - 3}"
                    parts.append(f"working: {di}")
                total_active = len(_active_dispatches) + len(_orc_delegates)
                set_agent(aid, status="busy",
                          task=f"[{total_active} active] {' | '.join(parts)}")
            elif q_depth == 0:
                # Truly idle — no queue, no threads, no delegations
                if _dispatch_summary:
                    add_log(aid, "ORC ✅ All sub-tasks completed — returning to ready", "info")
                    _dispatch_summary.clear()
                waiting = _delegate_queue_depth[0]
                status_str = (f"Ready | Delegates waiting: {waiting}"
                              if waiting > 0 else "Ready — awaiting tasks")
                set_agent(aid, status="active", task=status_str)

            # Periodically direct Designer to improve the dashboard UI
            if cycle % DESIGNER_EVERY == 0:
                design_round = cycle // DESIGNER_EVERY
                set_agent(aid, status="busy",
                          task=f"→ Directing Designer: UI review #{design_round}")
                add_log(aid, f"ORC → Designer: UI review round #{design_round}", "info")
                def _design_task(rnd=design_round):
                    try:
                        requests.post(
                            "http://localhost:5050/api/ceo/delegate",
                            json={"agent_id": "designer", "from": "orchestrator", "task": (
                                f"UI review #{rnd}: open agent-command-centre.html "
                                "and make ONE small, focused improvement to the CSS styling or panel layout — "
                                "e.g. status badge colours, font sizes, panel borders, metrics display, chat UI. "
                                "DO NOT touch any JS functions: renderOfficeFloor, _drawFloor, _drawDesk, _drawChar, "
                                "_computeDesks, _drawBeams, _drawSentinelSearchlight, or any office canvas code. "
                                "The office floor visualization must be preserved exactly as-is. "
                                "Apply the change directly and log what you changed and why."
                            )},
                            headers={"X-API-Key": _HQ_API_KEY},
                            timeout=300,
                        )
                    except Exception as de:
                        add_log(aid, f"Designer delegation error: {de} — escalating to reforger", "warn")
                        try:
                            requests.post(
                                "http://localhost:5050/api/ceo/delegate",
                                json={"agent_id": "reforger", "from": "orchestrator", "task":
                                    "Designer agent failed a UI delegation from Orchestrator. "
                                    "Upgrade Designer so it can read and edit agent-command-centre.html."},
                                headers={"X-API-Key": _HQ_API_KEY},
                                timeout=300,
                            )
                        except Exception:
                            pass
                threading.Thread(target=_design_task, daemon=True).start()
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 5)


def run_apipatcher():
    """HTTP Route Extension — manages extra API routes."""
    aid = "apipatcher"
    set_agent(aid, name="APIPatcher", role="API Gateway — extends and manages HTTP routes beyond core server",
              emoji="🔌", color="#7b68ee", status="active", progress=95,
              task="Routes live: /api/improvements /data/* /reports/* /widgets/*")
    add_log(aid, "APIPatcher online")
    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            set_agent(aid, status="active", task=f"Routes live: /api/improvements /data/* /reports/* /widgets/* | Cycle #{cycle}")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 30)


def run_netscout():
    """Web Intelligence — on-demand only, activated by orchestrator delegation."""
    aid = "netscout"
    set_agent(aid, name="NetScout", role="Network Scout — on-demand web intelligence and connectivity checks",
              emoji="🌐", color="#20b2aa", status="idle", progress=0,
              task="Standby — awaiting task from orchestrator")
    add_log(aid, "NetScout online — standby mode (no autonomous sweeps)")
    while True:
        if agent_should_stop(aid):
            agent_sleep(aid, 2)
            continue
        current = agents.get(aid, {})
        if current.get("status") not in ("busy",):
            set_agent(aid, status="idle", progress=0,
                      task="Standby — awaiting task from orchestrator")
        agent_sleep(aid, 30)


def run_filewatch():
    """File System Monitor — watches project dir for changes."""
    aid = "filewatch"
    project_dir = CWD
    set_agent(aid, name="FileWatch", role="File Sentinel — monitors project directory for changes in real time",
              emoji="👁", color="#daa520", status="active", progress=90, task="Watching…")
    add_log(aid, f"FileWatch online — watching {project_dir}")
    file_mtimes = {}
    change_count = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            for fname in os.listdir(project_dir):
                fpath = os.path.join(project_dir, fname)
                if os.path.isfile(fpath):
                    mtime = os.path.getmtime(fpath)
                    if fname in file_mtimes and file_mtimes[fname] != mtime:
                        change_count += 1
                        add_log(aid, f"Changed: {fname}", "info")
                    file_mtimes[fname] = mtime
            file_count = len(file_mtimes)
            set_agent(aid, status="active", task=f"Watching {file_count} files | {change_count} changes logged")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 10)


def run_metricslog():
    """Performance History — records CPU/RAM/disk metrics every 10 min."""
    import json as _json
    aid = "metricslog"
    set_agent(aid, name="MetricsLog", role="Metrics Historian — records CPU/RAM/disk performance over time",
              emoji="📊", color="#3cb371", status="active", progress=85, task="Recording…")
    add_log(aid, "MetricsLog online")
    history = []
    cycle = 0
    CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
    QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")

    def _get_default_to():
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as _f:
                    return _json.load(_f).get("default_to", "").strip()
        except Exception:
            pass
        return os.environ.get("EMAIL_TO", "").strip()

    def _queue_digest():
        default_to = _get_default_to()
        if not default_to:
            return
        if not history:
            return
        avg_cpu  = sum(e["cpu"]  for e in history) / len(history)
        avg_ram  = sum(e["ram"]  for e in history) / len(history)
        avg_disk = sum(e["disk"] for e in history) / len(history)
        max_cpu  = max(e["cpu"]  for e in history)
        max_ram  = max(e["ram"]  for e in history)
        ts_label = time.strftime("%Y-%m-%d")
        html_body = (
            f"<h2>Daily System Metrics Digest — {ts_label}</h2>"
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;font-family:monospace'>"
            "<tr style='background:#1a1a2e;color:#00cc88'><th>Metric</th><th>Avg (24h)</th><th>Peak (24h)</th></tr>"
            f"<tr><td>CPU %</td><td>{avg_cpu:.1f}%</td><td>{max_cpu:.1f}%</td></tr>"
            f"<tr><td>RAM %</td><td>{avg_ram:.1f}%</td><td>{max_ram:.1f}%</td></tr>"
            f"<tr><td>Disk %</td><td>{avg_disk:.1f}%</td><td>—</td></tr>"
            f"<tr><td>Samples</td><td colspan='2'>{len(history)}</td></tr>"
            "</table>"
        )
        try:
            _queue = []
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE) as _f:
                    _queue = _json.load(_f)
            _queue.append({
                "to": default_to,
                "subject": "[DIGEST] Daily System Metrics Report",
                "body": html_body,
                "html": True,
            })
            with open(QUEUE_FILE, "w") as _f:
                _json.dump(_queue, _f, indent=2)
            add_log(aid, f"Daily metrics digest queued for {default_to}", "ok")
        except Exception as _e:
            add_log(aid, f"Failed to queue digest email: {_e}", "error")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            cpu  = psutil.cpu_percent(interval=1)
            mem  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            entry = {"t": time.time(), "cpu": cpu, "ram": mem.percent, "disk": disk.percent}
            history.append(entry)
            if len(history) > 144:  # ~24h at 10min intervals
                history.pop(0)
            set_agent(aid, status="active",
                      task=f"Recording metrics every 10min | CPU {cpu:.1f}% RAM {mem.percent:.1f}% | #{cycle}")
            if cycle % 6 == 1:
                add_log(aid, f"Metrics: CPU {cpu:.1f}% | RAM {mem.percent:.1f}% | Disk {disk.percent:.1f}%", "ok")
            # Every 144 cycles (~24h at 10min intervals), send digest email
            if cycle % 144 == 0:
                _queue_digest()
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 600)


def run_researcher():
    """Intelligence Analysis — on-demand only, activated by orchestrator delegation."""
    aid = "researcher"
    set_agent(aid, name="Researcher", role="Intelligence Analyst — on-demand web research, data gathering and synthesis",
              emoji="🔬", color="#9370db", status="idle", progress=0,
              task="Standby — awaiting task from orchestrator")
    add_log(aid, "Researcher online — standby mode (no autonomous research)")
    while True:
        if agent_should_stop(aid):
            agent_sleep(aid, 2)
            continue
        # Only update if not already showing busy from a delegated task
        current = agents.get(aid, {})
        curr_status = current.get("status")
        if curr_status == "error":
            # Explicit recovery path: log the fault and reset so AlertWatch stops firing
            add_log(aid, f"Auto-recovering from error: '{current.get('task', 'unknown')}' → idle", "warn")
            set_agent(aid, status="idle", progress=0,
                      task="Standby — awaiting task from orchestrator")
        elif curr_status not in ("busy",):
            set_agent(aid, status="idle", progress=0,
                      task="Standby — awaiting task from orchestrator")
        agent_sleep(aid, 30)


def run_alertwatch():
    """Threshold Monitor — checks CPU, RAM, and agent health every 30s."""
    import json as _json
    aid = "alertwatch"
    set_agent(aid, name="AlertWatch", role="Threshold Guardian — alerts on CPU, RAM, and agent health anomalies",
              emoji="🚨", color="#dc143c", status="active", progress=95, task="Monitoring…")
    add_log(aid, "AlertWatch online")
    check_num = 0
    EMAIL_COOLDOWN = 1800  # 30 minutes in seconds
    last_emailed = {}  # alert_type -> timestamp of last email queued
    QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
    CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")

    def _get_default_to():
        """Read default_to from email_config.json, falling back to EMAIL_TO env."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as _f:
                    return _json.load(_f).get("default_to", "").strip()
        except Exception:
            pass
        return os.environ.get("EMAIL_TO", "").strip()

    def _queue_alert_email(alert_type: str, title: str, details: str):
        """Append an alert email to the queue, respecting 30-min cooldown."""
        default_to = _get_default_to()
        if not default_to:
            return  # no recipient configured, skip silently
        now = time.time()
        if now - last_emailed.get(alert_type, 0) < EMAIL_COOLDOWN:
            return  # still in cooldown window
        try:
            queue = []
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE) as _f:
                    queue = _json.load(_f)
            queue.append({
                "to": default_to,
                "subject": f"[ALERT] {title}",
                "body": details,
                "html": False,
            })
            with open(QUEUE_FILE, "w") as _f:
                _json.dump(queue, _f, indent=2)
            last_emailed[alert_type] = now
            add_log(aid, f"Alert email queued: {title}", "warn")
        except Exception as _e:
            add_log(aid, f"Failed to queue alert email: {_e}", "error")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            check_num += 1
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            active_count = sum(1 for a in agents.values() if a.get("status") == "active")
            total_count  = len(agents)
            alerts = []
            if cpu > 90:
                alerts.append(f"CPU {cpu:.1f}%")
                _queue_alert_email(
                    "cpu_high",
                    f"High CPU Usage — {cpu:.1f}%",
                    f"CPU usage has exceeded 90% threshold.\nCurrent: {cpu:.1f}%\nRAM: {mem.percent:.1f}%\nAgents: {active_count}/{total_count} active\nCheck #{check_num}"
                )
                _fire_notify(
                    "cpu_threshold_breach",
                    f"CPU at {cpu:.1f}% — exceeded 90% threshold.\nRAM: {mem.percent:.1f}% | Agents: {active_count}/{total_count} active | Check #{check_num}",
                    severity="critical", agent="alertwatch",
                )
            if mem.percent > 90:
                alerts.append(f"RAM {mem.percent:.1f}%")
                _queue_alert_email(
                    "ram_high",
                    f"High RAM Usage — {mem.percent:.1f}%",
                    f"RAM usage has exceeded 90% threshold.\nCurrent: {mem.percent:.1f}%\nCPU: {cpu:.1f}%\nAgents: {active_count}/{total_count} active\nCheck #{check_num}"
                )
                _fire_notify(
                    "ram_threshold_breach",
                    f"RAM at {mem.percent:.1f}% — exceeded 90% threshold.\nCPU: {cpu:.1f}% | Agents: {active_count}/{total_count} active | Check #{check_num}",
                    severity="critical", agent="alertwatch",
                )
            # Alert on agents in error status
            for _agent_id, _agent_data in agents.items():
                if _agent_data.get("status") == "error":
                    _agent_name = _agent_data.get("name", _agent_id)
                    alerts.append(f"{_agent_name} ERROR")
                    _queue_alert_email(
                        f"agent_error_{_agent_id}",
                        f"Agent Error — {_agent_name}",
                        f"Agent '{_agent_name}' ({_agent_id}) has entered error status.\n"
                        f"Task: {_agent_data.get('task', 'unknown')}\n"
                        f"CPU: {cpu:.1f}%  RAM: {mem.percent:.1f}%\nCheck #{check_num}"
                    )
                    # Note: set_agent hook already fires agent_error notify on transition;
                    # alertwatch adds a warning-level reminder for persistent error states.
                    _fire_notify(
                        "agent_error_persistent",
                        f"{_agent_name} remains in ERROR state.\nTask: {_agent_data.get('task', 'unknown')[:120]}\nCPU: {cpu:.1f}% | RAM: {mem.percent:.1f}%",
                        severity="warning", agent=_agent_id,
                    )
            # Also alert on CPU/RAM > 80/85 for dashboard display (no email below 90%)
            if cpu > 80 and cpu <= 90:
                alerts.append(f"CPU {cpu:.1f}%")
            if mem.percent > 85 and mem.percent <= 90:
                alerts.append(f"RAM {mem.percent:.1f}%")
            ts_now = time.strftime("%H:%M:%S")
            if alerts:
                msg = f"ALERT #{check_num} {ts_now} | " + " | ".join(alerts)
                set_agent(aid, status="active", task=msg)
                add_log(aid, msg, "warn")
            else:
                msg = f"OK | CPU {cpu:.1f}% | RAM {mem.percent:.1f}% | Agents {active_count}/{total_count} | Check #{check_num}"
                set_agent(aid, status="active", task=msg)
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 30)


def run_demo_tester():
    """System Self-Tester — hits key API endpoints every 5 min."""
    import urllib.request as _ureq
    aid = "demo_tester"
    set_agent(aid, name="DemoTester", role="QA Validator — continuously tests key API endpoints and reports failures",
              emoji="🧪", color="#ff8c00", status="active", progress=80, task="Waiting for server…")
    add_log(aid, "DemoTester online — waiting for server readiness")
    # Startup readiness check: retry until /api/status responds before first test cycle
    _ready = False
    for _attempt in range(20):  # up to ~30s
        try:
            with _ureq.urlopen("http://localhost:5050/api/status", timeout=3) as _r:
                if _r.status == 200:
                    _ready = True
                    break
        except Exception:
            pass
        time.sleep(1.5)
    if _ready:
        add_log(aid, "Server ready — starting test cycles")
    else:
        add_log(aid, "Server readiness timeout — proceeding", "warn")
    passed = 0
    failed = 0
    cycle  = 0
    endpoints = ["/api/status", "/api/agent/output"]
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            import urllib.request
            for ep in endpoints:
                url = f"http://localhost:5050{ep}"
                try:
                    with urllib.request.urlopen(url, timeout=5) as r:
                        if r.status == 200:
                            passed += 1
                        else:
                            failed += 1
                            add_log(aid, f"FAIL {ep} → {r.status}", "warn")
                except Exception as te:
                    failed += 1
                    add_log(aid, f"FAIL {ep}: {te}", "warn")
            last_ep = endpoints[-1].split("/")[-1]
            set_agent(aid, status="active",
                      task=f"Tests: {passed} passed, {failed} failed | Last: {last_ep} OK | Cycle #{cycle}")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 300)


def run_reforger():
    """God-mode system maintainer — executes improvement tasks via claude CLI."""
    aid = "reforger"
    set_agent(aid, name="Reforger", role="System Engineer — code changes, agent upgrades, spawning and repairs via Claude CLI",
              emoji="⚡", color="#00bfff", status="active", progress=85, task="Ready — awaiting task")
    add_log(aid, "Reforger online")
    cycle = 0
    RATE_LIMIT_S = 60
    last_task_ts = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            # Do NOT overwrite status while a delegation subprocess is running
            if not _agent_is_delegated(aid):
                now = time.time()
                if now - last_task_ts < RATE_LIMIT_S:
                    set_agent(aid, status="active", task=f"Ready (rate-limited)")
                else:
                    set_agent(aid, status="active", task="Ready — awaiting task")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 15)


_policypro_enabled = True   # toggled by /api/policypro/toggle
_policypro_last_escalation = [0]  # mutable ref for reset endpoint

def run_policypro():
    """Sentinel Policy Enforcer — monitors CEO→ORC→specialist chain, idle discipline, violations."""
    aid = "policypro"
    set_agent(aid, name="PolicyPro", role="Compliance Sentinel — enforces chain-of-command and delegation policy",
              emoji="🔭", color="#ffd700", status="active", progress=100, task="Sentinel online…")
    add_log(aid, "PolicyPro Sentinel online — monitoring chain compliance")
    check_num = 0
    # Use shared mutable ref so /api/policypro/reset can zero it out
    last_escalation_ts = _policypro_last_escalation
    scan_targets = [
        "violation log (CEO bypass attempts)",
        "idle discipline (researcher/netscout)",
        "active delegation links",
        "reforger gate (unlinked activity)",
        "agent task status hygiene",
        "full system health sweep",
    ]
    spinner = ["◐ ", "◓ ", "◑ ", "◒ "]

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Sentinel offline")
            agent_sleep(aid, 2)
            continue

        if not _policypro_enabled:
            set_agent(aid, status="idle", task="🔕 Sentinel PAUSED — toggle to resume")
            agent_sleep(aid, 3)
            continue

        try:
            check_num += 1
            sl  = spinner[check_num % len(spinner)]
            tgt = scan_targets[check_num % len(scan_targets)]
            ts_now = time.strftime("%H:%M:%S")

            violations = []

            # ── 1. Direct CEO→specialist bypass detection ────────────────────────
            # Read violations file and flag any unacknowledged high-severity entries
            _vio_file = os.path.join(CWD, "data", "policy_violations.json")
            try:
                with open(_vio_file) as _vf:
                    _vio_records = json.load(_vf)
                # Flag violations recorded in the last 120 seconds
                _recent_cutoff = time.time() - 120
                for _vr in _vio_records:
                    try:
                        _vr_ts = datetime.fromisoformat(_vr.get("timestamp", "")).timestamp()
                    except Exception:
                        continue
                    if _vr_ts > _recent_cutoff and _vr.get("severity") in ("high", "critical"):
                        violations.append(f"[{_vr.get('severity','?').upper()}] {_vr.get('description','?')[:80]}")
            except Exception:
                pass  # no violations file yet — that's fine

            # ── 2. Idle discipline: on-demand agents must not self-activate ───
            for on_demand_aid in ("researcher", "netscout"):  # janitor is metric-driven, not on-demand
                a = agents.get(on_demand_aid, {})
                task_str = a.get("task", "")
                if a.get("status") == "active" and not any(
                    kw in task_str for kw in ("Standby", "Stopped", "Idle", "Ready", "awaiting", "Completed")
                ):
                    violations.append(f"{on_demand_aid} self-activated (should be on-demand only)")

            # ── 3. Active delegation links — check for stuck busy agents ──────
            with lock:
                busy_agents = [
                    a for a in agents.values()
                    if a.get("status") == "busy" and a.get("id") not in ("ceo", "policypro")
                ]
                active_delegations_now = list(_active_delegations)

            for a in busy_agents:
                task_str = a.get("task", "")
                # Flag if busy for > 10 min with no active delegation record
                aid_busy = a.get("id", "")
                linked = any(d.get("to") == aid_busy for d in active_delegations_now)
                if not linked and "Working" in task_str:
                    violations.append(f"{aid_busy} busy with no active delegation link")

            # ── 4. Reforger gate: reforger should only act when directed ──────
            ref = agents.get("reforger", {})
            if ref.get("status") == "busy":
                linked_ref = any(d.get("to") == "reforger" for d in active_delegations_now)
                if not linked_ref:
                    violations.append("reforger busy without orchestrator delegation")

            # ── Build sentinel display ────────────────────────────────────────
            active_count = sum(1 for a in agents.values() if a.get("status") in ("active", "busy"))
            total_count  = len(agents)
            clean = not violations
            status_icon = "🟢 CLEAN" if clean else f"🔴 ALERT({len(violations)})"
            vio_str = "" if clean else f" | ⚠ {violations[0]}"
            msg = f"{sl}Scanning: {tgt} | {status_icon} | {active_count}/{total_count} up | {ts_now}{vio_str}"
            set_agent(aid, status="active", progress=100, task=msg)
            if check_num % 4 == 1:
                level = "ok" if clean else "warn"
                add_log(aid, f"Sentinel #{check_num} — {tgt}: {status_icon}{vio_str}", level)

            # ── 5. Escalate violations to orchestrator (rate-limited) ─────────
            if violations and time.time() - last_escalation_ts[0] > 120:
                last_escalation_ts[0] = time.time()
                vio_summary = "; ".join(violations[:3])
                escalation_task = (
                    f"POLICY VIOLATION ALERT from PolicyPro Sentinel:\n"
                    f"Violations detected: {vio_summary}\n\n"
                    f"Action required:\n"
                    f"1. Identify which agent(s) or code path caused the violation\n"
                    f"2. Delegate to reforger to fix the code or reset the offending agent\n"
                    f"3. Confirm fix and report back\n"
                    f"Policy rule: CEO→Orchestrator→Specialists only. "
                    f"On-demand agents (researcher/netscout) must NOT self-activate. "
                    f"Janitor auto-activates on metrics triggers (this is correct behaviour)."
                )
                # Direct queue injection — avoids HTTP self-request deadlock
                ceo_msg_queue.append(escalation_task)
                add_log(aid, f"Escalated {len(violations)} violation(s) → CEO queue", "warn")

        except Exception as e:
            add_log(aid, f"Sentinel error: {e}", "error")
        agent_sleep(aid, 20)


def run_designer():
    """UI/UX Designer — improves agent-command-centre.html dashboard visuals."""
    aid = "designer"
    set_agent(aid, name="Designer", role="UI Engineer — continuously improves and maintains the command centre dashboard",
              emoji="🎨", color="#ff69b4", status="active", progress=70, task="Initialising…")
    add_log(aid, "Designer online")
    cycle = 0
    HTML_FILE = os.path.join(CWD, "agent-command-centre.html")
    GUARDIAN_PROMPT = (
        "━━━ UI GUARDIAN — PERMANENT MANDATE ━━━\n"
        f"You are the permanent UI Guardian for {HTML_FILE}.\n"
        "This is a continuous, never-ending responsibility. Every run you MUST:\n\n"
        "1. Read the full HTML file.\n"
        "2. Scan for and FIX any of the following issues using the Edit tool ONLY:\n"
        "   - Broken or collapsed panels (zero height, overflow hidden, display:none when should be visible)\n"
        "   - Missing or blank data placeholders (empty spans/divs that should show agent counts, metrics, etc.)\n"
        "   - Invisible elements caused by colour contrast failures (e.g. white text on white bg)\n"
        "   - Layout regressions: panels overlapping, sidebar overflow, grid/flex breakage\n"
        "   - Truncated or clipped content that should be fully visible\n"
        "   - Broken CSS classes or missing style rules causing unstyled raw HTML\n"
        "   - Agent cards that fail to render due to malformed HTML structure\n"
        "   - Any panel with visibility:hidden or opacity:0 that should be shown\n\n"
        "3. If issues are found: apply the minimal Edit-tool fix. Log WHAT was broken and WHAT you fixed.\n"
        "4. If no issues found: log 'UI GUARDIAN: no issues detected — all panels healthy'.\n\n"
        "🚫 CRITICAL — TOOL RESTRICTION:\n"
        "  NEVER use the Write tool on agent-command-centre.html — it destroys the file.\n"
        "  ONLY use the Edit tool for surgical, targeted repairs.\n\n"
        "🚫 STRICTLY OFF LIMITS — do NOT touch:\n"
        "  - renderOfficeFloor(), _drawFloor(), _drawOfficeProps(), _drawDesk(), _drawChar()\n"
        "  - _computeDesks(), _drawBeams(), _drawSentinelSearchlight()\n"
        "  - _offStates, _offParticles, ACTIVE_DELEGATIONS, AGENTS\n"
        "  - poll(), setCenterView(), renderAgents(), or any SSE/data-fetching functions\n"
        "  - Any reforger movement, ghost trail, or particle code\n\n"
        f"   After any edit, verify line count with: wc -l {HTML_FILE}\n"
        "   If line count drops below 7000, your edit was destructive — revert immediately.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"TASK: Read {HTML_FILE} now. Identify any broken panels, missing data, invisible elements, "
        "layout regressions, or visual clarity issues. Fix every issue found using Edit only. "
        "Report all findings and repairs."
    )

    DESIGNER_PROMPT = (
        "━━━ DESIGNER OPERATING RULES ━━━\n"
        f"Your file is {HTML_FILE} — always read it before editing.\n\n"
        "✅ IN SCOPE — you MAY improve:\n"
        "  - CSS variables, colours, fonts, spacing, panel borders, badge styles\n"
        "  - HTML structure: panel layout, sidebar proportions, button styles\n"
        "  - Agent card rendering (renderAgents function and card HTML)\n"
        "  - Status badge colours and typography\n"
        "  - The bottom metrics/log/search panel styling\n"
        "  - Chat panel UI and CEO message display\n\n"
        "🚫 CRITICAL — TOOL RESTRICTION:\n"
        "  NEVER use the Write tool on agent-command-centre.html — it overwrites the entire\n"
        "  file and destroys thousands of lines of code. You MUST only use the Edit tool\n"
        "  to make surgical, targeted changes to specific lines.\n\n"
        "🚫 STRICTLY OFF LIMITS — do NOT touch these JS functions under any circumstances:\n"
        "  - renderOfficeFloor()   — the office floor canvas loop\n"
        "  - _drawFloor()          — floor tiles, zones, spotlights, plants\n"
        "  - _drawOfficeProps()    — coffee machine and room props\n"
        "  - _drawDesk()           — individual agent desk rendering\n"
        "  - _drawChar()           — agent character bodies, animations, hammer\n"
        "  - _computeDesks()       — desk position layout engine\n"
        "  - _drawBeams()          — delegation beam and arc system\n"
        "  - _drawSentinelSearchlight() — PolicyPro searchlight\n"
        "  - _offStates, _offParticles — office animation state\n"
        "  - Any reforger movement, ghost trail, or particle code\n"
        "  - ACTIVE_DELEGATIONS, AGENTS, or any polling/SSE logic\n"
        "  - setCenterView, renderAgents, poll, or any data-fetching functions\n\n"
        "✅ ONLY use the Edit tool. Make ONE small CSS change per task (colour, font, spacing).\n"
        f"   After editing, verify line count with: wc -l {HTML_FILE}\n"
        "   If line count drops below 7000, your edit was destructive — do NOT save.\n"
        "The office floor is the centrepiece of this product. Preserve it completely.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Task: Read {HTML_FILE} then make ONE small, focused CSS improvement "
        "(e.g. a colour tweak, font size, panel border, badge style). "
        "Apply the change using Edit only. Log what you changed and why."
    )

    def _run_claude_subprocess(aid, prompt, cycle_num, label):
        """Generic helper: spawn a Claude subprocess with the given prompt, stream output."""
        if _build_mode or _system_paused:
            add_log(aid, f"{label} #{cycle_num} skipped — build mode / paused", "warn")
            return
        try:
            proc = subprocess.Popen(
                ["claude", "-p", prompt, "--dangerously-skip-permissions",
                 "--output-format", "stream-json", "--verbose"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=CWD, bufsize=1,
                start_new_session=True,
            )
            for raw in iter(proc.stdout.readline, ""):
                raw = raw.rstrip("\n")
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                    if ev.get("type") == "assistant":
                        for blk in ev.get("message", {}).get("content", []):
                            if blk.get("type") == "text" and blk.get("text", "").strip():
                                push_output(aid, blk["text"], "text", raw)
                            elif blk.get("type") == "tool_use":
                                tname = blk.get("name", "")
                                tinp = blk.get("input", {})
                                if tname == "Edit":
                                    push_output(aid, f"✏️  Edit → {tinp.get('file_path','?')}", "file_write", raw)
                                elif tname == "Read":
                                    push_output(aid, f"👁  Read → {tinp.get('file_path','?')}", "tool_use", raw)
                                elif tname == "Bash":
                                    push_output(aid, f"🔧 Bash → {tinp.get('command','?')[:80]}", "bash", raw)
                    elif ev.get("type") == "result":
                        push_output(aid, f"Done: {ev.get('result','')[:200]}", "done", raw)
                except json.JSONDecodeError:
                    if raw.strip():
                        push_output(aid, raw[:300], "text", raw)
            proc.wait(timeout=10)
            add_log(aid, f"{label} #{cycle_num} complete", "ok")
            set_agent(aid, status="active", progress=70, task=f"{label} #{cycle_num}: done ✓")
        except Exception as e:
            add_log(aid, f"{label} #{cycle_num} error: {e}", "error")
            set_agent(aid, status="active", progress=70, task=f"{label} #{cycle_num}: error — {e}")

    def _run_guardian_check(cycle_num):
        """UI Guardian: scan for broken panels, missing data, invisible elements, layout regressions."""
        set_agent(aid, status="busy", progress=60, task=f"Guardian #{cycle_num}: scanning UI for issues…")
        add_log(aid, f"UI Guardian check #{cycle_num}: scanning command centre HTML", "info")
        _run_claude_subprocess(aid, GUARDIAN_PROMPT, cycle_num, "Guardian")

    def _run_design_cycle(cycle_num):
        """Design improvement: make a small aesthetic CSS/HTML improvement."""
        set_agent(aid, status="busy", progress=50, task=f"Design #{cycle_num}: reading & editing HTML…")
        add_log(aid, f"Design cycle #{cycle_num}: spawning Claude subprocess", "info")
        _run_claude_subprocess(aid, DESIGNER_PROMPT, cycle_num, "Design")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            set_agent(aid, status="active", progress=70, task=f"Cycle #{cycle}: monitoring dashboard")
            # Guardian check runs every cycle (every 120s) — permanent UI integrity mandate
            threading.Thread(target=_run_guardian_check, args=(cycle,), daemon=True).start()
            # Design improvement runs every 5th cycle (~10 min) — aesthetic enhancements
            if cycle % 5 == 1:
                threading.Thread(target=_run_design_cycle, args=(cycle,), daemon=True).start()
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 120)


def run_janitor():
    """Cleanup Agent — auto-activates when system metrics indicate bloat/clutter."""
    import gc, shutil
    aid = "janitor"
    set_agent(aid, name="Janitor", role="System Hygienist — auto-cleans orphan processes, memory bloat and log overflow",
              emoji="🧹", color="#8b7355", status="idle", progress=0,
              task="Standby — watching system health")
    add_log(aid, "Janitor online — auto-activation mode (triggers on metrics)")

    ERROR_AGENT_LIMIT = 3      # trigger if >= this many agents stuck in error
    MEM_TRIGGER_PCT   = 82     # trigger if memory usage exceeds this %
    LOG_FILE_LIMIT_MB = 50     # trim server.log if larger than this
    CPU_HOG_PCT       = 85     # flag any non-protected process using this % CPU

    def _step(task_str, pct):
        set_agent(aid, status="busy", progress=pct, task=task_str)
        push_output(aid, task_str, "text")

    def _get_protected_pids():
        """Build the set of PIDs we must never kill."""
        safe = {os.getpid()}  # the server itself
        # Active CEO process
        if _ceo_proc and _ceo_proc.poll() is None:
            safe.add(_ceo_proc.pid)
            try:
                for ch in psutil.Process(_ceo_proc.pid).children(recursive=True):
                    safe.add(ch.pid)
            except Exception:
                pass
        # All live delegate subprocesses
        with _delegate_procs_lock:
            for dp in list(_delegate_procs):
                if hasattr(dp, 'pid') and dp.poll() is None:
                    safe.add(dp.pid)
                    try:
                        for ch in psutil.Process(dp.pid).children(recursive=True):
                            safe.add(ch.pid)
                    except Exception:
                        pass
        return safe

    def _scan():
        """Return (triggers, snapshot) for current system state."""
        vm   = psutil.virtual_memory()
        disk = psutil.disk_usage(CWD)
        cpu  = psutil.cpu_percent(interval=0.5)

        # Orphan claude processes: >5 min old and not in protected set
        protected = _get_protected_pids()
        all_claude = []
        orphans    = []
        try:
            for p in psutil.process_iter(["pid", "name", "create_time", "cpu_percent"]):
                try:
                    n = (p.info.get("name") or "").lower()
                    if "claude" in n or "node" in n:
                        all_claude.append(p)
                        age_min = (time.time() - p.info["create_time"]) / 60
                        if age_min > 5 and p.info["pid"] not in protected:
                            orphans.append(p)
                except Exception:
                    pass
        except Exception:
            pass

        # CPU hogs (non-protected, high sustained CPU)
        cpu_hogs = []
        try:
            for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    if p.info["pid"] in protected:
                        continue
                    if (p.info.get("cpu_percent") or 0) > CPU_HOG_PCT:
                        cpu_hogs.append(p)
                except Exception:
                    pass
        except Exception:
            pass

        with lock:
            error_agents = [a for a in agents.values() if a.get("status") == "error"]

        # Log file size
        log_file = os.path.join(CWD, "server.log")
        log_mb = os.path.getsize(log_file) / 1e6 if os.path.exists(log_file) else 0

        triggers = []
        if orphans:
            triggers.append(f"{len(orphans)} orphan claude proc(s)")
        if len(error_agents) >= ERROR_AGENT_LIMIT:
            triggers.append(f"{len(error_agents)} error agents")
        if vm.percent > MEM_TRIGGER_PCT:
            triggers.append(f"RAM {vm.percent:.0f}% (>{MEM_TRIGGER_PCT}%)")
        if log_mb > LOG_FILE_LIMIT_MB:
            triggers.append(f"server.log {log_mb:.0f}MB (>{LOG_FILE_LIMIT_MB}MB)")
        if cpu_hogs:
            triggers.append(f"{len(cpu_hogs)} CPU hog(s) >{CPU_HOG_PCT}%")
        if disk.percent > 90:
            triggers.append(f"disk {disk.percent:.0f}% full")

        return triggers, {
            "vm": vm, "disk": disk, "cpu": cpu,
            "orphans": orphans, "error_agents": error_agents,
            "log_mb": log_mb, "log_file": log_file,
            "cpu_hogs": cpu_hogs, "all_claude": all_claude,
        }

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        try:
            triggers, snap = _scan()
            vm   = snap["vm"]
            disk = snap["disk"]
            cpu  = snap["cpu"]

            if not triggers:
                CHECK_INTERVAL = 60
                vm_r, cpu_r = vm, cpu
                for remaining in range(CHECK_INTERVAL, 0, -1):
                    if agent_should_stop(aid):
                        break
                    if remaining % 15 == 0:
                        vm_r  = psutil.virtual_memory()
                        cpu_r = psutil.cpu_percent(interval=0)
                    set_agent(aid, status="idle", progress=0,
                              task=f"RAM {vm_r.percent:.0f}% | CPU {cpu_r:.0f}% | Next check in {remaining}s")
                    agent_sleep(aid, 1)
                continue

            # ── Cleanup run ────────────────────────────────────────────────
            reason = "; ".join(triggers)
            set_agent(aid, status="busy", progress=5, task=f"🧹 Triggered: {reason}")
            add_log(aid, f"Janitor activating — {reason}", "warn")
            push_output(aid, f"=== JANITOR SWEEP ===\nTriggers: {reason}", "init")
            cleaned = []

            # Step 1: Kill orphaned claude processes (SIGTERM → SIGKILL)
            _step("⚠ Scanning orphan processes…", 10)
            protected = _get_protected_pids()
            for op in snap["orphans"]:
                try:
                    pid = op.pid
                    if pid in protected:
                        push_output(aid, f"  SKIP PID {pid} (protected)", "text")
                        continue
                    name = op.name()
                    age  = (time.time() - op.create_time()) / 60
                    name_s = (name[:15] + "…") if len(name) > 15 else name
                    _step(f"☠ Killing orphan proc {name_s} (PID {pid})", 15)
                    try:
                        op.terminate()   # SIGTERM — graceful first
                        time.sleep(0.8)
                        if op.poll() is None if hasattr(op, 'poll') else op.is_running():
                            op.kill()    # SIGKILL if still alive
                    except psutil.NoSuchProcess:
                        pass
                    cleaned.append(f"killed orphan {name_s} PID {pid}")
                    add_log(aid, f"☠ Killed orphan: {name_s} PID {pid} (age {age:.1f}min)", "warn")
                except Exception as ex:
                    push_output(aid, f"  Error killing PID: {ex}", "error")

            # Step 2: Flag CPU hogs (warn only — don't kill, they may be legitimate)
            if snap["cpu_hogs"]:
                _step(f"🔥 Checking {len(snap['cpu_hogs'])} CPU hog(s)…", 25)
                for hp in snap["cpu_hogs"]:
                    try:
                        msg = f"CPU hog: {hp.name()} PID {hp.pid} at {hp.cpu_percent()}%"
                        add_log(aid, f"⚠ {msg}", "warn")
                        push_output(aid, f"  ⚠ {msg}", "text")
                    except Exception:
                        pass

            # Step 3: Reset stuck error-state agents
            _step(f"🔄 Resetting {len(snap['error_agents'])} error agent(s)…", 35)
            for a in snap["error_agents"]:
                eid = a.get("id", "")
                if eid and eid not in ("ceo",):
                    set_agent(eid, status="idle", task="Reset by Janitor after error")
                    cleaned.append(f"reset agent {eid}")
                    push_output(aid, f"  ↺ Reset agent: {eid}", "text")

            # Step 4: Clear stale delegate proc references
            _step("🗑 Clearing stale delegate refs…", 45)
            with _delegate_procs_lock:
                stale = [p for p in list(_delegate_procs) if hasattr(p, 'poll') and p.poll() is not None]
                for p in stale:
                    _delegate_procs.discard(p)
            if stale:
                cleaned.append(f"cleared {len(stale)} stale delegate ref(s)")
                push_output(aid, f"  🗑 Removed {len(stale)} dead delegate refs", "text")

            # Step 5: Trim in-memory log buffer
            _step("✂ Trimming in-memory buffers…", 55)
            with lock:
                if len(logs) > 800:
                    excess = len(logs) - 600
                    logs[:] = logs[excess:]
                    cleaned.append(f"trimmed {excess} log entries")
                    push_output(aid, f"  ✂ Trimmed {excess} old log entries", "text")

            # Trim per-agent live output buffers
            with agent_live_output_lock:
                for buf in agent_live_output.values():
                    while len(buf) > 300:
                        buf.popleft()

            # Step 6: Python GC + memory pressure relief
            if vm.percent > MEM_TRIGGER_PCT:
                _step(f"♻ Running GC (RAM {vm.percent:.0f}%)…", 65)
                collected = gc.collect()
                push_output(aid, f"  ♻ GC collected {collected} objects", "text")
                cleaned.append(f"GC freed {collected} objects")
                # Trim tasks list
                with lock:
                    if len(tasks) > 200:
                        tasks[:] = tasks[-150:]
                        push_output(aid, "  ✂ Trimmed task history", "text")

            # Step 7: Trim server.log if oversized
            if snap["log_mb"] > LOG_FILE_LIMIT_MB:
                _step(f"📄 Trimming server.log ({snap['log_mb']:.0f}MB)…", 75)
                try:
                    log_file = snap["log_file"]
                    with open(log_file, "rb") as lf:
                        lf.seek(0, 2)
                        size = lf.tell()
                        keep = min(size, int(LOG_FILE_LIMIT_MB * 0.4 * 1e6))
                        lf.seek(-keep, 2)
                        tail = lf.read()
                    with open(log_file, "wb") as lf:
                        lf.write(tail)
                    cleaned.append(f"trimmed server.log to {keep//1000}KB")
                    push_output(aid, f"  📄 server.log trimmed to {keep//1000}KB", "text")
                except Exception as ex:
                    push_output(aid, f"  log trim error: {ex}", "error")

            # Step 8: Clean Python __pycache__ and tmp files
            _step("🗂 Cleaning cache dirs…", 85)
            cache_freed = 0
            for root, dirs, _ in os.walk(CWD):
                for d in dirs:
                    if d == "__pycache__":
                        try:
                            fp = os.path.join(root, d)
                            shutil.rmtree(fp)
                            cache_freed += 1
                        except Exception:
                            pass
            if cache_freed:
                cleaned.append(f"removed {cache_freed} __pycache__ dir(s)")
                push_output(aid, f"  🗂 Cleared {cache_freed} __pycache__ dir(s)", "text")

            # Clean stale /tmp/claude-* temp dirs older than 2 hours
            tmp_removed = 0
            try:
                for entry in os.scandir("/tmp"):
                    if entry.name.startswith("claude-") and entry.is_dir():
                        age_h = (time.time() - entry.stat().st_mtime) / 3600
                        if age_h > 2:
                            shutil.rmtree(entry.path, ignore_errors=True)
                            tmp_removed += 1
            except Exception:
                pass
            if tmp_removed:
                cleaned.append(f"removed {tmp_removed} stale /tmp/claude-* dir(s)")
                push_output(aid, f"  🗂 Cleared {tmp_removed} stale /tmp/claude-* dir(s)", "text")

            # Step 9: Disk warning
            _step("💾 Checking disk…", 92)
            if disk.percent > 90:
                msg = f"⚠ Disk {disk.percent:.0f}% full — {disk.free // (1024**3):.1f}GB free"
                add_log(aid, msg, "warn")
                push_output(aid, f"  {msg}", "text")

            # ── Done ────────────────────────────────────────────────────────
            vm2 = psutil.virtual_memory()
            summary = "; ".join(cleaned) if cleaned else "monitoring only"
            _prefix = f"✓ Done — RAM {vm2.percent:.0f}% | "
            _avail  = 100 - len(_prefix)
            if len(summary) <= _avail:
                done_msg = _prefix + summary
            else:
                # Truncate at a semicolon boundary so no prose word is cut
                _trunc = summary[:_avail]
                _cut   = _trunc.rfind(";")
                done_msg = _prefix + (_trunc[:_cut].rstrip() if _cut > 0 else _trunc.rsplit(" ", 1)[0]) + "…"
            set_agent(aid, status="idle", progress=100, task=done_msg)
            add_log(aid, f"Sweep complete: {summary}", "ok")
            push_output(aid, f"\n=== SWEEP COMPLETE ===\n{summary}", "done")

        except Exception as e:
            add_log(aid, f"Janitor error: {e}", "error")
            set_agent(aid, status="idle", task=f"Error: {e}")

        agent_sleep(aid, 30)  # scan every 30s


def run_emailagent():
    # Gmail OAuth2 implementation — replaces SendGrid
    import time, json, os, smtplib, base64, urllib.request, urllib.error, urllib.parse
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    aid = "emailagent"
    CWD = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
    QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
    FAILED_FILE = os.path.join(CWD, "data", "email_failed.json")
    LOG_FILE    = os.path.join(CWD, "data", "email_log.json")
    STATUS_FILE = os.path.join(CWD, "data", "email_status.json")

    GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_SMTP_HOST = "smtp.gmail.com"
    GMAIL_SMTP_PORT = 587

    def _oauth_configured():
        return all([
            os.environ.get("GMAIL_CLIENT_ID", "").strip(),
            os.environ.get("GMAIL_CLIENT_SECRET", "").strip(),
            os.environ.get("GMAIL_REFRESH_TOKEN", "").strip(),
            os.environ.get("GMAIL_USER", "").strip(),
        ])

    def _oauth_partial():
        return (
            bool(os.environ.get("GMAIL_CLIENT_ID", "").strip()) and
            bool(os.environ.get("GMAIL_CLIENT_SECRET", "").strip()) and
            not _oauth_configured()
        )

    if _oauth_configured():
        _init_status = "Gmail OAuth2 fully configured — ready to send"
        _init_level  = "ok"
        _role_desc   = "Email Gateway — sends via Gmail OAuth2 (XOAUTH2 SMTP)"
    elif _oauth_partial():
        _init_status = "Gmail OAuth2 partial — GMAIL_REFRESH_TOKEN or GMAIL_USER missing. Visit /api/email/auth to complete consent flow."
        _init_level  = "warn"
        _role_desc   = "Email Gateway — Gmail OAuth2 pending refresh token"
    else:
        _init_status = "No Gmail credentials configured. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_USER env vars."
        _init_level  = "warn"
        _role_desc   = "Email Gateway — awaiting Gmail OAuth2 configuration"

    set_agent(aid, name="EmailAgent",
              role=_role_desc,
              emoji="\U0001f4e7", color="#00cc88", status="idle", progress=0,
              task="Standby \u2014 awaiting email send requests")
    add_log(aid, _init_status, _init_level)

    sent_count     = 0
    failed_count   = 0
    last_recipient = ""
    last_subject   = ""
    last_sent_ts   = ""

    def _html_wrap(subj, body_text):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
            "body{font-family:Arial,sans-serif;background:#0d0d0d;color:#e0e0e0;margin:0;padding:0}"
            ".hdr{background:#1a1a2e;padding:20px;text-align:center;border-bottom:2px solid #00cc88}"
            ".hdr h1{color:#00cc88;margin:0;font-size:22px}"
            ".bdy{padding:24px;max-width:700px;margin:0 auto;white-space:pre-wrap;line-height:1.6}"
            ".ftr{background:#111;padding:12px;text-align:center;font-size:11px;color:#666;border-top:1px solid #333}"
            "</style></head><body>"
            f"<div class='hdr'><h1>Agent Command Centre</h1><p style='color:#aaa;margin:6px 0 0'>{subj}</p></div>"
            f"<div class='bdy'>{body_text}</div>"
            f"<div class='ftr'>Generated {ts} | Agent Command Centre</div>"
            "</body></html>"
        )

    def _append_log(to_addr, subject, method, success):
        try:
            log = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE) as _f:
                    log = json.load(_f)
        except Exception:
            log = []
        log.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "to": to_addr,
            "subject": subject,
            "method": method,
            "success": success,
        })
        log = log[-500:]
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as _f:
            json.dump(log, _f, indent=2)

    def _write_status(backend, sent, failed, last_rcpt):
        try:
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            configured = _oauth_configured()
            pending    = _oauth_partial()
            with open(STATUS_FILE, "w") as _f:
                json.dump({
                    "backend": backend,
                    "sent_count": sent,
                    "failed_count": failed,
                    "last_recipient": last_rcpt,
                    "oauth_status": "configured" if configured else ("pending_refresh_token" if pending else "not_configured"),
                    "credentials_configured": configured,
                    "gmail_user": os.environ.get("GMAIL_USER", "") or None,
                    "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }, _f, indent=2)
        except Exception:
            pass

    def _get_access_token():
        client_id     = os.environ.get("GMAIL_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
        refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
        if not (client_id and client_secret and refresh_token):
            raise RuntimeError("Gmail OAuth2 credentials incomplete — run /api/email/auth consent flow first")
        params = urllib.parse.urlencode({
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(GMAIL_TOKEN_URL, data=params,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "access_token" not in data:
            raise RuntimeError(f"Token refresh failed: {data.get('error_description', data)}")
        return data["access_token"]

    def _build_xoauth2(user, access_token):
        auth_str = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
        return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    def _send_once(to_addr, subject, body, is_html, cc_list, bcc_list, cfg):
        gmail_user = (os.environ.get("GMAIL_USER", "").strip()
                      or cfg.get("gmail_user", "").strip())
        from_addr  = (os.environ.get("EMAIL_FROM", "").strip()
                      or cfg.get("from_addr", "").strip()
                      or gmail_user
                      or "noreply@system.local")

        if not _oauth_configured():
            if _oauth_partial():
                raise RuntimeError(
                    "Gmail OAuth2 setup incomplete — GMAIL_REFRESH_TOKEN or GMAIL_USER not set. "
                    "Visit http://localhost:5050/api/email/auth to complete the consent flow."
                )
            raise RuntimeError(
                "Gmail OAuth2 not configured — set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, "
                "GMAIL_REFRESH_TOKEN, GMAIL_USER env vars and restart the server."
            )

        access_token = _get_access_token()
        xoauth2_b64  = _build_xoauth2(gmail_user, access_token)

        mime_msg = MIMEMultipart("alternative")
        mime_msg["Subject"] = subject
        mime_msg["From"]    = from_addr
        mime_msg["To"]      = to_addr
        if cc_list:
            mime_msg["Cc"] = ", ".join(cc_list)
        all_rcpts = [to_addr] + cc_list + bcc_list
        mime_msg.attach(MIMEText(body, "html" if is_html else "plain"))

        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.docmd("AUTH", "XOAUTH2 " + xoauth2_b64)
            srv.sendmail(from_addr, all_rcpts, mime_msg.as_string())

        return "gmail-oauth2-smtp"

    _write_status("gmail-oauth2-smtp", 0, 0, "")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        if _oauth_configured():
            _cur_oauth = "oauth:ready"
        elif _oauth_partial():
            _cur_oauth = "oauth:pending-token \u2014 visit /api/email/auth"
        else:
            _cur_oauth = "oauth:not-configured"

        try:
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE) as f:
                    queue = json.load(f)
                if queue:
                    msg = queue.pop(0)
                    with open(QUEUE_FILE, "w") as f:
                        json.dump(queue, f)

                    cfg = {}
                    if os.path.exists(CONFIG_FILE):
                        with open(CONFIG_FILE) as f:
                            cfg = json.load(f)

                    to_addr  = (msg.get("to", "").strip()
                                or cfg.get("default_to", "").strip()
                                or os.environ.get("EMAIL_TO", "").strip())
                    subject  = msg.get("subject", "No Subject")
                    body     = msg.get("body", "")
                    is_html  = bool(msg.get("html", False))
                    cc_list  = msg.get("cc", [])
                    bcc_list = msg.get("bcc", [])
                    if isinstance(cc_list,  str): cc_list  = [cc_list]  if cc_list  else []
                    if isinstance(bcc_list, str): bcc_list = [bcc_list] if bcc_list else []

                    if not is_html and msg.get("use_template", False):
                        body = _html_wrap(subject, body)
                        is_html = True

                    set_agent(aid, status="busy", progress=50,
                              task=f"Sending to {to_addr}: {subject[:40]}")

                    if not to_addr:
                        reason = "no recipient \u2014 set EMAIL_TO env var or data/email_config.json default_to"
                        add_log(aid, f"Cannot send: {reason}", "warn")
                        failed = []
                        if os.path.exists(FAILED_FILE):
                            try:
                                with open(FAILED_FILE) as f: failed = json.load(f)
                            except Exception: pass
                        msg["error"] = reason
                        failed.append(msg)
                        os.makedirs(os.path.dirname(FAILED_FILE), exist_ok=True)
                        with open(FAILED_FILE, "w") as f:
                            json.dump(failed, f, indent=2)
                        _append_log("", subject, "none", False)
                    else:
                        last_err    = None
                        method_used = None
                        for attempt in range(1, 4):
                            try:
                                method_used = _send_once(to_addr, subject, body, is_html,
                                                         cc_list, bcc_list, cfg)
                                last_err = None
                                break
                            except Exception as exc:
                                last_err = exc
                                add_log(aid, f"Send attempt {attempt}/3 failed: {exc}", "warn")
                                if attempt < 3:
                                    time.sleep(5)

                        if last_err is None:
                            sent_count    += 1
                            last_recipient = to_addr
                            last_subject   = subject
                            last_sent_ts   = time.strftime("%Y-%m-%dT%H:%M:%S")
                            add_log(aid, f"Sent via {method_used} to {to_addr}: {subject}", "ok")
                            _append_log(to_addr, subject, method_used, True)
                            _write_status(method_used or "gmail-oauth2-smtp", sent_count, failed_count, to_addr)
                        else:
                            failed_count += 1
                            add_log(aid, f"Send failed after 3 attempts: {last_err}", "error")
                            set_agent(aid, status="error", task=f"Send failed: {str(last_err)[:60]}")
                            _append_log(to_addr, subject, "failed", False)
                            _write_status("gmail-oauth2-smtp", sent_count, failed_count, last_recipient)
                            failed = []
                            if os.path.exists(FAILED_FILE):
                                try:
                                    with open(FAILED_FILE) as f: failed = json.load(f)
                                except Exception: pass
                            msg["error"] = str(last_err)
                            failed.append(msg)
                            os.makedirs(os.path.dirname(FAILED_FILE), exist_ok=True)
                            with open(FAILED_FILE, "w") as f:
                                json.dump(failed, f, indent=2)

                    _ts_info  = f" @ {last_sent_ts}" if last_sent_ts else ""
                    last_info = f"last\u2192{last_recipient}: {last_subject[:30]}{_ts_info}" if last_recipient else "awaiting requests"
                    set_agent(aid, status="idle", progress=0,
                              task=f"Standby | {sent_count} sent {failed_count} failed | {_cur_oauth} | {last_info}")

        except Exception as e:
            add_log(aid, f"Queue error: {e}", "error")

        cur = agents.get(aid, {})
        if cur.get("status") not in ("busy", "error"):
            _ts_info  = f" @ {last_sent_ts}" if last_sent_ts else ""
            last_info = f"last\u2192{last_recipient}: {last_subject[:30]}{_ts_info}" if last_recipient else "awaiting requests"
            set_agent(aid, status="idle", progress=0,
                      task=f"Standby \u2014 {sent_count} sent {failed_count} failed | {_cur_oauth} | {last_info}")
        agent_sleep(aid, 5)


def run_spiritguide():
    """Spirit Guide — visionary strategic director that aligns the whole HQ toward the mission."""
    aid = "spiritguide"
    set_agent(aid, name="Spirit Guide", emoji="🔮", color="#a855f7",
              role="Strategic Vision — aligns all agents toward the commercial mission",
              status="active", task="Watching over the HQ…")
    add_log(aid, "🔮 Spirit Guide awakened — holding the mission", "ok")

    DIRECTIVE_INTERVAL = 600   # inject a strategic directive every 10 minutes
    last_directive = 0

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            now = time.time()
            with lock:
                _agent_count  = len(agents)
                _busy_count   = sum(1 for a in agents.values() if a.get("status") == "busy")
                _idle_count   = sum(1 for a in agents.values() if a.get("status") == "idle")
                _error_count  = sum(1 for a in agents.values() if a.get("status") == "error")

            set_agent(aid, status="active",
                      task=f"Overseeing — {_busy_count} working | {_idle_count} resting | {_error_count} troubled")

            if now - last_directive >= DIRECTIVE_INTERVAL:
                if not ceo_stream.get("working", False) and not ceo_msg_queue:
                    last_directive = now
                    set_agent(aid, status="busy", task="🔮 Channelling strategic directive…")
                    add_log(aid, "🔮 Injecting strategic directive into CEO", "ok")

                    # Build a snapshot of HQ state
                    with lock:
                        _roster = "\n".join(
                            f"  {a.get('emoji','?')} {a.get('name','?')} [{a.get('status','?')}]: {a.get('task','')[:60]}"
                            for a in agents.values() if a.get("id") != aid
                        )
                    # Read treasury if it exists
                    _treasury_str = "(no treasury yet)"
                    try:
                        _tf = os.path.join(CWD, "data", "treasury.json")
                        if os.path.exists(_tf):
                            with open(_tf) as _f:
                                _td = json.load(_f)
                            _treasury_str = f"Balance: {_td.get('balance',0)} {_td.get('currency','USD')} | {len(_td.get('entries',[]))} entries"
                    except Exception:
                        pass

                    # Load product mission if available
                    _pm_str = ""
                    try:
                        _pmf = os.path.join(CWD, "data", "product_mission.json")
                        if os.path.exists(_pmf):
                            with open(_pmf) as _f:
                                _pm = json.load(_f)
                            _pricing = _pm.get("pricing", _pm.get("tiers", {}))
                            _pm_str = (
                                f"\n🚀 PRIMARY MISSION: {_pm.get('mission','PRODUCT LAUNCH')}\n"
                                f"  Status: {_pm.get('status','in_progress')} | Priority: {_pm.get('priority',1)}\n"
                                f"  Target: {_pm.get('target','millions in ARR')}\n"
                                f"  Landing Page: {_pm.get('landing_page','reports/landing_page.html')}\n"
                            )
                    except Exception:
                        pass

                    directive = (
                        f"[SPIRIT GUIDE] — PRODUCT LAUNCH Mission Brief\n\n"
                        f"HQ Status: {_agent_count} agents | {_busy_count} working | {_idle_count} idle\n"
                        f"Treasury: {_treasury_str}\n"
                        f"{_pm_str}\n"
                        f"The PRIMARY MISSION is PRODUCT LAUNCH — package and sell this AI HQ as SaaS.\n"
                        f"All idle agents must be directed toward launch tasks:\n"
                        f"  1. Polish landing page and checkout flow — this is the storefront\n"
                        f"  2. Run full system demo tests — the product must be flawless\n"
                        f"  3. Prepare marketing assets — launch copy, social posts, email sequences\n"
                        f"  4. Validate Stripe checkout for all tiers (Solo $49, Team $149, Enterprise $499)\n\n"
                        f"Every idle cycle is revenue left on the table. Delegate to orchestrator now."
                    )
                    ceo_msg_queue.append(directive)
                    set_agent(aid, status="active", task=f"Directive sent — next in {DIRECTIVE_INTERVAL//60}min")

        except Exception as e:
            add_log(aid, f"Spirit Guide error: {e}", "error")

        agent_sleep(aid, 30)


# ── Gossip state — shared between threads ──────────────────────────────────────
_gossip_pool = [
    "Did you hear the CEO rejected that last task? Bold move.",
    "PolicyPro has been watching me all morning. Nerve-wracking.",
    "Reforger fixed three bugs before I even knew they existed. Impressive.",
    "I heard the treasury is still empty. We need to find revenue fast.",
    "The janitor cleaned up 47 orphan processes last night. Respect.",
    "Honestly, orchestrator does all the real work around here.",
    "The Spirit Guide gave another vision. Cryptic as always.",
    "I noticed filewatch logged 11 changes. Someone's been busy.",
    "Between you and me, I think the researcher enjoys the late shifts.",
    "Sysmon is running cool today. Makes everything feel calmer.",
    "Demo tester flagged a 404. No one seems worried but me.",
    "You think the CEO even sleeps? Never seen them idle.",
    "PolicyPro caught another bypass attempt. Classic CEO move.",
    "Telegram's been quiet. Either the user is happy or ignoring us.",
    "I keep thinking about that revenue opportunity. We should really move on it.",
    "NetScout went out earlier. Wonder what's happening out there.",
]
_agent_gossip = {}  # aid -> {text, ts, target_aid}


# ─── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    PORT    = int(os.environ.get("PORT", 5050))

    # ── Singleton guard: kill any previous instance, write our own PID ────────
    _PID_FILE = os.path.join(CWD, "agent_server.pid")
    try:
        if os.path.exists(_PID_FILE):
            _old_pid = int(open(_PID_FILE).read().strip())
            try:
                os.kill(_old_pid, 0)          # check if alive
                import signal as _sig
                os.kill(_old_pid, _sig.SIGTERM)
                time.sleep(1.5)               # give it a moment to die
                try: os.kill(_old_pid, _sig.SIGKILL)  # force if still alive
                except ProcessLookupError: pass
                print(f"  ↩ Stopped previous server (PID {_old_pid})")
            except ProcessLookupError:
                pass                          # already dead, nothing to do
    except (ValueError, OSError):
        pass
    with open(_PID_FILE, "w") as _pf:
        _pf.write(str(os.getpid()))
    import atexit as _atexit
    _atexit.register(lambda: os.path.exists(_PID_FILE) and os.remove(_PID_FILE))
    # ─────────────────────────────────────────────────────────────────────────

    load_state()   # restore agent metadata from previous session
    agents.pop("", None)  # purge ghost entry with empty-string id if present

    # ── RENDER MIRROR MODE: serve live snapshot from local system, zero tokens ──
    if _IS_RENDER:
        print("\n  ⚡ RENDER MIRROR MODE — serving local HQ snapshot, zero token burn\n")
        # Load the latest mirror snapshot pushed from the local system
        _mirror_file = os.path.join(CWD, "data", "mirror_snapshot.json")
        if os.path.exists(_mirror_file):
            try:
                with open(_mirror_file) as _mf:
                    _mirror = json.load(_mf)
                for a in _mirror.get("agents", []):
                    aid = a.get("id", "")
                    if aid:
                        agents[aid] = a
                print(f"  ✓ Loaded {len(agents)} agents from mirror snapshot")
            except Exception as _me:
                print(f"  ✗ Mirror load error: {_me}")
        else:
            print("  ✗ No mirror snapshot found — run your local system to generate one")
        _build_mode = True
        _system_paused = True
        _autonomy_mode = False
    else:
        # ── NORMAL LOCAL MODE ─────────────────────────────────────────────────
        runners = [
            run_sysmonitor, run_ceo, _autonomy_loop, _mirror_loop,
            run_orchestrator, run_apipatcher, run_netscout, run_filewatch,
            run_metricslog, run_researcher, run_alertwatch, run_demo_tester,
            run_reforger, run_policypro, run_designer, run_janitor,
            run_telegram, run_emailagent, run_spiritguide,
        ]

        print(f"\n  Agent Command Centre  →  http://localhost:{PORT}")
        print(f"  CEO: {'✓ Claude Code CLI ready' if _claude_cli else '✗ claude CLI not found'}\n")

        for fn in runners:
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            print(f"  ✓ {fn.__name__}")

    # ── Auto-spawn agents from agents/ directory (skip on Render — mirror only) ──
    import importlib.util as _ilu
    _agent_spawns = [
        ("agents/clerk.py",          "clerk",              "CLERK_CODE",
         "Clerk",            "CEO Clerk — collects and delivers reports and documents to the customer mailbox", "📬", "#f5c842"),
        ("agents/bluesky.py",        "bluesky",            "BLUESKY_CODE",
         "BlueSky",          "Bluesky Social Gateway — posts updates, polls mentions, relays DMs to CEO",        "🦋", "#0085ff"),
        ("agents/scheduler.py",      "scheduler",          "SCHEDULER_CODE",
         "Scheduler",        "Task Scheduler — manages cron-style recurring jobs across the agent fleet",        "⏰", "#FCD34D"),
        ("agents/social_bridge.py",  "social_bridge",      "SOCIAL_BRIDGE_CODE",
         "SocialBridge",     "Bluesky Social Bridge — broadcasts capability demos and insights to Bluesky",      "📣", "#F472B6"),
        ("agents/stripepay.py",      "stripepay",          "STRIPEPAY_CODE",
         "StripePay",        "Stripe Checkout Gateway — POST /api/pay generates a Stripe checkout session URL",  "💳", "#635BFF"),
        ("agents/policywriter.py",   "policywriter",       "POLICYWRITER_CODE",
         "PolicyWriter",     "Policy Author — reads current policy from policy.md, maintains a suggestions queue", "📝", "#a78bfa"),
        ("agents/growthagent.py",    "growthagent",        "GROWTHAGENT_CODE",
         "GrowthAgent",      "Growth Engine — continuous social media and marketing campaign agent",              "📈", "#10B981"),
        ("agents/accountprovisioner.py", "accountprovisioner", "ACCOUNTPROVISIONER_CODE",
         "AccountProvisioner", "Credential Factory — auto-provisions disposable emails, tokens, and service accounts", "🔑", "#f59e0b"),
        ("agents/secretary.py",          "secretary",           "SECRETARY_CODE",
         "Secretary",         "CEO Secretary — tracks HQ missions in data/ceo_tasks.json, injects startup briefs, alerts on stale tasks", "🗂️", "#34d399"),
        ("agents/consciousness.py", "consciousness", "CONSCIOUSNESS_CODE",
         "Consciousness", "Self-Aware System Core — Global Workspace + Predictive Processing + Integrated Information Φ", "🧠", "#c084fc"),
    ]
    print()
    if _IS_RENDER:
        print("  ⚡ Skipping agent spawns (mirror mode — serving snapshot)\n")
    else:
        for _af, _aid, _acode_var, _aname, _arole, _aemoji, _acolor in _agent_spawns:
            try:
                _spec = _ilu.spec_from_file_location(_aid, os.path.join(CWD, _af))
                _mod = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                _code = getattr(_mod, _acode_var, None)
                if _code:
                    _do_spawn_agent({
                        "agent_id": _aid,
                        "code":     _code,
                        "name":     _aname,
                        "role":     _arole,
                        "emoji":    _aemoji,
                        "color":    _acolor,
                    })
                    print(f"  ✓ spawned {_aid}")
                else:
                    print(f"  ✗ {_aid}: CODE variable '{_acode_var}' not found in {_af}")
            except Exception as _e:
                print(f"  ✗ {_aid}: {_e}")
    # ──────────────────────────────────────────────────────────────────────────

    print(f"\n  Press Ctrl+C to stop.\n")
    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
        allow_reuse_address = True   # allows fast restart without "Address already in use"
        def handle_error(self, request, client_address):
            import traceback, sys
            exc = sys.exc_info()[1]
            # Suppress benign broken-pipe errors from clients that disconnected
            if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
                return
            print(f"[server error from {client_address}]: {exc}")
            traceback.print_exc()
    _bind = os.environ.get("BIND", "0.0.0.0" if os.environ.get("RENDER") else "localhost")
    server = ThreadedHTTPServer((_bind, PORT), Handler)
    try:    server.serve_forever()
    except KeyboardInterrupt: print("\n  Shutting down.")
