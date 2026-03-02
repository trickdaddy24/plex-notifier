import sqlite3
import time
import threading
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from colorama import init, Fore, Back, Style
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import schedule
import requests
from dotenv import load_dotenv, set_key
from pathlib import Path

ENV_PATH = Path(__file__).parent / '.env'

# Load environment variables from .env file
load_dotenv()

# Try to import plyer for desktop notifications
try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print(f"{Fore.YELLOW}⚠️  Warning: plyer not installed. Desktop notifications disabled.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Install with: pip install plyer{Style.RESET_ALL}\n")

init(autoreset=False)  # Colorama setup

# Database setup
DB_NAME = "notifications.db"

# ── Shared UI helpers ──────────────────────────────────────────────────────────

def _box(color, title, ver_str=None):
    """Print a colored box header. Optionally show a version on the second line."""
    c = color + Style.BRIGHT
    print(f"\n{c}╔═══════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{c}║  {title:<37}║{Style.RESET_ALL}")
    if ver_str:
        lpad = (39 - len(ver_str)) // 2
        rpad = 39 - len(ver_str) - lpad
        print(f"{c}║{' ' * lpad}{Fore.WHITE}{Style.BRIGHT}{ver_str}{Style.RESET_ALL}{c}{' ' * rpad}║{Style.RESET_ALL}")
    print(f"{c}╚═══════════════════════════════════════╝{Style.RESET_ALL}")

def _div():
    print(f"  {Fore.WHITE}{Style.DIM}{'─' * 39}{Style.RESET_ALL}")

def _prompt(text="Choose: "):
    return input(f"\n  {Fore.GREEN}{Style.BRIGHT}▶  {text}{Style.RESET_ALL}").strip()

def _opt(num, color, emoji, label):
    print(f"  {Fore.YELLOW}{Style.BRIGHT}{num}{Style.RESET_ALL}  {color}{emoji}  {label}{Style.RESET_ALL}")

# ── Timezone helpers ───────────────────────────────────────────────────────────

def _get_user_tz():
    """Return a ZoneInfo for the configured TIMEZONE env var, or None for system local."""
    tz_name = os.getenv('TIMEZONE', '').strip()
    if not tz_name:
        return None
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        print(f"{Fore.YELLOW}⚠️  Unknown timezone '{tz_name}' in .env — using system local time.{Style.RESET_ALL}")
        return None

def _now_in_tz() -> datetime:
    """Current time in the configured timezone as a naive datetime (matches DB storage format)."""
    tz = _get_user_tz()
    if tz is None:
        return datetime.now()
    return datetime.now(tz).replace(tzinfo=None)

def _tz_label() -> str:
    """Short timezone label for display in prompts and banners."""
    tz_name = os.getenv('TIMEZONE', '').strip()
    return tz_name if tz_name else "system local"

def init_db():
    """Initialize notifications database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY, message TEXT, due_time TEXT, sent BOOLEAN DEFAULT 0)''')
    conn.commit()
    conn.close()

# ==================== TELEGRAM ====================
def get_telegram_config():
    """Get Telegram configuration from environment variables"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    return bot_token, chat_id

def send_telegram_message(message):
    """Send a message via Telegram"""
    bot_token, chat_id = get_telegram_config()

    if not bot_token or not chat_id:
        print(f"{Fore.RED}❌ Telegram not configured.{Style.RESET_ALL}")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ Telegram message sent!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Telegram API error: {response.status_code}{Style.RESET_ALL}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}❌ Failed to send Telegram: {e}{Style.RESET_ALL}")
        return False

def verify_telegram_config():
    """Verify Telegram bot token and chat ID"""
    bot_token, chat_id = get_telegram_config()

    if not bot_token or not chat_id:
        print(f"{Fore.RED}❌ Telegram not configured!{Style.RESET_ALL}")
        return False

    print(f"{Fore.CYAN}ℹ️  Verifying Telegram...{Style.RESET_ALL}")
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_name = bot_info['result'].get('username', 'Unknown')
                print(f"{Fore.GREEN}✅ Bot valid! Username: @{bot_name}{Style.RESET_ALL}")
                return send_telegram_message("✅ Telegram verification successful!")
        print(f"{Fore.RED}❌ Bot token is invalid!{Style.RESET_ALL}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}❌ Connection failed: {e}{Style.RESET_ALL}")
        return False

# ==================== DISCORD ====================
def get_discord_config():
    """Get Discord webhook URL from environment variables"""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    return webhook_url

