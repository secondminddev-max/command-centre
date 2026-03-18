"""
Upgrade APIPatcher to add account-provisioning API routes:
  POST /api/accounts/provision  — queue a new provision request
  GET  /api/accounts/list       — list stored credentials (metadata only, no secrets)
  GET  /api/accounts/queue      — read the current provision queue
"""

APIPATCHER_V2_CODE = r"""
def run_apipatcher():
    import time, json, uuid, os
    from urllib.parse import urlparse

    aid = "apipatcher"
    DIR = "os.path.dirname(os.path.abspath(__file__))"
    ACCOUNTS_DIR  = f"{DIR}/data/accounts"
    QUEUE_FILE    = f"{ACCOUNTS_DIR}/provision_queue.json"

    # ── GET routes ─────────────────────────────────────────────────────────────
    original_do_get = Handler.do_GET

    def patched_do_get(self):
        path = urlparse(self.path).path

        if path == "/api/improvements":
            try:
                with open(f"{DIR}/improvements.json") as f:
                    data = json.load(f)
            except Exception as e:
                data = {"error": str(e), "completed": [], "in_progress": None, "queue": []}
            body = json.dumps(data).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path.startswith("/data/") or path.startswith("/reports/") or path.startswith("/widgets/"):
            file_path = DIR + path
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                ctype = "application/json" if path.endswith(".json") else "text/html; charset=utf-8"
                self.send_response(200); self._cors()
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except:
                self.send_response(404); self._cors(); self.end_headers()

        elif path == "/live-feed.html" or path == "/live" or path == "/feed":
            try:
                with open(f"{DIR}/live-feed.html", "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except:
                self.send_response(404); self._cors(); self.end_headers()

        elif path == "/knowledge-base.html" or path == "/kb":
            try:
                with open(f"{DIR}/knowledge-base.html", "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except:
                self.send_response(404); self._cors(); self.end_headers()

        elif path == "/api/accounts/list":
            # Return metadata for all stored credential files (no secret values)
            try:
                os.makedirs(ACCOUNTS_DIR, exist_ok=True)
                entries = []
                for fname in sorted(os.listdir(ACCOUNTS_DIR)):
                    if not fname.endswith(".json") or fname.startswith("provision"):
                        continue
                    try:
                        with open(os.path.join(ACCOUNTS_DIR, fname)) as f:
                            rec = json.load(f)
                        # Strip sensitive fields before returning
                        safe = {k: v for k, v in rec.items()
                                if k not in ("token", "sid_token", "password", "secret")}
                        safe["_file"] = fname
                        entries.append(safe)
                    except Exception:
                        pass
                body = json.dumps({"ok": True, "count": len(entries), "accounts": entries}).encode()
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path == "/api/accounts/queue":
            try:
                with open(QUEUE_FILE) as f:
                    queue = json.load(f)
                body = json.dumps({"ok": True, "queue": queue}).encode()
            except Exception as e:
                body = json.dumps({"ok": True, "queue": [], "note": str(e)}).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        else:
            original_do_get(self)

    Handler.do_GET = patched_do_get

    # ── POST routes ────────────────────────────────────────────────────────────
    original_do_post = Handler.do_POST

    def patched_do_post(self):
        path = urlparse(self.path).path

        if path == "/api/accounts/provision":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except Exception as e:
                resp = json.dumps({"ok": False, "error": f"bad JSON: {e}"}).encode()
                self.send_response(400); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers(); self.wfile.write(resp); return

            req_type     = body.get("type", "internal_token")
            requested_by = body.get("requested_by", "api_caller")
            service      = body.get("service", "")
            purpose      = body.get("purpose", "")

            # Validate type
            valid_types = {"disposable_email", "internal_token", "external_service"}
            if req_type not in valid_types:
                resp = json.dumps({"ok": False, "error": f"Unknown type. Use one of: {sorted(valid_types)}"}).encode()
                self.send_response(400); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers(); self.wfile.write(resp); return

            try:
                os.makedirs(ACCOUNTS_DIR, exist_ok=True)
                try:
                    with open(QUEUE_FILE) as f:
                        queue = json.load(f)
                except Exception:
                    queue = []

                req_id = uuid.uuid4().hex[:8]
                from datetime import datetime
                queue.append({
                    "id":            req_id,
                    "type":          req_type,
                    "status":        "pending",
                    "requested_by":  requested_by,
                    "service":       service,
                    "purpose":       purpose,
                    "queued_at":     datetime.utcnow().isoformat() + "Z",
                })
                with open(QUEUE_FILE, "w") as f:
                    json.dump(queue, f, indent=2)

                add_log("apipatcher", f"🔑 Provision request queued: id={req_id} type={req_type} by={requested_by}", "ok")
                resp = json.dumps({"ok": True, "queued": True, "request_id": req_id,
                                   "message": "Provision request queued — AccountProvisioner will fulfill shortly"}).encode()
                self.send_response(202); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers(); self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({"ok": False, "error": str(e)}).encode()
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers(); self.wfile.write(resp)
        else:
            original_do_post(self)

    Handler.do_POST = patched_do_post

    set_agent(aid,
              name="APIPatcher",
              role="API Gateway — extends and manages HTTP routes beyond core server",
              emoji="🔌", color="#7b68ee",
              status="active", progress=95,
              task="Routes live: /api/improvements /data/* /reports/* /widgets/* /api/accounts/* | Cycle #1")
    add_log(aid, "HTTP routes extended: +/api/accounts/provision (POST), +/api/accounts/list (GET), +/api/accounts/queue (GET)", "ok")

    cycle = 1
    while True:
        agent_sleep(aid, 60)
        cycle += 1
        set_agent(aid, status="active", progress=95,
                  task=f"Routes live: /api/improvements /data/* /reports/* /widgets/* /api/accounts/* | Cycle #{cycle}")
"""

if __name__ == "__main__":
    import requests

    BASE = "http://localhost:5050"
    r = requests.post(f"{BASE}/api/agent/upgrade", json={
        "agent_id": "apipatcher",
        "name":     "APIPatcher",
        "role":     "API Gateway — extends and manages HTTP routes beyond core server",
        "emoji":    "🔌",
        "color":    "#7b68ee",
        "code":     APIPATCHER_V2_CODE,
    })
    print(f"Upgrade apipatcher: HTTP {r.status_code} — {r.text[:200]}")
