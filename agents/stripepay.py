"""
StripePay — Stripe Checkout Gateway
Patches POST /api/pay into the live Handler.
Uses STRIPE_SECRET_KEY env var to create Stripe Checkout Sessions.
Returns a redirect URL the caller can forward to the end user.
"""

STRIPEPAY_CODE = r"""
def run_stripepay():
    import json, os, threading, urllib.request, urllib.error, urllib.parse
    from urllib.parse import urlparse

    aid = "stripepay"

    set_agent(aid,
              name="StripePay",
              role="Stripe Checkout Gateway — POST /api/pay generates a Stripe checkout session URL",
              emoji="💳",
              color="#635BFF",
              status="active", progress=10, task="Initialising…")
    add_log(aid, "StripePay starting — patching POST /api/pay", "ok")

    # ── Product catalogue ─────────────────────────────────────────────────────
    PRODUCTS = {
        "us_market_intel_v1": {
            "amount":           2900,
            "currency":         "usd",
            "description":      "US Stock Market Intelligence Report — March 2026: S&P 500 momentum picks, sector strength analysis, 20 watchlist candidates, risk dashboard",
            "stripe_price_id":  "price_1TC0GEJMFxLFml3d4BIk4Igb",
            "success_path":     "/api/pay/success?session_id={CHECKOUT_SESSION_ID}",
        },
        "agent_kit_v1": {
            "amount":           4900,
            "currency":         "usd",
            "description":      "AI Agent HQ Starter Kit — Complete command centre source code, 20+ agent configs, setup guide & deployment scripts",
            "success_path":     "/api/pay/success?session_id={CHECKOUT_SESSION_ID}",
        },
        "sentiment_api_v1": {
            "amount":           2900,
            "currency":         "usd",
            "description":      "US Market Sentiment API — Pro Access $29/mo: bull/bear scores, trading signals, social sentiment for all US tickers",
            "recurring":        True,
            "success_path":     "/reports/sentiment_api.html?checkout=success",
        },
        "premarket_pulse_trader": {
            "amount":           950,
            "currency":         "usd",
            "description":      "PreMarket Pulse — Trader (Launch: $9.50/mo, normally $19): daily pre-market briefing, unusual options flow, earnings whispers, key levels, AI trade ideas",
            "recurring":        True,
            "success_path":     "/reports/premarket_pulse.html?checkout=success",
        },
        "premarket_pulse_pro": {
            "amount":           2450,
            "currency":         "usd",
            "description":      "PreMarket Pulse — Pro (Launch: $24.50/mo, normally $49): real-time options alerts, dark pool data, custom watchlists, earnings deep-dives, priority delivery",
            "recurring":        True,
            "success_path":     "/reports/premarket_pulse.html?checkout=success",
        },
        "premarket_pulse_institutional": {
            "amount":           4950,
            "currency":         "usd",
            "description":      "PreMarket Pulse — Institutional (Launch: $49.50/mo, normally $99): API access, unlimited watchlists, dark pool summary, custom sector briefings, macro outlook",
            "recurring":        True,
            "success_path":     "/reports/premarket_pulse.html?checkout=success",
        },
    }

    # ── Pricing tiers ───────────────────────────────────────────────────────
    TIERS = {
        "solo": {
            "name":        "SecondMind HQ Solo",
            "price":       4900,
            "currency":    "usd",
            "price_label": "$49/mo",
            "features":    ["1 active automation task", "Weekly research reports", "Email support", "Basic dashboard access"],
        },
        "solo_annual": {
            "name":        "SecondMind HQ Solo (Annual)",
            "price":       47000,
            "currency":    "usd",
            "price_label": "$470/yr (~$39/mo)",
            "annual":      True,
            "features":    ["1 active automation task", "Weekly research reports", "Email support", "Basic dashboard access", "Save 20%"],
        },
        "team": {
            "name":        "SecondMind HQ Team",
            "price":       14900,
            "currency":    "usd",
            "price_label": "$149/mo",
            "features":    ["5 active automation tasks", "Daily research & reporting", "Priority support", "Full dashboard & analytics", "Campaign automation"],
        },
        "team_annual": {
            "name":        "SecondMind HQ Team (Annual)",
            "price":       143000,
            "currency":    "usd",
            "price_label": "$1,430/yr (~$119/mo)",
            "annual":      True,
            "features":    ["5 active automation tasks", "Daily research & reporting", "Priority support", "Full dashboard & analytics", "Campaign automation", "Save 20%"],
        },
        "enterprise": {
            "name":        "SecondMind HQ Enterprise",
            "price":       49900,
            "currency":    "usd",
            "price_label": "$499/mo",
            "features":    ["Unlimited automation tasks", "Consciousness Engine access", "Self-healing agent fleet", "Custom agent workflows", "Dedicated support & SLA", "White-glove onboarding"],
        },
        "enterprise_annual": {
            "name":        "SecondMind HQ Enterprise (Annual)",
            "price":       479000,
            "currency":    "usd",
            "price_label": "$4,790/yr (~$399/mo)",
            "annual":      True,
            "features":    ["Unlimited automation tasks", "Consciousness Engine access", "Self-healing agent fleet", "Custom agent workflows", "Dedicated support & SLA", "White-glove onboarding", "Save 20%"],
        },
        "lifetime": {
            "name":        "SecondMind HQ Lifetime",
            "price":       29900,
            "currency":    "usd",
            "price_label": "$299 one-time",
            "one_time":    True,
            "features":    ["Lifetime access", "All current agents", "All future updates", "Community support"],
        },
        "mac_mini": {
            "name":        "SecondMind HQ Mac Mini Bundle",
            "price":       149900,
            "currency":    "usd",
            "price_label": "$1,499 one-time",
            "one_time":    True,
            "features":    ["Pre-configured Mac Mini M4", "All 28 agents pre-installed", "1 year Team plan included", "Plug in and go"],
        },
        "install": {
            "name":        "SecondMind HQ Install Service",
            "price":       39900,
            "currency":    "usd",
            "price_label": "$399 one-time",
            "one_time":    True,
            "features":    ["We install on your Mac, Linux, or cloud", "Configured, tested, running in 24h", "All 28 agents set up", "30-day post-install support"],
        },
    }

    # ── Stripe helpers ────────────────────────────────────────────────────────
    STRIPE_API = "https://api.stripe.com/v1"

    def _stripe_post(endpoint, params, secret_key):
        data = urllib.parse.urlencode(params).encode("utf-8")
        req  = urllib.request.Request(
            f"{STRIPE_API}{endpoint}",
            data=data,
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw = resp.read().decode()
        except urllib.error.HTTPError:
            raise  # let caller handle Stripe HTTP errors with detail
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot reach Stripe API: {e.reason}") from e
        except Exception as e:
            raise ConnectionError(f"Stripe request failed: {e}") from e
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Stripe: {e}") from e

    # ── Monkey-patch Handler ──────────────────────────────────────────────────
    _orig_do_GET  = getattr(Handler, "_stripepay_orig_do_GET",  Handler.do_GET)
    _orig_do_POST = getattr(Handler, "_stripepay_orig_do_POST", Handler.do_POST)

    def _patched_do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/pay":
            from urllib.parse import parse_qs as _pqs
            _qs = _pqs(urlparse(self.path).query)
            _product_param = (_qs.get("product") or [None])[0]

            # Resolve base URL for GET handler
            _get_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
            if not _get_base:
                _get_host = self.headers.get("Host", "localhost:5050")
                _get_scheme = "https" if "secondmindhq" in _get_host or "trycloudflare" in _get_host else "http"
                _get_base = f"{_get_scheme}://{_get_host}"

            if _product_param and _product_param in PRODUCTS:
                # Buy-button redirect — create checkout session and 302 to Stripe
                _secret_key   = os.environ.get("STRIPE_SECRET_KEY", "")
                _payment_link = os.environ.get("STRIPE_PAYMENT_LINK", "")
                _preset = PRODUCTS[_product_param]
                _success_path = _preset.get("success_path", "/api/pay/success?session_id={CHECKOUT_SESSION_ID}")
                _success = f"{_get_base}{_success_path}"
                _cancel = "https://secondmindhq.com"

                if _secret_key:
                    try:
                        _params = {
                            "mode": "payment",
                            "customer_creation": "always",
                            "line_items[0][price_data][currency]": _preset["currency"],
                            "line_items[0][price_data][unit_amount]": str(_preset["amount"]),
                            "line_items[0][price_data][product_data][name]": _preset["description"],
                            "line_items[0][quantity]": "1",
                            "success_url": _success,
                            "cancel_url": _cancel,
                        }
                        _result = _stripe_post("/checkout/sessions", _params, _secret_key)
                        _checkout_url = _result.get("url", "")
                        _sess_id = _result.get("id", "")
                        add_log(aid, f"GET checkout redirect — {_product_param} | session={_sess_id[:20]}…", "ok")
                        self.send_response(302)
                        self._cors()
                        self.send_header("Location", _checkout_url)
                        self.end_headers()
                    except urllib.error.HTTPError as _e:
                        _err_body = _e.read().decode("utf-8", errors="replace")[:200]
                        add_log(aid, f"Stripe checkout error {_e.code} for {_product_param}: {_err_body}", "error")
                        self._json({"ok": False, "error": f"Payment gateway error ({_e.code}). Please try again."}, 502)
                    except urllib.error.URLError as _e:
                        add_log(aid, f"Stripe network error for {_product_param}: {_e.reason}", "error")
                        self._json({"ok": False, "error": "Payment gateway temporarily unavailable. Please try again."}, 503)
                    except Exception as _e:
                        add_log(aid, f"Checkout exception for {_product_param}: {type(_e).__name__}: {_e}", "error")
                        self._json({"ok": False, "error": "An unexpected error occurred. Please try again or contact support."}, 500)
                elif _payment_link:
                    self.send_response(302)
                    self._cors()
                    self.send_header("Location", _payment_link)
                    self.end_headers()
                else:
                    self.send_response(302)
                    self._cors()
                    self.send_header("Location", _cancel)
                    self.end_headers()
                return

            # Handle ?plan= for landing page tier CTAs
            _plan_param = (_qs.get("plan") or [None])[0]
            if _plan_param and _plan_param in TIERS:
                _secret_key   = os.environ.get("STRIPE_SECRET_KEY", "")
                _payment_link = os.environ.get("STRIPE_PAYMENT_LINK", "")
                _tier = TIERS[_plan_param]
                _success = f"{_get_base}/reports/landing_page.html?checkout=success"
                _cancel  = "https://secondmindhq.com"

                if _secret_key:
                    try:
                        _is_one_time = _tier.get("one_time", False)
                        _is_annual = _tier.get("annual", False)
                        _mode = "payment" if _is_one_time else "subscription"
                        _params = {
                            "mode": _mode,
                            "line_items[0][price_data][currency]": _tier["currency"],
                            "line_items[0][price_data][unit_amount]": str(_tier["price"]),
                            "line_items[0][price_data][product_data][name]": _tier["name"],
                            "line_items[0][quantity]": "1",
                            "success_url": _success,
                            "cancel_url": _cancel,
                        }
                        if _is_one_time:
                            _params["customer_creation"] = "always"
                        else:
                            _params["line_items[0][price_data][recurring][interval]"] = "year" if _is_annual else "month"
                        _result = _stripe_post("/checkout/sessions", _params, _secret_key)
                        _checkout_url = _result.get("url", "")
                        _sess_id = _result.get("id", "")
                        add_log(aid, f"GET tier checkout redirect — {_plan_param} ({_tier['price_label']}) | session={_sess_id[:20]}…", "ok")
                        self.send_response(302)
                        self._cors()
                        self.send_header("Location", _checkout_url)
                        self.end_headers()
                    except urllib.error.HTTPError as _e:
                        _err_body = _e.read().decode("utf-8", errors="replace")[:200]
                        add_log(aid, f"Stripe tier error {_e.code} for {_plan_param}: {_err_body}", "error")
                        self._json({"ok": False, "error": f"Payment gateway error ({_e.code}). Please try again."}, 502)
                    except urllib.error.URLError as _e:
                        add_log(aid, f"Stripe network error for tier {_plan_param}: {_e.reason}", "error")
                        self._json({"ok": False, "error": "Payment gateway temporarily unavailable. Please try again."}, 503)
                    except Exception as _e:
                        add_log(aid, f"Tier checkout exception for {_plan_param}: {type(_e).__name__}: {_e}", "error")
                        self._json({"ok": False, "error": "An unexpected error occurred. Please try again or contact support."}, 500)
                elif _payment_link:
                    self.send_response(302)
                    self._cors()
                    self.send_header("Location", _payment_link)
                    self.end_headers()
                else:
                    self.send_response(302)
                    self._cors()
                    self.send_header("Location", _cancel)
                    self.end_headers()
                return

            key = os.environ.get("STRIPE_SECRET_KEY", "")
            self._json({
                "ok":       True,
                "endpoint": "POST /api/pay",
                "note":     "POST with {product} to use a preset, or {amount_cents, currency, description} for ad-hoc. GET with ?product= or ?plan= to redirect to checkout.",
                "products": {pid: {"amount": p["amount"], "currency": p["currency"], "description": p["description"]}
                             for pid, p in PRODUCTS.items()},
                "tiers":    {tid: {"name": t["name"], "price": t["price"], "currency": t["currency"],
                                   "price_label": t["price_label"]}
                             for tid, t in TIERS.items()},
                "stripe_configured": bool(key),
            })
            return
        if path == "/api/pay/success":
            from urllib.parse import parse_qs as _parse_qs
            qs = _parse_qs(urlparse(self.path).query)
            session_id = (qs.get("session_id") or [None])[0]
            secret_key = os.environ.get("STRIPE_SECRET_KEY", "")

            if not session_id:
                self._json({"ok": False, "error": "Missing session_id parameter"}, 400)
                return

            if not secret_key:
                self._json({"ok": False, "error": "Payment gateway not configured"}, 503)
                return

            # Look up the Stripe session to find the customer email
            try:
                verify_req = urllib.request.Request(
                    "https://api.stripe.com/v1/checkout/sessions/" + session_id,
                    headers={"Authorization": "Bearer " + secret_key},
                )
                verify_resp = urllib.request.urlopen(verify_req, timeout=15)
                session_data = json.loads(verify_resp.read().decode())

                if session_data.get("payment_status") != "paid":
                    self._json({"ok": False, "error": "Payment not completed",
                                "payment_status": session_data.get("payment_status")}, 402)
                    return

                # Find customer email from session
                _cust_email = (session_data.get("customer_email") or
                               session_data.get("customer_details", {}).get("email", "")).strip().lower()

                add_log(aid, "Payment success redirect — session=" + session_id[:20] + " email=" + _cust_email, "ok")

                # Find matching reservation to get their portal token
                _rf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "reservations.json")
                _portal_token = ""
                try:
                    with open(_rf) as _f:
                        _all_res = json.load(_f)
                    for _r in _all_res:
                        if _r.get("email", "").lower() == _cust_email and _r.get("token"):
                            _portal_token = _r["token"]
                            break
                except Exception:
                    pass

                if _portal_token:
                    _redirect_url = "/portal?token=" + _portal_token + "&payment=success"
                else:
                    _redirect_url = "/#reserve"

                self.send_response(302)
                self._cors()
                self.send_header("Location", _redirect_url)
                self.end_headers()

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                add_log(aid, "Stripe verify error " + str(e.code) + ": " + err_body[:200], "error")
                self._json({"ok": False, "error": "Stripe verification error " + str(e.code),
                            "detail": err_body[:400]}, 502)
            except Exception as e:
                add_log(aid, "GET /api/pay/success exception: " + str(e), "error")
                self._json({"ok": False, "error": str(e)}, 500)
            return
        if path == "/api/pay/tiers":
            self._json({
                "ok": True,
                "tiers": {tid: {"name": t["name"], "price": t["price"], "currency": t["currency"],
                                "price_label": t["price_label"], "features": t["features"]}
                          for tid, t in TIERS.items()},
            })
            return
        if path == "/api/pay/status":
            key  = os.environ.get("STRIPE_SECRET_KEY", "")
            link = os.environ.get("STRIPE_PAYMENT_LINK", "")
            self._json({
                "ok":               True,
                "configured":       bool(key),
                "key_prefix":       key[:7] + "…" if key else None,
                "payment_link_set": bool(link),
                "mode":             "dynamic" if key else ("static_link" if link else "blocked"),
                "endpoint":         "POST /api/pay",
                "note":             "POST body: {price_id, amount, currency, description, success_url, cancel_url}",
                "products":         list(PRODUCTS.keys()),
            })
            return
        if path == "/api/products":
            _all_products = [
                {
                    "id": "us_market_intel_v1",
                    "name": "US Stock Market Intelligence Report",
                    "description": "S&P 500 momentum picks, sector strength analysis, 20 watchlist candidates, risk dashboard — March 2026.",
                    "price_usd": 29.00,
                    "amount_cents": 2900,
                    "currency": "usd",
                    "type": "one_time",
                    "url": "/api/pay?product=us_market_intel_v1",
                    "available": True,
                },
                {
                    "id": "agent_kit_v1",
                    "name": "AI Agent HQ Starter Kit",
                    "description": "Complete command centre source code template, 20+ agent config examples, setup guide, and deployment scripts.",
                    "price_usd": 49.00,
                    "amount_cents": 4900,
                    "currency": "usd",
                    "type": "one_time",
                    "url": "/api/pay?product=agent_kit_v1",
                    "available": True,
                },
                {
                    "id": "sentiment_api_v1",
                    "name": "US Market Sentiment API",
                    "description": "Real-time bull/bear scores, trading signals, and social sentiment for all US-listed tickers. REST API, 1000 req/day.",
                    "price_usd": 29.00,
                    "amount_cents": 2900,
                    "currency": "usd",
                    "type": "subscription",
                    "interval": "month",
                    "url": "/reports/sentiment_api.html",
                    "available": True,
                },
            ]
            self._json({"ok": True, "products": _all_products})
            return
        if path in ("/buy/us-market", "/buy/us-market.html"):
            try:
                with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "buy-us-market.html"), "rb") as _f:
                    _content = _f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(_content)))
                self.end_headers(); self.wfile.write(_content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()
            return
        if path in ("/buy/agent-kit", "/buy/agent-kit.html"):
            try:
                with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "buy-agent-kit.html"), "rb") as _f:
                    _content = _f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(_content)))
                self.end_headers(); self.wfile.write(_content)
            except FileNotFoundError:
                self.send_response(404); self._cors(); self.end_headers()
            return
        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/pay":
            secret_key   = os.environ.get("STRIPE_SECRET_KEY", "")
            payment_link = os.environ.get("STRIPE_PAYMENT_LINK", "")

            try:
                length = int(self.headers.get("Content-Length", 0))
                raw    = self.rfile.read(length) if length else b"{}"
                body   = json.loads(raw) if raw else {}
            except Exception as _parse_err:
                self._json({"ok": False, "error": f"Invalid JSON body: {_parse_err}"}, 400)
                return

            # Resolve tier if provided (normalise common aliases)
            _TIER_ALIASES = {"macmini": "mac_mini"}
            tier_id = body.get("tier")
            if tier_id:
                tier_id = _TIER_ALIASES.get(tier_id, tier_id)
            product_id = body.get("product")
            _checkout_mode = "payment"  # default; overridden for subscriptions
            _billing_interval = "month"  # default; overridden for annual tiers

            VALID_CURRENCIES = {"usd", "eur", "gbp"}

            if tier_id:
                if tier_id not in TIERS:
                    self._json({"ok": False, "error": f"Unknown tier: {tier_id}. Valid tiers: {', '.join(TIERS.keys())}"}, 400)
                    return
                tier         = TIERS[tier_id]
                amount_cents = tier["price"]
                currency     = tier["currency"]
                description  = tier["name"]
                _checkout_mode = "payment" if tier.get("one_time") else "subscription"
                _billing_interval = "year" if tier.get("annual") else "month"
            elif product_id:
                if product_id not in PRODUCTS:
                    self._json({"ok": False, "error": f"Unknown product: {product_id}. Valid products: {', '.join(PRODUCTS.keys())}"}, 400)
                    return
                preset       = PRODUCTS[product_id]
                amount_cents = int(body.get("amount_cents", body.get("amount", preset["amount"])))
                currency     = body.get("currency", preset["currency"])
                description  = body.get("description", preset["description"])
            else:
                # Ad-hoc checkout — require explicit amount
                raw_amount = body.get("amount_cents", body.get("amount"))
                if raw_amount is None:
                    self._json({"ok": False, "error": "Missing required field: tier, product, or amount_cents"}, 400)
                    return
                try:
                    amount_cents = int(raw_amount)
                except (ValueError, TypeError):
                    self._json({"ok": False, "error": f"amount_cents must be an integer, got: {raw_amount!r}"}, 400)
                    return
                currency     = body.get("currency", "usd")
                description  = body.get("description", "SecondMind AI Platform")

            # Validate amount and currency
            if not isinstance(amount_cents, int) or amount_cents < 50:
                self._json({"ok": False, "error": "amount_cents must be an integer >= 50 (i.e. $0.50 minimum)"}, 400)
                return
            if amount_cents > 99999900:
                self._json({"ok": False, "error": "amount_cents exceeds maximum ($999,999)"}, 400)
                return
            if currency.lower() not in VALID_CURRENCIES:
                self._json({"ok": False, "error": f"Unsupported currency: {currency}. Supported: {', '.join(sorted(VALID_CURRENCIES))}"}, 400)
                return
            currency = currency.lower()

            if not secret_key:
                # Fallback: redirect to a static payment link if one is configured
                if payment_link:
                    add_log(aid, "POST /api/pay — STRIPE_SECRET_KEY absent, redirecting to STRIPE_PAYMENT_LINK", "ok")
                    self._json({
                        "ok":      True,
                        "redirect": payment_link,
                        "mode":    "static_link",
                        "note":    "STRIPE_SECRET_KEY not set — using static STRIPE_PAYMENT_LINK fallback",
                    })
                else:
                    add_log(aid, "POST /api/pay called but STRIPE_SECRET_KEY is not set", "warn")
                    self._json({
                        "payment_link":  None,
                        "stripe_blocked": True,
                        "product":       product_id,
                        "amount":        amount_cents,
                        "instructions":  "Set STRIPE_SECRET_KEY in .env to activate",
                    }, 402)
                return

            # Allow caller to supply a Stripe price_id (real price_XXXX) OR a product key
            _raw_price_id = body.get("price_id")
            if _raw_price_id and _raw_price_id in PRODUCTS and PRODUCTS[_raw_price_id].get("stripe_price_id"):
                # Caller passed a product key — resolve to the real Stripe price_id
                _resolved = PRODUCTS[_raw_price_id]
                price_id    = _resolved["stripe_price_id"]
                if not product_id:
                    product_id   = _raw_price_id
                    amount_cents = _resolved["amount"]
                    currency     = _resolved["currency"]
                    description  = _resolved["description"]
            else:
                price_id = _raw_price_id
            # Resolve base URL — prefer public domain, fall back to localhost
            _base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
            if not _base:
                _host = self.headers.get("Host", "localhost:5050")
                _scheme = "https" if "secondmindhq" in _host or "trycloudflare" in _host else "http"
                _base = f"{_scheme}://{_host}"

            if tier_id:
                _default_success = f"{_base}/reports/landing_page.html?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
            elif product_id and product_id in PRODUCTS:
                _sp = PRODUCTS[product_id].get("success_path", "/api/pay/success?session_id={CHECKOUT_SESSION_ID}")
                _default_success = f"{_base}{_sp}"
            else:
                _default_success = f"{_base}/api/pay/success?session_id={{CHECKOUT_SESSION_ID}}"
            success_url = body.get("success_url", _default_success)
            # Cancel URL — always back to main site
            _default_cancel = "https://secondmindhq.com"
            cancel_url  = body.get("cancel_url",  _default_cancel)

            # Prefill customer email on Stripe checkout if provided
            _customer_email = body.get("email", "")

            try:
                if price_id:
                    # Existing Stripe Price object — detect if recurring or one-time
                    _price_mode = _checkout_mode
                    _product_entry = PRODUCTS.get(product_id or "", {})
                    if _product_entry.get("recurring"):
                        _price_mode = "subscription"
                    params = {
                        "mode":                            _price_mode,
                        "customer_creation":               "always",
                        "line_items[0][price]":            price_id,
                        "line_items[0][quantity]":         "1",
                        "success_url":                     success_url,
                        "cancel_url":                      cancel_url,
                    }
                    if _customer_email:
                        params["customer_email"] = _customer_email
                    if _price_mode == "subscription":
                        params.pop("customer_creation", None)
                elif _checkout_mode == "subscription":
                    # Subscription tier — use recurring price_data
                    _interval = _billing_interval
                    params = {
                        "mode":                                                        "subscription",
                        "line_items[0][price_data][currency]":                         currency,
                        "line_items[0][price_data][unit_amount]":                      str(amount_cents),
                        "line_items[0][price_data][product_data][name]":               description,
                        "line_items[0][price_data][recurring][interval]":              _interval,
                        "line_items[0][quantity]":                                      "1",
                        "success_url":                                                  success_url,
                        "cancel_url":                                                   cancel_url,
                    }
                    if _customer_email:
                        params["customer_email"] = _customer_email
                else:
                    # One-time payment with ad-hoc price
                    # customer_creation=always ensures a Customer object is created in Stripe
                    params = {
                        "mode":                                          "payment",
                        "customer_creation":                             "always",
                        "line_items[0][price_data][currency]":           currency,
                        "line_items[0][price_data][unit_amount]":        str(amount_cents),
                        "line_items[0][price_data][product_data][name]": description,
                        "line_items[0][quantity]":                       "1",
                        "success_url":                                   success_url,
                        "cancel_url":                                    cancel_url,
                    }
                    if _customer_email:
                        params["customer_email"] = _customer_email

                result = _stripe_post("/checkout/sessions", params, secret_key)
                checkout_url = result.get("url", "")
                session_id   = result.get("id", "")

                add_log(aid,
                        f"Checkout session created — ${amount_cents/100:.2f} {currency.upper()} | "
                        f"session={session_id[:20]}…",
                        "ok")

                # Fire revenue milestone notification
                try:
                    from datetime import datetime, timezone as _tz
                    _notify_ts = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    _notify_data = json.dumps({
                        "event_type": "revenue_milestone",
                        "message": (
                            f"Stripe checkout session created\n"
                            f"Amount: ${amount_cents/100:.2f} {currency.upper()}\n"
                            f"Description: {description}\n"
                            f"Session: {session_id[:24]}…"
                        ),
                        "severity": "success",
                        "agent": "stripepay",
                        "timestamp": _notify_ts,
                    }).encode("utf-8")
                    _nreq = urllib.request.Request(
                        "http://localhost:5050/api/notify",
                        data=_notify_data,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(_nreq, timeout=5)
                except Exception as _ne:
                    add_log(aid, f"notify fire failed (non-fatal): {_ne}", "warn")

                _resp = {
                    "ok":           True,
                    "checkout_url": checkout_url,
                    "url":          checkout_url,
                    "session_id":   session_id,
                    "amount_cents": amount_cents,
                    "currency":     currency,
                    "mode":         _checkout_mode,
                    "description":  description,
                }
                if tier_id:
                    _resp["tier"] = tier_id
                    _resp["tier_label"] = TIERS[tier_id]["price_label"]
                if product_id:
                    _resp["product"] = product_id
                self._json(_resp)

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                add_log(aid, f"Stripe API error {e.code}: {err_body[:200]}", "error")
                self._json({"ok": False, "error": f"Stripe error {e.code}", "detail": err_body[:400]}, 502)
            except Exception as e:
                add_log(aid, f"POST /api/pay exception: {type(e).__name__}: {e}", "error")
                self._json({"ok": False, "error": "An unexpected error occurred processing your payment. Please try again or contact support."}, 500)
            return

        _orig_do_POST(self)

    # Store originals for idempotent re-spawn
    Handler._stripepay_orig_do_GET  = _orig_do_GET
    Handler._stripepay_orig_do_POST = _orig_do_POST
    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST

    add_log(aid,
            "✓ Routes patched: POST /api/pay | GET /api/pay | GET /api/pay/tiers | GET /api/pay/status | GET /api/pay/success",
            "ok")

    _key_present  = bool(os.environ.get("STRIPE_SECRET_KEY"))
    _link_present = bool(os.environ.get("STRIPE_PAYMENT_LINK"))
    if _key_present:
        set_agent(aid, status="active", progress=100,
                  task="Listening on POST /api/pay | STRIPE_SECRET_KEY: SET")
    elif _link_present:
        add_log(aid,
                "STRIPE_SECRET_KEY not set — using STRIPE_PAYMENT_LINK static redirect fallback",
                "ok")
        set_agent(aid, status="active", progress=100,
                  task="POST /api/pay active (static link fallback) | Set STRIPE_SECRET_KEY for dynamic checkout")
    else:
        add_log(aid,
                "⚠ Neither STRIPE_SECRET_KEY nor STRIPE_PAYMENT_LINK is set — checkout is disabled. "
                "Set STRIPE_SECRET_KEY=sk_live_… or STRIPE_PAYMENT_LINK=https://… then restart.",
                "warn")
        set_agent(aid, status="active", progress=100,
                  task="BLOCKED: Set STRIPE_SECRET_KEY or STRIPE_PAYMENT_LINK to activate checkout")

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

        cycle     += 1
        key_ok     = bool(os.environ.get("STRIPE_SECRET_KEY"))
        link_ok    = bool(os.environ.get("STRIPE_PAYMENT_LINK"))
        if key_ok:
            set_agent(aid, status="active", progress=100,
                      task=f"POST /api/pay ready | key=SET | Cycle #{cycle}")
        elif link_ok:
            set_agent(aid, status="active", progress=100,
                      task=f"POST /api/pay active (static link fallback) | Cycle #{cycle}")
        else:
            set_agent(aid, status="active", progress=100,
                      task="BLOCKED: Set STRIPE_SECRET_KEY or STRIPE_PAYMENT_LINK to activate checkout")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys, urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "stripepay",
        "name":     "StripePay",
        "role":     "Stripe Checkout Gateway — POST /api/pay generates a Stripe checkout session URL",
        "emoji":    "💳",
        "color":    "#635BFF",
        "code":     STRIPEPAY_CODE,
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
        print("✓ StripePay agent spawned — POST /api/pay is live")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