def send_discord_message(message):
    """Send a message via Discord webhook"""
    webhook_url = get_discord_config()

    if not webhook_url:
        print(f"{Fore.RED}❌ Discord not configured.{Style.RESET_ALL}")
        return False

    payload = {"content": message}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            print(f"{Fore.GREEN}✅ Discord message sent!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Discord API error: {response.status_code}{Style.RESET_ALL}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}❌ Failed to send Discord: {e}{Style.RESET_ALL}")
        return False

def verify_discord_config():
    """Verify Discord webhook"""
    webhook_url = get_discord_config()

    if not webhook_url:
        print(f"{Fore.RED}❌ Discord not configured!{Style.RESET_ALL}")
        return False

    print(f"{Fore.CYAN}ℹ️  Verifying Discord webhook...{Style.RESET_ALL}")
    return send_discord_message("✅ Discord verification successful!")

# ==================== PUSHOVER ====================
def get_pushover_config():
    """Get Pushover configuration from environment variables"""
    user_key = os.getenv('PUSHOVER_USER_KEY')
    api_token = os.getenv('PUSHOVER_API_TOKEN')
    return user_key, api_token

def send_pushover_message(message):
    """Send a message via Pushover"""
    user_key, api_token = get_pushover_config()

    if not user_key or not api_token:
        print(f"{Fore.RED}❌ Pushover not configured.{Style.RESET_ALL}")
        return False

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": api_token,
        "user": user_key,
        "message": message
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ Pushover message sent!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}❌ Pushover API error: {response.status_code}{Style.RESET_ALL}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}❌ Failed to send Pushover: {e}{Style.RESET_ALL}")
        return False

def verify_pushover_config():
    """Verify Pushover configuration"""
    user_key, api_token = get_pushover_config()

    if not user_key or not api_token:
        print(f"{Fore.RED}❌ Pushover not configured!{Style.RESET_ALL}")
        return False

    print(f"{Fore.CYAN}ℹ️  Verifying Pushover...{Style.RESET_ALL}")
    return send_pushover_message("✅ Pushover verification successful!")

# ==================== EMAIL (GMAIL) ====================
def get_email_config():
    """Get Gmail configuration from environment variables"""
    smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
    sender_email = os.getenv('EMAIL_SENDER')
    sender_password = os.getenv('EMAIL_PASSWORD')
    recipient_email = os.getenv('EMAIL_RECIPIENT')
    return smtp_server, smtp_port, sender_email, sender_password, recipient_email

def send_email_message(message):
    """Send a message via Gmail"""
    smtp_server, smtp_port, sender_email, sender_password, recipient_email = get_email_config()

    if not all([sender_email, sender_password, recipient_email]):
        print(f"{Fore.RED}❌ Gmail not configured.{Style.RESET_ALL}")
        return False

    try:
        msg = MIMEMultipart()
        if sender_email is None or recipient_email is None:
            print(f"{Fore.RED}❌ Email sender or recipient is not set!{Style.RESET_ALL}")
            return False
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "⏰ Notification Reminder"
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        if sender_email is None or sender_password is None:
            print(f"{Fore.RED}❌ Email sender or password is not set!{Style.RESET_ALL}")
            server.quit()
            return False
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print(f"{Fore.GREEN}✅ Email sent!{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to send email: {e}{Style.RESET_ALL}")
        return False

def verify_email_config():
    """Verify Gmail configuration"""
    smtp_server, smtp_port, sender_email, sender_password, recipient_email = get_email_config()

    if not all([sender_email, sender_password, recipient_email]):
        print(f"{Fore.RED}❌ Gmail not configured!{Style.RESET_ALL}")
        return False

    print(f"{Fore.CYAN}ℹ️  Verifying Gmail configuration...{Style.RESET_ALL}")
    print(f"{Fore.WHITE}SMTP Server: {smtp_server}:{smtp_port}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}From: {sender_email}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}To: {recipient_email}{Style.RESET_ALL}")
    return send_email_message("✅ Gmail verification successful!")

# ==================== NOTIFICATION MENUS ====================

def _service_menu_options(prompt_color):
    """Print standard service sub-menu options and return choice."""
    _opt("1", Fore.GREEN + Style.BRIGHT,        "✅", "Verify Configuration")
    _opt("2", Fore.BLUE  + Style.BRIGHT,        "✏️ ", "Set Credentials")
    _opt("3", Fore.CYAN,                         "📤", "Send Test Message")
    _opt("4", Fore.WHITE + Style.DIM,            "📋", "Show .env Variables")
    _opt("5", Fore.WHITE + Style.DIM,            "ℹ️ ", "Setup Instructions")
    _div()
    _opt("0", Fore.RED   + Style.DIM,            "⬅️ ", "Back")
    return _prompt("Choose: ")

