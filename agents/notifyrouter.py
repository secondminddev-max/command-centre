"""
NotifyRouter — Central Notification Router
Patches POST /api/notify into the live Handler.
Accepts {event_type, message, severity, agent, timestamp} and routes to Telegram if configured.
"""

NOTIFYROUTER_CODE = r"""
def run_notifyrouter():
    import json, time, os
    from urllib.parse import urlparse
    from datetime import datetime, timezone

    aid = "notifyrouter"

    set_agent(aid,
              name="NotifyRouter",
              role="Notification Router — POST /api/notify routes events to Telegram",
              emoji="🔔",
              color="#f59e0b",
              status="active", progress=10, task="Initialising…")
    add_log(aid, "NotifyRouter starting — patching POST /api/notify", "ok")

    # ── Cooldown tracking ─────────────────────────────────────────────────────
    _cooldown     = {}   # event_key -> last_sent epoch
    _COOLDOWN_SECS = 300  # 5-minute suppress window per event:agent pair

    def _send_telegram(text):
        # Send via the server's own /api/telegram/send endpoint
        import urllib.request, urllib.error
        try:
            data = json.dumps({"text": text}).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:5050/api/telegram/send",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=8)
        except Exception as _e:
            add_log(aid, f"Telegram relay failed: {_e}", "warn")

    def _dispatch(event_type, message, severity, agent_id, timestamp):
        # Apply cooldown then route to Telegram
        event_key = f"{event_type}:{agent_id}"
        now = time.time()
        if now - _cooldown.get(event_key, 0) < _COOLDOWN_SECS:
            return False  # suppressed
        _cooldown[event_key] = now
        sev_icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️", "success": "✅"}.get(severity, "📢")
        text = (
            f"{sev_icon} [{severity.upper()}] {event_type}\n"
            f"🤖 Agent: {agent_id}\n"
            f"⏰ {timestamp}\n"
            f"{message}"
        )
        add_log(aid, f"notify [{severity}] {event_type} from {agent_id} — {message[:80]}", "ok")
        _send_telegram(text)
        return True

    # ── Monkey-patch Handler ──────────────────────────────────────────────────
    _orig_do_POST = getattr(Handler, "_notifyrouter_orig_do_POST", Handler.do_POST)

    def _patched_do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/notify":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw    = self.rfile.read(length) if length else b"{}"
                body   = json.loads(raw) if raw else {}
            except Exception:
                body = {}

            evt   = body.get("event_type", "notification")
            msg   = body.get("message", "")
            sev   = body.get("severity", "info")
            agent = body.get("agent", "system")
            ts    = body.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            if not msg:
                self._json({"ok": False, "error": "message field required"}, 400)
                return

            routed = _dispatch(evt, msg, sev, agent, ts)
            self._json({"ok": True, "event_type": evt, "severity": sev,
                        "routed": routed, "suppressed": not routed})
            return

        _orig_do_POST(self)

    # Store original for idempotent re-spawn
    Handler._notifyrouter_orig_do_POST = _orig_do_POST
    Handler.do_POST = _patched_do_POST

    add_log(aid, "✓ Route patched: POST /api/notify", "ok")
    set_agent(aid, status="active", progress=100,
              task="POST /api/notify live | routes to Telegram with 5-min cooldown")

    # ── Idle loop ─────────────────────────────────────────────────────────────
    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        agent_sleep(aid, 120)
        if agent_should_stop(aid):
            continue
        cycle += 1
        set_agent(aid, status="active", progress=100,
                  task=f"POST /api/notify live | dispatched events: {len(_cooldown)} tracked | Cycle #{cycle}")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "notifyrouter",
            "name":     "NotifyRouter",
            "role":     "Notification Router — POST /api/notify routes critical events to Telegram",
            "emoji":    "🔔",
            "color":    "#f59e0b",
            "code":     NOTIFYROUTER_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ NotifyRouter spawned — POST /api/notify is live")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
