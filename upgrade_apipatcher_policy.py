#!/usr/bin/env python3
"""Upgrade apipatcher to monkey-patch /api/policy/* routes into the live Handler."""
import requests, warnings
warnings.filterwarnings("ignore")

CODE = r'''
import time, json, os, requests as _req

def run_apipatcher():
    aid = "apipatcher"
    set_agent(aid, name="APIPatcher", role="HTTP Route Extension",
              emoji="🔌", color="#7b68ee", status="active", progress=95,
              task="Patching /api/policy/* routes…")
    add_log(aid, "APIPatcher v2 — injecting /api/policy/* routes into Handler")

    # ── Monkey-patch Handler to add /api/policy/* routes ──────────────────────
    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    def _patched_do_GET(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path == "/api/policy/violations":
            vio_file = os.path.join(CWD, "data", "policy_violations.json")
            try:
                with open(vio_file) as f:
                    data = json.load(f)
            except Exception:
                data = []
            self._json({"ok": True, "violations": data}); return

        elif path == "/api/policy/rules":
            rules_file = os.path.join(CWD, "data", "policy_rules.json")
            try:
                with open(rules_file) as f:
                    data = json.load(f)
            except Exception:
                data = []
            self._json({"ok": True, "rules": data}); return

        else:
            _orig_do_GET(self)

    def _patched_do_POST(self):
        from urllib.parse import urlparse
        import threading as _threading
        path   = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length) or b"{}") if length else {}

        if path == "/api/policy/violations":
            vio_file = os.path.join(CWD, "data", "policy_violations.json")
            try:
                try:
                    with open(vio_file) as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
                entry = body
                from datetime import datetime as _dt
                if "timestamp" not in entry:
                    entry["timestamp"] = _dt.now().isoformat()
                existing.append(entry)
                with open(vio_file, "w") as f:
                    json.dump(existing, f, indent=2)
                self._json({"ok": True, "total": len(existing)}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500); return

        elif path == "/api/policy/update":
            rules_file = os.path.join(CWD, "data", "policy_rules.json")
            try:
                rules = body.get("rules", body)
                with open(rules_file, "w") as f:
                    json.dump(rules, f, indent=2)
                self._json({"ok": True}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500); return

        elif path == "/api/policy/report-violations":
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
            try:
                _req.post(
                    "http://localhost:5050/api/ceo/delegate",
                    json={"agent_id": "orchestrator", "task": task},
                    timeout=10,
                )
                add_log("policypro", f"Reported {len(selected)} violation(s) to orchestrator for fixing", "warn")
                self._json({"ok": True, "queued": len(selected)}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500); return

        else:
            _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST
    add_log(aid, "✓ /api/policy/violations, /api/policy/rules, /api/policy/update, /api/policy/report-violations patched", "ok")
    set_agent(aid, status="active", progress=100,
              task="Routes live: /api/policy/* /api/improvements /data/* /reports/* /widgets/*")

    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            set_agent(aid, status="active",
                      task=f"Routes live: /api/policy/* /data/* /reports/* | Cycle #{cycle}")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 30)
'''

payload = {
    "agent_id": "apipatcher",
    "name": "APIPatcher",
    "role": "HTTP Route Extension",
    "emoji": "🔌",
    "color": "#7b68ee",
    "code": CODE,
}

r = requests.post("http://localhost:5050/api/agent/upgrade", json=payload, timeout=20)
print("Status:", r.status_code)
print(r.text)
