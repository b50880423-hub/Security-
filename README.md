# Telegram Group Security Bot — MongoDB / Render

Serious Telegram group security and moderation foundation using **MongoDB** for persistent storage.

## Features currently included

- Non-admin automatic moderation
- Automatic message deletion
- Automatic temporary mute
- Admin bypass with security alert
- Bot-added detection
- Bot-promotion detection
- Security incidents
- Moderation/audit history
- `/unmute`
- `/unban`
- `/ban`
- `/mute`
- Anti-spam/flood/repeated-message detection
- Telegram invite-link protection
- Emergency lockdown
- MongoDB persistence using PyMongo Async
- FastAPI `/health` endpoint for Render

MongoDB is accessed through the current PyMongo Async API rather than Motor.

## Environment variables

```text
BOT_TOKEN=your_bot_token
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=telegram_security
OWNER_ID=your_numeric_telegram_user_id
DEFAULT_MUTE_MINUTES=60
ALERT_CHAT_ID=optional_logger_chat_id
```

Do not commit real credentials.

## Telegram permissions

Add the bot as an administrator and grant the permissions required for the features you enable, especially:

- Delete messages
- Restrict members
- Ban members

Disable Group Privacy Mode if you want message-level anti-spam checks.

## Explicit-content detection

The project deliberately does not pretend that Telegram's Bot API can identify nudity from a media file by itself. The moderation engine contains a hook for a dedicated content-classification provider. When integrated, high-confidence prohibited content can be deleted and non-admin users can be automatically restricted according to policy.

## Bot/admin security limitation

Telegram's permission model cannot be overridden by another bot. The security bot can monitor bot additions/promotions, log who performed them, alert the owner, and remediate when its own Telegram permissions permit.

## Render

This project includes `render.yaml`. Set the environment variables in Render's Environment section. The service exposes `/health` and binds to Render's `PORT`.

## Local run

```bash
pip install -r requirements.txt
python -m security_bot
```