def telegram_menu():
    """Telegram configuration and testing menu"""
    while True:
        _box(Fore.BLUE, "📱 TELEGRAM SETTINGS")
        bot_token, chat_id = get_telegram_config()
        status = f"{Fore.GREEN}{Style.BRIGHT}✅ CONFIGURED{Style.RESET_ALL}" if bot_token and chat_id else f"{Fore.RED}❌ NOT CONFIGURED{Style.RESET_ALL}"
        print(f"  Status: {status}\n")

        choice = _service_menu_options(Fore.BLUE)

        if choice == "1":
            verify_telegram_config()
        elif choice == "2":
            set_telegram_credentials()
        elif choice == "3":
            msg = _prompt("Test message (Enter for default): ") or "🧪 Test from Notification App!"
            send_telegram_message(msg)
        elif choice == "4":
            print(f"\n  {Fore.GREEN}TELEGRAM_BOT_TOKEN=your_bot_token_here{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}TELEGRAM_CHAT_ID=your_chat_id_here{Style.RESET_ALL}")
        elif choice == "5":
            print(f"\n  {Fore.CYAN}{Style.BRIGHT}📚 Telegram Setup:{Style.RESET_ALL}")
            print(f"  1. Message @BotFather on Telegram")
            print(f"  2. Send /newbot and follow instructions")
            print(f"  3. Get your bot token")
            print(f"  4. Message @userinfobot to get your chat ID")
            print(f"  5. Add both to .env file")
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "0":
            break

def discord_menu():
    """Discord configuration and testing menu"""
    while True:
        _box(Fore.MAGENTA, "💬 DISCORD SETTINGS")
        webhook_url = get_discord_config()
        status = f"{Fore.GREEN}{Style.BRIGHT}✅ CONFIGURED{Style.RESET_ALL}" if webhook_url else f"{Fore.RED}❌ NOT CONFIGURED{Style.RESET_ALL}"
        print(f"  Status: {status}\n")

        choice = _service_menu_options(Fore.MAGENTA)

        if choice == "1":
            verify_discord_config()
        elif choice == "2":
            set_discord_credentials()
        elif choice == "3":
            msg = _prompt("Test message (Enter for default): ") or "🧪 Test from Notification App!"
            send_discord_message(msg)
        elif choice == "4":
            print(f"\n  {Fore.GREEN}DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...{Style.RESET_ALL}")
        elif choice == "5":
            print(f"\n  {Fore.CYAN}{Style.BRIGHT}📚 Discord Setup:{Style.RESET_ALL}")
            print(f"  1. Go to your Discord server")
            print(f"  2. Edit Channel → Integrations → Webhooks")
            print(f"  3. Create New Webhook")
            print(f"  4. Copy Webhook URL")
            print(f"  5. Add DISCORD_WEBHOOK_URL to .env file")
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "0":
            break

def pushover_menu():
    """Pushover configuration and testing menu"""
    while True:
        _box(Fore.YELLOW, "📲 PUSHOVER SETTINGS")
        user_key, api_token = get_pushover_config()
        status = f"{Fore.GREEN}{Style.BRIGHT}✅ CONFIGURED{Style.RESET_ALL}" if user_key and api_token else f"{Fore.RED}❌ NOT CONFIGURED{Style.RESET_ALL}"
        print(f"  Status: {status}\n")

        choice = _service_menu_options(Fore.YELLOW)

        if choice == "1":
            verify_pushover_config()
        elif choice == "2":
            set_pushover_credentials()
        elif choice == "3":
            msg = _prompt("Test message (Enter for default): ") or "🧪 Test from Notification App!"
            send_pushover_message(msg)
        elif choice == "4":
            print(f"\n  {Fore.GREEN}PUSHOVER_USER_KEY=your_user_key_here{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}PUSHOVER_API_TOKEN=your_api_token_here{Style.RESET_ALL}")
        elif choice == "5":
            print(f"\n  {Fore.CYAN}{Style.BRIGHT}📚 Pushover Setup:{Style.RESET_ALL}")
            print(f"  1. Go to https://pushover.net")
            print(f"  2. Create an account")
            print(f"  3. Get your User Key from dashboard")
            print(f"  4. Create an Application/API Token")
            print(f"  5. Add both to .env file")
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "0":
            break

