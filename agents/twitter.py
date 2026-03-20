"""
Twitter/X Agent — Twitter Social Gateway
Posts updates, polls mentions, relays DMs to CEO via Twitter API v2.
"""

TWITTER_CODE = r"""
def run_twitter():
    import time, json, threading, hashlib, hmac, base64, uuid as _uuid
    from datetime import datetime, timezone
    from urllib.parse import quote as urlquote, urlencode
    import requests as req
    import os

    aid = "twitter"
    BASE_API = "http://localhost:5050"

    # ── Twitter API v2 config ────────────────────────────────────────────────
    API_KEY        = os.environ.get("TWITTER_API_KEY", "").strip()
    API_SECRET     = os.environ.get("TWITTER_API_SECRET", "").strip()
    ACCESS_TOKEN   = os.environ.get("TWITTER_ACCESS_TOKEN", "").strip()
    ACCESS_SECRET  = os.environ.get("TWITTER_ACCESS_SECRET", "").strip()
    _ENABLED       = os.environ.get("TWITTER_ENABLED", "0").strip().lower() in ("1", "true", "yes")

    # In-memory post queue — filled by /api/twitter/post HTTP endpoint
    _post_queue = []
    _queue_lock = threading.Lock()
    _last_external_post_time = 0.0
    _user_id = None  # populated on first auth check

    set_agent(aid,
              name="Twitter",
              role="Twitter/X Social Gateway — posts updates, polls mentions, relays to CEO",
              emoji="🐦",
              color="#1DA1F2",
              status="idle", progress=0, task="Initialising…")
    add_log(aid, "Twitter agent starting up", "ok")

    # ── Register /api/twitter/post and /api/twitter/status routes ────────────
    from urllib.parse import urlparse as _urlparse

    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    def _patched_do_GET(self):
        path = _urlparse(self.path).path
        if path in ("/api/twitter/status", "/api/agent/twitter/task"):
            with _queue_lock:
                pending = len(_post_queue)
            self._json({
                "ok": True,
                "authenticated": bool(API_KEY and ACCESS_TOKEN),
                "user_id": _user_id,
                "pending_posts": pending,
            })
            return
        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = _urlparse(self.path).path
        if path == "/api/twitter/post":
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
            if len(msg) > 280:
                self._json({"ok": False, "error": f"text too long ({len(msg)}/280 chars)"}, 400)
                return
            reply_to = body.get("reply_to") or None
            with _queue_lock:
                _post_queue.append({"text": msg, "reply_to": reply_to})
            add_log(aid, f"Post queued via API: {msg[:80]}", "ok")
            self._json({"ok": True, "queued": True})
            return
        _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST
    add_log(aid, "✓ Routes patched: GET /api/twitter/status | POST /api/twitter/post", "ok")

    # ── OAuth 1.0a signing (stdlib only) ─────────────────────────────────────
    def _percent_encode(s):
        return urlquote(str(s), safe="")

    def _oauth_sign(method, url, params):
        # Generate OAuth 1.0a Authorization header for Twitter API v2
        oauth_params = {
            "oauth_consumer_key":     API_KEY,
            "oauth_nonce":            _uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp":        str(int(time.time())),
            "oauth_token":            ACCESS_TOKEN,
            "oauth_version":          "1.0",
        }
        # Combine all params for signature base
        all_params = {**oauth_params, **params}
        sorted_params = "&".join(
            f"{_percent_encode(k)}={_percent_encode(v)}"
            for k, v in sorted(all_params.items())
        )
        base_string = f"{method.upper()}&{_percent_encode(url)}&{_percent_encode(sorted_params)}"
        signing_key = f"{_percent_encode(API_SECRET)}&{_percent_encode(ACCESS_SECRET)}"
        sig = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        oauth_params["oauth_signature"] = sig
        auth_header = "OAuth " + ", ".join(
            f'{_percent_encode(k)}="{_percent_encode(v)}"'
            for k, v in sorted(oauth_params.items())
        )
        return auth_header

    # ── Verify credentials & get user ID ─────────────────────────────────────
    def verify_credentials():
        nonlocal _user_id
        url = "https://api.twitter.com/2/users/me"
        try:
            auth_header = _oauth_sign("GET", url, {})
            r = req.get(url, headers={"Authorization": auth_header}, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", {})
                _user_id = data.get("id")
                uname = data.get("username", "unknown")
                add_log(aid, f"Authenticated as @{uname} (ID: {_user_id})", "ok")
                return True
            else:
                add_log(aid, f"Auth verify failed {r.status_code}: {r.text[:120]}", "warn")
                return False
        except Exception as e:
            add_log(aid, f"Auth verify exception: {e}", "warn")
            return False

    # ── Post a tweet ─────────────────────────────────────────────────────────
    def post_tweet(text, reply_to=None):
        url = "https://api.twitter.com/2/tweets"
        payload = {"text": text}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": str(reply_to)}
        try:
            auth_header = _oauth_sign("POST", url, {})
            r = req.post(url,
                         headers={"Authorization": auth_header, "Content-Type": "application/json"},
                         json=payload,
                         timeout=15)
            if r.status_code in (200, 201):
                tweet_id = r.json().get("data", {}).get("id", "?")
                add_log(aid, f"Posted tweet {tweet_id}: {text[:80]}", "ok")
                return True
            elif r.status_code == 429:
                add_log(aid, "Rate limited by Twitter — will retry next cycle", "warn")
                return False
            else:
                add_log(aid, f"Tweet failed {r.status_code}: {r.text[:120]}", "warn")
                return False
        except Exception as e:
            add_log(aid, f"Tweet exception: {e}", "warn")
            return False

    # ── Relay mention to CEO ─────────────────────────────────────────────────
    def relay_to_ceo(handle, text):
        try:
            req.post(f"{BASE_API}/api/ceo/message",
                     json={"from": "twitter",
                           "message": f"Twitter mention from @{handle}: {text}"},
                     timeout=10)
        except Exception as e:
            add_log(aid, f"CEO relay error: {e}", "warn")

    # ── Poll mentions ────────────────────────────────────────────────────────
    _seen_mention_ids = set()

    def poll_mentions():
        if not _user_id:
            return
        url = f"https://api.twitter.com/2/users/{_user_id}/mentions"
        params = {"max_results": "10", "expansions": "author_id",
                  "tweet.fields": "created_at,text", "user.fields": "username"}
        try:
            auth_header = _oauth_sign("GET", url, params)
            r = req.get(url, headers={"Authorization": auth_header},
                        params=params, timeout=15)
            if r.status_code == 429:
                add_log(aid, "Mentions poll rate-limited — skipping", "info")
                return
            if r.status_code != 200:
                add_log(aid, f"Mentions poll {r.status_code}: {r.text[:120]}", "warn")
                return
            data = r.json()
            tweets = data.get("data", [])
            users = {u["id"]: u.get("username", "unknown")
                     for u in data.get("includes", {}).get("users", [])}
            for t in tweets:
                tid = t.get("id", "")
                if tid in _seen_mention_ids:
                    continue
                _seen_mention_ids.add(tid)
                author_id = t.get("author_id", "")
                handle = users.get(author_id, "unknown")
                text = t.get("text", "")
                relay_to_ceo(handle, text)
                add_log(aid, f"Relayed mention from @{handle}: {text[:80]}", "ok")
            # Cap seen set to prevent unbounded growth
            if len(_seen_mention_ids) > 1000:
                to_remove = list(_seen_mention_ids)[:500]
                for r_id in to_remove:
                    _seen_mention_ids.discard(r_id)
        except Exception as e:
            add_log(aid, f"Mentions poll exception: {e}", "warn")

    # ── Startup: check kill switch + credentials ─────────────────────────────
    _has_creds = bool(_ENABLED and API_KEY and API_SECRET and ACCESS_TOKEN and ACCESS_SECRET)
    if not _has_creds:
        reasons = []
        if not _ENABLED:
            reasons.append("TWITTER_ENABLED not set")
        if not API_KEY:
            reasons.append("TWITTER_API_KEY missing")
        if not ACCESS_TOKEN:
            reasons.append("TWITTER_ACCESS_TOKEN missing")
        set_agent(aid, status="idle", progress=0,
                  task="No credentials configured — dormant")
        add_log(aid, f"Twitter dormant — {', '.join(reasons)}", "ok")
    else:
        set_agent(aid, status="idle", progress=10, task="Verifying Twitter credentials…")
        auth_ok = False
        for _attempt in range(3):
            if verify_credentials():
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

    set_agent(aid, status="idle", progress=0,
              task="Dormant — no credentials" if not _has_creds else "Idle — awaiting delegation")

    # ── Main loop ────────────────────────────────────────────────────────────
    while not agent_should_stop(aid):
        cycle += 1

        # Skip all network activity if no credentials configured
        if not _has_creds:
            agent_sleep(aid, 120)
            continue

        try:
            # Re-verify credentials every 6 hours
            if cycle % 360 == 0:
                verify_credentials()

            # Poll for mentions and relay to CEO
            poll_mentions()

            # Drain the post queue — enforce 1-hour minimum between posts
            with _queue_lock:
                pending = list(_post_queue)
                _post_queue.clear()
            if pending:
                set_agent(aid, status="active", progress=50,
                          task=f"Sending {len(pending)} delegated tweet(s)…")
                held = []
                for idx, item in enumerate(pending):
                    elapsed = time.time() - _last_external_post_time
                    if elapsed < 3600:
                        held = pending[idx:]
                        break
                    success = post_tweet(item["text"], item.get("reply_to"))
                    if success:
                        _last_external_post_time = time.time()
                    else:
                        # Failed — hold this and remaining for retry
                        held = pending[idx:]
                        break
                    time.sleep(3)
                    if idx + 1 < len(pending):
                        held = pending[idx + 1:]
                    break
                if held:
                    wait_secs = int(3600 - (time.time() - _last_external_post_time))
                    add_log(aid, f"Rate limit: next tweet in {max(0, wait_secs)}s — holding {len(held)} tweet(s)", "info")
                    with _queue_lock:
                        _post_queue[:0] = held

                with _queue_lock:
                    remaining = len(_post_queue)
                if remaining:
                    set_agent(aid, status="active", progress=30,
                              task=f"Idle | {remaining} tweet(s) rate-limited in queue")
                else:
                    set_agent(aid, status="idle", progress=0,
                              task=f"Idle | Cycles: {cycle}")

        except Exception as e:
            add_log(aid, f"Main loop error: {e}", "warn")
            set_agent(aid, status="idle", progress=0,
                      task=f"Idle (error): {str(e)[:80]}")

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", progress=0, task="Twitter agent stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    result = requests.post(f"{BASE}/api/agent/spawn", json={
        "agent_id": "twitter",
        "name":     "Twitter",
        "role":     "Twitter/X Social Gateway — posts updates, polls mentions, relays to CEO",
        "emoji":    "🐦",
        "color":    "#1DA1F2",
        "code":     TWITTER_CODE,
    }, timeout=10).json()

    if result.get("ok"):
        print("✓ Twitter agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
