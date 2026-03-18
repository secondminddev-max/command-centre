#!/usr/bin/env python3
"""
Upgrade APIPatcher to inject:
  POST /api/emailagent/send   — SendGrid SMTP direct send, params: to, subject, body, html_body
  GET  /api/emailagent/status — Config health: credentials, FROM/TO env vars, counters
"""
import json, urllib.request

SERVER = "http://localhost:5050"

def post(path, data):
    body = json.dumps(data).encode()
    req  = urllib.request.Request(f"{SERVER}{path}", data=body,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

APIPATCHER_CODE = r'''
import time, json, os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def run_apipatcher():
    aid = "apipatcher"
    set_agent(aid, name="APIPatcher",
              role="API Gateway \u2014 extends and manages HTTP routes beyond core server",
              emoji="\U0001f50c", color="#7b68ee", status="active", progress=95,
              task="Patching /api/emailagent/* routes\u2026")
    add_log(aid, "APIPatcher v3 \u2014 injecting POST /api/emailagent/send + GET /api/emailagent/status")

    _orig_do_POST = Handler.do_POST
    _orig_do_GET  = Handler.do_GET

    def _patched_do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path == "/api/emailagent/send":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except Exception as e:
                self._json({"ok": False, "error": f"bad JSON: {e}"}, 400); return

            _to        = body.get("to", "").strip() or os.environ.get("TO_EMAIL", "").strip()
            _subject   = body.get("subject", "").strip()
            _html_body = body.get("html_body", "")
            _plain     = body.get("body", body.get("text", ""))
            _is_html   = bool(_html_body or body.get("html", False))
            _content   = _html_body if _html_body else _plain
            if not _to or not _subject:
                self._json({"ok": False, "error": "to and subject required (or set TO_EMAIL env var)"}); return
            _sg_key    = os.environ.get("SENDGRID_API_KEY", "").strip()
            _from_addr = (os.environ.get("FROM_EMAIL", "").strip()
                          or os.environ.get("SENDGRID_FROM_EMAIL", "").strip()
                          or "noreply@system.local")
            if not _sg_key:
                self._json({"ok": False, "error": "SENDGRID_API_KEY env var not set"}); return

            _last_exc = None
            _method   = None
            for _attempt in range(1, 4):
                try:
                    _mime = MIMEMultipart("alternative")
                    _mime["Subject"] = _subject
                    _mime["From"]    = _from_addr
                    _mime["To"]      = _to
                    _mime.attach(MIMEText(_content, "html" if _is_html else "plain"))
                    with smtplib.SMTP("smtp.sendgrid.net", 587, timeout=15) as _srv:
                        _srv.ehlo(); _srv.starttls(); _srv.ehlo()
                        _srv.login("apikey", _sg_key)
                        _srv.sendmail(_from_addr, [_to], _mime.as_string())
                    _method = "sendgrid-smtp"
                    _last_exc = None
                    break
                except Exception as _exc:
                    _last_exc = _exc
                    add_log("emailagent", f"/api/emailagent/send attempt {_attempt}/3 failed: {_exc}", "warn")
                    if _attempt < 3:
                        time.sleep(5)

            _ts = time.strftime("%Y-%m-%dT%H:%M:%S")
            if _last_exc is None:
                add_log("emailagent", f"Sent via {_method} to {_to}: {_subject}", "ok")
                set_agent("emailagent", task=f"Last sent {_ts} \u2192 {_to}: {_subject[:40]}")
                _LOG_FILE = os.path.join(CWD, "data", "email_log.json")
                try:
                    _log = json.load(open(_LOG_FILE)) if os.path.exists(_LOG_FILE) else []
                except Exception:
                    _log = []
                _log.append({"timestamp": _ts, "to": _to, "subject": _subject,
                             "method": _method, "success": True})
                _log = _log[-500:]
                with open(_LOG_FILE, "w") as _lf:
                    json.dump(_log, _lf, indent=2)
                self._json({"ok": True, "method": _method, "to": _to, "timestamp": _ts}); return
            else:
                add_log("emailagent", f"/api/emailagent/send failed after 3 attempts: {_last_exc}", "error")
                set_agent("emailagent", status="error", task=f"Send failed: {str(_last_exc)[:60]}")
                self._json({"ok": False, "error": str(_last_exc), "attempts": 3}); return
        else:
            _orig_do_POST(self)

    def _patched_do_GET(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path == "/api/emailagent/status":
            _QUEUE  = os.path.join(CWD, "data", "email_queue.json")
            _LOG    = os.path.join(CWD, "data", "email_log.json")
            _FAILED = os.path.join(CWD, "data", "email_failed.json")
            try:
                _q = json.load(open(_QUEUE)) if os.path.exists(_QUEUE) else []
            except Exception:
                _q = []
            try:
                _le = json.load(open(_LOG)) if os.path.exists(_LOG) else []
            except Exception:
                _le = []
            try:
                _fe = json.load(open(_FAILED)) if os.path.exists(_FAILED) else []
            except Exception:
                _fe = []
            _sg_set  = bool(os.environ.get("SENDGRID_API_KEY", "").strip())
            _from_em = (os.environ.get("FROM_EMAIL", "").strip()
                        or os.environ.get("SENDGRID_FROM_EMAIL", "").strip())
            _to_em   = os.environ.get("TO_EMAIL", "").strip()
            _healthy = _sg_set and bool(_from_em)
            _last_ok = next((e["timestamp"] for e in reversed(_le) if e.get("success")), None)
            _issues  = []
            if not _sg_set:
                _issues.append("SENDGRID_API_KEY not set")
            if not _from_em:
                _issues.append("FROM_EMAIL / SENDGRID_FROM_EMAIL not set")
            _payload = {
                "ok": True,
                "healthy": _healthy,
                "backend": "sendgrid-smtp",
                "smtp_host": "smtp.sendgrid.net",
                "smtp_port": 587,
                "smtp_user": "apikey",
                "credentials_configured": _sg_set,
                "from_email_configured": bool(_from_em),
                "from_email": _from_em or None,
                "to_email_default": _to_em or None,
                "queued": len(_q),
                "sent": sum(1 for e in _le if e.get("success")),
                "failed": len(_fe),
                "last_sent": _last_ok,
                "issues": _issues,
            }
            _body = json.dumps(_payload).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(_body)))
            self.end_headers(); self.wfile.write(_body)
        else:
            _orig_do_GET(self)

    Handler.do_POST = _patched_do_POST
    Handler.do_GET  = _patched_do_GET
    add_log(aid, "\u2713 POST /api/emailagent/send + GET /api/emailagent/status live", "ok")
    set_agent(aid, status="active", progress=100,
              task="Routes live: /api/emailagent/send /api/emailagent/status /api/improvements /data/* /reports/*")

    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        cycle += 1
        set_agent(aid, status="active",
                  task=f"Routes live: /api/emailagent/send /api/emailagent/status /data/* /reports/* | Cycle #{cycle}")
        agent_sleep(aid, 30)
'''

payload = {
    "agent_id": "apipatcher",
    "name":     "APIPatcher",
    "role":     "API Gateway \u2014 extends and manages HTTP routes beyond core server",
    "emoji":    "\U0001f50c",
    "color":    "#7b68ee",
    "code":     APIPATCHER_CODE,
}

print("Upgrading apipatcher...", end=" ", flush=True)
result = post("/api/agent/upgrade", payload)
status = "\u2713" if result.get("ok") else "\u2717"
print(f"{status} {result.get('result', result.get('error', result))}")
