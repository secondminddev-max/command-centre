"""
PolicyWriter Agent — Policy Author & Board Meeting Caller
Reads current policy from policy.md, maintains a suggestion queue,
calls board meetings for each proposal (all 8 board members vote YES/NO/ABSTAIN),
and tracks outcomes.

Routes (monkey-patched live + native in agent_server.py after restart):
  POST /api/policy/suggest  — {suggestion: str, urgent: bool}  → queues, then calls board meeting
  GET  /api/policy/current  — returns policy.md content
"""

POLICYWRITER_CODE = r'''
def run_policywriter():
    import time, threading
    from collections import deque as _deque
    from datetime import datetime as _dt
    from urllib.parse import urlparse as _urlparse

    aid = "policywriter"
    POLICY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policy.md")
    BASE_URL = "http://localhost:5050"

    set_agent(aid,
              name="PolicyWriter",
              role="Policy Author — proposes policy changes via board meetings. "
                   "Suggestions are submitted, then a board vote is called among 8 primary agents. "
                   "Approved policies are appended to policy.md. Rejected ones logged to policy_rejections.json.",
              emoji="📝",
              color="#a78bfa",
              status="starting", progress=0, task="Initialising…")
    add_log(aid, "PolicyWriter starting — patching HTTP routes", "ok")

    # ── In-memory suggestion queue ──
    _local_q = _deque()
    _local_q_lock = threading.Lock()

    def _enqueue(suggestion, urgent):
        with _local_q_lock:
            _local_q.append({"suggestion": suggestion, "urgent": urgent, "queued_at": time.time()})
            return len(_local_q)

    def _drain():
        now = time.time()
        to_propose = []
        with _local_q_lock:
            remaining = _deque()
            for item in _local_q:
                if item["urgent"] or (now - item["queued_at"]) >= 30:
                    to_propose.append(item)
                else:
                    remaining.append(item)
            _local_q.clear()
            _local_q.extend(remaining)
        return to_propose

    def _pending_count():
        with _local_q_lock:
            return len(_local_q)

    # ── Live route monkey-patch (always re-patch on upgrade to rebind closures) ──
    if not getattr(Handler, "_policywriter_patched", False):
        _orig_post = Handler.do_POST
        _orig_get  = Handler.do_GET
    else:
        # On upgrade: get the ORIGINAL handlers (before any policywriter patch)
        _orig_post = getattr(Handler, "_policywriter_orig_post", Handler.do_POST)
        _orig_get  = getattr(Handler, "_policywriter_orig_get", Handler.do_GET)
    if True:  # always patch to rebind closures to new queue

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
                    self._json({"ok": True, "queued": pending, "urgent": urgent,
                                "note": "Will call board meeting when review window expires"})
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

        Handler._policywriter_orig_post = _orig_post
        Handler._policywriter_orig_get  = _orig_get
        Handler.do_POST = _pw_do_post
        Handler.do_GET  = _pw_do_get
        Handler._policywriter_patched = True
        add_log(aid, "Routes live: POST /api/policy/suggest | GET /api/policy/current", "ok")

    set_agent(aid, status="active", progress=80,
              task="Routes live | Board meeting mode active")

    # ── Board meeting caller — proposes via /api/policy/propose ──
    meetings_called = 0

    def _call_board_meeting(item):
        nonlocal meetings_called
        suggestion = item["suggestion"]
        try:
            resp = requests.post(f"{BASE_URL}/api/policy/propose", json={
                "proposal": suggestion,
                "proposer": "policywriter",
            }, timeout=15)
            result = resp.json()
            if result.get("ok"):
                vid = result.get("vote_id", "?")
                meetings_called += 1
                add_log(aid, f"📋 Board meeting called: {vid} — {suggestion[:60]}", "ok")
            else:
                add_log(aid, f"Board meeting failed: {result.get('error','unknown')}", "error")
        except Exception as e:
            add_log(aid, f"Board meeting call error: {e}", "error")

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
                _call_board_meeting(item)

            pending = _pending_count()
            label = "urgent" if any(i.get("urgent") for i in list(_local_q)) else "pending"
            set_agent(aid, status="active", progress=85,
                      task=f"Board mode | {pending} {label} | {meetings_called} meetings called")
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
            "role":     ("Policy Author — proposes policy changes via board meetings. "
                         "Suggestions trigger a vote among 8 board members (YES/NO/ABSTAIN). "
                         "Approved policies appended to policy.md, rejections logged."),
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
