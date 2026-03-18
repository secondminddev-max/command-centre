#!/usr/bin/env python3
"""
upgrade_rate_limit_survival.py
Hot-reloads NetScout, Researcher, and AccountProvisioner with
rate-limit survival upgrades (exponential backoff, TTL cache, key-pool rotation).
"""
import sys, json, requests

BASE = "http://localhost:5050"

def upgrade(agent_id, name, role, emoji, color, code):
    print(f"\n  Upgrading {emoji} {name} ({agent_id})...", end=" ", flush=True)
    r = requests.post(f"{BASE}/api/agent/upgrade", json={
        "agent_id": agent_id,
        "name":     name,
        "role":     role,
        "emoji":    emoji,
        "color":    color,
        "code":     code,
    }, timeout=15)
    result = r.json()
    ok = result.get("ok") or "running" in str(result).lower()
    print("✓" if ok else f"✗ {result}")
    return result


# ── Pull upgraded code strings from spawn_agents.py and accountprovisioner.py ─
import importlib.util, os, sys

# Load spawn_agents module to get NETSCOUT_CODE and RESEARCHER_CODE
spec = importlib.util.spec_from_file_location(
    "spawn_agents",
    os.path.join(os.path.dirname(__file__), "spawn_agents.py")
)
sa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa)

# Load accountprovisioner to get ACCOUNTPROVISIONER_CODE
spec2 = importlib.util.spec_from_file_location(
    "accountprovisioner",
    os.path.join(os.path.dirname(__file__), "agents", "accountprovisioner.py")
)
ap = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(ap)

print("\n  ━━━ Rate-Limit Survival Upgrade ━━━")

upgrade(
    "netscout",
    "NetScout",
    "Network Scout — on-demand web intelligence and connectivity checks",
    "🌐", "#20b2aa",
    sa.NETSCOUT_CODE,
)

upgrade(
    "researcher",
    "Researcher",
    "Intelligence Analyst — on-demand web research, data gathering and synthesis",
    "🔬", "#9370db",
    sa.RESEARCHER_CODE,
)

upgrade(
    "accountprovisioner",
    "AccountProvisioner",
    "Credential Factory — auto-provisions disposable emails, tokens, and service accounts",
    "🔑", "#f59e0b",
    ap.ACCOUNTPROVISIONER_CODE,
)

print("\n  ━━━ Done — all three agents hot-reloaded ━━━\n")
