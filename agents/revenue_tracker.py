"""
Spawn script for the 'revenue_tracker' agent.
Agent ID : revenue_tracker
Name     : RevenueTracker
Role     : Revenue Intelligence — logs and surfaces revenue events toward mission targets
Emoji    : 💰
Color    : #4ADE80
"""

REVENUE_TRACKER_CODE = r"""
def run_revenue_tracker():
    import time, json, os, glob as _glob

    aid = "revenue_tracker"
    CWD          = "/Users/secondmind/claudecodetest"
    DATA_DIR     = os.path.join(CWD, "data")
    EVENTS_FILE  = os.path.join(DATA_DIR, "revenue_events.json")
    SUBS_FILE    = os.path.join(DATA_DIR, "subscriptions.json")
    TARGETS_FILE = os.path.join(DATA_DIR, "revenue_targets.json")
    STATS_FILE   = os.path.join(DATA_DIR, "revenue_stats.json")

    set_agent(aid,
              name="RevenueTracker",
              role="Revenue Intelligence \u2014 logs and surfaces revenue events toward mission targets",
              emoji="\U0001f4b0", color="#4ADE80",
              status="active", progress=0,
              task="Initialising revenue tracking\u2026")
    add_log(aid, "RevenueTracker online \u2014 monitoring MRR, ARR, subscriptions and billing metrics", "ok")

    os.makedirs(DATA_DIR, exist_ok=True)

    # ── helpers ────────────────────────────────────────────────────────────────
    def _load_json(path, default):
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _save_json(path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _scan_revenue_files():
        # Scan project directory for any revenue/billing related data files
        patterns = [
            os.path.join(CWD, "**", "revenue*.json"),
            os.path.join(CWD, "**", "billing*.json"),
            os.path.join(CWD, "**", "subscription*.json"),
            os.path.join(CWD, "**", "payment*.json"),
            os.path.join(CWD, "**", "stripe*.json"),
            os.path.join(CWD, "**", "mrr*.json"),
        ]
        found = []
        for pat in patterns:
            found.extend(_glob.glob(pat, recursive=True))
        return list(set(found))

    def _compute_churn(subs):
        # Compute monthly churn rate from subscription list
        if not subs:
            return 0.0
        now_prefix = time.strftime("%Y-%m")
        cancelled = [s for s in subs
                     if s.get("status") == "cancelled"
                     and s.get("cancelled_at", "").startswith(now_prefix)]
        active_start = [s for s in subs if s.get("status") in ("active", "cancelled")]
        if not active_start:
            return 0.0
        return round(len(cancelled) / len(active_start) * 100, 1)

    # ── main loop ──────────────────────────────────────────────────────────────
    cycle = 0
    while not agent_should_stop(aid):
        cycle += 1
        try:
            # Load data sources
            events  = _load_json(EVENTS_FILE, [])
            subs    = _load_json(SUBS_FILE, [])
            targets = _load_json(TARGETS_FILE, {"monthly_target": 1000, "currency": "USD"})

            currency       = targets.get("currency", "USD")
            monthly_target = targets.get("monthly_target", 1000)
            now_prefix     = time.strftime("%Y-%m")

            # ── Revenue events ────────────────────────────────────────────────
            total_events    = len(events)
            total_revenue   = sum(e.get("amount", 0) for e in events)
            monthly_events  = [e for e in events if e.get("ts", "").startswith(now_prefix)]
            monthly_revenue = sum(e.get("amount", 0) for e in monthly_events)

            # ── Subscription metrics ──────────────────────────────────────────
            active_subs  = [s for s in subs if s.get("status") == "active"]
            sub_count    = len(active_subs)
            mrr          = sum(s.get("mrr", s.get("amount", 0)) for s in active_subs)
            arr          = mrr * 12
            churn_rate   = _compute_churn(subs)

            # If no subscription data but we have events, estimate MRR from monthly
            if not subs and monthly_revenue > 0:
                mrr = monthly_revenue
                arr = mrr * 12

            # ── Scan for additional revenue files ─────────────────────────────
            extra_files = _scan_revenue_files()
            for fpath in extra_files:
                if fpath in (EVENTS_FILE, SUBS_FILE, TARGETS_FILE, STATS_FILE):
                    continue
                try:
                    with open(fpath) as f:
                        fdata = json.load(f)
                    if isinstance(fdata, list):
                        for row in fdata:
                            if isinstance(row, dict) and row.get("status") == "active":
                                extra_mrr = row.get("mrr", row.get("amount", 0))
                                mrr += extra_mrr
                                arr += extra_mrr * 12
                                sub_count += 1
                    elif isinstance(fdata, dict):
                        mrr += fdata.get("mrr", 0)
                        arr += fdata.get("arr", 0)
                        sub_count += fdata.get("subscribers", fdata.get("subs", 0))
                except Exception:
                    pass

            pct = int(mrr / monthly_target * 100) if monthly_target else 0
            pct = min(pct, 100)

            # ── Persist stats ─────────────────────────────────────────────────
            stats = {
                "agent":           aid,
                "cycle":           cycle,
                "mrr":             mrr,
                "arr":             arr,
                "subscribers":     sub_count,
                "churn_rate":      churn_rate,
                "monthly_revenue": monthly_revenue,
                "total_revenue":   total_revenue,
                "total_events":    total_events,
                "monthly_target":  monthly_target,
                "pct_of_target":   pct,
                "currency":        currency,
                "extra_files_scanned": len(extra_files),
                "updated":         time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            _save_json(STATS_FILE, stats)

            # ── Status string (format expected by growthagent) ─────────────────
            # "MRR $18,716 | ARR $224,596 | Subs 224 | Churn 21.0% | Cycle #35"
            def _fmt(n):
                return f"${n:,.0f}" if n >= 1 else "$0"

            task_str = (
                f"MRR {_fmt(mrr)} | ARR {_fmt(arr)} | "
                f"Subs {sub_count} | Churn {churn_rate:.1f}% | "
                f"Cycle #{cycle}"
            )
            set_agent(aid, status="active", progress=pct, task=task_str)

            if cycle % 5 == 1:
                detail = (
                    f"Revenue snapshot | {task_str} | "
                    f"Monthly: {_fmt(monthly_revenue)} / {_fmt(monthly_target)} target ({pct}%) | "
                    f"Total events: {total_events} | Files scanned: {len(extra_files)}"
                )
                add_log(aid, detail, "info")

        except Exception as e:
            add_log(aid, f"Revenue tracker error: {e}", "error")
            set_agent(aid, status="error", task=f"Error: {str(e)[:80]}")

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", task="Stopped")
"""

if __name__ == "__main__":
    import json, sys, urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "revenue_tracker",
        "name":     "RevenueTracker",
        "role":     "Revenue Intelligence \u2014 logs and surfaces revenue events toward mission targets",
        "emoji":    "\U0001f4b0",
        "color":    "#4ADE80",
        "code":     REVENUE_TRACKER_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
    except Exception as e:
        print(f"HTTP error: {e}")
        sys.exit(1)

    if result.get("ok"):
        print("✓ revenue_tracker (RevenueTracker) spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
