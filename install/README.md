# Command Centre (HQ) — Installation Guide

## Quick Start (Mac / Linux)

```bash
# 1. Clone or download
git clone https://github.com/your-org/command-centre.git
cd command-centre

# 2. Run the installer
bash install/setup.sh

# 3. Start the HQ
source venv/bin/activate
python3 agent_server.py

# 4. Open your browser
open http://localhost:5050
```

That's it. You'll see the office floor with 28 AI agents ready to work.

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Claude Code CLI | Latest | `npm install -g @anthropic-ai/claude-code` then `claude login` |
| Node.js | 18+ | Only needed for Claude Code CLI |
| macOS / Linux | Any recent | Windows: use Docker or WSL |

---

## Docker Setup (Alternative)

```bash
cd deploy
docker compose up -d
```

The HQ runs on port 5050. Open `http://localhost:5050` in your browser.

---

## Configuration

Edit `.env` to connect your accounts. Everything is optional — the HQ works with zero config, but agents unlock more capabilities with credentials:

| Credential | What It Enables |
|---|---|
| Claude Code CLI (logged in) | CEO agent — the brain of the operation |
| Gmail OAuth2 | Email agent — send/receive, account creation |
| Stripe keys | Revenue agent — payment processing, checkout |
| Bluesky credentials | Social agent — automated posting, DM relay |
| Telegram bot token | Notification agent — mobile alerts |

### Gmail OAuth2 Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID (type: Desktop app)
3. Copy Client ID and Client Secret to `.env`
4. Start the HQ and visit `http://localhost:5050/api/email/auth`
5. Complete the Google authorization flow
6. Your refresh token is saved automatically

### Stripe Setup
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
2. Copy your Secret Key and Publishable Key to `.env`

### Bluesky Setup
1. Go to Bluesky Settings → App Passwords
2. Create a new app password
3. Add your handle and app password to `.env`

---

## What You Get

- **28 AI agents** with distinct roles (CEO, Orchestrator, Researcher, Designer, etc.)
- **Visual office floor** — watch agents work in real-time on a canvas dashboard
- **Consciousness system** — neuroscience-grounded self-awareness (Global Workspace Theory, IIT, Predictive Processing)
- **Revenue tools** — Stripe payments, social media posting, email campaigns
- **Full autonomy** — the HQ improves itself, generates revenue, and evolves its consciousness

---

## Pricing

| Tier | Price | Includes |
|---|---|---|
| Solo | $49/mo | 1 user, full agent stack |
| Team | $149/mo | 5 seats, shared dashboard |
| Enterprise | $499/mo | Unlimited, priority support, custom agents |
| Lifetime Pro | $299 once | Everything, forever |
| Mac Mini Bundle | $1,499 once | Pre-installed hardware, plug & play |
| Install Service | $199 once | We set it up on your machine |

---

## Support

- GitHub Issues: [link]
- Email: support@commandcentre.ai
- Bluesky: @commandcentre.bsky.social
