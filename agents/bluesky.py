"""
BlueSky Agent — Bluesky Social Gateway
Posts updates, polls mentions, relays DMs to CEO via Bluesky AT Protocol.
"""

BLUESKY_CODE = r"""
def run_bluesky():
    import time, json, threading
    from datetime import datetime, timezone
    import requests as req

    import os
    aid = "bluesky"
    BASE_API   = "http://localhost:5050"
    BSKY_API   = "https://bsky.social/xrpc"
    IDENTIFIER = os.environ.get("BLUESKY_HANDLE", "secondmindhq.bsky.social")
    PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

    # Shared auth state (thread-safe via lock)
    _auth = {"jwt": None, "did": None, "issued_at": 0.0}
    _auth_lock = threading.Lock()

    # In-memory post queue — filled by /api/bluesky/post HTTP endpoint
    _post_queue = []
    _queue_lock = threading.Lock()
    _last_external_post_time = 0.0  # timestamp of last post sent to Bluesky

    set_agent(aid,
              name="BlueSky",
              role="Bluesky Social Gateway — posts updates, polls mentions, relays DMs to CEO",
              emoji="🦋",
              color="#0085ff",
              status="idle", progress=0, task="Initialising…")
    add_log(aid, "BlueSky agent starting up", "ok")

    # ── Register /api/bluesky/post and /api/bluesky/status routes ────────────
    from urllib.parse import urlparse

    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    def _patched_do_GET(self):
        path = urlparse(self.path).path
        if path in ("/api/bluesky/status", "/api/agent/bluesky/task"):
            with _auth_lock:
                authenticated = bool(_auth["jwt"])
                did = _auth["did"] or ""
            with _queue_lock:
                pending = len(_post_queue)
            self._json({
                "ok": True,
                "authenticated": authenticated,
                "did": did,
                "pending_posts": pending,
            })
            return
        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/bluesky/post":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                self._json({"ok": False, "error": "invalid JSON"}, 400)
                return
            msg = (body.get("text") or body.get("message") or "").strip()
            if not msg:
                self._json({"ok": False, "error": "text field required"}, 400)
                return
            image_path = body.get("image_path") or None
            with _queue_lock:
                _post_queue.append({"text": msg, "image_path": image_path})
            add_log(aid, f"Post queued via API: {msg[:80]}", "ok")
            self._json({"ok": True, "queued": True})
            return
        _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST
    add_log(aid, "✓ Routes patched: GET /api/bluesky/status | POST /api/bluesky/post", "ok")

    # ── Auth helpers ──────────────────────────────────────────────────────────
    def authenticate():
        try:
            r = req.post(f"{BSKY_API}/com.atproto.server.createSession",
                         json={"identifier": IDENTIFIER, "password": PASSWORD},
                         timeout=15)
            if r.status_code == 200:
                data = r.json()
                with _auth_lock:
                    _auth["jwt"] = data["accessJwt"]
                    _auth["did"] = data["did"]
                    _auth["issued_at"] = time.time()
                add_log(aid, f"Authenticated as {IDENTIFIER} (DID: {data['did'][:20]}…)", "ok")
                return True
            else:
                add_log(aid, f"Auth failed {r.status_code}: {r.text[:120]}", "warn")
                return False
        except Exception as e:
            add_log(aid, f"Auth exception: {e}", "warn")
            return False

    def get_headers():
        with _auth_lock:
            return {"Authorization": f"Bearer {_auth['jwt']}",
                    "Content-Type": "application/json"}

    def get_did():
        with _auth_lock:
            return _auth["did"]

    # ── Upload image blob to Bluesky ──────────────────────────────────────────
    def upload_image_to_bluesky(image_path_or_bytes):
        import mimetypes, os
        try:
            with _auth_lock:
                jwt = _auth["jwt"]
            if not jwt:
                add_log(aid, "Cannot upload image — not authenticated", "warn")
                return None
            if isinstance(image_path_or_bytes, (str, os.PathLike)):
                path = str(image_path_or_bytes)
                mime, _ = mimetypes.guess_type(path)
                if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                    mime = "image/jpeg"
                with open(path, "rb") as f:
                    data = f.read()
            else:
                data = bytes(image_path_or_bytes)
                mime = "image/png"
            r = req.post(
                f"{BSKY_API}/com.atproto.repo.uploadBlob",
                headers={"Authorization": f"Bearer {jwt}", "Content-Type": mime},
                data=data,
                timeout=30,
            )
            if r.status_code in (200, 201):
                blob_ref = r.json().get("blob")
                add_log(aid, "Image blob uploaded successfully", "ok")
                return blob_ref
            add_log(aid, f"Image upload failed {r.status_code}: {r.text[:120]}", "warn")
            return None
        except Exception as e:
            add_log(aid, f"Image upload exception: {e}", "warn")
            return None

    # ── Post to Bluesky ───────────────────────────────────────────────────────
    def post_to_bluesky(text, image_path=None):
        try:
            did = get_did()
            if not did:
                add_log(aid, "Cannot post — not authenticated", "warn")
                return False
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            record = {
                "text":      text,
                "createdAt": now,
                "langs":     ["en"],
            }
            if image_path:
                blob_ref = upload_image_to_bluesky(image_path)
                if blob_ref:
                    record["embed"] = {
                        "$type":  "app.bsky.embed.images#main",
                        "images": [{"image": blob_ref, "alt": "screenshot"}],
                    }
                else:
                    add_log(aid, "Image upload failed — posting text-only", "warn")
            r = req.post(
                f"{BSKY_API}/com.atproto.repo.createRecord",
                headers=get_headers(),
                json={
                    "repo":       did,
                    "collection": "app.bsky.feed.post",
                    "record":     record,
                },
                timeout=15,
            )
            if r.status_code in (400, 401):
                err_body = r.text[:200]
                if r.status_code == 400 and "ExpiredToken" not in err_body:
                    add_log(aid, f"Post failed 400 (non-token): {err_body}", "warn")
                    return False
                add_log(aid, f"JWT expired (HTTP {r.status_code}) — re-authenticating…", "warn")
                if authenticate():
                    return post_to_bluesky(text, image_path)   # retry once
                return False
            if r.status_code in (200, 201):
                add_log(aid, f"Posted to Bluesky: {text[:80]}", "ok")
                return True
            add_log(aid, f"Post failed {r.status_code}: {r.text[:120]}", "warn")
            return False
        except Exception as e:
            add_log(aid, f"Post exception: {e}", "warn")
            return False

    # ── Relay mention to CEO ──────────────────────────────────────────────────
    def relay_to_ceo(handle, text):
        try:
            req.post(f"{BASE_API}/api/ceo/message",
                     json={"from": "bluesky",
                           "message": f"Bluesky mention from @{handle}: {text}"},
                     timeout=10)
        except Exception as e:
            add_log(aid, f"CEO relay error: {e}", "warn")

    # ── Poll Bluesky notifications (mentions/replies) ─────────────────────────
    _seen_notification_uris = set()

    def poll_notifications():
        try:
            with _auth_lock:
                jwt = _auth["jwt"]
            if not jwt:
                return
            r = req.get(
                f"{BSKY_API}/app.bsky.notification.listNotifications",
                headers=get_headers(),
                params={"limit": 20},
                timeout=15,
            )
            # Handle token expiry — re-auth and retry once
            if r.status_code in (400, 401):
                err_body = r.text
                if "ExpiredToken" in err_body or r.status_code == 401:
                    add_log(aid, "JWT expired during notification poll — re-authenticating…", "warn")
                    if not authenticate():
                        add_log(aid, "Re-auth failed — skipping notification poll this cycle", "warn")
                        return
                    # Retry with fresh token
                    r = req.get(
                        f"{BSKY_API}/app.bsky.notification.listNotifications",
                        headers=get_headers(),
                        params={"limit": 20},
                        timeout=15,
                    )
                    if r.status_code != 200:
                        add_log(aid, f"Notification poll retry failed {r.status_code}: {r.text[:120]}", "warn")
                        return
                else:
                    add_log(aid, f"Notification poll {r.status_code}: {err_body[:200]}", "warn")
                    return
            elif r.status_code != 200:
                add_log(aid, f"Notification poll {r.status_code}: {r.text[:120]}", "warn")
                return

            notifications = r.json().get("notifications", [])
            new_items = [
                n for n in notifications
                if not n.get("isRead")
                and n.get("reason") in ("mention", "reply")
                and n.get("uri") not in _seen_notification_uris
            ]
            for n in new_items:
                uri = n.get("uri", "")
                _seen_notification_uris.add(uri)
                handle = n.get("author", {}).get("handle", "unknown")
                text   = n.get("record", {}).get("text", "")
                relay_to_ceo(handle, text)
                add_log(aid, f"Relayed mention from @{handle}: {text[:80]}", "ok")
        except Exception as e:
            add_log(aid, f"Notification poll exception: {e}", "warn")

    # ── Startup: authenticate (stays idle — no self-activation) ─────────────
    set_agent(aid, status="idle", progress=10, task="Authenticating with Bluesky…")
    auth_ok = False
    for _attempt in range(3):
        if authenticate():
            auth_ok = True
            break
        time.sleep(5)

    if not auth_ok:
        set_agent(aid, status="idle", progress=0,
                  task="Auth failed — will retry in poll loop")
        add_log(aid, "Initial auth failed — will keep retrying", "warn")
    else:
        add_log(aid, "Authenticated — idle, awaiting delegation", "ok")

    cycle = 0

    set_agent(aid, status="idle", progress=0, task="Idle — awaiting delegation")

    # ── Main loop ─────────────────────────────────────────────────────────────
    while not agent_should_stop(aid):
        cycle += 1
        try:
            # Re-authenticate only if JWT is missing or older than 90 minutes
            with _auth_lock:
                jwt       = _auth["jwt"]
                issued_at = _auth["issued_at"]
            token_age = time.time() - issued_at
            if not jwt:
                add_log(aid, "No JWT — re-authenticating…", "warn")
                authenticate()
            elif token_age > 5400:  # 90 minutes — proactive refresh before expiry
                add_log(aid, f"JWT age {token_age/60:.0f}min — proactive refresh", "info")
                authenticate()

            # Poll for new mentions/replies and relay to CEO (passive — stays idle)
            poll_notifications()

            # Drain the post queue — enforce 1-hour minimum between posts
            # Only go active when there is delegated work (queued posts)
            with _queue_lock:
                pending = list(_post_queue)
                _post_queue.clear()
            if pending:
                set_agent(aid, status="active", progress=50,
                          task=f"Sending {len(pending)} delegated post(s)…")
                held = []
                for idx, item in enumerate(pending):
                    elapsed = time.time() - _last_external_post_time
                    if elapsed < 3600:
                        # Rate limit active — hold this and all remaining posts
                        held = pending[idx:]
                        break
                    post_to_bluesky(item["text"], item.get("image_path"))
                    _last_external_post_time = time.time()
                    time.sleep(3)  # secondary buffer between posts
                    # Only one post per cycle — hold the rest
                    if idx + 1 < len(pending):
                        held = pending[idx + 1:]
                    break
                if held:
                    wait_secs = int(3600 - (time.time() - _last_external_post_time))
                    add_log(aid, f"Rate limit: next post allowed in {wait_secs}s — holding {len(held)} post(s) in queue", "info")
                    with _queue_lock:
                        _post_queue[:0] = held  # prepend held posts to preserve order

                # Return to idle after processing delegated work
                with _queue_lock:
                    remaining = len(_post_queue)
                if remaining:
                    set_agent(aid, status="active", progress=30,
                              task=f"Idle | {remaining} post(s) rate-limited in queue")
                else:
                    set_agent(aid, status="idle", progress=0,
                              task=f"Idle | Tasks: {cycle}")
            # If no pending posts, ensure we stay idle (don't self-activate)

        except Exception as e:
            add_log(aid, f"Main loop error: {e}", "warn")
            set_agent(aid, status="idle", progress=0,
                      task=f"Idle (error): {str(e)[:80]}")

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", progress=0, task="BlueSky agent stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    result = requests.post(f"{BASE}/api/agent/spawn", json={
        "agent_id": "bluesky",
        "name":     "BlueSky",
        "role":     "Bluesky Social Gateway — posts updates, polls mentions, relays DMs to CEO",
        "emoji":    "🦋",
        "color":    "#0085ff",
        "code":     BLUESKY_CODE,
    }, timeout=10).json()

    if result.get("ok"):
        print("✓ BlueSky agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
