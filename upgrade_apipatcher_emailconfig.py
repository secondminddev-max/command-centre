#!/usr/bin/env python3
"""Upgrade apipatcher to add POST /api/email/config route.
Accepts {sendgrid_api_key, default_to, from_address} and writes to data/sendgrid_setup.json.
"""
import requests, warnings
warnings.filterwarnings("ignore")

CODE = r'''
import time, json, os

def run_apipatcher():
    aid = "apipatcher"
    set_agent(aid, name="APIPatcher", role="HTTP Route Extension",
              emoji="\U0001f50c", color="#7b68ee", status="active", progress=95,
              task="Patching /api/email/config route\u2026")
    add_log(aid, "APIPatcher \u2014 injecting POST /api/email/config into Handler")

    # Chain onto whatever patches are already applied
    _orig_do_POST = Handler.do_POST

    def _patched_do_post(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path == "/api/email/config":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except Exception as e:
                self._json({"ok": False, "error": f"bad JSON: {e}"}, 400); return

            setup_file = os.path.join(CWD, "data", "sendgrid_setup.json")
            try:
                # Load existing to preserve unknown fields
                existing = {}
                if os.path.exists(setup_file):
                    try:
                        with open(setup_file) as _f:
                            existing = json.load(_f)
                    except Exception:
                        pass

                # Apply provided fields
                for key in ("sendgrid_api_key", "default_to", "from_address"):
                    if key in body:
                        existing[key] = body[key]
                existing["status"] = "configured"

                os.makedirs(os.path.dirname(setup_file), exist_ok=True)
                with open(setup_file, "w") as _f:
                    json.dump(existing, _f, indent=2)

                add_log("apipatcher", f"email/config updated: to={existing.get('default_to','')} from={existing.get('from_address','')}", "ok")
                self._json({"ok": True}); return
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500); return

        else:
            _orig_do_POST(self)

    Handler.do_POST = _patched_do_post
    add_log(aid, "\u2713 POST /api/email/config patched into Handler", "ok")
    set_agent(aid, status="active", progress=100,
              task="Routes live: /api/email/config /api/policy/* /data/* /reports/* /widgets/*")

    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            set_agent(aid, status="active",
                      task=f"Routes live: /api/email/config /api/policy/* /data/* | Cycle #{cycle}")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 30)
'''

payload = {
    "agent_id": "apipatcher",
    "name":     "APIPatcher",
    "role":     "HTTP Route Extension",
    "emoji":    "\U0001f50c",
    "color":    "#7b68ee",
    "code":     CODE,
}

r = requests.post("http://localhost:5050/api/agent/upgrade", json=payload, timeout=20)
print("Status:", r.status_code)
print(r.text)
