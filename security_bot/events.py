from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

async def my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.my_chat_member
    if not cm or not cm.chat or not cm.new_chat_member:
        return
    if cm.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        await context.bot.send_message(
            context.bot_data["settings"].owner_id,
            f"🔐 Security bot is now administrator in {cm.chat.title or cm.chat.id}."
        )

async def chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member
    if not cm:
        return
    target = cm.new_chat_member.user
    actor = cm.from_user
    old_status = cm.old_chat_member.status
    new_status = cm.new_chat_member.status

    added = old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED) and new_status in (
        ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR
    )
    promoted = new_status == ChatMemberStatus.ADMINISTRATOR and old_status != ChatMemberStatus.ADMINISTRATOR

    if target.is_bot and (added or promoted):
        await context.bot_data["db"].bot_event(
            cm.chat.id, target.id, target.username, actor.id, new_status == ChatMemberStatus.ADMINISTRATOR
        )
        title = "BOT ADMIN PROMOTION" if promoted else "BOT SECURITY ALERT"
        await context.bot_data["engine"].alert(
            f"🚨 <b>{title}</b>\n"
            f"Bot: @{target.username or target.first_name}\n"
            f"Actor: {actor.mention_html()}\n"
            f"New status: {new_status}\nOwner review required."
        )
