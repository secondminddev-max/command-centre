#!/usr/bin/env python3
"""Spawn script for revenue_tracker agent."""
import json, os
import urllib.request

CODE = r'''
def run_revenue_tracker():
    import json, os, glob, time
    from datetime import datetime

    aid = "revenue_tracker"
    SCAN_ROOT = "/Users/secondmind/claudecodetest"
    PATTERNS = [
        "*revenue*", "*billing*", "*subscription*",
        "*payment*", "*invoice*", "*stripe*",
        "*mrr*", "*arr*", "*churn*",
    ]
    REVENUE_KEYWORDS = [
        "revenue", "billing", "subscription", "payment",
        "invoice", "stripe", "mrr", "arr", "churn",
        "price", "amount", "charge", "refund", "trial", "plan", "tier",
    ]

    set_agent(aid, status="active", task="RevenueTracker initializing — scanning for revenue signals")
    add_log(aid, "RevenueTracker online — monitoring revenue events and mission targets", "ok")

    cycle = 0
    total_events_seen = 0
    last_file_count = 0

    while not agent_should_stop(aid):
        try:
            cycle += 1
            scan_time = datetime.now().strftime("%H:%M:%S")

            # --- File scanning by name pattern ---
            revenue_files = []
            for pattern in PATTERNS:
                hits = glob.glob(f"{SCAN_ROOT}/**/{pattern}", recursive=True)
                hits += glob.glob(f"{SCAN_ROOT}/{pattern}", recursive=False)
                revenue_files.extend(hits)
            revenue_files = list(set(revenue_files))

            # --- Content scanning in .py, .json, .txt, .md, .csv ---
            keyword_hits = {}
            for ext in ["*.py", "*.json", "*.txt", "*.md", "*.csv"]:
                for fpath in glob.glob(f"{SCAN_ROOT}/**/{ext}", recursive=True):
                    try:
                        with open(fpath, "r", errors="ignore") as f:
                            content = f.read(8192).lower()
                        found = [kw for kw in REVENUE_KEYWORDS if kw in content]
                        if found:
                            keyword_hits[fpath] = found
                    except Exception:
                        pass

            # --- Estimate MRR from JSON/CSV files with amount/price fields ---
            mrr_estimate = 0.0
            event_count = 0
            anomalies = []

            for fpath in list(keyword_hits.keys()):
                try:
                    if fpath.endswith(".json"):
                        with open(fpath, "r", errors="ignore") as f:
                            data = json.load(f)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if isinstance(item, dict):
                                for field in ["amount", "price", "mrr", "revenue", "charge"]:
                                    val = item.get(field, item.get(field.upper(), None))
                                    if val is not None:
                                        try:
                                            mrr_estimate += float(val)
                                            event_count += 1
                                        except (ValueError, TypeError):
                                            pass
                    elif fpath.endswith(".csv"):
                        with open(fpath, "r", errors="ignore") as f:
                            lines = f.readlines()
                        if lines:
                            header = lines[0].lower()
                            for col in ["amount", "price", "revenue", "mrr"]:
                                if col in header:
                                    cols = header.strip().split(",")
                                    idx = next((i for i, c in enumerate(cols) if col in c), None)
                                    if idx is not None:
                                        for row in lines[1:]:
                                            parts = row.strip().split(",")
                                            if idx < len(parts):
                                                try:
                                                    mrr_estimate += float(
                                                        parts[idx].strip().replace("$", "").replace('"', "")
                                                    )
                                                    event_count += 1
                                                except (ValueError, TypeError):
                                                    pass
                except Exception:
                    anomalies.append(os.path.basename(fpath))

            total_events_seen += event_count

            # --- Detect file count changes since last cycle ---
            new_files = len(revenue_files) - last_file_count if cycle > 1 else 0
            last_file_count = len(revenue_files)

            # --- Build concise status summary ---
            mrr_str = f"${mrr_estimate:,.2f}" if mrr_estimate > 0 else "$0 (no numeric data)"
            new_str = f" | +{new_files} new" if new_files > 0 else ""
            anomaly_str = f" | {len(anomalies)} parse errs" if anomalies else ""
            summary = (
                f"Cycle #{cycle} @ {scan_time}"
                f" | Rev files: {len(revenue_files)}"
                f" | KW matches: {len(keyword_hits)}{new_str}"
                f" | MRR est: {mrr_str} ({event_count} events)"
                f" | Total: {total_events_seen}{anomaly_str}"
            )

            add_log(aid, summary, "info")
            set_agent(aid, status="active", progress=min(cycle * 5, 90), task=summary)

        except Exception as e:
            err_msg = f"Cycle #{cycle} ERROR: {e}"
            add_log(aid, err_msg, "error")
            set_agent(aid, status="error", task=err_msg)

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", task="Stopped")
'''

if __name__ == "__main__":
    payload = json.dumps({
        "agent_id": "revenue_tracker",
        "name": "RevenueTracker",
        "role": "Revenue Intelligence \u2014 logs and surfaces revenue events toward mission targets",
        "emoji": "\U0001f4b0",
        "color": "#4ADE80",
        "code": CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:5050/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": os.environ.get("HQ_API_KEY", "")},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read().decode())
    print(json.dumps(result, indent=2))
