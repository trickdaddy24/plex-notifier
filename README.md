# Notifier

A Python CLI tool for scheduling and delivering reminders across multiple notification platforms — Telegram, Discord, Pushover, and Gmail — with a built-in SQLite-backed scheduler and an integrated version management system.

## Features

- **Multi-platform delivery** — send reminders to Telegram, Discord, Pushover, and Gmail simultaneously
- **SQLite scheduler** — store notifications with due times; a background thread fires them automatically every minute
- **Desktop notifications** — optional Windows/macOS/Linux system toasts via `plyer`
- **Full CRUD** — add, view, edit, and delete scheduled notifications
- **Service health checks** — verify each integration directly from the menu
- **Version management** — built-in release tracker with auto-generated `CHANGELOG.md` (System menu → Version History)

---

## Installation

### Windows 11

**1. Install Python 3.10+**

Download and run the installer from [python.org](https://www.python.org/downloads/windows/).
On the first screen, check **"Add Python to PATH"** before clicking Install.

Verify the install:
```cmd
python --version
```

**2. Install Git**

Download from [git-scm.com](https://git-scm.com/download/win) and run the installer with default settings.

Verify:
```cmd
git --version
```

**3. Clone the repo**
```cmd
git clone https://github.com/trickdaddy24/notifier.git
cd notifier
```

**4. Create and activate a virtual environment**
```cmd
python -m venv .venv
.venv\Scripts\activate
```
You should see `(.venv)` appear at the start of your prompt.

**5. Install dependencies**
```cmd
pip install -r requirements.txt
```

**6. Create your `.env` file**
```cmd
copy .env.example .env
```
Then open `.env` in Notepad or any editor and fill in your credentials (see [Configuration](#configuration) below).

**7. Run the app**
```cmd
python notifier.py
```

> **Desktop notifications on Windows 11** are handled automatically via `plyer` — no extra setup needed.

---

### macOS

**1. Install Python 3.10+**

The recommended way is via [Homebrew](https://brew.sh). If you don't have Homebrew, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python:
```bash
brew install python
```

Verify:
```bash
python3 --version
```

**2. Install Git**

Git ships with Xcode Command Line Tools. If you don't have it:
```bash
xcode-select --install
```

Or install via Homebrew:
```bash
brew install git
```

**3. Clone the repo**
```bash
git clone https://github.com/trickdaddy24/notifier.git
cd notifier
```

**4. Create and activate a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```
You should see `(.venv)` appear at the start of your prompt.

**5. Install dependencies**
```bash
pip install -r requirements.txt
```

**6. Create your `.env` file**
```bash
cp .env.example .env
```
Then open `.env` in any editor and fill in your credentials (see [Configuration](#configuration) below).

**7. Run the app**
```bash
python notifier.py
```

> **Desktop notifications on macOS** require granting terminal notification permissions.
> Go to **System Settings → Notifications** and allow notifications for your terminal app (Terminal or iTerm2).

---

### Linux (Ubuntu / Debian)

**One-liner install (recommended)**

```bash
bash <(curl -sL https://raw.githubusercontent.com/trickdaddy24/notifier/main/install.sh)
```

The script will:
- Verify Python 3.10+ (and offer install instructions if missing)
- Install `git` and `libnotify-bin` if not present
- Clone the repo to `~/notifier`
- Create a virtual environment and install all dependencies
- Generate a starter `.env` file
- Create a `notifier` launch command available system-wide

Then run:
```bash
notifier
```

> **If the command is not found** after install, reload your shell:
> ```bash
> source ~/.bashrc
> ```

---

**Manual install (any distro)**

Ubuntu / Debian:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git libnotify-bin -y
```

Fedora:
```bash
sudo dnf install python3 python3-pip git libnotify -y
```

Arch:
```bash
sudo pacman -S python python-pip git libnotify
```

```bash
git clone https://github.com/trickdaddy24/notifier.git
cd notifier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python notifier.py
```

---

## Configuration

Create a `.env` file in the project root. **Never commit this file.**

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Pushover
PUSHOVER_USER_KEY=your_user_key_here
PUSHOVER_API_TOKEN=your_api_token_here

# Gmail (use an App Password, not your regular password)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENT=recipient@email.com
```

Each service is optional — unconfigured services are silently skipped when sending. You can verify and test each one inside the **Notification Services** menu (option 6).

### Telegram setup
1. Message `@BotFather` → `/newbot` → copy the token
2. Message `@userinfobot` to get your chat ID

### Discord setup
1. Server Settings → Integrations → Webhooks → New Webhook → Copy URL

### Pushover setup
1. Create an account at [pushover.net](https://pushover.net)
2. Copy your User Key and create an API Token

### Gmail setup
1. Google Account → Security → 2-Step Verification → App Passwords
2. Generate a password for "Mail" and use it as `EMAIL_PASSWORD`

---

## Usage

```bash
python notifier.py
```

### Main menu

```
╔═══════════════════════════════════════╗
║       NOTIFICATION MENU               ║
║             v1.0.33                   ║
╚═══════════════════════════════════════╝
1.  Add Notification
2.  View Notifications
3.  Send Due Notifications Now
4.  Edit Notification
5.  Delete Notification
6.  Notification Services
7.  System  [v1.0.33]
0.  Exit
```

### System menu (option 7)

Provides access to the integrated version management system:

```
╔═══════════════════════════════════════╗
║       SYSTEM                          ║
║             v1.0.33                   ║
╚═══════════════════════════════════════╝
1.  View Version History
2.  Add New Version Release
3.  Edit Version Notes
0.  Back
```

Release notes are stored in `version_notes.db` and `CHANGELOG.md` is regenerated automatically after every add or edit.

---

## Project Structure

```
notifier/
├── notifier.py          # Main application
├── version_manager.py   # Version tracking & changelog generation
├── requirements.txt
├── .gitignore
├── .env                 # Your secrets (NOT in repo)
├── CHANGELOG.md         # Auto-generated by version_manager
├── notifications.db     # Runtime — excluded from repo
└── version_notes.db     # Runtime — excluded from repo
```

---

## License

MIT