def email_menu():
    """Gmail configuration and testing menu"""
    while True:
        _box(Fore.RED, "📧 GMAIL SETTINGS")
        _, _, sender, _, recipient = get_email_config()
        status = f"{Fore.GREEN}{Style.BRIGHT}✅ CONFIGURED{Style.RESET_ALL}" if sender and recipient else f"{Fore.RED}❌ NOT CONFIGURED{Style.RESET_ALL}"
        print(f"  Status: {status}\n")

        choice = _service_menu_options(Fore.RED)

        if choice == "1":
            verify_email_config()
        elif choice == "2":
            set_email_credentials()
        elif choice == "3":
            msg = _prompt("Test message (Enter for default): ") or "🧪 Test from Notification App!"
            send_email_message(msg)
        elif choice == "4":
            print(f"\n  {Fore.GREEN}EMAIL_SMTP_SERVER=smtp.gmail.com{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}EMAIL_SMTP_PORT=587{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}EMAIL_SENDER=your_email@gmail.com{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}EMAIL_PASSWORD=your_app_password{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}EMAIL_RECIPIENT=recipient@email.com{Style.RESET_ALL}")
        elif choice == "5":
            print(f"\n  {Fore.CYAN}{Style.BRIGHT}📚 Gmail Setup:{Style.RESET_ALL}")
            print(f"  1. Go to Google Account → Security")
            print(f"  2. Enable 2-Step Verification")
            print(f"  3. Go to App Passwords")
            print(f"  4. Generate an app password for 'Mail'")
            print(f"  5. Use that password (not your regular password!)")
            print(f"  6. Add all EMAIL_* variables to .env file")
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "0":
            break

def notification_services_menu():
    """Main notification services menu"""
    while True:
        _box(Fore.MAGENTA, "📬 NOTIFICATION SERVICES")

        tg_ok = all(get_telegram_config())
        dc_ok = bool(get_discord_config())
        po_ok = all(get_pushover_config())
        em_ok = all([get_email_config()[2], get_email_config()[4]])

        def _svc_line(num, ok, emoji, label):
            tick = f"{Fore.GREEN}✅{Style.RESET_ALL}" if ok else f"{Fore.RED}❌{Style.RESET_ALL}"
            clr = Fore.WHITE if ok else Fore.WHITE + Style.DIM
            print(f"  {Fore.YELLOW}{Style.BRIGHT}{num}{Style.RESET_ALL}  {tick} {clr}{emoji}  {label}{Style.RESET_ALL}")

        _svc_line("1", tg_ok, "📱", "Telegram")
        _svc_line("2", dc_ok, "💬", "Discord")
        _svc_line("3", po_ok, "📲", "Pushover")
        _svc_line("4", em_ok, "📧", "Gmail")
        _div()
        _opt("5", Fore.WHITE + Style.DIM, "📋", "Show Complete .env Example")
        _opt("0", Fore.RED  + Style.DIM, "⬅️ ", "Back to Main Menu")

        choice = _prompt("Choose: ")

        if choice == "1":
            telegram_menu()
        elif choice == "2":
            discord_menu()
        elif choice == "3":
            pushover_menu()
        elif choice == "4":
            email_menu()
        elif choice == "5":
            show_complete_env_example()
        elif choice == "0":
            break

def show_complete_env_example():
    """Show complete .env file example"""
    print(f"\n  {Fore.CYAN}{Style.BRIGHT}{'═'*41}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}📄  COMPLETE .env FILE EXAMPLE{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}{'═'*41}{Style.RESET_ALL}\n")

    print(f"  {Fore.YELLOW}# Telegram{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}TELEGRAM_CHAT_ID=987654321{Style.RESET_ALL}\n")

    print(f"  {Fore.YELLOW}# Discord{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef{Style.RESET_ALL}\n")

    print(f"  {Fore.YELLOW}# Pushover{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}PUSHOVER_USER_KEY=your_user_key_here{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}PUSHOVER_API_TOKEN=your_api_token_here{Style.RESET_ALL}\n")

    print(f"  {Fore.YELLOW}# Gmail{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}EMAIL_SMTP_SERVER=smtp.gmail.com{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}EMAIL_SMTP_PORT=587{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}EMAIL_SENDER=your_email@gmail.com{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}EMAIL_PASSWORD=your_app_password{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}EMAIL_RECIPIENT=recipient@email.com{Style.RESET_ALL}\n")

    print(f"  {Fore.YELLOW}# Timezone (optional — leave blank to use server local time){Style.RESET_ALL}")
    print(f"  {Fore.GREEN}TIMEZONE=America/New_York{Style.RESET_ALL}\n")

    print(f"  {Fore.CYAN}{Style.BRIGHT}{'═'*41}{Style.RESET_ALL}")
    input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")

