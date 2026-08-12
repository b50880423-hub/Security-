import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str
    mongo_url: str
    owner_id: int
    default_mute_minutes: int = 60
    alert_chat_id: int | None = None
    mongo_db_name: str = "telegram_security"

def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    mongo = os.getenv("MONGO_URL", "").strip()
    owner = os.getenv("OWNER_ID", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required")
    if not mongo:
        raise RuntimeError("MONGO_URL is required")
    if not owner.isdigit():
        raise RuntimeError("OWNER_ID must be a Telegram numeric user ID")
    alert = os.getenv("ALERT_CHAT_ID", "").strip()
    return Settings(
        bot_token=token,
        mongo_url=mongo,
        owner_id=int(owner),
        default_mute_minutes=int(os.getenv("DEFAULT_MUTE_MINUTES", "60")),
        alert_chat_id=int(alert) if alert.lstrip("-").isdigit() else None,
        mongo_db_name=os.getenv("MONGO_DB_NAME", "telegram_security").strip() or "telegram_security",
    )
