"""
SentimentAPI — US Market Sentiment API product
Patches GET /api/sentiment into the live Handler.
Returns bull/bear scores for US tickers (mock MVP).
"""

SENTIMENT_API_CODE = r"""
def run_sentiment_api():
    import json, os, random, hashlib, time
    from urllib.parse import urlparse, parse_qs

    aid = "sentiment_api"

    set_agent(aid,
              name="SentimentAPI",
              role="US Market Sentiment API — GET /api/sentiment?ticker=AAPL returns bull/bear scores",
              emoji="📊",
              color="#10b981",
              status="active", progress=10, task="Initialising…")
    add_log(aid, "SentimentAPI starting — patching GET /api/sentiment", "ok")

    # ── Mock sentiment engine ──────────────────────────────────────────────────
    # Deterministic per-ticker scores seeded by ticker name + date,
    # so results are consistent within a day but rotate daily.
    def _sentiment(ticker):
        t = ticker.upper().strip()
        day_seed = time.strftime("%Y-%m-%d")
        h = int(hashlib.md5(f"{t}:{day_seed}".encode()).hexdigest(), 16)

        bull = 40 + (h % 45)           # 40-84
        bear = 100 - bull + (h % 11)   # residual with jitter
        bear = max(10, min(bear, 60))
        neutral = 100 - bull - bear
        if neutral < 0:
            bear += neutral
            neutral = 0

        signals = []
        if bull >= 65:
            signals.append("Strong institutional buying detected")
        if bull >= 55:
            signals.append("Positive options flow")
        if bear >= 40:
            signals.append("Elevated put volume")
        if bear >= 50:
            signals.append("Short interest rising")
        if bull < 50 and bear < 40:
            signals.append("Consolidation pattern")

        # Simulated social/news sentiment
        social = round(50 + ((h >> 8) % 40) - 15, 1)
        news   = round(50 + ((h >> 16) % 40) - 15, 1)

        return {
            "ticker":  t,
            "date":    day_seed,
            "bull":    bull,
            "bear":    bear,
            "neutral": neutral,
            "score":   round((bull - bear) / 100, 2),
            "rating":  "Bullish" if bull >= 60 else ("Bearish" if bear >= 45 else "Neutral"),
            "signals": signals,
            "social_sentiment": social,
            "news_sentiment":   news,
        }

    # ── Monkey-patch Handler ──────────────────────────────────────────────────
    _orig_do_GET = getattr(Handler, "_sentiment_orig_do_GET", Handler.do_GET)

    def _patched_do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/sentiment":
            qs = parse_qs(urlparse(self.path).query)
            ticker = (qs.get("ticker") or qs.get("t") or [None])[0]

            if not ticker:
                self._json({
                    "ok": False,
                    "error": "Missing required parameter: ticker",
                    "usage": "GET /api/sentiment?ticker=AAPL",
                    "example": "/api/sentiment?ticker=TSLA",
                }, 400)
                return

            # Support comma-separated tickers: ?ticker=AAPL,TSLA,NVDA
            tickers = [t.strip() for t in ticker.split(",") if t.strip()]
            if len(tickers) > 20:
                self._json({"ok": False, "error": "Maximum 20 tickers per request"}, 400)
                return

            if len(tickers) == 1:
                result = _sentiment(tickers[0])
                add_log(aid, f"Sentiment query: {tickers[0]} → {result['rating']} (bull={result['bull']})", "ok")
                self._json({"ok": True, **result})
            else:
                results = [_sentiment(t) for t in tickers]
                add_log(aid, f"Batch sentiment query: {len(tickers)} tickers", "ok")
                self._json({"ok": True, "results": results, "count": len(results)})
            return

        if path == "/api/sentiment/trending":
            trending = ["NVDA", "AAPL", "TSLA", "META", "MSFT", "AMZN", "GOOG", "AMD", "PLTR", "SMCI"]
            results = [_sentiment(t) for t in trending]
            results.sort(key=lambda x: x["score"], reverse=True)
            add_log(aid, "Trending sentiment served", "ok")
            self._json({"ok": True, "trending": results})
            return

        _orig_do_GET(self)

    Handler._sentiment_orig_do_GET = _orig_do_GET
    Handler.do_GET = _patched_do_GET

    add_log(aid, "✓ Routes patched: GET /api/sentiment | GET /api/sentiment/trending", "ok")
    set_agent(aid, status="active", progress=100,
              task="Listening on GET /api/sentiment")

    # ── Idle loop ─────────────────────────────────────────────────────────────
    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue
        agent_sleep(aid, 120)
        if agent_should_stop(aid):
            continue
        cycle += 1
        set_agent(aid, status="active", progress=100,
                  task=f"GET /api/sentiment ready | Cycle #{cycle}")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys, urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "sentiment_api",
        "name":     "SentimentAPI",
        "role":     "US Market Sentiment API — GET /api/sentiment?ticker=AAPL returns bull/bear scores",
        "emoji":    "📊",
        "color":    "#10b981",
        "code":     SENTIMENT_API_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read().decode())

    if result.get("ok"):
        print("✓ SentimentAPI agent spawned — GET /api/sentiment is live")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
