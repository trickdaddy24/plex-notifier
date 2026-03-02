#!/usr/bin/env bash
# install.sh — Ubuntu / Linux installer for Plex Notifier
set -e

REPO="https://github.com/trickdaddy24/plex-notifier.git"
INSTALL_DIR="$HOME/plex-notifier"

echo ""
echo "🔔 Plex Notifier — Installer"
echo "=============================="
echo ""

OS_TYPE=$(uname -s)

if [[ "$OS_TYPE" != "Linux" ]]; then
    echo "❌ This installer targets Ubuntu / Linux only."
    echo "   For macOS and Windows 11 see the README."
    exit 1
fi

echo "🐧 Detected Linux"
echo ""

# ── Python 3.10+ ───────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "📦 python3 not found — installing..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip python3-venv
fi

PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PY_VER="$PY_MAJOR.$PY_MINOR"

if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
    echo "❌ Python 3.10+ required. Found: Python $PY_VER"
    echo ""
    echo "   Upgrade with:"
    echo "   sudo apt install python3.10 python3.10-venv python3.10-pip"
    exit 1
fi
echo "✅ Python $PY_VER found"

# ── git ────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo "📦 git not found — installing..."
    sudo apt-get update -qq
    sudo apt-get install -y git
fi
echo "✅ git found"

# ── libnotify (desktop notifications) ─────────────────────────
if ! command -v notify-send &>/dev/null; then
    echo "📦 Installing libnotify-bin for desktop notifications..."
    sudo apt-get install -y libnotify-bin
fi
echo "✅ libnotify found"

# ── Clone or update ────────────────────────────────────────────
echo ""
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "🔄 Existing install found — updating $INSTALL_DIR..."
    git -C "$INSTALL_DIR" fetch origin
    git -C "$INSTALL_DIR" reset --hard origin/main
else
    echo "📦 Cloning plex-notifier to $INSTALL_DIR..."
    git clone "$REPO" "$INSTALL_DIR"
fi
echo "✅ Repo ready at $INSTALL_DIR"

# ── Virtual environment ────────────────────────────────────────
echo ""
echo "📦 Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
echo "✅ Virtual environment ready"

# ── Dependencies ───────────────────────────────────────────────
echo "📦 Installing dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "✅ Dependencies installed"

# ── Starter .env ───────────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo ""
    echo "📄 Creating starter .env file..."
    cat > "$INSTALL_DIR/.env" << 'ENVFILE'
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Discord
DISCORD_WEBHOOK_URL=

# Pushover
PUSHOVER_USER_KEY=
PUSHOVER_API_TOKEN=

# Gmail
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_RECIPIENT=
ENVFILE
    echo "✅ .env created at $INSTALL_DIR/.env"
    echo "   Tip: You can set credentials from inside the app (option 6 → service → option 2)"
else
    echo "✅ Existing .env found — not overwritten."
fi

# ── Launcher script ────────────────────────────────────────────
LAUNCHER="$HOME/.local/bin/plex-notifier"
mkdir -p "$HOME/.local/bin"
cat > "$LAUNCHER" << LAUNCHER_EOF
#!/usr/bin/env bash
source "$INSTALL_DIR/.venv/bin/activate"
python "$INSTALL_DIR/notifier.py"
LAUNCHER_EOF
chmod +x "$LAUNCHER"
echo "✅ Launcher created: $LAUNCHER"

# ── PATH ───────────────────────────────────────────────────────
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
fi

# ── Done ───────────────────────────────────────────────────────
echo ""
echo "✅ Installation complete!"
echo ""
echo "Run the app:"
echo "  plex-notifier"
echo ""
echo "Or directly:"
echo "  cd $INSTALL_DIR && source .venv/bin/activate && python notifier.py"
echo ""
echo "First-time setup:"
echo "  1. Run: plex-notifier"
echo "  2. Go to option 6 — Notification Services"
echo "  3. Choose a service and select option 2 — Set Credentials"
echo "  4. Enter your tokens/keys — saved automatically to .env"
echo ""
echo "⚠️  If 'plex-notifier' command is not found after install, run:"
echo "   source ~/.bashrc"
echo ""
