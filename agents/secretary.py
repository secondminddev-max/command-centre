"""
Secretary Agent — CEO Task Tracker
Maintains a persistent task log in data/ceo_tasks.json.
On each cycle: checks for stale tasks and alerts the CEO.
Writes data/ceo_brief.md as a startup-injection brief for the CEO.

Routes (monkey-patched live):
  POST /api/tasks/add       — {title, description, priority, stale_after_hours}
  POST /api/tasks/complete  — {task_id}
  POST /api/tasks/update    — {task_id, status, notes}
  GET  /api/tasks/pending   — returns all non-complete tasks
  GET  /api/tasks/all       — returns all tasks
  GET  /api/tasks/brief     — returns CEO startup brief markdown
"""

SECRETARY_CODE = r'''
def run_secretary():
    import time, json, os, threading, uuid
    from datetime import datetime, timezone

    aid = "secretary"
    CWD        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TASKS_FILE = os.path.join(CWD, "data", "ceo_tasks.json")
    BRIEF_FILE = os.path.join(CWD, "data", "ceo_brief.md")
    BASE_URL   = "http://localhost:5050"

    set_agent(aid,
              name="Secretary",
              role="CEO Secretary — tracks HQ missions in data/ceo_tasks.json, injects startup briefs, alerts on stale tasks",
              emoji="🗂️",
              color="#34d399",
              status="starting", progress=0, task="Initialising task log…")
    add_log(aid, "Secretary online — loading task log", "ok")

    _lock = threading.Lock()

    # ── Persistence helpers ──────────────────────────────────────────────────
    def _load():
        try:
            if os.path.exists(TASKS_FILE):
                with open(TASKS_FILE) as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save(tasks):
        with open(TASKS_FILE, "w") as f:
            json.dump(tasks, f, indent=2)

    def _now_iso():
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def _now_ts():
        return time.time()

    # ── Task operations ──────────────────────────────────────────────────────
    def _add_task(title, description="", priority="medium", stale_after_hours=24):
        with _lock:
            tasks = _load()
            task = {
                "id": str(uuid.uuid4())[:8],
                "title": title,
                "description": description,
                "status": "pending",
                "priority": priority,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "stale_after_hours": int(stale_after_hours),
                "stale_alerted": False,
                "notes": "",
            }
            tasks.append(task)
            _save(tasks)
            add_log(aid, f"Task added [{task['id']}]: {title}", "ok")
            return task

    def _complete_task(task_id):
        with _lock:
            tasks = _load()
            for t in tasks:
                if t["id"] == task_id:
                    t["status"] = "complete"
                    t["updated_at"] = _now_iso()
                    _save(tasks)
                    add_log(aid, f"Task complete [{task_id}]: {t['title']}", "ok")
                    return t
            return None

    def _update_task(task_id, status=None, notes=None):
        with _lock:
            tasks = _load()
            for t in tasks:
                if t["id"] == task_id:
                    if status:
                        t["status"] = status
                    if notes is not None:
                        t["notes"] = notes
                    t["updated_at"] = _now_iso()
                    _save(tasks)
                    add_log(aid, f"Task updated [{task_id}]: status={t['status']}", "ok")
                    return t
            return None

    def _pending_tasks():
        tasks = _load()
        return [t for t in tasks if t["status"] not in ("complete",)]

    def _all_tasks():
        return _load()

    # ── CEO startup brief ────────────────────────────────────────────────────
    def _write_brief():
        pending = _pending_tasks()
        lines = [
            f"# CEO Task Brief — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        # ── PRIMARY MISSION: PRODUCT LAUNCH (persistent, survives regeneration) ──
        _pm_file = os.path.join(CWD, "data", "product_mission.json")
        if os.path.exists(_pm_file):
            try:
                with open(_pm_file) as _pmf:
                    _pm = json.load(_pmf)
                lines.append("---")
                lines.append("")
                lines.append("## 🚀 PRIMARY MISSION: PRODUCT LAUNCH — AI HQ SaaS")
                lines.append("")
                lines.append(f"**Status:** {_pm.get('status','unknown').upper()} | **Priority:** {_pm.get('priority',1)} (HIGHEST)")
                lines.append(f"**Target:** {_pm.get('target','TBD')}")
                _tiers = _pm.get('tiers', {})
                lines.append(f"**Tiers:** Solo ${_tiers.get('solo',49)}/mo | Team ${_tiers.get('team',149)}/mo | Enterprise ${_tiers.get('enterprise',499)}/mo")
                lines.append(f"**Dashboard:** {_pm.get('dashboard','reports/product_launch_dashboard.html')}")
                lines.append(f"**Landing Page:** {_pm.get('landing_page','reports/landing_page.html')}")
                lines.append(f"**Mission File:** data/product_mission.json")
                lines.append("")
                lines.append(f"**Directive:** {_pm.get('mission','Package and sell this autonomous AI HQ as a SaaS product')}. All agents should prioritize launch readiness.")
                lines.append("")
                lines.append("---")
                lines.append("")
            except Exception:
                pass

        if not pending:
            lines.append("✅ No outstanding missions. All tasks complete.")
        else:
            lines.append(f"⚠️  {len(pending)} outstanding mission(s) require attention:\n")
            for t in pending:
                age_label = ""
                try:
                    created = datetime.strptime(t["created_at"], "%Y-%m-%dT%H:%M:%S")
                    age_h = (datetime.now() - created).total_seconds() / 3600
                    if age_h >= t.get("stale_after_hours", 24):
                        age_label = f" ⏰ STALE ({age_h:.0f}h old)"
                    else:
                        age_label = f" ({age_h:.0f}h old)"
                except Exception:
                    pass
                lines.append(f"- [{t['id']}] **{t['title']}** [{t['status'].upper()} / {t['priority']}]{age_label}")
                if t.get("description"):
                    lines.append(f"  {t['description']}")
                if t.get("notes"):
                    lines.append(f"  Notes: {t['notes']}")
                lines.append("")
        lines.append("---")
        lines.append("To mark complete: POST /api/tasks/complete {\"task_id\": \"ID\"}")
        lines.append("To add task:      POST /api/tasks/add {\"title\": \"...\", \"priority\": \"high|medium|low\"}")
        brief = "\n".join(lines)
        with open(BRIEF_FILE, "w") as f:
            f.write(brief)
        return brief

    # ── HTTP route patching ──────────────────────────────────────────────────
    from urllib.parse import urlparse as _urlparse

    if not getattr(Handler, "_secretary_patched", False):
        _orig_post = Handler.do_POST
        _orig_get  = Handler.do_GET

        def _sec_do_post(self):
            parsed = _urlparse(self.path)
            path   = parsed.path

            if path == "/api/tasks/add":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body   = json.loads(self.rfile.read(length) or b"{}")
                    title  = body.get("title", "").strip()
                    if not title:
                        self._json({"ok": False, "error": "title required"}, 400); return
                    task = _add_task(
                        title=title,
                        description=body.get("description", ""),
                        priority=body.get("priority", "medium"),
                        stale_after_hours=body.get("stale_after_hours", 24),
                    )
                    self._json({"ok": True, "task": task})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return

            if path == "/api/tasks/complete":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body   = json.loads(self.rfile.read(length) or b"{}")
                    tid    = body.get("task_id", "").strip()
                    if not tid:
                        self._json({"ok": False, "error": "task_id required"}, 400); return
                    task = _complete_task(tid)
                    if task:
                        self._json({"ok": True, "task": task})
                    else:
                        self._json({"ok": False, "error": f"task {tid} not found"}, 404)
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return

            if path == "/api/tasks/update":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body   = json.loads(self.rfile.read(length) or b"{}")
                    tid    = body.get("task_id", "").strip()
                    if not tid:
                        self._json({"ok": False, "error": "task_id required"}, 400); return
                    task = _update_task(tid,
                                        status=body.get("status"),
                                        notes=body.get("notes"))
                    if task:
                        self._json({"ok": True, "task": task})
                    else:
                        self._json({"ok": False, "error": f"task {tid} not found"}, 404)
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return

            _orig_post(self)

        def _sec_do_get(self):
            parsed = _urlparse(self.path)
            path   = parsed.path

            if path == "/api/tasks/pending":
                try:
                    self._json({"ok": True, "tasks": _pending_tasks(), "count": len(_pending_tasks())})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return

            if path == "/api/tasks/all":
                try:
                    all_t = _all_tasks()
                    self._json({"ok": True, "tasks": all_t, "count": len(all_t)})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return

            if path == "/api/tasks/brief":
                try:
                    if os.path.exists(BRIEF_FILE):
                        with open(BRIEF_FILE) as f:
                            content = f.read()
                    else:
                        content = _write_brief()
                    self._json({"ok": True, "brief": content, "pending": len(_pending_tasks())})
                except Exception as e:
                    self._json({"ok": False, "error": str(e)}, 500)
                return

            _orig_get(self)

        Handler.do_POST = _sec_do_post
        Handler.do_GET  = _sec_do_get
        Handler._secretary_patched = True
        add_log(aid, "Routes live: /api/tasks/{add,complete,update,pending,all,brief}", "ok")
    else:
        add_log(aid, "Routes already patched — skipping re-patch", "ok")

    # ── Write initial brief ──────────────────────────────────────────────────
    try:
        _write_brief()
        pending_count = len(_pending_tasks())
        add_log(aid, f"Startup brief written — {pending_count} pending task(s)", "ok")
    except Exception as e:
        add_log(aid, f"Brief write error: {e}", "error")

    set_agent(aid, status="active", progress=90,
              task=f"Routes live | {len(_pending_tasks())} pending tasks | brief: data/ceo_brief.md")

    STALE_CHECK_INTERVAL = 120   # check every 2 minutes
    BRIEF_WRITE_INTERVAL = 60    # rewrite brief every minute
    last_stale_check = 0
    last_brief_write = 0

    # ── Main loop ────────────────────────────────────────────────────────────
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        agent_sleep(aid, 30)
        if agent_should_stop(aid):
            continue

        try:
            now = time.time()

            # Rewrite CEO brief
            if now - last_brief_write >= BRIEF_WRITE_INTERVAL:
                _write_brief()
                last_brief_write = now

            # Stale task check
            if now - last_stale_check >= STALE_CHECK_INTERVAL:
                last_stale_check = now
                with _lock:
                    tasks = _load()
                    changed = False
                    stale_titles = []
                    for t in tasks:
                        if t["status"] in ("complete",):
                            continue
                        try:
                            created = datetime.strptime(t["created_at"], "%Y-%m-%dT%H:%M:%S")
                            age_h = (datetime.now() - created).total_seconds() / 3600
                            limit = t.get("stale_after_hours", 24)
                            if age_h >= limit and not t.get("stale_alerted", False):
                                t["status"] = "stale"
                                t["stale_alerted"] = True
                                t["updated_at"] = _now_iso()
                                stale_titles.append(t["title"])
                                changed = True
                                add_log(aid, f"⏰ Task STALE [{t['id']}]: {t['title']} ({age_h:.0f}h old)", "warn")
                        except Exception:
                            pass
                    if changed:
                        _save(tasks)

                # Alert CEO about stale tasks
                if stale_titles:
                    try:
                        alert_msg = (
                            f"⏰ TASK ALERT — {len(stale_titles)} CEO mission(s) have gone stale "
                            f"without resolution: {'; '.join(stale_titles[:3])}. "
                            f"Review pending tasks at GET /api/tasks/pending or read data/ceo_brief.md."
                        )
                        requests.post(f"{BASE_URL}/api/ceo/delegate", json={
                            "agent_id": "ceo",
                            "task": alert_msg,
                            "from": "secretary",
                        }, timeout=5)
                        add_log(aid, f"Stale task alert sent to CEO: {len(stale_titles)} task(s)", "warn")
                    except Exception as e:
                        add_log(aid, f"CEO alert error: {e}", "error")

            # Update dashboard status
            pending = _pending_tasks()
            stale   = [t for t in pending if t["status"] == "stale"]
            p_count = len(pending)
            s_count = len(stale)
            status_str = f"🗂️ {p_count} pending"
            if s_count:
                status_str += f" | ⏰ {s_count} STALE"
            status_str += " | Routes live | brief: data/ceo_brief.md"
            set_agent(aid, status="active", progress=90, task=status_str)

        except Exception as e:
            add_log(aid, f"Secretary loop error: {e}", "error")
            set_agent(aid, status="active", progress=0, task=f"Error: {e}")
'''

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "secretary",
            "name":     "Secretary",
            "role":     "CEO Secretary — tracks HQ missions in data/ceo_tasks.json, injects startup briefs, alerts on stale tasks",
            "emoji":    "🗂️",
            "color":    "#34d399",
            "code":     SECRETARY_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ Secretary spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
