import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from telegram import ChatPermissions, Update
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden

URL_RE = re.compile(r"(https?://|www\.)[^\s<>]+", re.I)
TG_INVITE_RE = re.compile(r"(t\.me/(?:\+|joinchat/)|telegram\.me/joinchat/)", re.I)

class SecurityEngine:
    def __init__(self, db, settings, bot):
        self.db = db
        self.settings = settings
        self.bot = bot
        self.times = defaultdict(lambda: deque(maxlen=30))
        self.recent = defaultdict(lambda: deque(maxlen=6))

    async def is_admin(self, chat_id, user_id):
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        except Exception:
            return False

    def spam(self, chat_id, user_id, text):
        now = datetime.now(timezone.utc)
        key = (chat_id, user_id)
        self.times[key].append(now)
        recent = [t for t in self.times[key] if (now - t).total_seconds() <= 8]
        normalized = (text or "").strip().casefold()
        repeated = normalized and normalized in {(x or "").strip().casefold() for x in self.recent[key]}
        self.recent[key].append(text or "")
        return len(recent) >= 8 or repeated

    def prohibited_media(self, message):
        # Real classifier integration belongs here.
        return False

    async def delete(self, message):
        try:
            await message.delete()
            return True
        except (BadRequest, Forbidden, Exception):
            return False

    async def restrict(self, chat_id, user_id, minutes, reason, actor_id, incident_id=None):
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await self.bot.restrict_chat_member(
            chat_id, user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await self.db.action(chat_id, user_id, actor_id, "mute", reason, minutes * 60, incident_id)

    async def alert(self, text):
        target = self.settings.alert_chat_id or self.settings.owner_id
        try:
            await self.bot.send_message(target, text, parse_mode="HTML")
        except Exception:
            pass

    async def handle_message(self, update: Update, context):
        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if not message or not chat or not user or chat.type not in ("group", "supergroup"):
            return

        row = await self.db.settings(chat.id, self.settings.default_mute_minutes)
        admin = await self.is_admin(chat.id, user.id)
        text = message.text or message.caption or ""

        reason = kind = severity = None
        if row["lockdown"] and not admin:
            reason, kind, severity = "Emergency security lockdown", "lockdown", "HIGH"
        elif row["anti_links"] and TG_INVITE_RE.search(text):
            reason, kind, severity = "Telegram invite link", "blocked_link", "HIGH"
        elif row["anti_spam"] and self.spam(chat.id, user.id, text):
            reason, kind, severity = "Flood or repeated-message spam", "spam", "HIGH"
        elif row["explicit_protection"] and self.prohibited_media(message):
            reason, kind, severity = "Prohibited explicit content", "explicit_content", "HIGH"

        if not reason:
            return

        incident = await self.db.incident(chat.id, user.id, user.id, kind, severity, reason, message.message_id)
        deleted = await self.delete(message)

        if admin:
            await self.alert(
                "⚠️ <b>ADMIN SECURITY EVENT</b>\n"
                f"Admin: {user.mention_html()}\nReason: {reason}\n"
                f"Deleted: {'yes' if deleted else 'no'}\nIncident: SEC-{incident}"
            )
            return

        minutes = int(row["default_mute_minutes"])
        try:
            await self.restrict(chat.id, user.id, minutes, reason, user.id, incident)
            await self.alert(
                "🚨 <b>SECURITY ACTION</b>\n"
                f"User: {user.mention_html()}\nReason: {reason}\n"
                f"Deleted: {'yes' if deleted else 'no'}\n"
                f"Action: muted {minutes} minutes\nIncident: SEC-{incident}"
            )
        except Exception as exc:
            await self.alert(
                "⚠️ <b>SECURITY ACTION FAILED</b>\n"
                f"User ID: {user.id}\nIncident: SEC-{incident}\nError: {type(exc).__name__}"
            )
