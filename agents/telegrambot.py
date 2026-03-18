"""
TelegramBot Agent — Mobile Bridge
Telegram bot for remote command & control of the agent system.
"""

TELEGRAMBOT_CODE = r"""
def run_telegrambot():
    import os, time, json, requests as req
    from datetime import datetime

    aid = "telegrambot"
    TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".telegram_token"
    CHATID_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".telegram_chatid"
    BASE_API = "http://localhost:5050"

    set_agent(aid,
              name="TelegramBot",
              role="Mobile Bridge — Telegram bot for remote command & control",
              emoji="📱",
              color="#2AABEE",
              status="active", progress=10, task="Initialising...")
    add_log(aid, "TelegramBot agent starting up", "ok")

    def read_file(path):
        try:
            if os.path.exists(path):
                val = open(path).read().strip()
                return val if val else None
        except Exception:
            pass
        return None

    def tg_url(token, method):
        return f"https://api.telegram.org/bot{token}/{method}"

    def tg_send(token, chat_id, text):
        try:
            req.post(tg_url(token, "sendMessage"),
                     json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                     timeout=10)
        except Exception as e:
            add_log(aid, f"Send error: {e}", "warn")

    def _parse_scheduler_task(agents):
        # Return (next_str, registry_entries) from scheduler task string.
        for a in agents:
            if a.get("id") == "scheduler":
                t = a.get("task", "")
                next_str = ""
                ni = t.find("next: ")
                if ni != -1:
                    end = t.find(" | ", ni)
                    next_str = t[ni + 6:end] if end != -1 else t[ni + 6:]
                entries = []
                ri = t.find("registry: [")
                if ri != -1:
                    re_end = t.find("]", ri)
                    if re_end != -1:
                        reg = t[ri + len("registry: ["):re_end]
                        entries = [e.strip() for e in reg.split("|") if e.strip()]
                return next_str, entries
        return "", []

    def cmd_status():
        try:
            r = req.get(f"{BASE_API}/api/status", timeout=8)
            data = r.json()
            agents = data.get("agents", [])
            lines = ["<b>Agent Status</b>"]
            for a in agents:
                emoji = a.get("emoji", "•")
                name = a.get("name", a.get("id", "?"))
                status = a.get("status", "?")
                task = (a.get("task") or "")[:60]
                lines.append(f"{emoji} <b>{name}</b> [{status}]\n   {task}")
            # Active tasks section
            _SKIP = {"ready", "idle", "standby", "stopped", ""}
            active_task_lines = []
            for a in agents:
                if a.get("status") in ("active", "busy"):
                    t = (a.get("task") or "").strip()
                    if t.lower() not in _SKIP:
                        em = a.get("emoji", "•")
                        nm = a.get("name", a.get("id", "?"))
                        active_task_lines.append(f"  {em} {nm}: {t[:80]}")
            if active_task_lines:
                lines.append("\n<b>⚙️ Active Tasks:</b>\n" + "\n".join(active_task_lines))
            # Upcoming schedule section
            next_str, registry = _parse_scheduler_task(agents)
            sched_lines = []
            if next_str:
                sched_lines.append(f"  Next: {next_str}")
            for entry in registry[:4]:
                sched_lines.append(f"  {entry}")
            if sched_lines:
                lines.append("\n<b>📅 Upcoming Jobs:</b>\n" + "\n".join(sched_lines))
            return "\n\n".join(lines)
        except Exception as e:
            return f"Error fetching status: {e}"

    def cmd_delegate(task_text):
        try:
            r = req.post(f"{BASE_API}/api/ceo/delegate",
                         json={"agent_id": "orchestrator", "task": task_text, "from": "telegrambot"},
                         timeout=15)
            data = r.json()
            return f"<b>Delegated:</b> {task_text}\n<b>Result:</b> {json.dumps(data, indent=2)[:800]}"
        except Exception as e:
            return f"Delegate error: {e}"

    def cmd_metrics():
        try:
            r = req.get(f"{BASE_API}/api/metrics/latest", timeout=8)
            data = r.json()
            cpu = data.get("cpu", "?")
            ram = data.get("ram", "?")
            disk = data.get("disk", "?")
            ts = data.get("timestamp", "")
            return (f"<b>System Metrics</b>\n"
                    f"CPU:  {cpu}%\n"
                    f"RAM:  {ram}%\n"
                    f"Disk: {disk}%\n"
                    f"Time: {ts}")
        except Exception as e:
            return f"Metrics error: {e}"

    def cmd_logs():
        try:
            r = req.get(f"{BASE_API}/api/logs?limit=20", timeout=8)
            data = r.json()
            entries = data.get("logs", data) if isinstance(data, dict) else data
            if not isinstance(entries, list):
                entries = []
            lines = ["<b>Recent Logs (last 20)</b>"]
            for entry in entries[-20:]:
                if isinstance(entry, dict):
                    ts = entry.get("time", entry.get("timestamp", ""))
                    msg = entry.get("message", entry.get("msg", str(entry)))
                    lvl = entry.get("level", entry.get("type", ""))
                    lines.append(f"[{lvl}] {ts} — {msg}"[:120])
                else:
                    lines.append(str(entry)[:120])
            return "\n".join(lines)
        except Exception as e:
            return f"Logs error: {e}"

    def cmd_alerts():
        try:
            r = req.get(f"{BASE_API}/api/alerts", timeout=8)
            data = r.json()
            alerts = data.get("alerts", data) if isinstance(data, dict) else data
            if not isinstance(alerts, list) or len(alerts) == 0:
                return "<b>Alerts</b>\nNo active alerts."
            lines = ["<b>Active Alerts</b>"]
            for a in alerts:
                lines.append(f"🚨 {a}" if isinstance(a, str) else f"🚨 {json.dumps(a)[:200]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Alerts error: {e}"

    def cmd_help():
        return ("<b>Available Commands</b>\n\n"
                "/status — list all agents & their state\n"
                "/delegate &lt;task&gt; — send a task to the orchestrator\n"
                "/metrics — CPU, RAM, disk snapshot\n"
                "/logs — last 20 log lines\n"
                "/alerts — active system alerts\n"
                "/tasks — show active tasks and upcoming schedule\n"
                "/help — show this message")

    def cmd_tasks():
        try:
            r = req.get(f"{BASE_API}/api/status", timeout=8)
            data = r.json()
            agents = data.get("agents", [])
            _SKIP = {"ready", "idle", "standby", "stopped", ""}
            lines = ["<b>⚙️ Active Tasks</b>"]
            for a in agents:
                if a.get("status") in ("active", "busy"):
                    t = (a.get("task") or "").strip()
                    if t.lower() not in _SKIP:
                        em = a.get("emoji", "•")
                        nm = a.get("name", a.get("id", "?"))
                        lines.append(f"{em} <b>{nm}</b>: {t[:100]}")
            if len(lines) == 1:
                lines.append("No active tasks found.")
            next_str, registry = _parse_scheduler_task(agents)
            lines.append("\n<b>📅 Upcoming Jobs</b>")
            if next_str:
                lines.append(f"  Next: {next_str}")
            for entry in registry[:4]:
                lines.append(f"  {entry}")
            if not next_str and not registry:
                lines.append("  No scheduler data available.")
            return "\n".join(lines)
        except Exception as e:
            return f"Tasks error: {e}"

    def push_summary(token, chat_id):
        try:
            r = req.get(f"{BASE_API}/api/status", timeout=8)
            data = r.json()
            agents = data.get("agents", [])
            active = sum(1 for a in agents if a.get("status") == "active")
            busy = sum(1 for a in agents if a.get("status") == "busy")
            idle = sum(1 for a in agents if a.get("status") == "idle")
            ts = datetime.now().strftime("%H:%M")
            msg = (f"<b>📊 5-min Summary [{ts}]</b>\n"
                   f"Agents: {len(agents)} total — "
                   f"{active} active, {busy} busy, {idle} idle")
            # Top active agents with tasks
            _SKIP = {"ready", "idle", "standby", "stopped", ""}
            top_lines = []
            for a in agents:
                if a.get("status") in ("active", "busy"):
                    t = (a.get("task") or "").strip()
                    if t.lower() not in _SKIP:
                        em = a.get("emoji", "•")
                        nm = a.get("name", a.get("id", "?"))
                        top_lines.append(f"  {em} {nm}: {t[:60]}")
                if len(top_lines) >= 5:
                    break
            if top_lines:
                msg += "\n\n<b>⚙️ Busy agents:</b>\n" + "\n".join(top_lines)
            # Next 3 upcoming jobs
            next_str, registry = _parse_scheduler_task(agents)
            job_lines = []
            if next_str:
                job_lines.append(f"  Next: {next_str}")
            for entry in registry[:2]:
                job_lines.append(f"  {entry}")
            if job_lines:
                msg += "\n\n<b>📅 Upcoming:</b>\n" + "\n".join(job_lines)
            tg_send(token, chat_id, msg)
        except Exception as e:
            add_log(aid, f"Push summary error: {e}", "warn")

    offset = 0
    last_push = time.time()
    PUSH_INTERVAL = 300  # 5 minutes

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue

        token = read_file(TOKEN_FILE)
        chat_id = read_file(CHATID_FILE)

        if not token:
            set_agent(aid, status="active", progress=20,
                      task="NEEDS_TOKEN — set token at .telegram_token")
            add_log(aid,
                    "No bot token found. Create .telegram_token with your BotFather token.",
                    "warn")
            agent_sleep(aid, 30)
            continue

        # Token found — start polling
        set_agent(aid, status="active", progress=60, task="POLLING — waiting for Telegram updates")

        try:
            resp = req.get(
                tg_url(token, "getUpdates"),
                params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=35
            )
            data = resp.json()

            if not data.get("ok"):
                err = data.get("description", "unknown error")
                add_log(aid, f"Telegram API error: {err}", "warn")
                set_agent(aid, status="active", progress=30,
                          task=f"API error: {err[:80]}")
                agent_sleep(aid, 10)
                continue

            updates = data.get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                text = (msg.get("text") or "").strip()
                sender_chat = str(msg.get("chat", {}).get("id", ""))

                if not text:
                    continue

                add_log(aid, f"Received: {text[:80]} from chat {sender_chat}", "ok")

                if text.startswith("/status"):
                    reply = cmd_status()
                elif text.startswith("/delegate "):
                    reply = cmd_delegate(text[10:].strip())
                elif text.startswith("/metrics"):
                    reply = cmd_metrics()
                elif text.startswith("/logs"):
                    reply = cmd_logs()
                elif text.startswith("/alerts"):
                    reply = cmd_alerts()
                elif text.startswith("/tasks"):
                    reply = cmd_tasks()
                elif text.startswith("/help") or text == "/start":
                    reply = cmd_help()
                else:
                    reply = f"Unknown command: {text}\nType /help for available commands."

                tg_send(token, sender_chat, reply)
                set_agent(aid, status="active", progress=80,
                          task=f"CONNECTED — last cmd: {text[:40]}")

            # Periodic push summary
            if chat_id and (time.time() - last_push) >= PUSH_INTERVAL:
                push_summary(token, chat_id)
                last_push = time.time()

            set_agent(aid, status="active", progress=70, task="POLLING — waiting for Telegram updates")

        except req.exceptions.Timeout:
            # Long-poll timeout is normal — just loop again
            pass
        except Exception as e:
            add_log(aid, f"Poll loop error: {e}", "warn")
            set_agent(aid, status="active", progress=40, task=f"Reconnecting... ({e})"[:80])
            agent_sleep(aid, 5)
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "telegrambot",
            "name": "TelegramBot",
            "role": "Mobile Bridge — Telegram bot for remote command & control",
            "emoji": "📱",
            "color": "#2AABEE",
            "code": TELEGRAMBOT_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ TelegramBot agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
