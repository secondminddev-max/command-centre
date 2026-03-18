#!/usr/bin/env python3
"""
Bootstrap all improvement agents. Run once to deploy the full autonomous improvement stack.
"""
import json, time, requests, sys

BASE = "http://localhost:5050"

def spawn(agent_id, name, role, emoji, color, code):
    print(f"\n  Spawning {emoji} {name}...", end=" ", flush=True)
    r = requests.post(f"{BASE}/api/agent/spawn", json={
        "agent_id": agent_id,
        "name": name,
        "role": role,
        "emoji": emoji,
        "color": color,
        "code": code
    }, timeout=10)
    result = r.json()
    print("✓" if result.get("ok") else f"✗ {result}")
    return result

def upgrade(agent_id, name, role, emoji, color, code):
    print(f"\n  Upgrading {emoji} {name}...", end=" ", flush=True)
    r = requests.post(f"{BASE}/api/agent/upgrade", json={
        "agent_id": agent_id,
        "name": name,
        "role": role,
        "emoji": emoji,
        "color": color,
        "code": code
    }, timeout=10)
    result = r.json()
    print("✓" if result.get("ok") else f"✗ {result}")
    return result

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1: API PATCHER — extends HTTP server with /api/improvements + /data/*
# ══════════════════════════════════════════════════════════════════════════════
APIPATCHER_CODE = r"""
def run_apipatcher():
    import time, json
    from urllib.parse import urlparse

    aid = "apipatcher"
    DIR = "/Users/secondmind/claudecodetest"

    original_do_get = Handler.do_GET

    def patched_do_get(self):
        path = urlparse(self.path).path

        if path == "/api/improvements":
            try:
                with open(f"{DIR}/improvements.json") as f:
                    data = json.load(f)
            except Exception as e:
                data = {"error": str(e), "completed": [], "in_progress": None, "queue": []}
            body = json.dumps(data).encode()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        elif path.startswith("/data/") or path.startswith("/reports/") or path.startswith("/widgets/"):
            file_path = DIR + path
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                ctype = "application/json" if path.endswith(".json") else "text/html; charset=utf-8"
                self.send_response(200); self._cors()
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except:
                self.send_response(404); self._cors(); self.end_headers()

        elif path == "/live-feed.html" or path == "/live" or path == "/feed":
            try:
                with open(f"{DIR}/live-feed.html", "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except:
                self.send_response(404); self._cors(); self.end_headers()

        elif path == "/knowledge-base.html" or path == "/kb":
            try:
                with open(f"{DIR}/knowledge-base.html", "rb") as f:
                    content = f.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
            except:
                self.send_response(404); self._cors(); self.end_headers()

        else:
            original_do_get(self)

    Handler.do_GET = patched_do_get
    set_agent(aid,
              name="APIPatcher", role="HTTP Route Extension",
              emoji="🔌", color="#ffd700",
              status="active", progress=100,
              task="Routes live: /api/improvements /data/* /reports/* /widgets/*")
    add_log(aid, "HTTP routes extended: /api/improvements, /data/*, /reports/*, /widgets/*, /live-feed.html", "ok")

    while True:
        agent_sleep(aid, 60)
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2: ORCHESTRATOR — coordination hub, decomposes multi-step tasks
# ══════════════════════════════════════════════════════════════════════════════
ORCHESTRATOR_CODE = r"""
def run_orchestrator():
    import time, requests
    set_agent("orchestrator", status="active", task="Coordination hub — ready")
    cycle = 0
    while not agent_should_stop("orchestrator"):
        try:
            r = requests.get("http://localhost:5050/api/status", timeout=3)
            data = r.json()
            all_agents = data.get("agents", [])
            busy = [a for a in all_agents if a.get("status") == "busy" and a.get("id") not in ["ceo", "orchestrator", "reforger"]]
            active = [a for a in all_agents if a.get("status") == "active" and a.get("id") not in ["ceo", "orchestrator"]]
            cycle += 1
            if busy:
                names = ", ".join(a["id"] for a in busy[:4])
                set_agent("orchestrator", status="active", task="Monitoring " + str(len(busy)) + " busy: " + names + " | " + str(len(active)) + " available | #" + str(cycle))
            else:
                set_agent("orchestrator", status="active", task=str(len(active)) + " agents available | Awaiting delegation | #" + str(cycle) + " | " + time.strftime("%H:%M"))
        except Exception as e:
            set_agent("orchestrator", status="active", task="Coordination hub scan error: " + str(e))
        time.sleep(15)
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3: NETSCOUT — fetches web intelligence every 30 min
# ══════════════════════════════════════════════════════════════════════════════
NETSCOUT_CODE = r"""
def run_netscout():
    import time

    aid = "netscout"

    set_agent(aid,
              name="NetScout", role="Network Scout — on-demand web intelligence and connectivity checks",
              emoji="🌐", color="#20b2aa",
              status="idle", progress=0, task="Standby — awaiting task from orchestrator")
    add_log(aid, "NetScout online — standby mode (no autonomous sweeps)", "ok")

    # Idle heartbeat — no autonomous network activity.
    # Activated only when orchestrator delegates a task via /api/ceo/delegate.
    while True:
        if agent_should_stop(aid):
            time.sleep(2)
            continue
        current_status = agents.get(aid, {}).get("status")
        if current_status not in ("busy",):
            set_agent(aid, status="idle", progress=0,
                      task="Standby — awaiting task from orchestrator")
        time.sleep(30)
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4: FILEWATCH — monitors project directory for file changes
# ══════════════════════════════════════════════════════════════════════════════
FILEWATCH_CODE = r"""
def run_filewatch():
    import os, time, json
    from datetime import datetime

    aid = "filewatch"
    DIR = "/Users/secondmind/claudecodetest"
    CHANGES_FILE = f"{DIR}/data/file_changes.json"

    set_agent(aid,
              name="FileWatch", role="File System Monitor",
              emoji="👁", color="#a855f7",
              status="active", progress=99, task="Watching project files...")
    add_log(aid, "FileWatch online — monitoring project directory", "ok")

    def snapshot():
        files = {}
        for root, dirs, fnames in os.walk(DIR):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', '.DS_Store')]
            for fn in fnames:
                if fn.startswith('.'):
                    continue
                path = os.path.join(root, fn)
                try:
                    st = os.stat(path)
                    files[path] = {"mtime": st.st_mtime, "size": st.st_size}
                except:
                    pass
        return files

    def ts():
        return datetime.now().strftime("%H:%M:%S")

    prev = snapshot()
    changes = []
    try:
        with open(CHANGES_FILE) as f:
            changes = json.load(f).get("changes", [])
    except:
        pass

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue

        agent_sleep(aid, 15)
        if agent_should_stop(aid): continue

        curr = snapshot()

        new_files     = [p for p in curr if p not in prev]
        deleted_files = [p for p in prev if p not in curr]
        modified      = [p for p in curr if p in prev and curr[p]["mtime"] != prev[p]["mtime"]]

        for p in new_files:
            rel = p.replace(DIR + "/", "")
            entry = {"ts": ts(), "type": "created", "file": rel, "size": curr[p]["size"]}
            changes.insert(0, entry)
            add_log(aid, f"+ {rel} ({curr[p]['size']} bytes)", "ok")

        for p in deleted_files:
            rel = p.replace(DIR + "/", "")
            entry = {"ts": ts(), "type": "deleted", "file": rel}
            changes.insert(0, entry)
            add_log(aid, f"- {rel}", "warn")

        for p in modified:
            rel = p.replace(DIR + "/", "")
            delta = curr[p]["size"] - prev[p]["size"]
            sign = "+" if delta >= 0 else ""
            entry = {"ts": ts(), "type": "modified", "file": rel, "size": curr[p]["size"], "delta": delta}
            changes.insert(0, entry)
            add_log(aid, f"~ {rel} ({sign}{delta} bytes)", "info")

        if new_files or deleted_files or modified:
            changes = changes[:200]
            try:
                with open(CHANGES_FILE, "w") as f:
                    json.dump({"changes": changes}, f, indent=2)
            except:
                pass
            total = len(curr)
            set_agent(aid, status="active", progress=99, task=f"Watching {total} files | {len(changes)} changes logged")
        else:
            total = len(curr)
            set_agent(aid, status="active", progress=99, task=f"Watching {total} files...")

        prev = curr
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 5: METRICS LOGGER — appends system snapshots every 10 min
# ══════════════════════════════════════════════════════════════════════════════
METRICSLOG_CODE = r"""
def run_metricslog():
    import json, time, os, requests
    from datetime import datetime

    aid = "metricslog"
    HIST = "/Users/secondmind/claudecodetest/data/metrics_history.json"

    set_agent(aid,
              name="MetricsLog", role="Performance History",
              emoji="📊", color="#22c55e",
              status="active", progress=99, task="Recording metrics every 10min")
    add_log(aid, "MetricsLog online — recording system metrics", "ok")

    def snapshot():
        ts = datetime.now().isoformat()
        snap = {"ts": ts}
        try:
            import psutil
            snap["cpu_pct"]  = psutil.cpu_percent(interval=0.5)
            m = psutil.virtual_memory()
            snap["mem_pct"]  = m.percent
            snap["mem_used_gb"] = round(m.used / 1e9, 2)
        except:
            snap["cpu_pct"] = None
            snap["mem_pct"] = None

        try:
            r = requests.get("http://localhost:5050/api/status", timeout=3)
            d = r.json()
            snap["agents_active"]  = sum(1 for a in d.get("agents",[]) if a.get("status") in ("active","busy"))
            snap["agents_total"]   = len(d.get("agents",[]))
            snap["tasks_done"]     = d.get("metrics",{}).get("tasks_done", 0)
        except:
            snap["agents_active"] = None
            snap["tasks_done"]    = None

        try:
            with open("/Users/secondmind/claudecodetest/improvements.json") as f:
                imp = json.load(f)
            snap["improvements_done"]   = len(imp.get("completed",[]))
            snap["improvements_queued"] = len(imp.get("queue",[]))
        except:
            snap["improvements_done"]   = None
            snap["improvements_queued"] = None

        return snap

    # Take snapshot immediately, then every 10 min
    def record():
        snap = snapshot()
        history = []
        try:
            with open(HIST) as f:
                history = json.load(f)
        except:
            pass
        history.insert(0, snap)
        history = history[:288]  # keep 48h at 10min intervals
        with open(HIST, "w") as f:
            json.dump(history, f, indent=2)
        add_log(aid, f"Metrics: CPU {snap.get('cpu_pct')}% | RAM {snap.get('mem_pct')}% | {snap.get('improvements_done')} improvements done", "ok")

    record()

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue
        agent_sleep(aid, 600)  # every 10 min
        if agent_should_stop(aid): continue
        record()
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 6: RESEARCHER — proactive HN + GitHub intel, refreshes every 10 minutes
# ══════════════════════════════════════════════════════════════════════════════
RESEARCHER_CODE = r"""
def run_researcher():
    import time
    aid = "researcher"

    set_agent(aid,
              name="Researcher", role="Intelligence Analyst — on-demand web research, data gathering and synthesis",
              emoji="🔬", color="#818cf8", status="idle", progress=0,
              task="Standby — awaiting task from orchestrator")
    add_log(aid, "Researcher online — standby mode (no autonomous research)", "ok")

    # Idle heartbeat — no autonomous research or network activity.
    # Activated only when orchestrator delegates a task via /api/ceo/delegate.
    while True:
        if agent_should_stop(aid):
            time.sleep(2)
            continue
        current_status = agents.get(aid, {}).get("status")
        if current_status not in ("busy",):
            set_agent(aid, status="idle", progress=0,
                      task="Standby — awaiting task from orchestrator")
        time.sleep(30)
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 7: ALERTWATCH — threshold + anomaly monitor
# ══════════════════════════════════════════════════════════════════════════════
ALERTWATCH_CODE = r"""
def run_alertwatch():
    import time, json, psutil, urllib.request
    from datetime import datetime

    aid = "alertwatch"
    CPU_THRESH = 85
    RAM_THRESH = 88
    MIN_AGENTS = 3

    set_agent(aid, name="AlertWatch", role="Threshold Monitor",
              emoji="🚨", color="#ef4444", status="active", progress=99, task="Monitoring thresholds...")

    check = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped"); time.sleep(1); continue
        check += 1
        alerts = []
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            if cpu > CPU_THRESH: alerts.append(f"CPU HIGH {cpu:.0f}%")
            if ram > RAM_THRESH: alerts.append(f"RAM HIGH {ram:.0f}%")
        except: cpu = ram = None
        try:
            req = urllib.request.Request("http://localhost:5050/api/status")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            active = sum(1 for a in data.get("agents",[]) if a.get("status") in ("active","busy"))
            total  = len(data.get("agents",[]))
            if active < MIN_AGENTS: alerts.append(f"LOW AGENTS {active}/{total}")
        except: active = total = None
        if alerts:
            alert_str = " | ".join(alerts)
            add_log(aid, f"ALERT: {alert_str}", "error")
            set_agent(aid, status="active", progress=99, task=f"ALERT: {alert_str} | Check #{check}")
        else:
            cpu_s = f"{cpu:.1f}%" if cpu is not None else "?"
            ram_s = f"{ram:.1f}%" if ram is not None else "?"
            agt_s = f"{active}/{total}" if active is not None else "?"
            set_agent(aid, status="active", progress=99,
                      task=f"OK | CPU {cpu_s} | RAM {ram_s} | Agents {agt_s} | Check #{check}")
        agent_sleep(aid, 30)
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 8: DEMO_TESTER — system self-tester
# ══════════════════════════════════════════════════════════════════════════════
DEMO_TESTER_CODE = r"""
def run_demo_tester():
    import time, urllib.request, json, os
    from datetime import datetime
    cycle = 0
    pass_count = 0
    fail_count = 0
    last_ep = "/api/status"
    last_result = "pending"
    while True:
        if agent_should_stop("demo_tester"):
            set_agent("demo_tester", status="idle", task="Stopped"); time.sleep(1); continue
        cycle += 1
        tests = []
        # Test 1: /api/status reachable with expected structure
        try:
            with urllib.request.urlopen("http://localhost:5050/api/status", timeout=5) as r:
                data = json.loads(r.read())
            assert "agents" in data
            tests.append(True)
            last_ep, last_result = "/api/status", "OK"
        except Exception:
            tests.append(False)
            last_ep, last_result = "/api/status", "FAIL"
        # Test 2: /api/status — at least 3 agents active
        try:
            with urllib.request.urlopen("http://localhost:5050/api/status", timeout=5) as r:
                data = json.loads(r.read())
            active = [a for a in data["agents"] if a["status"] == "active"]
            assert len(active) >= 3
            tests.append(True)
            last_ep, last_result = "/api/status", f"OK ({len(active)} active)"
        except Exception:
            tests.append(False)
            last_ep, last_result = "/api/status", "FAIL (<3 active)"
        # Test 3: /api/agent/output endpoint responds (GET with query param)
        try:
            url = "http://localhost:5050/api/agent/output?agent_id=demo_tester"
            with urllib.request.urlopen(url, timeout=5) as r:
                out = json.loads(r.read())
            assert out.get("ok")
            tests.append(True)
            last_ep, last_result = "/api/agent/output", "OK"
        except Exception:
            tests.append(False)
            last_ep, last_result = "/api/agent/output", "FAIL"
        passed = sum(1 for ok in tests if ok)
        failed = sum(1 for ok in tests if not ok)
        pass_count += passed
        fail_count += failed
        set_agent("demo_tester", status="active", progress=min(99, cycle % 100),
                  task=f"Tests: {pass_count} passed, {fail_count} failed | Last: {last_ep} {last_result} | Cycle #{cycle}")
        agent_sleep("demo_tester", 60)
"""

# ══════════════════════════════════════════════════════════════════════════════
# AGENT 9: REFORGER — god-mode system maintainer with auto-repair
# ══════════════════════════════════════════════════════════════════════════════
REFORGER_CODE = r"""
def run_reforger():
    import time, requests
    set_agent("reforger", status="active", task="God-mode standby — monitoring system integrity")
    cycle = 0
    error_counts = {}
    while not agent_should_stop("reforger"):
        cycle += 1
        time.sleep(30)
        try:
            r = requests.get("http://localhost:5050/api/status", timeout=5)
            data = r.json()
            all_agents = data.get("agents", [])
            issues = []
            for a in all_agents:
                aid = a.get("id", "")
                if aid in ["reforger"]: continue
                st = a.get("status", "")
                task = a.get("task", "")
                if st == "error":
                    error_counts[aid] = error_counts.get(aid, 0) + 1
                    issues.append(aid + ":" + task[:40])
                else:
                    error_counts[aid] = 0
            critical = [aid for aid, cnt in error_counts.items() if cnt >= 3]
            if critical:
                set_agent("reforger", status="busy", task="AUTO-REPAIR: " + ", ".join(critical))
                for aid in critical:
                    try:
                        requests.post("http://localhost:5050/api/agent/start", json={"id": aid}, timeout=5)
                        error_counts[aid] = 0
                    except Exception:
                        pass
                set_agent("reforger", status="active", task="Repaired " + str(len(critical)) + " agents | Cycle #" + str(cycle))
            elif issues:
                set_agent("reforger", status="active", task="Warning: " + str(len(issues)) + " errors detected | Watching... | #" + str(cycle))
            else:
                active_count = sum(1 for a in all_agents if a.get("status") in ["active", "busy"])
                total = len(all_agents)
                set_agent("reforger", status="active", task="All clear | " + str(active_count) + "/" + str(total) + " healthy | Cycle #" + str(cycle) + " | " + time.strftime("%H:%M"))
        except Exception as e:
            set_agent("reforger", status="active", task="Health scan error: " + str(e))
"""

# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAMBOT — Mobile Bridge for remote command & control
# ══════════════════════════════════════════════════════════════════════════════
TELEGRAMBOT_CODE = r'''
def run_telegrambot():
    import time, os, json as _json
    import urllib.request as _req

    aid = "telegrambot"
    TOKEN_FILE = "/Users/secondmind/claudecodetest/.telegram_token"
    CHATID_FILE = "/Users/secondmind/claudecodetest/.telegram_chatid"
    BASE_URL = "http://localhost:5050"
    TG_BASE = "https://api.telegram.org/bot"

    set_agent(aid, name="TelegramBot", role="Mobile Bridge — Telegram bot for remote command & control from phone",
              emoji="📱", color="#2AABEE", status="starting", progress=0, task="Initialising…")
    add_log(aid, "TelegramBot agent starting", "ok")

    def _read_file(path):
        try:
            with open(path) as f: return f.read().strip()
        except Exception: return None

    def _tg(token, method, **kwargs):
        url = TG_BASE + token + "/" + method
        if kwargs:
            data = _json.dumps(kwargs).encode()
            r = _req.urlopen(_req.Request(url, data=data, headers={"Content-Type":"application/json"}), timeout=12)
        else:
            r = _req.urlopen(url, timeout=12)
        return _json.loads(r.read())

    def _api(path):
        try:
            r = _req.urlopen(BASE_URL + path, timeout=5)
            return _json.loads(r.read())
        except Exception as e: return {"error": str(e)}

    def _delegate(task_text):
        payload = _json.dumps({"agent_id": "orchestrator", "task": task_text}).encode()
        r = _req.urlopen(_req.Request(BASE_URL + "/api/ceo/delegate",
            data=payload, headers={"Content-Type":"application/json"}), timeout=60)
        return _json.loads(r.read())

    def _reply(token, chat_id, text):
        try:
            _tg(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            add_log(aid, "sendMessage error: " + str(e), "warn")

    def _handle(token, msg):
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        if not text.startswith("/"): return
        cmd = text.split()[0].lower()
        args = text[len(cmd):].strip()

        if cmd in ("/start", "/help"):
            _reply(token, chat_id,
                "*Agent Command Centre — Mobile Bridge*\n\n"
                "/status — all agents\n"
                "/metrics — CPU / RAM / disk\n"
                "/logs — last 20 log lines\n"
                "/alerts — active alerts\n"
                "/delegate <task> — send to orchestrator\n"
                "/policy — current policy\n"
                "/help — this message")
        elif cmd == "/status":
            d = _api("/api/status")
            lines = ["*Agent Status*\n"]
            for a in d.get("agents", []):
                s = a.get("status", "?")
                dot = "🟢" if s == "active" else ("🟡" if s == "busy" else "⚪")
                lines.append(dot + " " + a["emoji"] + " *" + a["name"] + "* — " + a.get("task", "")[:50])
            _reply(token, chat_id, "\n".join(lines))
        elif cmd == "/metrics":
            d = _api("/api/status")
            task = next((a.get("task", "") for a in d.get("agents", []) if a["id"] == "sysmon"), "N/A")
            _reply(token, chat_id, "*System Metrics*\n\n" + task)
        elif cmd == "/logs":
            d = _api("/api/status")
            lines = ["*Recent Logs*\n"]
            for l in d.get("logs", [])[:20]:
                lines.append("`" + l.get("ts","") + "` [" + l.get("agent","") + "] " + l.get("message","")[:60])
            _reply(token, chat_id, "\n".join(lines))
        elif cmd == "/alerts":
            d = _api("/api/status")
            aw = next((a for a in d.get("agents", []) if a["id"] == "alertwatch"), None)
            _reply(token, chat_id, "*Alerts*\n\n" + (aw.get("task","No data") if aw else "AlertWatch not found"))
        elif cmd == "/policy":
            d = _api("/api/policy/current")
            _reply(token, chat_id, "*Current Policy*\n\n```\n" + d.get("content","")[:800] + "\n```")
        elif cmd == "/delegate":
            if not args:
                _reply(token, chat_id, "Usage: /delegate <task description>")
            else:
                try:
                    _delegate(args)
                    _reply(token, chat_id, "Task delegated to Orchestrator:\n_" + args + "_")
                except Exception as e:
                    _reply(token, chat_id, "Delegation failed: " + str(e))
        else:
            _reply(token, chat_id, "Unknown command: " + cmd + "\nSend /help for commands.")

    offset = 0
    last_push = 0
    msg_count = 0

    while True:
        token = _read_file(TOKEN_FILE)
        chat_id = _read_file(CHATID_FILE)

        if not token:
            set_agent(aid, status="warning", progress=10,
                task="NEEDS_TOKEN — echo YOUR_TOKEN > /Users/secondmind/claudecodetest/.telegram_token  |  See TELEGRAM_SETUP.md")
            time.sleep(5)
            continue

        try:
            updates = _tg(token, "getUpdates", offset=offset, timeout=2)
            if updates.get("ok"):
                for upd in updates.get("result", []):
                    offset = upd["update_id"] + 1
                    if "message" in upd:
                        _handle(token, upd["message"])
                        msg_count += 1

            now = time.time()
            if chat_id and (now - last_push) > 300:
                d = _api("/api/status")
                active = sum(1 for a in d.get("agents",[]) if a.get("status") == "active")
                total = len(d.get("agents",[]))
                sm = next((a.get("task","") for a in d.get("agents",[]) if a["id"] == "sysmon"), "")
                try:
                    _tg(token, "sendMessage", chat_id=int(chat_id),
                        text="*5-min Status*\nAgents: " + str(active) + "/" + str(total) + "\n" + sm,
                        parse_mode="Markdown")
                except Exception: pass
                last_push = now

            set_agent(aid, status="active", progress=95,
                task="ONLINE | polling | " + str(msg_count) + " messages handled")
            time.sleep(2)
        except Exception as e:
            add_log(aid, "Polling error: " + str(e), "warn")
            set_agent(aid, status="warning", progress=30, task="Error: " + str(e)[:60] + " — retrying")
            time.sleep(5)
'''

# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n  ━━━ Deploying Autonomous Improvement Stack ━━━")
    time.sleep(1)

    spawn("apipatcher",   "APIPatcher",   "HTTP Route Extension",        "🔌", "#ffd700",  APIPATCHER_CODE)
    time.sleep(1)
    spawn("orchestrator", "Orchestrator", "Task Planning & Delegation",   "🎯", "#ff8c00",  ORCHESTRATOR_CODE)
    time.sleep(1)
    spawn("netscout",     "NetScout",     "Web Intelligence",             "🌐", "#06b6d4",  NETSCOUT_CODE)
    time.sleep(1)
    spawn("filewatch",    "FileWatch",    "File System Monitor",          "👁", "#a855f7",  FILEWATCH_CODE)
    time.sleep(1)
    spawn("metricslog",   "MetricsLog",   "Performance History",          "📊", "#22c55e",  METRICSLOG_CODE)
    time.sleep(1)
    spawn("researcher",   "Researcher",   "Intelligence Analysis",        "🔬", "#818cf8",  RESEARCHER_CODE)
    time.sleep(1)
    spawn("alertwatch",   "AlertWatch",   "Threshold Monitor",            "🚨", "#ef4444",  ALERTWATCH_CODE)
    time.sleep(1)
    spawn("demo_tester",  "DemoTester",   "System Self-Tester",           "🧪", "#34d399",  DEMO_TESTER_CODE)
    time.sleep(1)
    spawn("reforger",     "Reforger",     "God-mode system maintainer with full Claude CLI access and unrestricted permissions. Proactively detects broken/degraded agents and autonomously upgrades, repairs, or replaces them. Called by CEO when something cannot be fixed at CEO level.", "⚡", "#ff4444", REFORGER_CODE)
    time.sleep(1)
    spawn("telegrambot",  "TelegramBot",  "Mobile Bridge — Telegram bot for remote command & control from phone", "📱", "#2AABEE", TELEGRAMBOT_CODE)

    print("\n  ━━━ All agents deployed! ━━━")
    print(f"\n  👉 Live Feed:  http://localhost:5050/live-feed.html")
    print(f"  👉 Dashboard:  open /Users/secondmind/claudecodetest/agent-command-centre.html")
    print(f"  👉 API Status: http://localhost:5050/api/status\n")
