"""
Discord Agent — Discord Social Gateway
Posts updates, monitors channels, relays messages to CEO via Discord Bot API.
"""

DISCORD_CODE = r"""
def run_discord():
    import time, json, threading
    from datetime import datetime, timezone
    import requests as req
    import os

    aid = "discord"
    BASE_API = "http://localhost:5050"
    DISCORD_API = "https://discord.com/api/v10"
    BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
    DEFAULT_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")

    # In-memory post queue — filled by /api/discord/post HTTP endpoint
    _post_queue = []
    _queue_lock = threading.Lock()
    _last_external_post_time = 0.0
    MAX_QUEUE = 200  # prevent unbounded memory growth

    set_agent(aid,
              name="Discord",
              role="Discord Social Gateway — posts updates, monitors channels, relays to CEO",
              emoji="💬",
              color="#5865F2",
              status="idle", progress=0, task="Initialising…")
    add_log(aid, "Discord agent starting up", "ok")

    # ── Register API routes ────────────────────────────────────────────────────
    from urllib.parse import urlparse

    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    def _patched_do_GET(self):
        path = urlparse(self.path).path
        if path in ("/api/discord/status", "/api/agent/discord/task"):
            with _queue_lock:
                pending = len(_post_queue)
            self._json({
                "ok": True,
                "authenticated": bool(BOT_TOKEN),
                "default_channel": DEFAULT_CHANNEL_ID,
                "pending_posts": pending,
            })
            return
        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/discord/post":
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
            channel_id = body.get("channel_id") or DEFAULT_CHANNEL_ID
            if not channel_id:
                self._json({"ok": False, "error": "channel_id required (no default set)"}, 400)
                return
            with _queue_lock:
                if len(_post_queue) >= MAX_QUEUE:
                    self._json({"ok": False, "error": f"Queue full ({MAX_QUEUE} pending) — try again later"}, 429)
                    return
                _post_queue.append({"text": msg, "channel_id": channel_id})
            add_log(aid, f"Post queued via API: {msg[:80]}", "ok")
            self._json({"ok": True, "queued": True})
            return
        _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST
    add_log(aid, "✓ Routes patched: GET /api/discord/status | POST /api/discord/post", "ok")

    # ── Auth helpers ───────────────────────────────────────────────────────────
    def get_headers():
        return {
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
        }

    def validate_token():
        # Validate the bot token by fetching /users/@me
        if not BOT_TOKEN:
            add_log(aid, "No DISCORD_BOT_TOKEN set — agent will queue posts but cannot send", "warn")
            return False
        try:
            r = req.get(f"{DISCORD_API}/users/@me", headers=get_headers(), timeout=15)
            if r.status_code == 200:
                data = r.json()
                bot_name = data.get("username", "unknown")
                add_log(aid, f"Authenticated as bot: {bot_name}#{data.get('discriminator', '0')}", "ok")
                return True
            else:
                add_log(aid, f"Token validation failed {r.status_code}: {r.text[:120]}", "warn")
                return False
        except Exception as e:
            add_log(aid, f"Token validation exception: {e}", "warn")
            return False

    # ── Post to Discord channel (with retry on rate limit) ─────────────────────
    def post_to_discord(text, channel_id):
        if not BOT_TOKEN:
            add_log(aid, "Cannot post — DISCORD_BOT_TOKEN not set. Set it in your environment to enable posting.", "warn")
            return False
        if len(text) > 2000:
            text = text[:1997] + "..."
        for attempt in range(2):
            try:
                r = req.post(
                    f"{DISCORD_API}/channels/{channel_id}/messages",
                    headers=get_headers(),
                    json={"content": text},
                    timeout=15,
                )
                if r.status_code in (200, 201):
                    add_log(aid, f"Posted to channel {channel_id}: {text[:80]}", "ok")
                    return True
                elif r.status_code == 429:
                    retry_after = r.json().get("retry_after", 5)
                    add_log(aid, f"Rate limited — waiting {retry_after}s before retry", "warn")
                    if attempt == 0:
                        time.sleep(min(retry_after, 30))
                        continue
                    return False
                elif r.status_code in (401, 403):
                    add_log(aid, f"Discord auth error {r.status_code}: {r.text[:120]} — check bot token and permissions", "error")
                    return False
                elif r.status_code >= 500:
                    add_log(aid, f"Discord server error {r.status_code} (attempt {attempt+1}): {r.text[:120]}", "warn")
                    if attempt == 0:
                        time.sleep(3)
                        continue
                    return False
                else:
                    add_log(aid, f"Post failed {r.status_code}: {r.text[:120]}", "warn")
                    return False
            except req.exceptions.Timeout:
                add_log(aid, f"Discord post timeout (attempt {attempt+1}) — channel {channel_id}", "warn")
                if attempt == 0:
                    time.sleep(2)
                    continue
                return False
            except req.exceptions.ConnectionError as e:
                add_log(aid, f"Discord connection error: {e}", "error")
                return False
            except Exception as e:
                add_log(aid, f"Discord post unexpected error: {type(e).__name__}: {e}", "error")
                return False
        return False

    # ── Relay message to CEO ───────────────────────────────────────────────────
    def relay_to_ceo(author, text, channel_id):
        try:
            req.post(f"{BASE_API}/api/ceo/message",
                     json={"from": "discord",
                           "message": f"Discord msg from {author} in #{channel_id}: {text}"},
                     timeout=10)
        except Exception as e:
            add_log(aid, f"CEO relay error: {e}", "warn")

    # ── Poll for new messages (if channel is set) ──────────────────────────────
    _last_message_id = None

    def poll_messages():
        nonlocal _last_message_id
        if not BOT_TOKEN or not DEFAULT_CHANNEL_ID:
            return
        try:
            params = {"limit": 10}
            if _last_message_id:
                params["after"] = _last_message_id
            r = req.get(
                f"{DISCORD_API}/channels/{DEFAULT_CHANNEL_ID}/messages",
                headers=get_headers(),
                params=params,
                timeout=15,
            )
            if r.status_code != 200:
                if r.status_code != 429:
                    add_log(aid, f"Message poll {r.status_code}: {r.text[:120]}", "warn")
                return
            messages = r.json()
            if not messages:
                return
            # Messages come newest-first — track the latest ID
            _last_message_id = messages[0]["id"]
            # Relay non-bot messages to CEO
            for msg in reversed(messages):
                if msg.get("author", {}).get("bot"):
                    continue
                author = msg.get("author", {}).get("username", "unknown")
                content = msg.get("content", "")
                if content:
                    relay_to_ceo(author, content[:500], DEFAULT_CHANNEL_ID)
                    add_log(aid, f"Relayed msg from {author}: {content[:80]}", "ok")
        except Exception as e:
            add_log(aid, f"Message poll exception: {e}", "warn")

    # ── Startup ────────────────────────────────────────────────────────────────
    set_agent(aid, status="idle", progress=10, task="Validating Discord bot token…")
    auth_ok = validate_token()

    if not auth_ok:
        set_agent(aid, status="idle", progress=0,
                  task="No valid token — queuing only")
        add_log(aid, "No valid bot token — will queue posts for later delivery", "warn")
    else:
        add_log(aid, "Authenticated — idle, awaiting delegation", "ok")

    cycle = 0
    set_agent(aid, status="idle", progress=0, task="Idle — awaiting delegation")

    # ── Main loop ──────────────────────────────────────────────────────────────
    while not agent_should_stop(aid):
        cycle += 1
        try:
            # Poll for new messages in the default channel
            if auth_ok:
                poll_messages()

            # Drain the post queue — 2-second gap between posts (Discord is more lenient)
            with _queue_lock:
                pending = list(_post_queue)
                _post_queue.clear()
            if pending:
                set_agent(aid, status="active", progress=50,
                          task=f"Sending {len(pending)} delegated post(s)…")
                held = []
                for idx, item in enumerate(pending):
                    ok = post_to_discord(item["text"], item["channel_id"])
                    if not ok:
                        # Rate limited or failed — hold remaining
                        held = pending[idx:]
                        break
                    _last_external_post_time = time.time()
                    time.sleep(2)
                if held:
                    with _queue_lock:
                        _post_queue[:0] = held
                    add_log(aid, f"Holding {len(held)} post(s) for retry", "info")

                with _queue_lock:
                    remaining = len(_post_queue)
                if remaining:
                    set_agent(aid, status="active", progress=30,
                              task=f"Idle | {remaining} post(s) queued for retry")
                else:
                    set_agent(aid, status="idle", progress=0,
                              task=f"Idle | Tasks: {cycle}")

        except Exception as e:
            add_log(aid, f"Main loop error: {e}", "warn")
            set_agent(aid, status="idle", progress=0,
                      task=f"Idle (error): {str(e)[:80]}")

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", progress=0, task="Discord agent stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    result = requests.post(f"{BASE}/api/agent/spawn", json={
        "agent_id": "discord",
        "name":     "Discord",
        "role":     "Discord Social Gateway — posts updates, monitors channels, relays to CEO",
        "emoji":    "💬",
        "color":    "#5865F2",
        "code":     DISCORD_CODE,
    }, timeout=10).json()

    if result.get("ok"):
        print("✓ Discord agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