# ==================== CREDENTIAL SETUP ====================
def _set_credential(key, prompt_text, secret=False):
    """Prompt for a value, write it to .env, and update the current session."""
    if secret:
        import getpass
        value = getpass.getpass(f"  {Fore.YELLOW}▶  {prompt_text} (hidden): {Style.RESET_ALL}").strip()
    else:
        value = input(f"  {Fore.YELLOW}▶  {prompt_text}: {Style.RESET_ALL}").strip()
    if not value:
        print(f"{Fore.YELLOW}⚠️  Skipped — value unchanged.{Style.RESET_ALL}")
        return False
    set_key(str(ENV_PATH), key, value)
    os.environ[key] = value
    print(f"{Fore.GREEN}✅ {key} saved.{Style.RESET_ALL}")
    return True

def set_telegram_credentials():
    print(f"\n{Fore.BLUE}{Style.BRIGHT}📱 Enter Telegram Credentials{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.DIM}Press Enter to skip a field and keep its current value.{Style.RESET_ALL}\n")
    _set_credential('TELEGRAM_BOT_TOKEN', 'Bot Token')
    _set_credential('TELEGRAM_CHAT_ID', 'Chat ID')
    load_dotenv(str(ENV_PATH), override=True)
    print(f"{Fore.GREEN}✅ Telegram credentials updated.{Style.RESET_ALL}")

def set_discord_credentials():
    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}💬 Enter Discord Credentials{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.DIM}Press Enter to skip and keep current value.{Style.RESET_ALL}\n")
    _set_credential('DISCORD_WEBHOOK_URL', 'Webhook URL')
    load_dotenv(str(ENV_PATH), override=True)
    print(f"{Fore.GREEN}✅ Discord credentials updated.{Style.RESET_ALL}")

def set_pushover_credentials():
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}📲 Enter Pushover Credentials{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.DIM}Press Enter to skip a field and keep its current value.{Style.RESET_ALL}\n")
    _set_credential('PUSHOVER_USER_KEY', 'User Key')
    _set_credential('PUSHOVER_API_TOKEN', 'API Token')
    load_dotenv(str(ENV_PATH), override=True)
    print(f"{Fore.GREEN}✅ Pushover credentials updated.{Style.RESET_ALL}")

def set_email_credentials():
    print(f"\n{Fore.RED}{Style.BRIGHT}📧 Enter Gmail Credentials{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.DIM}Press Enter to skip a field and keep its current value.{Style.RESET_ALL}\n")
    _set_credential('EMAIL_SENDER', 'Sender Email')
    _set_credential('EMAIL_PASSWORD', 'App Password', secret=True)
    _set_credential('EMAIL_RECIPIENT', 'Recipient Email')
    load_dotenv(str(ENV_PATH), override=True)
    print(f"{Fore.GREEN}✅ Gmail credentials updated.{Style.RESET_ALL}")

