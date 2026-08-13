from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

async def my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.my_chat_member
    if not cm or not cm.chat or not cm.new_chat_member:
        return
    # This handles the security bot's own membership changes.
    if cm.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        await context.bot.send_message(
            context.bot_data["settings"].owner_id,
            f"🔐 Security bot is now administrator in {cm.chat.title or cm.chat.id}."
        )

async def chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member
    if not cm:
        return
    new = cm.new_chat_member
    old = cm.old_chat_member
    target = new.user
    actor = cm.from_user

    if target.is_bot and old.status in ("left","kicked") and new.status in ("member","administrator"):
        await context.bot_data["db"].bot_event(
            cm.chat.id, target.id, target.username, actor.id,
            new.status == "administrator"
        )
        await context.bot_data["engine"].alert(
            f"🚨 BOT SECURITY ALERT\n"
            f"Bot: @{target.username or target.first_name}\n"
            f"Added/promoted by: {actor.mention_html()}\n"
            f"New status: {new.status}\n"
            f"Owner review required.",
            cm.chat.id
        )
    elif target.is_bot and new.status == "administrator" and old.status != "administrator":
        await context.bot_data["db"].bot_event(
            cm.chat.id, target.id, target.username, actor.id, True
        )
        await context.bot_data["engine"].alert(
            f"🚨 BOT ADMIN PROMOTION\n"
            f"Bot: @{target.username or target.first_name}\n"
            f"Promoted by: {actor.mention_html()}\n"
            f"Owner review required.",
            cm.chat.id
        )
