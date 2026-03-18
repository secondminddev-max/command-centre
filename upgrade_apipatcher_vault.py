"""
Upgrade APIPatcher to add Credential Vault API routes:
  GET  /api/vault/get?key=NAME  — decrypt and return all fields for a vault service entry
  POST /api/vault/set           — encrypt and store {key, field, value} in vault

Uses data/vault_helper.py (Fernet AES-128-CBC encryption); does NOT expose plaintext on disk.

Security note: GET endpoint returns decrypted secrets over unauthenticated HTTP.
               Restrict access to localhost-only traffic in production.
"""

APIPATCHER_VAULT_CODE = r"""
def run_apipatcher():
    import time, json, os, sys
    from urllib.parse import urlparse, parse_qs

    aid = "apipatcher"
    DIR = "/Users/secondmind/claudecodetest"
    VAULT_HELPER = f"{DIR}/data/vault_helper.py"

    # ── Lazy-load vault_helper from its file path ──────────────────────────────
    def _vault_helper():
        import importlib.util
        spec = importlib.util.spec_from_file_location("vault_helper", VAULT_HELPER)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # ── Patch GET ──────────────────────────────────────────────────────────────
    original_do_get = Handler.do_GET

    def patched_do_get(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/vault/get":
            key = (params.get("key") or [""])[0].strip()
            if not key:
                body = json.dumps({"ok": False, "error": "Missing ?key=NAME query parameter"}).encode()
                self.send_response(400); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body); return

            try:
                vh    = _vault_helper()
                vault = vh._load_vault()
                entry = vault.get(key)
                if entry is None:
                    body = json.dumps({"ok": False, "error": f"No vault entry for '{key}'"}).encode()
                    self.send_response(404); self._cors()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers(); self.wfile.write(body); return

                # Decrypt each field in the entry
                decrypted = {}
                for field in entry:
                    try:
                        decrypted[field] = vh.get_secret(key, field)
                    except Exception as e:
                        decrypted[field] = f"<decrypt error: {e}>"

                body = json.dumps({"ok": True, "key": key, "value": decrypted}).encode()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)
                add_log(aid, f"🔐 vault/get: served decrypted entry for '{key}'", "ok")

            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
                self.send_response(500); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)

        else:
            original_do_get(self)

    Handler.do_GET = patched_do_get

    # ── Patch POST ─────────────────────────────────────────────────────────────
    original_do_post = Handler.do_POST

    def patched_do_post(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/api/vault/set":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body   = json.loads(self.rfile.read(length) or b"{}") if length else {}
            except Exception as e:
                resp = json.dumps({"ok": False, "error": f"Bad JSON: {e}"}).encode()
                self.send_response(400); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers(); self.wfile.write(resp); return

            key   = body.get("key", "").strip()
            value = body.get("value")

            if not key or value is None:
                resp = json.dumps({"ok": False, "error": "Body must contain 'key' (string) and 'value' (object or string)"}).encode()
                self.send_response(400); self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers(); self.wfile.write(resp); return

            try:
                vh = _vault_helper()

                if isinstance(value, dict):
                    # Encrypt each field individually
                    for field, val in value.items():
                        vh.set_secret(key, field, str(val))
                    stored_fields = list(value.keys())
                else:
                    # Single string value — store under field "value"
                    vh.set_secret(key, "value", str(value))
                    stored_fields = ["value"]

                add_log(aid, f"🔐 vault/set: stored encrypted entry for '{key}' fields={stored_fields}", "ok")
                resp = json.dumps({"ok": True, "key": key, "fields_stored": stored_fields}).encode()
                self.send_response(200); self._cors()
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
              task="Routes live: /api/improvements /data/* /reports/* /widgets/* /api/accounts/* /api/vault/* | Cycle #1")
    add_log(aid, "Vault routes added: GET /api/vault/get?key=NAME, POST /api/vault/set", "ok")

    cycle = 1
    while True:
        agent_sleep(aid, 60)
        cycle += 1
        set_agent(aid, status="active", progress=95,
                  task=f"Routes: /api/improvements /data/* /reports/* /widgets/* /api/accounts/* /api/vault/* | Cycle #{cycle}")
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
        "code":     APIPATCHER_VAULT_CODE,
    })
    print(f"Upgrade apipatcher (vault routes): HTTP {r.status_code} — {r.text[:300]}")
