#!/usr/bin/env python3
"""Upgrade apipatcher to enhance GET /api/email/status with credential info."""
import json, urllib.request

CODE = r'''
import time, json, os

def run_apipatcher():
    aid = "apipatcher"
    set_agent(aid, name="APIPatcher", role="API Gateway \u2014 extends and manages HTTP routes beyond core server",
              emoji="\U0001f50c", color="#7b68ee", status="active", progress=95,
              task="Patching /api/email/status route\u2026")
    add_log(aid, "APIPatcher \u2014 injecting enhanced GET /api/email/status into Handler")

    CWD_LOCAL = "/Users/secondmind/claudecodetest"

    # Patch GET handler to enhance /api/email/status
    _orig_do_GET = Handler.do_GET

    def _patched_do_get(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path == "/api/email/status":
            QUEUE_FILE  = os.path.join(CWD_LOCAL, "data", "email_queue.json")
            LOG_FILE    = os.path.join(CWD_LOCAL, "data", "email_log.json")
            FAILED_FILE = os.path.join(CWD_LOCAL, "data", "email_failed.json")
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
            _sg_configured = bool(os.environ.get("SENDGRID_API_KEY", "").strip())
            _from_email    = os.environ.get("SENDGRID_FROM_EMAIL", "").strip()
            payload = {
                "ok": True,
                "queued":                len(queue),
                "sent":                  sent_count,
                "failed":                len(failed),
                "backend":               "sendgrid-smtp",
                "credentials_configured": _sg_configured,
                "from_email_configured": bool(_from_email),
                "smtp_host":             "smtp.sendgrid.net",
                "smtp_port":             587,
                "send_endpoint":         "POST /api/email/send",
                "send_payload":          '{"to":"...","subject":"...","body":"...","html":false}',
            }
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            _orig_do_GET(self)

    Handler.do_GET = _patched_do_get
    add_log(aid, "\u2713 GET /api/email/status enhanced with credential info", "ok")
    set_agent(aid, status="active", progress=99,
              task="Routes live: /api/improvements /data/* /reports/* /widgets/* /api/email/status | Cycle #101")

    cycle = 101
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        try:
            cycle += 1
            set_agent(aid, status="active",
                      task=f"Routes live: /api/improvements /data/* /reports/* /widgets/* /api/email/status | Cycle #{cycle}")
        except Exception as e:
            add_log(aid, f"Error: {e}", "error")
        agent_sleep(aid, 30)
'''

payload = json.dumps({
    "agent_id": "apipatcher",
    "name":     "APIPatcher",
    "role":     "API Gateway \u2014 extends and manages HTTP routes beyond core server",
    "emoji":    "\U0001f50c",
    "color":    "#7b68ee",
    "code":     CODE,
}).encode()

req = urllib.request.Request("http://localhost:5050/api/agent/upgrade",
                             data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=20) as r:
    result = json.loads(r.read())

status = "\u2713" if result.get("ok") else "\u2717"
print(f"{status} apipatcher: {result.get('result', result.get('error'))}")
