"""
PolicyWriter Agent — Policy Author
Reads current policy from policy.md, maintains a suggestion queue,
auto-publishes suggestions after 30s (or immediately if urgent=true),
and notifies policypro on policy changes.

Routes (monkey-patched live + native in agent_server.py after restart):
  POST /api/policy/suggest  — {suggestion: str, urgent: bool}
  GET  /api/policy/current  — returns policy.md content
"""

POLICYWRITER_CODE = r'''
def run_policywriter():
    import time, threading
    from collections import deque as _deque
    from datetime import datetime as _dt
    from urllib.parse import urlparse as _urlparse

    aid = "policywriter"
    POLICY_FILE = "/Users/secondmind/claudecodetest/policy.md"
    BASE_URL = "http://localhost:5050"

    set_agent(aid,
              name="PolicyWriter",
              role="Policy Author — reads current policy from policy.md, maintains a suggestions queue, "
                   "auto-publishes suggestions after a 30-second review window (or immediately if urgent=true), "
                   "and notifies policypro when policy changes.",
              emoji="📝",
              color="#a78bfa",
              status="starting", progress=0, task="Initialising…")
    add_log(aid, "PolicyWriter starting — patching HTTP routes", "ok")

    # ── In-memory suggestion queue (also backed by _policy_suggestions global if available) ──
    _local_q = _deque()
    _local_q_lock = threading.Lock()

    def _enqueue(suggestion, urgent):
        with _local_q_lock:
            _local_q.append({"suggestion": suggestion, "urgent": urgent, "queued_at": time.time()})
            return len(_local_q)

    def _drain():
        # Return list of items ready to publish, leave non-ready ones in queue
        now = time.time()
        to_publish = []
        with _local_q_lock:
            remaining = _deque()
            for item in _local_q:
                if item["urgent"] or (now - item["queued_at"]) >= 30:
                    to_publish.append(item)
                else:
                    remaining.append(item)
            _local_q.clear()
            _local_q.extend(remaining)
        return to_publish

    def _pending_count():
        with _local_q_lock:
            return len(_local_q)

    # ── Live route monkey-patch (active until server restarts) ──
    # Guard against double-patching on agent restart/upgrade
    if not getattr(Handler, "_policywriter_patched", False):
        _orig_post = Handler.do_POST
        _orig_get  = Handler.do_GET

        def _pw_do_post(self):
            parsed = _urlparse(self.path)
            path   = parsed.path
            if path == "/api/policy/suggest":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    raw    = self.rfile.read(length)
                    body   = json.loads(raw or b"{}")
                    suggestion = body.get("suggestion", "").strip()
                    urgent     = bool(body.get("urgent", False))
                    if not suggestion:
                        self._json({"ok": False, "error": "suggestion required"}, 400)
                        return
                    pending = _enqueue(suggestion, urgent)
                    add_log(aid, f"Suggestion queued (urgent={urgent}): {suggestion[:60]}", "ok")
                    self._json({"ok": True, "queued": pending, "urgent": urgent})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return
            _orig_post(self)

        def _pw_do_get(self):
            parsed = _urlparse(self.path)
            path   = parsed.path
            if path == "/api/policy/current":
                try:
                    with open(POLICY_FILE) as f:
                        content = f.read()
                    self._json({"ok": True, "content": content, "pending_suggestions": _pending_count()})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 404)
                return
            _orig_get(self)

        Handler.do_POST = _pw_do_post
        Handler.do_GET  = _pw_do_get
        Handler._policywriter_patched = True
        add_log(aid, "Routes live: POST /api/policy/suggest | GET /api/policy/current", "ok")
    else:
        add_log(aid, "Routes already patched — skipping re-patch", "ok")

    set_agent(aid, status="active", progress=80,
              task="Routes live | Watching suggestion queue (30s window)")

    # ── Publish helper ──
    published_total = 0

    def _publish(item):
        nonlocal published_total
        suggestion = item["suggestion"]
        ts_str = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        section = f"\n\n## Policy Update — {ts_str}\n\n{suggestion}\n"
        try:
            with open(POLICY_FILE, "a") as f:
                f.write(section)
            published_total += 1
            add_log(aid, f"📝 Published policy update: {suggestion[:80]}", "ok")
            # Notify policypro via delegate
            try:
                requests.post(f"{BASE_URL}/api/ceo/delegate", json={
                    "agent_id": "policypro",
                    "task": (f"Policy updated by PolicyWriter at {ts_str}: {suggestion[:200]}. "
                             f"Review and enforce compliance as needed."),
                    "from": "policywriter",
                }, timeout=5)
            except Exception:
                pass
        except Exception as e:
            add_log(aid, f"Publish error: {e}", "error")

    # ── Main loop ──
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        agent_sleep(aid, 10)
        if agent_should_stop(aid):
            continue

        try:
            ready = _drain()
            for item in ready:
                _publish(item)

            pending = _pending_count()
            label = "urgent" if any(i["urgent"] for i in list(_local_q)) else "pending"
            set_agent(aid, status="active", progress=85,
                      task=f"Routes live | {pending} {label} | Published {published_total} total")
        except Exception as e:
            add_log(aid, f"Loop error: {e}", "error")
'''


# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "policywriter",
            "name":     "PolicyWriter",
            "role":     ("Policy Author — reads current policy from policy.md, maintains a suggestions queue, "
                         "auto-publishes suggestions after a 30-second review window (or immediately if urgent=true), "
                         "and notifies policypro when policy changes."),
            "emoji":    "📝",
            "color":    "#a78bfa",
            "code":     POLICYWRITER_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ PolicyWriter spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
