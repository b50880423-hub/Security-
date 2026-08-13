import asyncio
import threading
from fastapi import FastAPI
import uvicorn

from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler,
    filters
)
from .config import load_settings
from .db import Database
from .moderation import SecurityEngine
from .handlers import security, lockdown, lockdown_off, mute, unmute, ban, unban, history
from .events import chat_member, my_chat_member

app_health = FastAPI()

@app_health.get("/health")
async def health():
    return {"status": "ok", "service": "telegram-group-security-bot"}

def run_health_server():
    port = int(__import__("os").getenv("PORT", "10000"))
    uvicorn.run(app_health, host="0.0.0.0", port=port, log_level="warning")

async def run_bot():
    settings = load_settings()
    db = Database(settings.mongo_url, settings.mongo_db_name)
    await db.connect()

    application = Application.builder().token(settings.bot_token).build()
    engine = SecurityEngine(db, settings, application.bot)
    application.bot_data["db"] = db
    application.bot_data["engine"] = engine
    application.bot_data["settings"] = settings

    application.add_handler(CommandHandler("security", security))
    application.add_handler(CommandHandler("lockdown", lockdown))
    application.add_handler(CommandHandler("lockdown_off", lockdown_off))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("history", history))

    application.add_handler(ChatMemberHandler(chat_member, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, engine.handle_message))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await db.close()

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    asyncio.run(run_bot())
