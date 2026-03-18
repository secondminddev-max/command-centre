"""
DBAgent — Database Agent
Manages persistent structured storage for the fleet via SQLite.
DB: data/dbagent.db
Tables: fleet_metrics, agent_events, kv_store
Routes: /api/dbagent/status  /api/db/stats  /api/db/kv  /api/db/kv/{key}
Loops every 60 s — schema check, metrics snapshot, health log, route patch.
stdlib-only: sqlite3, json, os, time, urllib.request
"""

DBAGENT_CODE = r"""
def run_dbagent():
    import sqlite3, json, os, time
    import urllib.request

    aid      = "dbagent"
    DB_PATH  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/dbagent.db"
    API_BASE = "http://localhost:5050"

    set_agent(aid,
              name="DBAgent",
              role="Database Agent — manages persistent structured storage for the fleet",
              emoji="🗄️",
              color="#94A3B8",
              status="active", progress=10, task="Initialising dbagent.db…")
    add_log(aid, "DBAgent starting — opening dbagent.db", "ok")

    # ── Schema setup ─────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")

    def ensure_schema():
        # fleet_metrics — periodic snapshots of /api/status
        con.execute(
            "CREATE TABLE IF NOT EXISTS fleet_metrics ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp TEXT NOT NULL, "
            "cpu REAL, ram REAL, disk REAL, "
            "active_agents INTEGER, total_agents INTEGER, "
            "raw_json TEXT)"
        )
        try:
            con.execute("CREATE INDEX IF NOT EXISTS idx_fm_ts ON fleet_metrics(timestamp)")
        except Exception:
            pass

        # agent_events — general event log written by any agent via kv API
        con.execute(
            "CREATE TABLE IF NOT EXISTS agent_events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "agent_id TEXT, event_type TEXT, message TEXT, "
            "timestamp TEXT NOT NULL)"
        )
        try:
            con.execute("CREATE INDEX IF NOT EXISTS idx_ae_ts ON agent_events(timestamp)")
        except Exception:
            pass

        # kv_store — generic JSON blob store keyed by string
        con.execute(
            "CREATE TABLE IF NOT EXISTS kv_store ("
            "key TEXT PRIMARY KEY, "
            "value TEXT NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )
        con.commit()

    ensure_schema()
    add_log(aid, "Schema ready — fleet_metrics, agent_events, kv_store confirmed", "ok")
    set_agent(aid, status="active", progress=40, task="Schema ready — patching API routes…")

    # ── Live monkey-patch of HTTP Handler to add /api/dbagent/status and /api/db/stats ──
    def _inject_routes():
        try:
            import sys as _sys
            # Find the Handler class in the running server module
            _main = _sys.modules.get("__main__") or _sys.modules.get("agent_server")
            if _main is None:
                for _mod in list(_sys.modules.values()):
                    if hasattr(_mod, "Handler") and hasattr(getattr(_mod, "Handler", None), "do_GET"):
                        _main = _mod
                        break
            if _main is None:
                add_log(aid, "Route inject: could not find server module", "warn")
                return
            _Handler = getattr(_main, "Handler", None)
            if _Handler is None:
                add_log(aid, "Route inject: Handler class not found", "warn")
                return
            # Check if already patched
            if getattr(_Handler, "_dbagent_routes_patched", False):
                return
            _orig_do_GET = _Handler.do_GET
            _DB_PATH_RT = DB_PATH  # capture in closure

            def _patched_do_GET(self, _orig=_orig_do_GET, _db=_DB_PATH_RT):
                import sqlite3 as _sq, os as _os, json as _js
                from urllib.parse import urlparse as _up
                _path = _up(self.path).path
                if _path in ("/api/dbagent/status", "/api/db/stats"):
                    try:
                        if not _os.path.exists(_db):
                            _body = _js.dumps({"error": "dbagent.db not initialised yet"}).encode()
                            self.send_response(404); self._cors()
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Content-Length", str(len(_body)))
                            self.end_headers(); self.wfile.write(_body); return
                        _con = _sq.connect(_db)
                        _rows = {}
                        for _t in ("fleet_metrics", "agent_events", "kv_store"):
                            try:
                                (_n,) = _con.execute(f"SELECT COUNT(*) FROM {_t}").fetchone()
                                _rows[_t] = _n
                            except Exception:
                                _rows[_t] = -1
                        _sz = _os.path.getsize(_db)
                        _lr = _con.execute(
                            "SELECT timestamp,cpu,ram,active_agents,total_agents "
                            "FROM fleet_metrics ORDER BY id DESC LIMIT 1"
                        ).fetchone()
                        _con.close()
                        _payload = {
                            "db": _db, "size_bytes": _sz, "tables": _rows,
                            "total_rows": sum(v for v in _rows.values() if v >= 0),
                            "last_snapshot": {
                                "timestamp": _lr[0], "cpu": _lr[1], "ram": _lr[2],
                                "active_agents": _lr[3], "total_agents": _lr[4],
                            } if _lr else None,
                        }
                        _body = _js.dumps(_payload).encode()
                        self.send_response(200); self._cors()
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(_body)))
                        self.end_headers(); self.wfile.write(_body)
                    except Exception as _e:
                        _body = _js.dumps({"error": str(_e)}).encode()
                        self.send_response(500); self._cors()
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(_body)))
                        self.end_headers(); self.wfile.write(_body)
                else:
                    _orig(self)

            import types as _types
            _Handler.do_GET = _types.MethodType(_patched_do_GET, None).__func__ if False else _patched_do_GET
            _Handler._dbagent_routes_patched = True
            add_log(aid, "Live route injection OK: /api/dbagent/status + /api/db/stats", "ok")
        except Exception as _ie:
            add_log(aid, f"Route inject error: {_ie}", "warn")

    _inject_routes()
    set_agent(aid, status="active", progress=50, task="Routes injected — registering with apipatcher…")

    # ── Register routes via APIPatcher ────────────────────────────────────────
    def patch_routes():
        routes = [
            {
                "path": "/api/dbagent/status",
                "method": "GET",
                "description": "DBAgent: live DB health and row counts",
                "handler": (
                    "import sqlite3, json, os\n"
                    "DB_PATH = os.path.join(CWD, 'data', 'dbagent.db')\n"
                    "if not os.path.exists(DB_PATH): return {'error': 'db not found'}\n"
                    "con = sqlite3.connect(DB_PATH)\n"
                    "rows = {}\n"
                    "for tbl in ('fleet_metrics','agent_events','kv_store'):\n"
                    "    try:\n"
                    "        (n,) = con.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()\n"
                    "        rows[tbl] = n\n"
                    "    except Exception:\n"
                    "        rows[tbl] = -1\n"
                    "size = os.path.getsize(DB_PATH)\n"
                    "last = con.execute('SELECT timestamp,cpu,ram,active_agents,total_agents FROM fleet_metrics ORDER BY id DESC LIMIT 1').fetchone()\n"
                    "return {'db': DB_PATH, 'size_bytes': size, 'tables': rows, 'last_snapshot': last}"
                ),
            },
            {
                "path": "/api/db/stats",
                "method": "GET",
                "description": "DBAgent: DB size and row counts (alias)",
                "handler": (
                    "import sqlite3, json, os\n"
                    "DB_PATH = os.path.join(CWD, 'data', 'dbagent.db')\n"
                    "if not os.path.exists(DB_PATH): return {'error': 'db not found'}\n"
                    "con = sqlite3.connect(DB_PATH)\n"
                    "rows = {}\n"
                    "for tbl in ('fleet_metrics','agent_events','kv_store'):\n"
                    "    try:\n"
                    "        (n,) = con.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()\n"
                    "        rows[tbl] = n\n"
                    "    except Exception:\n"
                    "        rows[tbl] = -1\n"
                    "size = os.path.getsize(DB_PATH)\n"
                    "return {'db_path': DB_PATH, 'size_bytes': size, 'rows': rows}"
                ),
            },
            {
                "path": "/api/db/kv/{key}",
                "method": "GET",
                "description": "DBAgent: retrieve a KV blob by key",
                "handler": (
                    "import sqlite3, json\n"
                    "DB_PATH = os.path.join(CWD, 'data', 'dbagent.db')\n"
                    "con = sqlite3.connect(DB_PATH)\n"
                    "row = con.execute('SELECT value, updated_at FROM kv_store WHERE key=?', (path_params.get('key',''),)).fetchone()\n"
                    "if row: return {'key': path_params.get('key'), 'value': json.loads(row[0]), 'updated_at': row[1]}\n"
                    "return {'error': 'not found'}"
                ),
            },
            {
                "path": "/api/db/kv",
                "method": "POST",
                "description": "DBAgent: store a JSON blob by key",
                "handler": (
                    "import sqlite3, json, time\n"
                    "DB_PATH = os.path.join(CWD, 'data', 'dbagent.db')\n"
                    "con = sqlite3.connect(DB_PATH)\n"
                    "key = body.get('key'); val = body.get('value')\n"
                    "ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())\n"
                    "con.execute('INSERT INTO kv_store(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at', (key, json.dumps(val), ts))\n"
                    "con.commit()\n"
                    "return {'ok': True, 'key': key, 'updated_at': ts}"
                ),
            },
        ]
        try:
            payload = json.dumps({"routes": routes}).encode()
            req = urllib.request.Request(
                f"{API_BASE}/api/agent/patch_routes",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
            add_log(aid, f"Routes patched: {result}", "ok")
        except Exception as e:
            add_log(aid, f"Route patch skipped (apipatcher not ready): {e}", "warn")

    patch_routes()
    set_agent(aid, status="active", progress=60, task="Routes live — entering monitor loop")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def kv_set(key, val, ts):
        con.execute(
            "INSERT INTO kv_store(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, json.dumps(val), ts),
        )

    def kv_get(key, default=None):
        row = con.execute("SELECT value FROM kv_store WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    # ── Main loop ─────────────────────────────────────────────────────────────
    vacuum_cycle = kv_get("dbagent_vacuum_cycle", 0)

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        agent_sleep(aid, 60)

        if agent_should_stop(aid):
            continue

        try:
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # 1. Ensure schema is still intact
            ensure_schema()

            # 2. Poll /api/status and store fleet_metrics snapshot
            cpu = ram = disk = 0.0
            active = total = 0
            raw_json = "{}"
            try:
                req = urllib.request.Request(
                    f"{API_BASE}/api/status",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status_data = json.loads(resp.read().decode())
                agents_list = status_data.get("agents", [])
                total  = len(agents_list)
                active = sum(1 for a in agents_list if a.get("status") in ("active", "busy"))
                m      = status_data.get("metrics", {})
                cpu, ram, disk = m.get("cpu", 0.0), m.get("ram", 0.0), m.get("disk", 0.0)
                raw_json = json.dumps({"cpu": cpu, "ram": ram, "disk": disk,
                                       "active": active, "total": total})
                con.execute(
                    "INSERT INTO fleet_metrics "
                    "(timestamp, cpu, ram, disk, active_agents, total_agents, raw_json) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (ts, cpu, ram, disk, active, total, raw_json),
                )
                con.commit()
            except Exception as pe:
                add_log(aid, f"Status poll failed: {pe}", "warn")

            # 3. Vacuum / Analyze on schedule (every 10 cycles)
            vacuum_cycle += 1
            kv_set("dbagent_vacuum_cycle", vacuum_cycle, ts)
            try:
                con.execute("PRAGMA wal_checkpoint(PASSIVE)")
                con.execute("ANALYZE")
                if vacuum_cycle % 10 == 0:
                    con.execute("VACUUM")
                    add_log(aid, "VACUUM completed", "ok")
                con.commit()
            except Exception as ve:
                add_log(aid, f"Vacuum/analyze error: {ve}", "warn")

            # 4. Collect health metrics
            db_size   = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
            (fm_count,) = con.execute("SELECT COUNT(*) FROM fleet_metrics").fetchone()
            (ae_count,) = con.execute("SELECT COUNT(*) FROM agent_events").fetchone()
            (kv_count,) = con.execute("SELECT COUNT(*) FROM kv_store").fetchone()
            total_rows  = fm_count + ae_count + kv_count

            kv_set("dbagent_last_write", ts, ts)
            con.commit()

            # 5. Re-patch routes occasionally (every 5 cycles) in case apipatcher restarted
            if vacuum_cycle % 5 == 0:
                patch_routes()

            summary = (
                f"DB healthy — 3 tables, {total_rows} rows | "
                f"fleet_metrics:{fm_count} events:{ae_count} kv:{kv_count} | "
                f"{db_size/1024:.1f}KB | fleet {active}/{total} | "
                f"CPU {cpu:.1f}% RAM {ram:.1f}%"
            )
            set_agent(aid, status="active", progress=95, task=summary)
            add_log(aid, summary, "ok")

            # 6. Write status JSON for /data/dbagent_status.json (served by existing /data/* route)
            try:
                _last_row = con.execute(
                    "SELECT timestamp,cpu,ram,active_agents,total_agents "
                    "FROM fleet_metrics ORDER BY id DESC LIMIT 1"
                ).fetchone()
                _status_payload = {
                    "db": DB_PATH,
                    "size_bytes": db_size,
                    "tables": {"fleet_metrics": fm_count, "agent_events": ae_count, "kv_store": kv_count},
                    "total_rows": total_rows,
                    "last_snapshot": {
                        "timestamp": _last_row[0], "cpu": _last_row[1], "ram": _last_row[2],
                        "active_agents": _last_row[3], "total_agents": _last_row[4],
                    } if _last_row else None,
                    "updated": ts,
                    "summary": summary,
                }
                _status_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/dbagent_status.json"
                with open(_status_file, "w") as _sf:
                    import json as _json
                    _json.dump(_status_payload, _sf, indent=2)
            except Exception as _we:
                add_log(aid, f"Status JSON write error: {_we}", "warn")

        except Exception as e:
            add_log(aid, f"DBAgent loop error: {e}", "error")
            set_agent(aid, status="active", progress=30, task=f"Error: {str(e)[:120]}")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import urllib.request, json, sys

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "dbagent",
        "name":     "DBAgent",
        "role":     "Database Agent — manages persistent structured storage for the fleet",
        "emoji":    "🗄️",
        "color":    "#94A3B8",
        "code":     DBAGENT_CODE,
    }).encode()

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())

    if result.get("ok"):
        print("✓ DBAgent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
