"""
telegram_bot/bot.py
---------------------

Multifunctional Telegram bot with:
- Free tier usage limit
- Premium redeem system
- Admin commands
- FastAPI health check for Koyeb
"""

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

# Load .env
load_dotenv()

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------
# ENV VARIABLES
# ---------------------------
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_IDS = {int(uid) for uid in os.environ.get("ADMIN_IDS", "").split(",") if uid.strip().isdigit()}
FREE_TIER_LIMIT = int(os.environ.get("FREE_TIER_LIMIT", "20"))

# ---------------------------
# API CONFIG
# ---------------------------
APIS = {
    "terabox": {
        "title": "Terabox Downloader",
        "description": "Download files from Terabox",
        "endpoint": lambda url: f"https://teraboxdownloderapi.revangeapi.workers.dev/?url={url}",
    },
    "social": {
        "title": "Social Downloader",
        "description": "Download videos from YouTube, Instagram, TikTok, Facebook",
        "endpoint": lambda url: f"https://nodejssocialdownloder.onrender.com/revangeapi/download?url={url}",
    },
    "llama": {
        "title": "LLaMA 3.1 Chat",
        "description": "Uncensored AI chat",
        "endpoint": lambda prompt: f"https://laama.revangeapi.workers.dev/chat?prompt={prompt}",
    },
    "gpt": {
        "title": "GPT-3.5 Chat",
        "description": "ChatGPT 3.5 (BJ Devs)",
        "endpoint": lambda prompt: f"https://gpt-3-5.apis-bj-devs.workers.dev/?prompt={prompt}",
    },
}

# ---------------------------
# Usage Tracker + Premium
# ---------------------------
class UsageTracker:
    def __init__(self, limit: int):
        self.limit = limit
        self._counts: Dict[int, Dict[str, int]] = {}

    def check_quota(self, user_id: int) -> bool:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        used = self._counts.setdefault(user_id, {}).get(today, 0)
        return used < self.limit

    def increment(self, user_id: int) -> None:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        counts = self._counts.setdefault(user_id, {})
        counts[today] = counts.get(today, 0) + 1

    def stats(self) -> str:
        lines = []
        for uid, daily in self._counts.items():
            for day, count in daily.items():
                lines.append(f"User {uid} on {day}: {count}")
        return "\n".join(lines) if lines else "No usage recorded."


usage_tracker = UsageTracker(FREE_TIER_LIMIT)

# Redeem system
redeem_codes: Dict[str, tuple] = {}  # {code: (days, admin_id)}
premium_users: Dict[int, datetime] = {}  # {user_id: expiry_datetime}


def is_premium(user_id: int) -> bool:
    exp = premium_users.get(user_id)
    if exp and exp > datetime.utcnow():
        return True
    return False

# ---------------------------
# Helpers
# ---------------------------
async def call_api(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "reply" in data:
                    return str(data["reply"])
                elif isinstance(data, dict) and "url" in data:
                    return str(data["url"])
                return json.dumps(data, indent=2)
            except json.JSONDecodeError:
                return text
    except Exception as exc:
        logger.error("API call failed: %s", exc)
        return None


def build_main_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, config in APIS.items():
        buttons.append([InlineKeyboardButton(text=config["title"], callback_data=f"menu:{key}")])
    return InlineKeyboardMarkup(buttons)

# ---------------------------
# Command Handlers
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = (
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to the multifunctional assistant bot.\n"
        "Use menu or commands below."
    )
    await update.message.reply_text(welcome, reply_markup=build_main_keyboard(), parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmds = [
        "/start – menu",
        "/help – help",
        "/terabox <link> – Terabox download",
        "/social <url> – Social media download",
        "/llama <prompt> – LLaMA 3.1 AI",
        "/gpt <prompt> – GPT-3.5 AI",
        "/stats – admin only",
        "/broadcast <msg> – admin only",
        "/gen_code <days> – admin only",
        "/redeem <code> – activate premium",
    ]
    await update.message.reply_text("\n".join(cmds))


async def handle_api_request(update: Update, context: ContextTypes.DEFAULT_TYPE, api_key: str, argument: str):
    user_id = update.effective_user.id
    if not usage_tracker.check_quota(user_id) and not is_premium(user_id) and user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Free tier limit reached. Wait until tomorrow or upgrade with /redeem.")
        return
    config = APIS.get(api_key)
    if not config:
        await update.message.reply_text("Unknown API.")
        return
    url = config["endpoint"](argument)
    async with aiohttp.ClientSession() as session:
        result = await call_api(session, url)
        if not result:
            await update.message.reply_text("😕 Service unavailable. Try later.")
            return
        usage_tracker.increment(user_id)
        await update.message.reply_text(result)

# API Commands
async def terabox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /terabox <link>")
        return
    await handle_api_request(update, context, "terabox", context.args[0])

async def social(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /social <url>")
        return
    await handle_api_request(update, context, "social", context.args[0])

async def llama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /llama <prompt>")
        return
    await handle_api_request(update, context, "llama", " ".join(context.args))

async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /gpt <prompt>")
        return
    await handle_api_request(update, context, "gpt", " ".join(context.args))

# Callback
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data.startswith("menu:"):
        api_key = data.split(":", 1)[1]
        cfg = APIS.get(api_key)
        if cfg:
            await q.edit_message_text(f"Send me input for <b>{cfg['title']}</b>", parse_mode=ParseMode.HTML)
        else:
            await q.edit_message_text("Unknown option.")

# Admin
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Not authorized.")
        return
    await update.message.reply_text(usage_tracker.stats())

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <msg>")
        return
    msg = " ".join(context.args)
    sent = 0
    for uid in usage_tracker._counts.keys():
        try:
            await context.bot.send_message(uid, f"📢 {msg}")
            sent += 1
        except Exception as e:
            logger.warning("Broadcast failed to %s: %s", uid, e)
    await update.message.reply_text(f"Broadcast sent to {sent} users.")

# Premium
async def gen_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /gen_code <days>")
        return
    try:
        days = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid number of days.")
        return
    code = secrets.token_hex(4)
    redeem_codes[code] = (days, update.effective_user.id)
    await update.message.reply_text(f"✅ Redeem code generated:\n`{code}` (valid {days} days)", parse_mode="Markdown")

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /redeem <code>")
        return
    code = context.args[0].strip()
    if code not in redeem_codes:
        await update.message.reply_text("❌ Invalid or already used code.")
        return
    days, admin_id = redeem_codes.pop(code)
    expiry = datetime.utcnow() + timedelta(days=days)
    premium_users[update.effective_user.id] = expiry
    await update.message.reply_text(f"🎉 Premium activated for {days} days!\nExpires: {expiry.strftime('%Y-%m-%d')}")

# Freeform
async def handle_freeform_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please use commands: /terabox, /social, /llama, /gpt")

# ---------------------------
# Telegram Bot + FastAPI Server
# ---------------------------
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("terabox", terabox))
application.add_handler(CommandHandler("social", social))
application.add_handler(CommandHandler("llama", llama))
application.add_handler(CommandHandler("gpt", gpt))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(CommandHandler("gen_code", gen_code))
application.add_handler(CommandHandler("redeem", redeem))
application.add_handler(CallbackQueryHandler(callback_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_freeform_input))

# FastAPI app
app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok", "bot": "running"}

# --- Main asyncio runner ---
async def main():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

    # On exit
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
