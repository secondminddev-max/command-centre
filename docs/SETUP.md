# Agent Command Centre — Setup & Credentials Guide

This document covers every integration that requires user credentials or configuration. Complete these sections in order of priority.

---

## Status Overview

| Integration | Status | Blocker |
|---|---|---|
| Bluesky | ✅ Active | — |
| Telegram | ⚠ Needs token | Create bot via BotFather |
| Email (SendGrid) | ⚠ Needs API key | Register at sendgrid.com |
| Stripe / Payments | ⏸ Paused | **Requires live website URL first** |

---

## 1. Bluesky

**Agent:** `bluesky` (🦋)
**Purpose:** Posts social updates, polls mentions, relays replies to CEO.

### What to provide

| Variable | Description | Example |
|---|---|---|
| `BLUESKY_HANDLE` | Your Bluesky handle | `yourname.bsky.social` |
| `BLUESKY_PASSWORD` | Your Bluesky **app password** | `xxxx-xxxx-xxxx-xxxx` |

> **Important:** Use an **app password**, not your account password.
> Generate one at: Bluesky → Settings → App Passwords → Add App Password

### Where to put it

Add to `/Users/secondmind/claudecodetest/.env`:

```
BLUESKY_HANDLE=yourname.bsky.social
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

Then restart the server. The agent reads these on startup.

---

## 2. Telegram

**Agent:** `telegram` (📱)
**Purpose:** Remote command & control via phone. Commands: `/status`, `/delegate`, `/metrics`, `/logs`, `/alerts`.

### What to provide

| File | Description |
|---|---|
| `.telegram_token` | Bot API token from BotFather |
| `.telegram_chatid` | Your personal Telegram chat ID |

### How to get your bot token

1. Open Telegram → search **@BotFather**
2. Send `/newbot`, follow prompts
3. Copy the token it gives you (format: `123456789:AAFxxxxxx`)

### How to save credentials

```bash
echo "123456789:AAFxxxxxx" > /Users/secondmind/claudecodetest/.telegram_token
echo "987654321" > /Users/secondmind/claudecodetest/.telegram_chatid
```

### How to find your chat ID

Option A: Message **@userinfobot** on Telegram → send `/start`
Option B: Start your bot, then run:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
# Look for "chat":{"id":987654321} in the response
```

The agent hot-reloads these files on every cycle — no server restart needed.

For full instructions see: `TELEGRAM_SETUP.md`

---

## 3. Email (SendGrid)

**Agent:** `emailagent` (📧)
**Purpose:** Sends notifications, reports, and alerts.

### What to provide

| Variable | Description | Example |
|---|---|---|
| `SENDGRID_API_KEY` | SendGrid Web API v3 key | `SG.xxxxxxxxxxxx` |
| `FROM_EMAIL` | Verified sender address | `you@yourdomain.com` |

> **Sender verification required:** SendGrid requires the `FROM_EMAIL` address to be verified in your account before emails will send.
> Verify at: **sendgrid.com → Settings → Sender Authentication**

### Getting a SendGrid API key

1. Register at [sendgrid.com](https://sendgrid.com) (free tier: 100 emails/day)
2. Go to **Settings → API Keys → Create API Key**
3. Choose **Full Access** or **Restricted** (Mail Send permission minimum)
4. Copy the key — it starts with `SG.`

### Where to put it

Add to `/Users/secondmind/claudecodetest/.env`:

```
SENDGRID_API_KEY=SG.YOUR_KEY_HERE
FROM_EMAIL=you@yourdomain.com
```

### Optional: recipient default

Edit `data/email_config.json`:
```json
{
  "default_to": "you@yourdomain.com",
  "from_address": "you@yourdomain.com"
}
```

### Gmail fallback (SMTP)

If you prefer Gmail SMTP instead of SendGrid, edit `data/email_config.json`:
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "youraddress@gmail.com",
  "smtp_password": "YOUR_APP_PASSWORD"
}
```

> **Gmail requires an App Password**, not your account password.
> Generate one at: myaccount.google.com/apppasswords
> (Requires 2FA to be enabled on your Google account)

---

## 4. Stripe / Payments ⏸ PAUSED

**Agent:** `stripepay` (💳)
**Purpose:** Generates Stripe Checkout sessions for paid products (ASX Screener Basic $19 AUD/mo, Pro $49 AUD/mo).
**Endpoint:** `POST /api/pay`

### ⚠ Dependency: Live Website Required

> **Stripe requires a business website URL before approving a live account.**
> Do not apply for a live Stripe account until you have a publicly accessible website that:
> - Describes your product/service clearly
> - Has a contact method
> - Shows pricing
>
> Attempting to activate Stripe without a website will result in account rejection or immediate suspension.
>
> **Current state:** Checkout endpoint is live but returns `stripe_blocked: true` until credentials are set.
> Product pages (asx-screener.html, buy.html) show "payment coming soon" messaging.

### What to provide (when ready)

| Variable | Description |
|---|---|
| `STRIPE_SECRET_KEY` | Live or test secret key from Stripe Dashboard |
| `STRIPE_PAYMENT_LINK` | Optional static fallback payment link URL |

### Getting a Stripe secret key

1. Go to [stripe.com](https://stripe.com) → create or log in to your account
2. Navigate to **Developers → API keys**
3. For testing: copy the **Secret key** starting with `sk_test_...`
4. For live payments: copy the key starting with `sk_live_...` (requires active website)

### Where to put it (when ready)

Add to `/Users/secondmind/claudecodetest/.env`:

```
STRIPE_SECRET_KEY=sk_live_YOUR_KEY_HERE
```

### Products already configured

| Product ID | Price | Currency | Description |
|---|---|---|---|
| `asx_screener_basic` | $19.00 | AUD | ASX Small-Cap Screener Basic Monthly |
| `asx_screener_pro` | $49.00 | AUD | ASX Small-Cap Screener Pro Monthly |

Once the key is set and the server is restarted, `POST /api/pay?product=asx_screener_basic` will return a live Stripe Checkout URL.

---

## Environment File Reference

All environment variables go in:
```
/Users/secondmind/claudecodetest/.env
```

Full reference (fill in your values):

```bash
# Bluesky
BLUESKY_HANDLE=yourname.bsky.social
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Email
SENDGRID_API_KEY=SG.YOUR_KEY_HERE
FROM_EMAIL=you@yourdomain.com

# Stripe (SET ONLY AFTER LIVE WEBSITE IS READY)
STRIPE_SECRET_KEY=sk_live_YOUR_KEY_HERE
# STRIPE_PAYMENT_LINK=https://buy.stripe.com/YOUR_LINK   # optional static fallback
```

After editing `.env`, restart the agent server:
```bash
cd /Users/secondmind/claudecodetest
python3 agent_server.py
```

---

## Telegram Note

Telegram credentials use flat files (not `.env`) because the agent hot-reloads them at runtime:
- `.telegram_token` — bot token
- `.telegram_chatid` — your chat ID

---

*Last updated: 2026-03-17*
