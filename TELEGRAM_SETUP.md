# Telegram Bot Setup Guide

Connect your agent system to Telegram for remote command & control via the **TelegramBot** agent (📱).

---

## Step 1 — Create a Bot via BotFather

1. Open Telegram and search for **@BotFather** (the official bot creation bot).
2. Start a chat and send: `/newbot`
3. Follow the prompts:
   - Enter a **display name** (e.g. `My Agent HQ`)
   - Enter a **username** ending in `bot` (e.g. `myagenthq_bot`)
4. BotFather will reply with your **API token**, looking like:
   ```
   123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
5. Copy this token — you'll need it in Step 2.

---

## Step 2 — Save the Bot Token

Save the token to the file the agent watches:

```bash
echo "123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > /Users/secondmind/claudecodetest/.telegram_token
```

> The agent checks this file on every poll cycle. Once it finds a valid token it will switch from **NEEDS_TOKEN** to **POLLING** automatically.

---

## Step 3 — Get Your Chat ID

You need your personal Telegram chat ID so the bot knows where to send push notifications.

**Option A — Use @userinfobot:**
1. Open Telegram, search for **@userinfobot**.
2. Send `/start` — it will reply with your numeric chat ID (e.g. `987654321`).

**Option B — Use getUpdates:**
1. Start a conversation with your new bot (send it `/start`).
2. Run this in your terminal (replace TOKEN with your actual token):
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
3. Look for `"chat":{"id":987654321,...}` in the response — that number is your chat ID.

---

## Step 4 — Save Your Chat ID

```bash
echo "987654321" > /Users/secondmind/claudecodetest/.telegram_chatid
```

The agent will read this on the next cycle and use it for 5-minute push summaries.

---

## Step 5 — Verify the Bot is Running

**In the dashboard:**
- Open the agent command centre HTML file in your browser.
- Find the **📱 TelegramBot** card.
- Status should read `POLLING — waiting for Telegram updates` once the token is set.

**In Telegram:**
- Send `/help` to your bot — it should reply with the command list.

**Via the API:**
```bash
curl http://localhost:5050/api/status | python3 -m json.tool | grep -A5 telegrambot
```

---

## Available Bot Commands

| Command | What it does |
|---------|-------------|
| `/status` | Lists all agents with name, status, and current task |
| `/delegate <task>` | Sends a task to the Orchestrator agent |
| `/metrics` | Shows current CPU, RAM, and disk usage |
| `/logs` | Returns the 20 most recent system log lines |
| `/alerts` | Shows any active system alerts |
| `/help` | Displays this command list |

---

## Notes

- The bot uses **long-polling** (no webhook required — works behind any firewall).
- Token and chat ID files are read fresh on every cycle — you can update them at any time without restarting the agent.
- Push notifications are sent every **5 minutes** if a chat ID is configured.
- Both files (`.telegram_token`, `.telegram_chatid`) are plain text — one value per file, no quotes needed.
