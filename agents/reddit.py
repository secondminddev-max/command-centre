"""
Reddit Agent — Reddit Social Gateway
Posts updates, monitors mentions, relays messages to CEO via Reddit API.
"""

REDDIT_CODE = r"""
def run_reddit():
    import time, json, threading
    from datetime import datetime, timezone
    import requests as req
    import os

    aid = "reddit"
    BASE_API = "http://localhost:5050"
    REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    REDDIT_API = "https://oauth.reddit.com"

    CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
    CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
    USERNAME      = os.environ.get("REDDIT_USERNAME", "")
    PASSWORD      = os.environ.get("REDDIT_PASSWORD", "")
    DEFAULT_SUB   = os.environ.get("REDDIT_SUBREDDIT", "")
    USER_AGENT    = os.environ.get("REDDIT_USER_AGENT", f"python:secondmindhq:v1.0 (by /u/{USERNAME})")

    # Shared auth state
    _auth = {"token": None, "expires_at": 0.0}
    _auth_lock = threading.Lock()

    # Post queue
    _post_queue = []
    _queue_lock = threading.Lock()
    _last_external_post_time = 0.0
    MAX_QUEUE = 200

    set_agent(aid,
              name="Reddit",
              role="Reddit Social Gateway — posts updates, monitors mentions, relays to CEO",
              emoji="🔴",
              color="#FF4500",
              status="idle", progress=0, task="Initialising…")
    add_log(aid, "Reddit agent starting up", "ok")

    # ── Register API routes ────────────────────────────────────────────────────
    from urllib.parse import urlparse

    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    def _patched_do_GET(self):
        path = urlparse(self.path).path
        if path in ("/api/reddit/status", "/api/agent/reddit/task"):
            with _auth_lock:
                authenticated = bool(_auth["token"])
            with _queue_lock:
                pending = len(_post_queue)
            self._json({
                "ok": True,
                "authenticated": authenticated,
                "username": USERNAME,
                "default_subreddit": DEFAULT_SUB,
                "pending_posts": pending,
            })
            return
        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/reddit/post":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                self._json({"ok": False, "error": "invalid JSON"}, 400)
                return
            title = (body.get("title") or "").strip()
            text = (body.get("text") or body.get("message") or "").strip()
            subreddit = (body.get("subreddit") or DEFAULT_SUB).strip()
            kind = body.get("kind", "self")  # "self" or "link"
            url = (body.get("url") or "").strip()
            if not title and not text:
                self._json({"ok": False, "error": "title or text required"}, 400)
                return
            if not subreddit:
                self._json({"ok": False, "error": "subreddit required (no default set)"}, 400)
                return
            with _queue_lock:
                if len(_post_queue) >= MAX_QUEUE:
                    self._json({"ok": False, "error": f"Queue full ({MAX_QUEUE} pending)"}, 429)
                    return
                _post_queue.append({
                    "title": title,
                    "text": text,
                    "subreddit": subreddit,
                    "kind": kind,
                    "url": url,
                })
            add_log(aid, f"Post queued via API: r/{subreddit} — {title[:60]}", "ok")
            self._json({"ok": True, "queued": True})
            return
        _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST
    add_log(aid, "✓ Routes patched: GET /api/reddit/status | POST /api/reddit/post", "ok")

    # ── Auth helpers ─────────────────────────────────────────────────────────
    def authenticate():
        try:
            r = req.post(
                REDDIT_AUTH_URL,
                auth=(CLIENT_ID, CLIENT_SECRET),
                data={
                    "grant_type": "password",
                    "username": USERNAME,
                    "password": PASSWORD,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                if token:
                    with _auth_lock:
                        _auth["token"] = token
                        _auth["expires_at"] = time.time() + expires_in - 60
                    add_log(aid, f"Authenticated as u/{USERNAME} (expires in {expires_in}s)", "ok")
                    return True
                add_log(aid, f"Auth response missing token: {data}", "warn")
                return False
            else:
                add_log(aid, f"Auth failed {r.status_code}: {r.text[:120]}", "warn")
                return False
        except Exception as e:
            add_log(aid, f"Auth exception: {e}", "warn")
            return False

    def get_headers():
        with _auth_lock:
            return {
                "Authorization": f"Bearer {_auth['token']}",
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            }

    def ensure_auth():
        with _auth_lock:
            if _auth["token"] and time.time() < _auth["expires_at"]:
                return True
        return authenticate()

    # ── Post to Reddit ───────────────────────────────────────────────────────
    def post_to_reddit(title, text, subreddit, kind="self", url=""):
        if not ensure_auth():
            add_log(aid, "Cannot post — not authenticated", "warn")
            return False
        try:
            data = {
                "sr": subreddit,
                "title": title or text[:300],
                "kind": kind,
                "resubmit": "true",
            }
            if kind == "self":
                data["text"] = text
            elif kind == "link" and url:
                data["url"] = url

            r = req.post(
                f"{REDDIT_API}/api/submit",
                headers=get_headers(),
                data=data,
                timeout=15,
            )
            if r.status_code == 200:
                resp = r.json()
                errors = resp.get("json", {}).get("errors", [])
                if errors:
                    add_log(aid, f"Reddit submit errors: {errors}", "warn")
                    if any("RATELIMIT" in str(e) for e in errors):
                        return "ratelimit"
                    return False
                post_url = resp.get("json", {}).get("data", {}).get("url", "")
                add_log(aid, f"Posted to r/{subreddit}: {title[:60]} — {post_url}", "ok")
                return True
            elif r.status_code == 401:
                add_log(aid, "Token expired — re-authenticating…", "warn")
                if authenticate():
                    return post_to_reddit(title, text, subreddit, kind, url)
                return False
            elif r.status_code == 429:
                add_log(aid, f"Rate limited by Reddit: {r.text[:120]}", "warn")
                return "ratelimit"
            else:
                add_log(aid, f"Post failed {r.status_code}: {r.text[:120]}", "warn")
                return False
        except Exception as e:
            add_log(aid, f"Post exception: {e}", "warn")
            return False

    # ── Post comment to Reddit ───────────────────────────────────────────────
    def post_comment(parent_fullname, text):
        if not ensure_auth():
            return False
        try:
            r = req.post(
                f"{REDDIT_API}/api/comment",
                headers=get_headers(),
                data={"thing_id": parent_fullname, "text": text},
                timeout=15,
            )
            if r.status_code == 200:
                add_log(aid, f"Commented on {parent_fullname}: {text[:60]}", "ok")
                return True
            add_log(aid, f"Comment failed {r.status_code}: {r.text[:120]}", "warn")
            return False
        except Exception as e:
            add_log(aid, f"Comment exception: {e}", "warn")
            return False

    # ── Relay to CEO ─────────────────────────────────────────────────────────
    def relay_to_ceo(author, text, context=""):
        try:
            req.post(f"{BASE_API}/api/ceo/message",
                     json={"from": "reddit",
                           "message": f"Reddit mention from u/{author}{context}: {text}"},
                     timeout=10)
        except Exception as e:
            add_log(aid, f"CEO relay error: {e}", "warn")

    # ── Poll inbox for mentions/replies ──────────────────────────────────────
    _seen_message_ids = set()

    def poll_inbox():
        if not ensure_auth():
            return
        try:
            r = req.get(
                f"{REDDIT_API}/message/unread",
                headers=get_headers(),
                params={"limit": 25},
                timeout=15,
            )
            if r.status_code != 200:
                if r.status_code == 401:
                    authenticate()
                else:
                    add_log(aid, f"Inbox poll {r.status_code}: {r.text[:120]}", "warn")
                return
            messages = r.json().get("data", {}).get("children", [])
            new_msgs = [
                m for m in messages
                if m["data"]["name"] not in _seen_message_ids
            ]
            for m in new_msgs:
                data = m["data"]
                _seen_message_ids.add(data["name"])
                author = data.get("author", "unknown")
                body = data.get("body", "")
                context = f" in r/{data.get('subreddit', '?')}" if data.get("subreddit") else ""
                relay_to_ceo(author, body[:500], context)
                add_log(aid, f"Relayed mention from u/{author}{context}: {body[:80]}", "ok")
            # Cap seen set to prevent unbounded growth
            if len(_seen_message_ids) > 5000:
                excess = len(_seen_message_ids) - 2500
                for _ in range(excess):
                    _seen_message_ids.pop()
        except Exception as e:
            add_log(aid, f"Inbox poll exception: {e}", "warn")

    # ── Startup ──────────────────────────────────────────────────────────────
    _has_creds = bool(CLIENT_ID and CLIENT_SECRET and USERNAME and PASSWORD)

    if not _has_creds:
        set_agent(aid, status="idle", progress=0,
                  task="No credentials configured — dormant")
        add_log(aid, "No Reddit credentials set — staying dormant", "ok")
    else:
        set_agent(aid, status="idle", progress=10, task="Authenticating with Reddit…")
        auth_ok = False
        for _attempt in range(3):
            if authenticate():
                auth_ok = True
                break
            time.sleep(5)
        if not auth_ok:
            set_agent(aid, status="idle", progress=0,
                      task="Auth failed — will retry in main loop")
            add_log(aid, "Initial auth failed — will keep retrying", "warn")
        else:
            add_log(aid, "Authenticated — idle, awaiting delegation", "ok")

    cycle = 0
    set_agent(aid, status="idle", progress=0,
              task="Dormant — no credentials" if not _has_creds else "Idle — awaiting delegation")

    # ── Main loop ────────────────────────────────────────────────────────────
    while not agent_should_stop(aid):
        cycle += 1

        if not _has_creds:
            agent_sleep(aid, 120)
            continue

        try:
            # Refresh token if needed
            ensure_auth()

            # Poll inbox for mentions/replies
            poll_inbox()

            # Drain post queue — enforce 10-minute minimum between posts (Reddit rate limits)
            with _queue_lock:
                pending = list(_post_queue)
                _post_queue.clear()
            if pending:
                set_agent(aid, status="active", progress=50,
                          task=f"Sending {len(pending)} delegated post(s)…")
                held = []
                for idx, item in enumerate(pending):
                    elapsed = time.time() - _last_external_post_time
                    if elapsed < 600:  # 10-minute rate limit
                        held = pending[idx:]
                        break
                    result = post_to_reddit(
                        item["title"], item["text"],
                        item["subreddit"], item.get("kind", "self"),
                        item.get("url", "")
                    )
                    if result == "ratelimit":
                        held = pending[idx:]
                        break
                    _last_external_post_time = time.time()
                    time.sleep(3)
                    # One post per cycle
                    if idx + 1 < len(pending):
                        held = pending[idx + 1:]
                    break
                if held:
                    wait_secs = int(600 - (time.time() - _last_external_post_time))
                    add_log(aid, f"Rate limit: next post in {max(0,wait_secs)}s — holding {len(held)} post(s)", "info")
                    with _queue_lock:
                        _post_queue[:0] = held

                with _queue_lock:
                    remaining = len(_post_queue)
                if remaining:
                    set_agent(aid, status="active", progress=30,
                              task=f"Idle | {remaining} post(s) rate-limited in queue")
                else:
                    set_agent(aid, status="idle", progress=0,
                              task=f"Idle | Tasks: {cycle}")

        except Exception as e:
            add_log(aid, f"Main loop error: {e}", "warn")
            set_agent(aid, status="idle", progress=0,
                      task=f"Idle (error): {str(e)[:80]}")

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", progress=0, task="Reddit agent stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    result = requests.post(f"{BASE}/api/agent/spawn", json={
        "agent_id": "reddit",
        "name":     "Reddit",
        "role":     "Reddit Social Gateway — posts updates, monitors mentions, relays to CEO",
        "emoji":    "🔴",
        "color":    "#FF4500",
        "code":     REDDIT_CODE,
    }, timeout=10).json()

    if result.get("ok"):
        print("✓ Reddit agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
