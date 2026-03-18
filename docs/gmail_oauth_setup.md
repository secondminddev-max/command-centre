# Gmail OAuth2 Setup Guide

## Overview

EmailAgent uses Gmail OAuth2 (XOAUTH2 SMTP) for all email sending. A one-time browser consent flow generates a refresh token — after that, sending is fully automatic.

---

## Required Environment Variables

Add these to your `.env` file (client ID and secret are already set):

| Variable | Description |
|---|---|
| `GMAIL_CLIENT_ID` | OAuth2 Client ID from Google Cloud Console |
| `GMAIL_CLIENT_SECRET` | OAuth2 Client Secret from Google Cloud Console |
| `GMAIL_REDIRECT_URI` | Must be `http://localhost:5050/api/email/callback` |
| `GMAIL_REFRESH_TOKEN` | Populated automatically after the consent flow |
| `GMAIL_USER` | Gmail address to send from (e.g. `hq@yourdomain.com`) |

---

## Step 1: Configure Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Open your OAuth 2.0 Client ID (Web application or Desktop app)
3. Add this exact **Authorized redirect URI**:
   ```
   http://localhost:5050/api/email/callback
   ```
4. Enable the **Gmail API** under **APIs & Services** → **Library**

---

## Step 2: Complete the OAuth2 Consent Flow

### Open this URL in your browser:

```
http://localhost:5050/api/email/auth
```

1. You will be redirected to Google's consent screen
2. Sign in with the Gmail account you want to send from
3. Grant the **Send email** (Gmail) permission
4. Google redirects to `/api/email/callback`
5. The server automatically saves the refresh token to:
   - `data/gmail_tokens.json` (primary token store)
   - `.env` as `GMAIL_REFRESH_TOKEN` (persists across restarts)

---

## Step 3: Set GMAIL_USER and Restart

After the consent flow completes, edit `.env` and set:

```
GMAIL_USER=you@gmail.com
```

Then restart the server:

```bash
kill $(cat agent_server.pid) && python3 agent_server.py &
```

---

## Step 4: Test Email Sending

```bash
# POST request — sends a test email to hq@secondmind.ai (default) or a custom address
curl -s -X POST http://localhost:5050/api/email/test -H 'Content-Type: application/json' -d '{}'

# Optional: override the recipient
curl -s -X POST http://localhost:5050/api/email/test -H 'Content-Type: application/json' -d '{"to":"your@email.com"}'
```

Expected response:

```json
{"ok": true, "method": "gmail-oauth2-smtp", "to": "hq@secondmind.ai", "message": "Test email sent"}
```

---

## Available API Routes

| Method | Path | Description |
|---|---|---|
| GET | `/api/email/auth` | Redirects to Google OAuth consent screen |
| GET | `/api/email/callback` | Handles Google's redirect, saves refresh token |
| POST | `/api/email/send` | Send email: `{"to","subject","body"}` |
| POST | `/api/email/test` | Send test email to `hq@secondmind.ai` (default) |
| GET | `/api/emailagent/status` | Check OAuth status and send counts |

---

## Checking OAuth Status

```bash
curl -s http://localhost:5050/api/emailagent/status | python3 -m json.tool
```

The `oauth_status` field will be one of:
- `configured` — all credentials present, ready to send
- `pending_refresh_token` — client ID/secret present, consent flow not yet completed
- `not_configured` — no credentials set at all

---

## Troubleshooting

**"535 Authentication failed"** — Refresh token may be revoked. Re-run the consent flow at `/api/email/auth`.

**"Invalid client"** — Check `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` match your Google Cloud project.

**"Redirect URI mismatch"** — Ensure `http://localhost:5050/api/email/callback` is listed in your Google Cloud authorized redirect URIs.

**Token expired** — Refresh tokens don't expire unless revoked. Access tokens auto-refresh on each send.
