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
        self.message_times = defaultdict(lambda: deque(maxlen=20))
        self.recent_text = defaultdict(lambda: deque(maxlen=5))

    async def is_admin(self, chat_id, user_id):
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        except Exception:
            return False

    def has_url(self, text):
        return bool(URL_RE.search(text or ""))

    def looks_like_spam(self, chat_id, user_id, text):
        now = datetime.now(timezone.utc)
        key = (chat_id, user_id)
        q = self.message_times[key]
        q.append(now)
        recent = [x for x in q if (now-x).total_seconds() <= 8]
        repeated = text and text.lower() in [x.lower() for x in self.recent_text[key] if x]
        self.recent_text[key].append(text or "")
        return len(recent) >= 8 or repeated

    def prohibited_media(self, message):
        # Safe baseline: media is not automatically classified as sexual.
        # Hook an approved moderation/vision provider here for actual nudity detection.
        return False

    async def restrict(self, chat_id, user_id, minutes, reason, incident_id=None):
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        permissions = ChatPermissions(can_send_messages=False)
        await self.bot.restrict_chat_member(chat_id, user_id, permissions=permissions, until_date=until)
        await self.db.action(chat_id,user_id,self.settings.owner_id,"mute",reason,minutes*60,incident_id)

    async def delete(self, message):
        try:
            await message.delete()
            return True
        except (BadRequest, Forbidden):
            return False

    async def handle_message(self, update: Update):
        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if not message or not chat or chat.type not in ("group","supergroup") or not user:
            return

        admin = await self.is_admin(chat.id, user.id)
        text = message.text or message.caption or ""

        row = await self.db.settings(chat.id)
        if not row:
            return

        reason = None
        kind = None
        severity = "MEDIUM"

        if row["anti_links"] and self.has_url(text):
            if TG_INVITE_RE.search(text):
                reason = "Telegram invite link"
                kind = "blocked_link"
                severity = "HIGH"

        if not reason and row["anti_spam"] and self.looks_like_spam(chat.id, user.id, text):
            reason = "Flood or repeated-message spam"
            kind = "spam"
            severity = "HIGH"

        if not reason and row["explicit_protection"] and self.prohibited_media(message):
            reason = "Prohibited explicit content"
            kind = "explicit_content"
            severity = "HIGH"

        if not reason:
            return

        incident_id = await self.db.incident(
            chat.id,user.id,user.id,kind,severity,reason,message.message_id
        )
        deleted = await self.delete(message)

        if admin:
            await self.alert(
                f"⚠️ ADMIN SECURITY EVENT\n"
                f"Admin: {user.mention_html()}\n"
                f"Reason: {reason}\n"
                f"Message deleted: {'yes' if deleted else 'no'}\n"
                f"Incident: SEC-{incident_id}",
                chat.id
            )
            return

        minutes = int(row["default_mute_minutes"])
        try:
            await self.restrict(chat.id,user.id,minutes,reason,incident_id)
            await self.alert(
                f"🚨 SECURITY ACTION\n"
                f"User: {user.mention_html()}\n"
                f"Reason: {reason}\n"
                f"Message deleted: {'yes' if deleted else 'no'}\n"
                f"Action: muted {minutes} minutes\n"
                f"Incident: SEC-{incident_id}",
                chat.id
            )
        except Exception as e:
            await self.alert(
                f"⚠️ SECURITY ACTION FAILED\nUser: {user.id}\nReason: {reason}\n"
                f"Incident: SEC-{incident_id}\nError: {type(e).__name__}",
                chat.id
            )

    async def alert(self, text, group_id):
        target = self.settings.alert_chat_id or self.settings.owner_id
        try:
            await self.bot.send_message(target, text, parse_mode="HTML")
        except Exception:
            pass
