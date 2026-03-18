#!/usr/bin/env bash
#
# deploy_render.sh — Push AI HQ to Render and verify deployment
# Usage: ./deploy/deploy_render.sh [--skip-checks]
#
set -euo pipefail

RENDER_SERVICE="command-centre"
RENDER_URL="https://command-centre.onrender.com"
CUSTOM_DOMAIN="https://secondmindhq.com"
BRANCH="main"
HEALTH_ENDPOINT="/api/health"
MAX_WAIT=300   # seconds to wait for deploy to go live
POLL_INTERVAL=15

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[deploy]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✔${NC} $*"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $*"; }
fail() { echo -e "${RED}  ✖${NC} $*"; exit 1; }

# ── Pre-flight checks ──────────────────────────────────────────────────────
preflight() {
    log "Running pre-flight checks..."

    # Git clean check
    if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
        warn "Working tree has uncommitted changes"
        echo "      Commit or stash before deploying to ensure Render builds the right code."
        if [[ "${1:-}" != "--skip-checks" ]]; then
            read -rp "      Continue anyway? [y/N] " ans
            [[ "$ans" =~ ^[Yy] ]] || exit 0
        fi
    else
        ok "Working tree is clean"
    fi

    # Branch check
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" != "$BRANCH" ]]; then
        warn "On branch '$current_branch', not '$BRANCH'. Render deploys from '$BRANCH'."
    else
        ok "On branch $BRANCH"
    fi

    # requirements.txt exists
    [[ -f requirements.txt ]] && ok "requirements.txt found" || fail "requirements.txt missing"

    # render.yaml exists
    [[ -f render.yaml ]] && ok "render.yaml found" || fail "render.yaml missing"

    # Key files present
    [[ -f agent_server.py ]] && ok "agent_server.py found" || fail "agent_server.py missing"

    # Check .env not tracked
    if git ls-files --error-unmatch .env &>/dev/null 2>&1; then
        fail ".env is tracked by git — secrets would be pushed! Run: git rm --cached .env"
    else
        ok ".env is not tracked (secrets safe)"
    fi
}

# ── Push to remote ──────────────────────────────────────────────────────────
push_to_render() {
    log "Pushing $BRANCH to origin (triggers Render auto-deploy)..."
    git push origin "$BRANCH" 2>&1 | sed 's/^/      /'
    ok "Push complete — Render build triggered"
}

# ── Wait for deployment ─────────────────────────────────────────────────────
wait_for_deploy() {
    log "Waiting for $RENDER_URL$HEALTH_ENDPOINT to respond (up to ${MAX_WAIT}s)..."
    elapsed=0
    while (( elapsed < MAX_WAIT )); do
        status=$(curl -s -o /dev/null -w "%{http_code}" "$RENDER_URL$HEALTH_ENDPOINT" 2>/dev/null || echo "000")
        if [[ "$status" == "200" ]]; then
            ok "Health check returned 200 after ${elapsed}s"
            return 0
        fi
        echo -ne "      Waiting... ${elapsed}s (HTTP $status)\r"
        sleep "$POLL_INTERVAL"
        elapsed=$((elapsed + POLL_INTERVAL))
    done
    fail "Health check did not return 200 within ${MAX_WAIT}s"
}

# ── Post-deploy verification ───────────────────────────────────────────────
verify() {
    log "Running post-deploy verification..."

    # Health endpoint
    health=$(curl -s "$RENDER_URL$HEALTH_ENDPOINT" 2>/dev/null || echo "FAIL")
    if echo "$health" | grep -qi "ok\|healthy\|alive"; then
        ok "Health endpoint: $health"
    else
        warn "Health response: $health"
    fi

    # Landing page loads
    lp_status=$(curl -s -o /dev/null -w "%{http_code}" "$RENDER_URL/" 2>/dev/null || echo "000")
    if [[ "$lp_status" == "200" ]]; then
        ok "Landing page (/) returns 200"
    else
        warn "Landing page returned HTTP $lp_status"
    fi

    # API status endpoint
    api_status=$(curl -s -o /dev/null -w "%{http_code}" "$RENDER_URL/api/status" 2>/dev/null || echo "000")
    if [[ "$api_status" == "200" ]]; then
        ok "API /api/status returns 200"
    else
        warn "API /api/status returned HTTP $api_status"
    fi

    # Dashboard loads
    hq_status=$(curl -s -o /dev/null -w "%{http_code}" "$RENDER_URL/hq" 2>/dev/null || echo "000")
    if [[ "$hq_status" == "200" ]]; then
        ok "Dashboard (/hq) returns 200"
    else
        warn "Dashboard (/hq) returned HTTP $hq_status"
    fi

    # Custom domain (if DNS configured)
    custom_status=$(curl -s -o /dev/null -w "%{http_code}" "$CUSTOM_DOMAIN/" --max-time 5 2>/dev/null || echo "000")
    if [[ "$custom_status" == "200" ]]; then
        ok "Custom domain $CUSTOM_DOMAIN returns 200"
    elif [[ "$custom_status" == "000" ]]; then
        warn "Custom domain not reachable yet — DNS may still be propagating"
    else
        warn "Custom domain returned HTTP $custom_status"
    fi

    echo ""
    log "Deployment verification complete."
    echo ""
    echo "  Render URL:    $RENDER_URL"
    echo "  Custom domain: $CUSTOM_DOMAIN"
    echo "  Dashboard:     $RENDER_URL/hq"
    echo "  API status:    $RENDER_URL/api/status"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║   AI HQ — Deploy to Render               ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo ""

    preflight "${1:-}"
    push_to_render
    wait_for_deploy
    verify

    echo -e "${GREEN}  ✔ Deployment successful.${NC}"
    echo ""
}

main "$@"
