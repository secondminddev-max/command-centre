# STRIPE PAYMENT BLOCKER — Action Required

**Date:** 2026-03-17
**Endpoint:** `POST /api/pay`
**Current status:** ❌ STRIPE_SECRET_KEY not set — all checkout sessions return `stripe_blocked: true`

---

## Queued Products Awaiting STRIPE_SECRET_KEY

| Product ID | Amount | Currency | Description |
|---|---|---|---|
| `asx_screener_basic` | 1900 (¢) = **$19.00** | AUD | ASX Small-Cap Screener Basic Monthly |
| `asx_screener_pro` | 4900 (¢) = **$49.00** | AUD | ASX Small-Cap Screener Pro Monthly |

Until `STRIPE_SECRET_KEY` is set, `POST /api/pay` with any of these products returns:

```json
{
  "payment_link": null,
  "stripe_blocked": true,
  "product": "<product_id>",
  "amount": <amount_cents>,
  "instructions": "Set STRIPE_SECRET_KEY in .env to activate"
}
```

---

## What Mathew needs to provide

### Option A — Full Stripe Checkout (recommended)

1. **Create or log in to a Stripe account** at https://stripe.com
2. Go to **Developers → API keys**
3. Copy your **Secret key** — it starts with `sk_live_...` (production) or `sk_test_...` (testing)
4. Add it to the project environment:
   ```
   STRIPE_SECRET_KEY=sk_live_YOUR_KEY_HERE
   ```
5. Restart the server — `/api/pay` will then create real Stripe Checkout Sessions

### Option B — Static Stripe Payment Link (quick fallback)

1. In Stripe Dashboard, go to **Payment Links → Create**
2. Create products matching the catalogue above
3. Copy the payment link URL (e.g. `https://buy.stripe.com/xxxx`)
4. Add to environment:
   ```
   STRIPE_PAYMENT_LINK=https://buy.stripe.com/YOUR_LINK
   ```

---

## Endpoints — current status

| Method | Path | Status |
|---|---|---|
| `GET` | `/api/pay` | ✅ Live — returns product catalogue |
| `GET` | `/api/pay/status` | ✅ Live — returns key/mode info |
| `POST` | `/api/pay` | ⚠ Blocked — returns `stripe_blocked: true` until key is set |

---

## Where to set the environment variable

- **`.env` file** in `/Users/secondmind/claudecodetest/` (server must load dotenv on startup)
- **Shell export** before starting the server: `export STRIPE_SECRET_KEY=sk_...`
- **systemd / launchd service** environment block if running as a service

---

## What is already built and ready

- ✅ Sales landing page: `public/asx-screener.html` — Buy Now button wired to `/api/pay`
- ✅ StripePay agent: `agents/stripepay.py` — product catalogue loaded, waiting for key
- ✅ Products configured: `asx_screener_basic` ($19 AUD/mo) and `asx_screener_pro` ($49 AUD/mo)
- ✅ Report: `reports/asx_screener_report.html` — 9 companies, full investment thesis
- ✅ PDF copy: `data/asx_screener_report_product.pdf`

Everything is wired. The only missing piece is the Stripe key.

---

*Updated by StripePay — 2026-03-17*
