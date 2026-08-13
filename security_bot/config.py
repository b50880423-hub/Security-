import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str
    mongo_url: str
    owner_id: int
    default_mute_minutes: int
    alert_chat_id: int | None
    mongo_db_name: str

def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    mongo_url = os.getenv("MONGO_URL", "").strip()
    owner = os.getenv("OWNER_ID", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is required")
    if not owner or not owner.lstrip("-").isdigit():
        raise RuntimeError("OWNER_ID must be numeric")
    minutes = int(os.getenv("DEFAULT_MUTE_MINUTES", "60"))
    if minutes < 1:
        raise RuntimeError("DEFAULT_MUTE_MINUTES must be >= 1")
    raw_alert = os.getenv("ALERT_CHAT_ID", "").strip()
    alert = int(raw_alert) if raw_alert and raw_alert.lstrip("-").isdigit() else None
    return Settings(
        bot_token=bot_token,
        mongo_url=mongo_url,
        owner_id=int(owner),
        default_mute_minutes=minutes,
        alert_chat_id=alert,
        mongo_db_name=os.getenv("MONGO_DB_NAME", "telegram_security").strip() or "telegram_security",
    )
