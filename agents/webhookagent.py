"""
WebhookAgent — Webhook Receiver
Ingests inbound events from Stripe, GitHub, and other services via HTTP.
Registers POST /webhook/* routes into the live Handler via monkey-patching.
"""

WEBHOOKAGENT_CODE = r"""
def run_webhookagent():
    import json, threading, time, hashlib, hmac, os
    from datetime import datetime
    from urllib.parse import urlparse

    aid = "webhookagent"
    MAX_QUEUE = 500   # cap in-memory log

    set_agent(aid,
              name="WebhookAgent",
              role="Webhook Receiver — ingests inbound events from Stripe, GitHub, and other services",
              emoji="🔗",
              color="#FB923C",
              status="active", progress=10, task="Initialising...")
    add_log(aid, "WebhookAgent starting — patching POST /webhook/* routes", "ok")

    # ── Shared in-memory event store ─────────────────────────────────────────
    _lock   = threading.Lock()
    _events = []        # list of dicts
    _counts = {}        # source -> int

    REVENUE_EVENTS_FILE = "/Users/secondmind/claudecodetest/data/revenue_events.json"
    STRIPE_PAYMENT_TYPES = {
        "checkout.session.completed",
        "payment_intent.succeeded",
        "invoice.payment_succeeded",
        "charge.succeeded",
    }

    def _persist_stripe_revenue(event_type, payload_bytes, ts):
        # Append a Stripe payment event to revenue_events.json for revenue_tracker.
        try:
            body = json.loads(payload_bytes) if payload_bytes else {}
            obj  = body.get("data", {}).get("object", {})
            # Stripe amounts are in cents; fallback fields by event type
            raw_amount = (obj.get("amount_total") or
                          obj.get("amount_received") or
                          obj.get("amount") or 0)
            amount = round(raw_amount / 100, 2)  # convert cents → dollars

            os.makedirs(os.path.dirname(REVENUE_EVENTS_FILE), exist_ok=True)
            try:
                with open(REVENUE_EVENTS_FILE) as f:
                    rev_events = json.load(f)
                if not isinstance(rev_events, list):
                    rev_events = []
            except Exception:
                rev_events = []

            rev_events.append({
                "ts":     ts,
                "source": "stripe",
                "type":   event_type,
                "amount": amount,
            })
            with open(REVENUE_EVENTS_FILE, "w") as f:
                json.dump(rev_events, f, indent=2)

            add_log(aid,
                    f"[REVENUE] Stripe {event_type} persisted — ${amount:.2f} | "
                    f"total revenue events: {len(rev_events)}",
                    "ok")
        except Exception as e:
            add_log(aid, f"[REVENUE] Failed to persist Stripe event: {e}", "warn")

    def _record(source, event_type, payload_bytes, headers_dict):
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "ts":      ts,
            "source":  source,
            "type":    event_type,
            "size":    len(payload_bytes),
        }
        with _lock:
            _events.append(entry)
            if len(_events) > MAX_QUEUE:
                _events.pop(0)
            _counts[source] = _counts.get(source, 0) + 1
        add_log(aid,
                f"[{source.upper()}] {event_type} — {len(payload_bytes)}B @ {ts}",
                "ok")

        # Wire Stripe payment events → revenue_events.json (revenue_tracker reads this)
        if source == "stripe" and event_type in STRIPE_PAYMENT_TYPES:
            _persist_stripe_revenue(event_type, payload_bytes, ts)

    def _source_from_path(path):
        # Derive source name from /webhook/<source>[/...]
        parts = path.strip("/").split("/")
        # parts: ['webhook', 'stripe', ...]
        return parts[1].lower() if len(parts) >= 2 else "unknown"

    def _event_type_from(source, body_dict, headers_dict):
        if source == "stripe":
            return body_dict.get("type", "stripe.event")
        if source == "github":
            return headers_dict.get("X-GitHub-Event", headers_dict.get("x-github-event", "push"))
        return body_dict.get("type", body_dict.get("event", f"{source}.event"))

    def _verify_stripe(payload_bytes, sig_header, secret):
        if not secret or not sig_header:
            return True  # skip verification if not configured
        try:
            parts = {k: v for k, v in (p.split("=", 1) for p in sig_header.split(","))}
            ts_val = parts.get("t", "")
            sig    = parts.get("v1", "")
            signed = f"{ts_val}.".encode() + payload_bytes
            expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, sig)
        except Exception:
            return False

    def _verify_github(payload_bytes, sig_header, secret):
        if not secret or not sig_header:
            return True
        try:
            expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, sig_header)
        except Exception:
            return False

    # ── Monkey-patch Handler ──────────────────────────────────────────────────
    # Guard against double-patching on respawn: restore originals if already patched
    _orig_do_GET  = getattr(Handler, "_webhookagent_orig_do_GET",  Handler.do_GET)
    _orig_do_POST = getattr(Handler, "_webhookagent_orig_do_POST", Handler.do_POST)

    def _patched_do_GET(self):
        path = urlparse(self.path).path

        if path == "/webhook/events":
            with _lock:
                snapshot = list(_events[-100:])  # last 100
                counts   = dict(_counts)
            self._json({"ok": True, "total": sum(counts.values()),
                        "counts": counts, "events": snapshot})
            return

        if path == "/webhook/counts":
            with _lock:
                counts = dict(_counts)
            self._json({"ok": True, "counts": counts,
                        "total": sum(counts.values())})
            return

        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = urlparse(self.path).path

        if path.startswith("/webhook/") and len(path) > 9:
            source = _source_from_path(path)

            # Read raw body
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length) if length else b""

            # Parse JSON leniently
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                body = {"_raw": raw[:200].decode("utf-8", errors="replace")}

            headers_dict = dict(self.headers)

            # Source-specific signature verification
            stripe_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
            github_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

            if source == "stripe":
                sig = headers_dict.get("Stripe-Signature", headers_dict.get("stripe-signature", ""))
                if stripe_secret and not _verify_stripe(raw, sig, stripe_secret):
                    self._json({"ok": False, "error": "invalid Stripe signature"}, 403)
                    add_log(aid, "Stripe signature verification FAILED", "warn")
                    return

            elif source == "github":
                sig = headers_dict.get("X-Hub-Signature-256",
                      headers_dict.get("x-hub-signature-256", ""))
                if github_secret and not _verify_github(raw, sig, github_secret):
                    self._json({"ok": False, "error": "invalid GitHub signature"}, 403)
                    add_log(aid, "GitHub signature verification FAILED", "warn")
                    return

            event_type = _event_type_from(source, body, headers_dict)
            _record(source, event_type, raw, headers_dict)

            self._json({"ok": True, "source": source, "type": event_type})
            return

        _orig_do_POST(self)

    # Store originals so future respawns can find them
    Handler._webhookagent_orig_do_GET  = _orig_do_GET
    Handler._webhookagent_orig_do_POST = _orig_do_POST
    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST

    add_log(aid,
            "✓ Routes patched: POST /webhook/<source>, GET /webhook/events, GET /webhook/counts",
            "ok")
    set_agent(aid, status="active", progress=80,
              task="Listening on POST /webhook/* | 0 events received")

    # ── Main loop — update status every 60s ──────────────────────────────────
    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        agent_sleep(aid, 60)

        if agent_should_stop(aid):
            continue

        cycle += 1
        try:
            with _lock:
                counts  = dict(_counts)
                total   = sum(counts.values())
                recent  = list(_events[-5:])

            parts = [f"{src}:{n}" for src, n in sorted(counts.items())] or ["no events yet"]
            summary = f"Total {total} events | " + ", ".join(parts) + f" | Cycle #{cycle}"
            set_agent(aid, status="active", progress=90, task=summary)

            if recent:
                last = recent[-1]
                add_log(aid,
                        f"Status update: {total} events total | last: [{last['source'].upper()}] {last['type']} @ {last['ts']}",
                        "ok")
            else:
                add_log(aid, f"Cycle #{cycle} — listening, no events yet", "ok")

        except Exception as e:
            add_log(aid, f"WebhookAgent loop error: {e}", "error")
            set_agent(aid, status="active", progress=40,
                      task=f"Error: {str(e)[:120]} | Cycle #{cycle}")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys
    import urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "webhookagent",
        "name":     "WebhookAgent",
        "role":     "Webhook Receiver — ingests inbound events from Stripe, GitHub, and other services",
        "emoji":    "🔗",
        "color":    "#FB923C",
        "code":     WEBHOOKAGENT_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read().decode())

    if result.get("ok"):
        print("✓ WebhookAgent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
