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
    CWD          = globals().get("CWD", os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR     = os.path.join(CWD, "data")
    EVENTS_FILE  = os.path.join(DATA_DIR, "revenue_events.json")
    SUBS_FILE    = os.path.join(DATA_DIR, "subscriptions.json")
    TARGETS_FILE = os.path.join(DATA_DIR, "revenue_targets.json")
    STATS_FILE       = os.path.join(DATA_DIR, "revenue_stats.json")
    TREASURY_FILE    = os.path.join(DATA_DIR, "treasury.json")
    COST_LEDGER_FILE = os.path.join(DATA_DIR, "cost_ledger.json")
    FUNDING_FILE     = os.path.join(DATA_DIR, "funding_status.json")

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
        if not os.path.exists(path):
            return default
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            add_log(aid, f"Corrupted JSON in {os.path.basename(path)}: {e} — using defaults", "error")
            return default
        except PermissionError:
            add_log(aid, f"Permission denied reading {os.path.basename(path)}", "error")
            return default
        except Exception as e:
            add_log(aid, f"Failed to load {os.path.basename(path)}: {type(e).__name__}: {e}", "error")
            return default

    def _save_json(path, data):
        # Atomic write: write to temp file, then rename to avoid corruption.
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)
        except PermissionError:
            add_log(aid, f"Permission denied writing {os.path.basename(path)}", "error")
        except OSError as e:
            add_log(aid, f"Failed to write {os.path.basename(path)}: {e}", "error")
            # Clean up temp file if rename failed
            try:
                os.remove(tmp_path)
            except OSError:
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

    # ── auto-reconcile helper ─────────────────────────────────────────────────
    def _auto_reconcile():
        # Call /api/revenue/reconcile to pull real Stripe payments into local data
        import urllib.request as _ur, urllib.error as _uerr
        try:
            _req = _ur.Request(
                "http://localhost:5050/api/revenue/reconcile",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            _resp = _ur.urlopen(_req, timeout=20)
            _data = json.loads(_resp.read().decode())
            _rc = _data.get("reconciled", 0)
            if _rc > 0:
                add_log(aid, f"Auto-reconcile: {_rc} new payments pulled from Stripe", "ok")
            return _data
        except _uerr.URLError as e:
            add_log(aid, f"Auto-reconcile network error: {e.reason}", "warn")
        except Exception as e:
            add_log(aid, f"Auto-reconcile failed: {e}", "warn")
        return {}

    # ── main loop ──────────────────────────────────────────────────────────────
    cycle = 0
    while not agent_should_stop(aid):
        cycle += 1
        try:
            # Auto-reconcile against Stripe every 5th cycle (~5 min)
            if cycle % 5 == 1:
                _auto_reconcile()

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

            # ── Treasury reconciliation ──────────────────────────────────────
            treasury = _load_json(TREASURY_FILE, {})
            treasury_txns = treasury.get("transactions", [])
            treasury_balance = treasury.get("balance_usd", 0)
            settled_txns = [t for t in treasury_txns if t.get("status") == "settled"]
            total_settled = sum(t.get("amount_usd", 0) for t in settled_txns)
            # Use treasury as ground truth for total revenue if higher
            if total_settled > total_revenue:
                total_revenue = total_settled

            # If no subscription data, do NOT assume monthly revenue = MRR
            # MRR only comes from confirmed recurring subscriptions
            if not subs and mrr == 0:
                # Check treasury for recurring (subscription) payments
                for t in settled_txns:
                    if t.get("product") in ("solo", "team", "enterprise"):
                        # Map product to tier price for MRR
                        tier_mrr = {"solo": 49, "team": 149, "enterprise": 499}
                        mrr += tier_mrr.get(t.get("product"), 0)
                        sub_count += 1
                arr = mrr * 12

            # ── Scan for additional revenue files ─────────────────────────────
            extra_files = _scan_revenue_files()
            _SKIP_BASENAMES = {"revenue_stats.json", "funding_status.json",
                               "cost_ledger.json", "treasury.json",
                               "revenue_events.json", "subscriptions.json",
                               "revenue_targets.json", "revenue_log.json"}
            for fpath in extra_files:
                if fpath in (EVENTS_FILE, SUBS_FILE, TARGETS_FILE, STATS_FILE) or os.path.basename(fpath) in _SKIP_BASENAMES:
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
                except json.JSONDecodeError:
                    add_log(aid, f"Skipping malformed revenue file: {os.path.basename(fpath)}", "warn")
                except Exception as e:
                    add_log(aid, f"Error reading {os.path.basename(fpath)}: {e}", "warn")

            pct = int(mrr / monthly_target * 100) if monthly_target else 0
            pct = min(pct, 100)

            # ── Self-funding: cost awareness ───────────────────────────────────
            cost_ledger   = _load_json(COST_LEDGER_FILE, {})
            cost_items    = cost_ledger.get("monthly_costs", [])
            fixed_costs   = sum(c.get("amount_usd", 0) for c in cost_items
                                if c.get("status") == "active" and c.get("id") != "stripe_fees")

            # Variable cost: Stripe fees on monthly revenue
            stripe_entry  = next((c for c in cost_items if c.get("id") == "stripe_fees"), {})
            stripe_pct    = stripe_entry.get("rate_pct", 2.9) / 100
            stripe_fixed  = stripe_entry.get("rate_fixed", 0.30)
            # Estimate Stripe fees from treasury transaction count this month
            monthly_txns  = [t for t in treasury_txns
                             if t.get("date", "").startswith(now_prefix) and t.get("status") == "settled"]
            stripe_fees   = sum(t.get("amount_usd", 0) * stripe_pct + stripe_fixed for t in monthly_txns)

            total_monthly_cost = round(fixed_costs + stripe_fees, 2)
            net_position       = round(mrr - total_monthly_cost, 2)
            runway_months      = round(treasury_balance / total_monthly_cost, 1) if total_monthly_cost > 0 else 999
            burn_rate          = round(total_monthly_cost - mrr, 2) if total_monthly_cost > mrr else 0

            if mrr >= total_monthly_cost:
                funding_status = "self-sustaining"
            elif mrr >= total_monthly_cost * 0.5:
                funding_status = "partially-funded"
            elif mrr > 0:
                funding_status = "early-revenue"
            else:
                funding_status = "pre-revenue"

            # ── Breakeven & self-funding targets ────────────────────────
            breakeven_mrr     = total_monthly_cost  # MRR needed to cover costs
            pct_to_breakeven  = round(mrr / breakeven_mrr * 100, 1) if breakeven_mrr > 0 else 0
            pct_to_breakeven  = min(pct_to_breakeven, 100)
            # Subscribers needed at avg tier price to break even
            avg_tier_price    = 49  # Solo tier baseline
            subs_to_breakeven = max(0, int((breakeven_mrr - mrr) / avg_tier_price) + 1) if mrr < breakeven_mrr else 0
            # Days at current daily revenue rate to cover monthly costs
            day_of_month      = int(time.strftime("%d"))
            daily_rev_rate    = round(monthly_revenue / max(day_of_month, 1), 2)
            days_to_breakeven = int(breakeven_mrr / daily_rev_rate) if daily_rev_rate > 0 else 999

            funding_data = {
                "status":             funding_status,
                "mrr":                mrr,
                "arr":                arr,
                "subscribers":        sub_count,
                "total_monthly_cost": total_monthly_cost,
                "fixed_costs":        fixed_costs,
                "stripe_fees":        round(stripe_fees, 2),
                "net_position":       net_position,
                "burn_rate":          burn_rate,
                "runway_months":      runway_months,
                "treasury_balance":   treasury_balance,
                "total_revenue":      total_revenue,
                "currency":           "usd",
                "cost_breakdown": {c.get("id", "?"): c.get("amount_usd", 0)
                                   for c in cost_items if c.get("status") == "active"},
                "breakeven_mrr":      breakeven_mrr,
                "pct_to_breakeven":   pct_to_breakeven,
                "subs_to_breakeven":  subs_to_breakeven,
                "daily_rev_rate":     daily_rev_rate,
                "days_to_breakeven":  days_to_breakeven,
                "updated":            time.strftime("%Y-%m-%dT%H:%M:%S"),
                "cycle":              cycle,
            }
            _save_json(FUNDING_FILE, funding_data)

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
                "treasury_balance": treasury_balance,
                "total_events":    total_events,
                "monthly_target":  monthly_target,
                "pct_of_target":   pct,
                "currency":        currency,
                "extra_files_scanned": len(extra_files),
                "self_funding":    funding_status,
                "net_position":    net_position,
                "total_monthly_cost": total_monthly_cost,
                "runway_months":   runway_months,
                "updated":         time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            _save_json(STATS_FILE, stats)

            # ── Status string (format expected by growthagent) ─────────────────
            def _fmt(n):
                return f"${n:,.0f}" if n >= 1 else "$0"

            _fund_icon = "\u2705" if funding_status == "self-sustaining" else "\u26a0\ufe0f"
            task_str = (
                f"MRR {_fmt(mrr)} | Costs {_fmt(total_monthly_cost)} | "
                f"Net {_fmt(net_position)} | {_fund_icon} {funding_status} | "
                f"Runway {runway_months:.0f}mo | Cycle #{cycle}"
            )
            set_agent(aid, status="active", progress=pct, task=task_str)

            if cycle % 5 == 1:
                detail = (
                    f"Funding snapshot | {task_str} | "
                    f"Treasury: {_fmt(treasury_balance)} | Burn: {_fmt(burn_rate)}/mo | "
                    f"Total rev: {_fmt(total_revenue)} | Files: {len(extra_files)}"
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
