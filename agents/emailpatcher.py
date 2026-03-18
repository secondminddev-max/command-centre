"""
EmailPatcher — HTTP Email Routes
Monkey-patches into the live Handler:
  GET  /api/email/config
  POST /api/email/config
  POST /api/email/send
  GET  /api/email/status
"""

EMAILPATCHER_CODE = r"""
def run_emailpatcher():
    import json, os, threading, time
    from urllib.parse import urlparse

    aid = "emailpatcher"
    CWD = "/Users/secondmind/claudecodetest"
    CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
    SETUP_FILE  = os.path.join(CWD, "data", "sendgrid_setup.json")
    QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
    _lock = threading.Lock()

    SAFE_WRITE_FIELDS = {"smtp_host", "smtp_port", "from_addr", "default_to", "sendgrid_api_key"}

    set_agent(aid,
              name="EmailPatcher",
              role="HTTP Email Routes",
              emoji="📧",
              color="#00cc88",
              status="active", progress=10, task="Patching /api/email/config routes...")
    add_log(aid, "EmailPatcher starting — patching GET/POST /api/email/config", "ok")

    def _read_cfg():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as _f:
                return json.load(_f)
        return {}

    def _write_cfg(data):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as _f:
            json.dump(data, _f, indent=2)

    def _masked(cfg):
        # Return cfg with sensitive fields replaced by '***' if non-empty
        out = dict(cfg)
        for key in ("sendgrid_api_key", "smtp_pass"):
            if out.get(key, ""):
                out[key] = "***"
        return out

    # ── Monkey-patch Handler ──────────────────────────────────────────────────
    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    STATUS_FILE = os.path.join(CWD, "data", "email_stats.json")

    def _patched_do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/email/config":
            with _lock:
                cfg = _read_cfg()
            self._json({"ok": True, "config": _masked(cfg)})
            return

        if path == "/api/email/status":
            with _lock:
                st = {}
                if os.path.exists(STATUS_FILE):
                    try:
                        with open(STATUS_FILE) as _f:
                            st = json.load(_f)
                    except Exception:
                        st = {}
            # Merge with live config keys (masked) for convenience
            cfg = _read_cfg()
            st.setdefault("backend", "sendgrid" if cfg.get("sendgrid_api_key") or os.environ.get("SENDGRID_API_KEY") else "smtp")
            st.setdefault("sent_count", 0)
            st.setdefault("failed_count", 0)
            st.setdefault("last_recipient", "")
            self._json({"ok": True, **st})
            return

        _orig_do_GET(self)

    def _enqueue(msg):
        os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
        with _lock:
            queue = []
            if os.path.exists(QUEUE_FILE):
                try:
                    with open(QUEUE_FILE) as _f:
                        queue = json.load(_f)
                except Exception:
                    queue = []
            queue.append(msg)
            with open(QUEUE_FILE, "w") as _f:
                json.dump(queue, _f, indent=2)

    def _patched_do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/email/config":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                self._json({"ok": False, "error": "invalid JSON"}, 400)
                return

            with _lock:
                cfg = _read_cfg()
                updated = []
                for field in SAFE_WRITE_FIELDS:
                    if field in body:
                        cfg[field] = body[field]
                        updated.append(field)
                _write_cfg(cfg)

                # Also write sendgrid-specific fields to sendgrid_setup.json
                sg_setup = {}
                if os.path.exists(SETUP_FILE):
                    try:
                        with open(SETUP_FILE) as _sf:
                            sg_setup = json.load(_sf)
                    except Exception:
                        pass
                for field in ("sendgrid_api_key", "default_to", "from_address"):
                    if field in body and body[field]:
                        sg_setup[field] = body[field]
                if any(f in body for f in ("sendgrid_api_key", "default_to", "from_address")):
                    sg_setup["status"] = "configured" if sg_setup.get("sendgrid_api_key") else "needs_api_key"
                    os.makedirs(os.path.dirname(SETUP_FILE), exist_ok=True)
                    with open(SETUP_FILE, "w") as _sf:
                        json.dump(sg_setup, _sf, indent=2)

            add_log(aid, f"email config updated: {updated}", "ok")
            self._json({"ok": True, "updated": updated, "config": _masked(cfg)})
            return

        if path == "/api/email/send":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                self._json({"ok": False, "error": "invalid JSON"}, 400)
                return

            to_addr   = body.get("to", "").strip()
            from_addr = body.get("from", "").strip()
            subject   = body.get("subject", "").strip()
            msg_body  = body.get("body", "")
            is_html   = bool(body.get("html", False))

            if not subject:
                self._json({"ok": False, "error": "subject is required"}, 400)
                return

            entry = {
                "to":        to_addr,
                "from":      from_addr,
                "subject":   subject,
                "body":      msg_body,
                "html":      is_html,
                "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            _enqueue(entry)
            add_log(aid, f"Queued email to {to_addr or '(default)'}: {subject[:50]}", "ok")
            self._json({"ok": True, "queued": True,
                        "to": to_addr or "(uses default_to / EMAIL_TO)",
                        "subject": subject})
            return

        _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST

    add_log(aid, "✓ Routes patched: GET /api/email/config | GET /api/email/status | POST /api/email/config | POST /api/email/send", "ok")
    set_agent(aid, status="active", progress=100,
              task="Serving GET/POST /api/email/config | GET /api/email/status | POST /api/email/send")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        agent_sleep(aid, 60)
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys
    import urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "emailpatcher",
        "name":     "EmailPatcher",
        "role":     "HTTP Email Routes",
        "emoji":    "📧",
        "color":    "#00cc88",
        "code":     EMAILPATCHER_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read().decode())

    if result.get("ok"):
        print("✓ EmailPatcher spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
