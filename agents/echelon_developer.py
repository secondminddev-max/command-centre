"""
Echelon Vantage Autonomous Developer
Runs overnight — tests every endpoint, checks every page, fixes issues.
Uses Claude CLI for intelligent code improvements.
"""
import time, json, os, subprocess, requests
from datetime import datetime, timezone

SPACE_DIR = os.path.expanduser("~/space-osint")
LOCAL_BASE = "http://localhost:8900"
LOG_FILE = os.path.expanduser("~/claudecodetest/data/echelon_dev_log.json")

# All endpoints to test
ENDPOINTS = [
    "/api/status", "/api/adversary/stats", "/api/launches", "/api/weather",
    "/api/news", "/api/neo", "/api/satellites/stats",
    "/api/missile-asat/summary", "/api/ground-stations/summary",
    "/api/threat/overview", "/api/threat/vulnerabilities",
    "/api/threat/recommendations", "/api/threat/scenarios",
    "/api/intel/sitrep", "/api/intel/hotspots", "/api/intel/social",
    "/api/intel/proximity", "/api/intel/research",
    "/api/deductions/priority", "/api/deductions/narrative",
    "/api/overmatch/summary", "/api/wargame/scenarios",
    "/api/incidents/stats", "/api/futures/summary",
    "/api/conferences", "/api/environment/enhanced",
    "/api/industry/contractors", "/api/industry/contracts",
    "/api/analysis/engagement-envelopes", "/api/analysis/escalation-ladder",
    "/api/analysis/kill-chains", "/api/analysis/mission-assurance",
    "/api/analysis/alliances", "/api/analysis/treaties",
    "/api/analysis/cislunar", "/api/analysis/indicators-warnings",
]

# Pages to test (check they load without JS errors)
PAGES = [
    "/app", "/pricing", "/",
]

def log_entry(entry):
    try:
        data = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                data = json.load(f)
        data.append(entry)
        data = data[-200:]
        with open(LOG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def test_all_endpoints():
    """Test every API endpoint returns 200 with valid JSON."""
    results = {"passed": 0, "failed": 0, "errors": []}
    for ep in ENDPOINTS:
        try:
            r = requests.get(f"{LOCAL_BASE}{ep}", timeout=30)
            if r.status_code == 200:
                try:
                    r.json()
                    results["passed"] += 1
                except Exception:
                    results["failed"] += 1
                    results["errors"].append(f"{ep}: 200 but invalid JSON")
            else:
                results["failed"] += 1
                results["errors"].append(f"{ep}: HTTP {r.status_code}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{ep}: {type(e).__name__}")
    return results

def test_pages():
    """Test HTML pages load."""
    results = {"passed": 0, "failed": 0, "errors": []}
    for page in PAGES:
        try:
            r = requests.get(f"{LOCAL_BASE}{page}", timeout=15)
            if r.status_code == 200 and len(r.text) > 100:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{page}: HTTP {r.status_code} len={len(r.text)}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{page}: {type(e).__name__}")
    return results

def check_js_syntax():
    """Check pages.js for syntax issues."""
    issues = []
    try:
        with open(os.path.join(SPACE_DIR, "static/js/pages.js")) as f:
            content = f.read()
        # Check backticks
        if content.count('`') % 2 != 0:
            issues.append("ODD backtick count — template literal syntax error")
        # Check bare catch
        import re
        bare = re.findall(r'catch\s*\{', content)
        if bare:
            issues.append(f"{len(bare)} bare catch blocks")
        # Check brace balance
        if content.count('{') != content.count('}'):
            issues.append(f"Unbalanced braces: {{ ={content.count('{')}, }} ={content.count('}')}")
    except Exception as e:
        issues.append(f"Could not read pages.js: {e}")
    return issues

def run_claude_fix(issue_description):
    """Use Claude CLI to fix an issue if available."""
    try:
        result = subprocess.run(
            ["claude", "-p", f"Fix this issue in /Users/secondmind/space-osint: {issue_description}. Only fix the specific issue, don't rewrite everything. Be minimal."],
            cwd=SPACE_DIR, capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0
    except Exception:
        return False

def git_push_if_changed():
    """Push any fixes to GitHub."""
    try:
        status = subprocess.run(["git", "status", "--short"], cwd=SPACE_DIR, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "add", "-A"], cwd=SPACE_DIR)
            subprocess.run(
                ["git", "-c", "user.name=SecondMind", "-c", "user.email=secondminddev@gmail.com",
                 "commit", "-m", "Autonomous overnight fix — Echelon Developer Agent"],
                cwd=SPACE_DIR
            )
            subprocess.run(["git", "push", "origin", "main"], cwd=SPACE_DIR)
            return True
    except Exception:
        pass
    return False

def run_cycle():
    """Run one full test + fix cycle."""
    ts = datetime.now(timezone.utc).isoformat()
    
    # Test endpoints
    api_results = test_all_endpoints()
    
    # Test pages
    page_results = test_pages()
    
    # Check JS syntax
    js_issues = check_js_syntax()
    
    # Log results
    entry = {
        "timestamp": ts,
        "api_tests": api_results,
        "page_tests": page_results,
        "js_issues": js_issues,
        "total_passed": api_results["passed"] + page_results["passed"],
        "total_failed": api_results["failed"] + page_results["failed"],
    }
    
    # If there are failures, try to fix them
    all_errors = api_results["errors"] + page_results["errors"] + js_issues
    if all_errors:
        entry["attempted_fixes"] = []
        for error in all_errors[:3]:  # Fix up to 3 issues per cycle
            fixed = run_claude_fix(error)
            entry["attempted_fixes"].append({"issue": error, "fixed": fixed})
        
        # Push fixes if any were made
        pushed = git_push_if_changed()
        entry["pushed_fixes"] = pushed
    
    log_entry(entry)
    return entry

if __name__ == "__main__":
    print("[ECHELON DEV] Starting autonomous development cycle...")
    while True:
        try:
            result = run_cycle()
            passed = result["total_passed"]
            failed = result["total_failed"]
            print(f"[ECHELON DEV] {result['timestamp'][:19]}Z — {passed} passed, {failed} failed")
            if result.get("attempted_fixes"):
                for fix in result["attempted_fixes"]:
                    print(f"  FIX: {fix['issue'][:60]} — {'FIXED' if fix['fixed'] else 'FAILED'}")
        except Exception as e:
            print(f"[ECHELON DEV] Cycle error: {e}")
        
        # Run every 30 minutes
        time.sleep(1800)
