#!/usr/bin/env bash
#
# verify_deploy.sh — Check all endpoints on the live Render deployment
# Usage: ./deploy/verify_deploy.sh [URL]
#
set -euo pipefail

BASE_URL="${1:-https://hq.secondmindhq.com}"
CUSTOM_DOMAIN="https://secondmindhq.com"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
PASS=0
WARN=0
FAIL=0

check() {
    local label="$1" url="$2" expect="${3:-200}"
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 10 2>/dev/null || echo "000")
    if [[ "$status" == "$expect" ]]; then
        echo -e "  ${GREEN}✔${NC} $label — HTTP $status"
        PASS=$((PASS + 1))
    elif [[ "$status" == "000" ]]; then
        echo -e "  ${YELLOW}⚠${NC} $label — unreachable"
        WARN=$((WARN + 1))
    else
        echo -e "  ${RED}✖${NC} $label — HTTP $status (expected $expect)"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo -e "${CYAN}Verifying deployment: $BASE_URL${NC}"
echo ""

check "Health"           "$BASE_URL/api/health"
check "Landing page"     "$BASE_URL/"
check "Dashboard"        "$BASE_URL/hq"
check "API status"       "$BASE_URL/api/status"
check "Stripe pay"       "$BASE_URL/api/pay"
check "Agent list"       "$BASE_URL/api/agents"

echo ""
echo -e "${CYAN}Custom domain: $CUSTOM_DOMAIN${NC}"
check "Root domain"      "$CUSTOM_DOMAIN/"
check "Domain dashboard" "$CUSTOM_DOMAIN/hq"

echo ""
echo -e "Results: ${GREEN}$PASS passed${NC}, ${YELLOW}$WARN warnings${NC}, ${RED}$FAIL failed${NC}"
echo ""

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
