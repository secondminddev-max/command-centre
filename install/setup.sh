#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Command Centre (HQ) — One-Click Setup
# Autonomous AI Agent OS for Mac / Linux
# ═══════════════════════════════════════════════════════════════════════
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

HQ_PORT="${HQ_PORT:-5050}"
HQ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

banner() {
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║          Command Centre (HQ)  v1.0                      ║${NC}"
    echo -e "${PURPLE}║      Autonomous AI Agent Operating System               ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

fail() { echo -e "${RED}ERROR: $1${NC}"; exit 1; }
warn() { echo -e "${YELLOW}  ! $1${NC}"; }
ok()   { echo -e "${GREEN}  + $1${NC}"; }
step() { echo -e "${CYAN}[$1/$TOTAL_STEPS] $2${NC}"; }

TOTAL_STEPS=7

banner

# ── 1. Check Python 3.10+ ───────────────────────────────────────────
step 1 "Checking Python..."
command -v python3 &>/dev/null || fail "Python 3 not found. Install Python 3.10+ from https://python.org"
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    fail "Python 3.10+ required (found $PY_VERSION)"
fi
ok "Python $PY_VERSION"

# ── 2. Check Node.js (for Claude Code CLI) ──────────────────────────
step 2 "Checking Node.js..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node -v)
    ok "Node.js $NODE_VERSION"
else
    warn "Node.js not found. Required for Claude Code CLI."
    warn "Install from https://nodejs.org (LTS recommended)"
fi

# ── 3. Check Claude Code CLI ────────────────────────────────────────
step 3 "Checking Claude Code CLI..."
if command -v claude &>/dev/null; then
    ok "Claude Code CLI found"
else
    warn "Claude Code CLI not found."
    warn "The CEO agent requires it. Install with:"
    warn "  npm install -g @anthropic-ai/claude-code"
    warn "  Then run: claude login"
    echo ""
    read -p "  Continue anyway? (CEO will be limited) [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
fi

# ── 4. Create virtual environment ───────────────────────────────────
step 4 "Setting up virtual environment..."
cd "$HQ_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi
source venv/bin/activate

# ── 5. Install dependencies ─────────────────────────────────────────
step 5 "Installing dependencies..."
pip install --quiet --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install --quiet -r requirements.txt
    ok "Core dependencies installed (from requirements.txt)"
else
    warn "requirements.txt not found — installing minimal deps"
    pip install --quiet requests psutil python-dotenv
fi

# Install optional extras (non-fatal)
pip install --quiet beautifulsoup4 google-auth-oauthlib 2>/dev/null && \
    ok "Optional extras installed (beautifulsoup4, google-auth-oauthlib)" || \
    warn "Some optional extras failed to install (non-critical)"

# ── 6. Configure environment ────────────────────────────────────────
step 6 "Configuring environment..."
mkdir -p data agents reports public campaigns metrics deploy install

if [ ! -f ".env" ]; then
    if [ -f "install/.env.example" ]; then
        cp install/.env.example .env
        warn "Created .env from template — edit it to add your API keys"
        warn "Gmail, Stripe, Bluesky, Telegram credentials go here"
    else
        cat > .env <<'ENVEOF'
# Command Centre (HQ) — Environment Configuration
# Uncomment and fill in the keys you need.

# HQ_API_KEY=your-secret-key-here
# ANTHROPIC_API_KEY=
# STRIPE_SECRET_KEY=
# STRIPE_PRICE_SOLO=
# STRIPE_PRICE_TEAM=
# STRIPE_PRICE_ENTERPRISE=
# STRIPE_PRICE_LIFETIME=
# BLUESKY_HANDLE=
# BLUESKY_APP_PASSWORD=
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_CHAT_ID=
# GMAIL_ADDRESS=
# GMAIL_CLIENT_ID=
# GMAIL_CLIENT_SECRET=
# GMAIL_REFRESH_TOKEN=
ENVEOF
        warn "Created .env skeleton — edit it to add your API keys"
    fi
else
    ok ".env already configured"
fi

# ── 7. Port check & readiness ──────────────────────────────────────
step 7 "Checking port ${HQ_PORT}..."
if lsof -i ":${HQ_PORT}" &>/dev/null; then
    EXISTING_PID=$(lsof -ti ":${HQ_PORT}" 2>/dev/null | head -1)
    warn "Port ${HQ_PORT} is already in use (PID ${EXISTING_PID})"
    warn "HQ may already be running. Check with: curl http://localhost:${HQ_PORT}/api/status"
else
    ok "Port ${HQ_PORT} is available"
fi

# ── Done ────────────────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                    Setup Complete                       ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Start the HQ:${NC}"
echo -e "    ${GREEN}source venv/bin/activate${NC}"
echo -e "    ${GREEN}python3 agent_server.py${NC}"
echo ""
echo -e "  ${BOLD}Quick start (one line):${NC}"
echo -e "    ${GREEN}source venv/bin/activate && python3 agent_server.py &${NC}"
echo ""
echo -e "  ${BOLD}Then open:${NC}"
echo -e "    ${CYAN}http://localhost:${HQ_PORT}${NC}"
echo ""
echo -e "  ${BOLD}Docker alternative:${NC}"
echo -e "    ${GREEN}cd deploy && docker compose up -d${NC}"
echo ""
echo -e "  ${BOLD}Configure agents:${NC}"
echo -e "    ${YELLOW}Edit .env to add Gmail, Stripe, Bluesky, Telegram keys${NC}"
echo ""

# ── Optional: auto-start ────────────────────────────────────────────
if [ "${1}" = "--start" ]; then
    echo -e "${CYAN}Starting HQ server...${NC}"
    cd "$HQ_DIR"
    source venv/bin/activate
    python3 agent_server.py &
    HQ_PID=$!
    echo "$HQ_PID" > agent_server.pid
    sleep 2
    if kill -0 "$HQ_PID" 2>/dev/null; then
        ok "HQ running (PID $HQ_PID)"
        # Health check
        if curl -sf "http://localhost:${HQ_PORT}/api/status" >/dev/null 2>&1; then
            ok "Health check passed — HQ is live at http://localhost:${HQ_PORT}"
        else
            warn "Server started but health check pending — give it a few seconds"
        fi
    else
        fail "Server failed to start. Check server.log for details."
    fi
fi
