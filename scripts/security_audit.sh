#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Security Audit — scan distributable files for leaked credentials
# Run: bash scripts/security_audit.sh
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
FAIL=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "═══ Security Audit: $ROOT ═══"
echo ""

# 1. Check .env is not tracked
echo -n "[1] .env in .gitignore ... "
if grep -q '^\.env$' "$ROOT/.gitignore" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL — .env not in .gitignore${NC}"; FAIL=1
fi

# 2. Check .dockerignore exists and excludes .env
echo -n "[2] .dockerignore excludes .env ... "
if [ -f "$ROOT/.dockerignore" ] && grep -q '^\.env$' "$ROOT/.dockerignore"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL — .dockerignore missing or doesn't exclude .env${NC}"; FAIL=1
fi

# 3. Scan for hardcoded secrets in code (excluding .env itself)
echo -n "[3] No hardcoded API keys in source ... "
PATTERNS='(sk_live_[a-zA-Z0-9]{20,}|sk_test_[a-zA-Z0-9]{20,}|GOCSPX--[a-zA-Z0-9_-]+|ghp_[a-zA-Z0-9]{36}|xox[bpas]-[a-zA-Z0-9-]+)'
HITS=$(grep -rE "$PATTERNS" "$ROOT" \
    --include='*.py' --include='*.js' --include='*.sh' --include='*.yml' --include='*.yaml' --include='*.json' \
    --exclude-dir=node_modules --exclude-dir=.git \
    -l 2>/dev/null | grep -v '\.env' | grep -v '.env.example' || true)
if [ -z "$HITS" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL — secrets found in:${NC}"
    echo "$HITS" | sed 's/^/    /'
    FAIL=1
fi

# 4. Check no private keys in repo
echo -n "[4] No .pem/.key files in source ... "
KEYS=$(find "$ROOT" -name '*.pem' -o -name '*.key' 2>/dev/null | grep -v node_modules | grep -v '.git' | grep -v 'public/' || true)
if [ -z "$KEYS" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARN — found key files:${NC}"
    echo "$KEYS" | sed 's/^/    /'
fi

# 5. Check install/.env.example has no real values
echo -n "[5] .env.example has no real values ... "
REAL=$(grep -E '=.{10,}' "$ROOT/install/.env.example" 2>/dev/null | grep -vE '(=your-|=xxxx|=sk_live_YOUR|=sk_test_YOUR|=$|=#|=http)' || true)
if [ -z "$REAL" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL — possible real values in .env.example:${NC}"
    echo "$REAL" | sed 's/^/    /'
    FAIL=1
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}═══ ALL CHECKS PASSED ═══${NC}"
else
    echo -e "${RED}═══ AUDIT FAILED — fix issues above ═══${NC}"
    exit 1
fi