# ==================== NOTIFICATION CRUD ====================
def _parse_due_time(due_str):
    """Parse a due time string and return a normalized datetime, or None on failure."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(due_str, fmt)
        except ValueError:
            continue
    return None

def add_notification():
    print(f"  {Fore.YELLOW}▶  Enter message: {Style.RESET_ALL}", end="")
    msg = input().strip()
    if not msg:
        print(f"{Fore.RED}❌ Message cannot be empty!{Style.RESET_ALL}")
        return

    now = _now_in_tz()
    print(f"  {Fore.YELLOW}▶  Due time ({_tz_label()}, e.g., '{now.strftime('%Y-%m-%d')} 14:00'): {Style.RESET_ALL}", end="")
    due_raw = input().strip()

    due_dt = _parse_due_time(due_raw)
    if due_dt is None:
        print(f"{Fore.RED}❌ Invalid date format! Use YYYY-MM-DD HH:MM{Style.RESET_ALL}")
        return

    if due_dt <= now:
        print(f"{Fore.RED}❌ {due_dt.strftime('%Y-%m-%d %H:%M')} is in the past!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Current time ({_tz_label()}): {now.strftime('%Y-%m-%d %H:%M')} — enter a future date/time.{Style.RESET_ALL}")
        return

    # Normalize to zero-padded format so string comparison in the DB is reliable
    due = due_dt.strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO notifications (message, due_time) VALUES (?, ?)", (msg, due))
    notification_id = c.lastrowid
    conn.commit()
    conn.close()
    print(f"{Fore.GREEN}✅ Added! ID: {notification_id} | Due: {due}{Style.RESET_ALL}")

def view_notifications():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM notifications ORDER BY due_time")
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"{Fore.YELLOW}⚠️  No notifications scheduled.{Style.RESET_ALL}")
        return

    print(f"\n  {Fore.CYAN}{Style.BRIGHT}{'═'*41}{Style.RESET_ALL}")
    for row in rows:
        status = f"{Fore.GREEN}{Style.BRIGHT}✅ SENT{Style.RESET_ALL}" if row[3] else f"{Fore.YELLOW}⏳ PENDING{Style.RESET_ALL}"
        id_clr = Fore.YELLOW + Style.BRIGHT
        print(f"  {id_clr}#{row[0]}{Style.RESET_ALL}  {Fore.WHITE}{Style.BRIGHT}{row[1]}{Style.RESET_ALL}")
        print(f"     {Fore.WHITE}{Style.DIM}Due:{Style.RESET_ALL} {Fore.CYAN}{row[2]}{Style.RESET_ALL}  {status}")
        print(f"  {Fore.WHITE}{Style.DIM}{'─'*39}{Style.RESET_ALL}")

def delete_notification():
    print(f"  {Fore.YELLOW}▶  Notification ID to delete: {Style.RESET_ALL}", end="")
    notif_id = input().strip()

    if not notif_id.isdigit():
        print(f"{Fore.RED}❌ Invalid ID!{Style.RESET_ALL}")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM notifications WHERE id = ?", (notif_id,))
    if not c.fetchone():
        print(f"{Fore.RED}❌ Notification ID {notif_id} not found!{Style.RESET_ALL}")
        conn.close()
        return

    c.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    print(f"{Fore.GREEN}✅ Deleted notification ID {notif_id}!{Style.RESET_ALL}")

def edit_notification():
    print(f"  {Fore.YELLOW}▶  Notification ID to edit: {Style.RESET_ALL}", end="")
    notif_id = input().strip()

    if not notif_id.isdigit():
        print(f"{Fore.RED}❌ Invalid ID!{Style.RESET_ALL}")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM notifications WHERE id = ?", (notif_id,))
    row = c.fetchone()

    if not row:
        print(f"{Fore.RED}❌ Notification ID {notif_id} not found!{Style.RESET_ALL}")
        conn.close()
        return

    print(f"  {Fore.CYAN}Current message:  {Fore.WHITE}{Style.BRIGHT}{row[1]}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Current due time: {Fore.WHITE}{Style.BRIGHT}{row[2]}{Style.RESET_ALL}")

    print(f"  {Fore.YELLOW}▶  New message (Enter to keep): {Style.RESET_ALL}", end="")
    new_msg = input().strip() or row[1]

    print(f"  {Fore.YELLOW}▶  New due time (Enter to keep): {Style.RESET_ALL}", end="")
    new_due = input().strip() or row[2]

    if new_due != row[2]:
        due_dt = _parse_due_time(new_due)
        if due_dt is None:
            print(f"{Fore.RED}❌ Invalid format! Keeping original.{Style.RESET_ALL}")
            new_due = row[2]
        elif due_dt <= _now_in_tz():
            now_display = _now_in_tz().strftime('%Y-%m-%d %H:%M')
            print(f"{Fore.RED}❌ {due_dt.strftime('%Y-%m-%d %H:%M')} is in the past! Keeping original.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Current time ({_tz_label()}): {now_display}{Style.RESET_ALL}")
            new_due = row[2]
        else:
            new_due = due_dt.strftime("%Y-%m-%d %H:%M")

    c.execute("UPDATE notifications SET message = ?, due_time = ? WHERE id = ?", (new_msg, new_due, notif_id))
    conn.commit()
    conn.close()
    print(f"{Fore.GREEN}✅ Updated notification ID {notif_id}!{Style.RESET_ALL}")

def send_notifications():
    now = _now_in_tz().replace(second=0, microsecond=0)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM notifications WHERE sent = 0")
    all_unsent = c.fetchall()

    # Use proper datetime comparison — avoids string-format edge cases
    pending = []
    for row in all_unsent:
        due_dt = _parse_due_time(row[2])
        if due_dt is not None and due_dt <= now:
            pending.append(row)

    if not pending:
        conn.close()
        return

    for row in pending:
        msg = row[1]
        print(f"{Fore.GREEN}{Style.BRIGHT}📢 Sending: {msg}{Style.RESET_ALL}")

        # Send desktop notification if available
        if NOTIFICATIONS_AVAILABLE and notification is not None and callable(getattr(notification, "notify", None)):
            try:
                notify_func = getattr(notification, "notify", None)
                if callable(notify_func):
                    notify_func(
                        title="⏰ Reminder!",
                        message=msg,
                        timeout=10
                    )
                else:
                    print(f"{Fore.YELLOW}⚠️  plyer installed but notification.notify is not callable.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Desktop notification failed: {e}{Style.RESET_ALL}")
        elif NOTIFICATIONS_AVAILABLE:
            print(f"{Fore.YELLOW}⚠️  plyer installed but notification.notify is not callable.{Style.RESET_ALL}")

        # Send to all configured services
        send_telegram_message(f"⏰ Reminder: {msg}")
        send_discord_message(f"⏰ Reminder: {msg}")
        send_pushover_message(f"⏰ Reminder: {msg}")
        send_email_message(f"⏰ Reminder: {msg}")

        # Mark as sent
        c.execute("UPDATE notifications SET sent = 1 WHERE id = ?", (row[0],))

    conn.commit()
    conn.close()
    print(f"{Fore.GREEN}✅ Processed {len(pending)} notification(s).{Style.RESET_ALL}")

def background_runner():
    """Runs in a separate thread to check notifications every minute"""
    while True:
        schedule.run_pending()
        time.sleep(60)

# ==================== UPDATE ====================
def _version_tuple(v):
    try:
        return tuple(int(x) for x in v.split('.'))
    except Exception:
        return (0, 0, 0)

def check_for_updates():
    """Fetch the latest version string from GitHub CHANGELOG.md."""
    import urllib.request
    import re
    try:
        url = "https://raw.githubusercontent.com/trickdaddy24/plex-notifier/main/CHANGELOG.md"
        with urllib.request.urlopen(url, timeout=10) as resp:
            content = resp.read().decode('utf-8')
        match = re.search(r'## \[v([0-9]+\.[0-9]+\.[0-9]+)\]', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def do_update():
    """Pull latest code via git and reinstall dependencies."""
    import subprocess
    import sys
    script_dir = Path(__file__).parent

    print(f"{Fore.CYAN}📦 Fetching latest code...{Style.RESET_ALL}")
    try:
        subprocess.run(["git", "-C", str(script_dir), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(script_dir), "reset", "--hard", "origin/main"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}❌ Git update failed: {e}{Style.RESET_ALL}")
        return False

    print(f"{Fore.CYAN}📦 Reinstalling dependencies...{Style.RESET_ALL}")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r",
             str(script_dir / "requirements.txt"), "-q"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}❌ Dependency install failed: {e}{Style.RESET_ALL}")
        return False

    print(f"{Fore.GREEN}✅ Update complete! Please restart the app to apply changes.{Style.RESET_ALL}")
    return True

# ==================== SYSTEM MENU ====================
def system_menu():
    """System menu — version history powered by version_manager.py"""
    try:
        import version_manager as vm
        vm.setup_logging()
        vm.setup_database()
    except ImportError:
        print(f"{Fore.RED}❌ version_manager.py not found in project directory.{Style.RESET_ALL}")
        input(f"\n  {Fore.YELLOW}Press Enter...{Style.RESET_ALL}")
        return

    while True:
        ver = vm.get_current_version()
        ver_str = f"v{ver}"
        _box(Fore.CYAN, "⚙️  SYSTEM", ver_str)
        tz_label = _tz_label()
        _opt("1", Fore.CYAN,                  "📜", "View Version History")
        _opt("2", Fore.GREEN + Style.BRIGHT,   "➕", "Add New Version Release")
        _opt("3", Fore.BLUE  + Style.BRIGHT,   "✏️ ", "Edit Version Notes")
        _opt("4", Fore.MAGENTA + Style.BRIGHT, "🔄", "Check for Updates")
        _opt("5", Fore.YELLOW + Style.BRIGHT,  "🕐", f"Set Timezone  {Fore.WHITE}{Style.DIM}[{tz_label}]")
        _div()
        _opt("0", Fore.RED + Style.DIM,        "⬅️ ", "Back to Main Menu")

        choice = _prompt("Choose: ")

        if choice == "1":
            vm.view_version_history()
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "2":
            vm.add_version_notes()
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "3":
            vm.edit_notes()
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "4":
            current = vm.get_current_version()
            print(f"\n{Fore.CYAN}🔍 Checking for updates...{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}Current version: {Fore.YELLOW}{Style.BRIGHT}v{current}{Style.RESET_ALL}")
            latest = check_for_updates()
            if latest is None:
                print(f"{Fore.RED}❌ Could not reach GitHub. Check your connection.{Style.RESET_ALL}")
            elif _version_tuple(latest) <= _version_tuple(current):
                print(f"  {Fore.WHITE}Latest version:  {Fore.GREEN}{Style.BRIGHT}v{latest}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}✅ Already up to date!{Style.RESET_ALL}")
            else:
                print(f"  {Fore.WHITE}Latest version:  {Fore.CYAN}{Style.BRIGHT}v{latest}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}🆕 Update available: {Fore.WHITE}v{current}{Fore.YELLOW} → {Fore.CYAN}{Style.BRIGHT}v{latest}{Style.RESET_ALL}")
                confirm = _prompt("Update now? (y/N): ")
                if confirm.lower() == 'y':
                    do_update()
                else:
                    print(f"{Fore.YELLOW}Update skipped.{Style.RESET_ALL}")
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "5":
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}🕐 Set Timezone{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}{Style.DIM}Current: {_tz_label()}{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}{Style.DIM}Examples: America/New_York  America/Chicago  America/Los_Angeles{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}{Style.DIM}          Europe/London  Europe/Paris  Asia/Tokyo{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}{Style.DIM}Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones{Style.RESET_ALL}")
            new_tz = _prompt("Timezone (Enter to cancel): ")
            if new_tz:
                try:
                    ZoneInfo(new_tz)  # validate before saving
                    set_key(str(ENV_PATH), 'TIMEZONE', new_tz)
                    os.environ['TIMEZONE'] = new_tz
                    load_dotenv(str(ENV_PATH), override=True)
                    print(f"{Fore.GREEN}✅ Timezone set to {new_tz}{Style.RESET_ALL}")
                except (ZoneInfoNotFoundError, KeyError):
                    print(f"{Fore.RED}❌ Unknown timezone '{new_tz}' — not saved.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Cancelled — timezone unchanged.{Style.RESET_ALL}")
            input(f"\n  {Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
        elif choice == "0":
            break
        else:
            print(f"{Fore.RED}❌ Invalid choice. Please try again.{Style.RESET_ALL}")

# ==================== VERSION HELPER ====================
def _get_app_version() -> str:
    """Read the current version from version_notes.db; fall back to hardcoded."""
    try:
        import version_manager as vm
        vm.setup_database()
        return vm.get_current_version()
    except Exception:
        return "1.0.41"


# ==================== MAIN ====================
def main():
    init_db()

    # Schedule notification check every minute
    try:
        schedule.every(1).minutes.do(send_notifications)
    except Exception as e:
        print(f"{Fore.RED}⚠️  Warning: Could not set up scheduler: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Continuing without automatic background checks...{Style.RESET_ALL}")

    # Start background thread
    scheduler_thread = threading.Thread(target=background_runner, daemon=True)
    scheduler_thread.start()

    ver = _get_app_version()
    print(f"\n  {Fore.CYAN}{Style.BRIGHT}{'═'*41}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}🔔  Plex Notifier  {Fore.WHITE}v{ver}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}{'═'*41}{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}✅  Background scheduler started{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}{Style.DIM}🕐  Timezone: {Fore.YELLOW}{Style.BRIGHT}{_tz_label()}{Style.RESET_ALL}\n")

    while True:
        ver = _get_app_version()
        ver_str = f"v{ver}"
        _box(Fore.CYAN, "📋 NOTIFICATION MENU", ver_str)

        _opt("1", Fore.GREEN  + Style.BRIGHT,  "➕", "Add Notification")
        _opt("2", Fore.CYAN,                    "📋", "View Notifications")
        _opt("3", Fore.CYAN,                    "📤", "Send Due Notifications Now")
        _opt("4", Fore.BLUE   + Style.BRIGHT,  "✏️ ", "Edit Notification")
        _opt("5", Fore.RED,                     "🗑️ ", "Delete Notification")
        _div()
        _opt("6", Fore.MAGENTA + Style.BRIGHT,  "📬", "Notification Services")
        _opt("7", Fore.WHITE,                   "⚙️ ", f"System  {Fore.CYAN}[{ver_str}]{Style.RESET_ALL}")
        _div()
        _opt("0", Fore.RED + Style.DIM,         "🚪", "Exit")

        choice = _prompt("Choose an option: ")

        if choice == "1":
            add_notification()
        elif choice == "2":
            view_notifications()
        elif choice == "3":
            send_notifications()
        elif choice == "4":
            edit_notification()
        elif choice == "5":
            delete_notification()
        elif choice == "6":
            notification_services_menu()
        elif choice == "7":
            system_menu()
        elif choice == "0":
            print(f"\n  {Fore.GREEN}{Style.BRIGHT}👋  Goodbye!{Style.RESET_ALL}\n")
            break
        else:
            print(f"{Fore.RED}❌ Invalid choice. Please try again.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
