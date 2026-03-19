#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────────
# Second Mind AI — Command Centre Installer
# Usage: curl -sL https://secondmindlabs.com/install.sh | bash
# ────────────────────────────────────────────────────────────────────────────────
set -e

REPO_URL="https://github.com/secondminddev-max/command-centre.git"
INSTALL_DIR="command-centre"

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║       Second Mind AI — Command Centre           ║"
echo "  ║              Installer v1.0                     ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo "  [ERROR] git is not installed. Please install git first."
    echo "          macOS:  xcode-select --install"
    echo "          Linux:  sudo apt install git"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "  [ERROR] python3 is not installed. Please install Python 3.9+."
    exit 1
fi

PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  [OK] Python $PYTHON_VER detected"

# ── Clone repository ──────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR" ]; then
    echo "  [INFO] Directory '$INSTALL_DIR' already exists — pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || echo "  [WARN] git pull failed — continuing with existing code"
else
    echo "  [STEP] Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── Create .env from template ────────────────────────────────────────────────
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "  [OK] Created .env from .env.example"
    else
        echo "  [WARN] No .env.example found — you will need to create .env manually"
    fi
else
    echo "  [OK] .env already exists — skipping"
fi

# ── Install Python dependencies ──────────────────────────────────────────────
echo "  [STEP] Installing Python dependencies..."
pip3 install --quiet requests psutil python-dotenv 2>/dev/null || \
    python3 -m pip install --quiet requests psutil python-dotenv 2>/dev/null || \
    echo "  [WARN] pip install failed — please run: pip3 install requests psutil python-dotenv"

echo ""
echo "  ════════════════════════════════════════════════════"
echo "  Installation complete!"
echo "  ════════════════════════════════════════════════════"
echo ""
echo "  Next steps:"
echo ""
echo "  1. cd $INSTALL_DIR"
echo "  2. Edit .env and add your API keys:"
echo "       ANTHROPIC_API_KEY=sk-ant-...    (required — from console.anthropic.com)"
echo "       HQ_API_KEY=your-secret-key      (protects admin endpoints)"
echo "       STRIPE_SECRET_KEY=sk_live_...    (optional — for payments)"
echo ""
echo "  3. Start the server:"
echo "       python3 agent_server.py"
echo ""
echo "  4. Open in browser:"
echo "       http://localhost:5050"
echo ""
echo "  Need help? hello@secondmindlabs.com"
echo ""
