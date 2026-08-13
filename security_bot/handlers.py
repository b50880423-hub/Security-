from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

async def owner_only(update, context):
    return bool(update.effective_user and update.effective_user.id == context.bot_data["settings"].owner_id)

def uid(value):
    return int(value)

async def security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text("Use this command inside a group.")
        return
    row = await context.bot_data["db"].settings(chat.id, context.bot_data["settings"].default_mute_minutes)
    await update.effective_message.reply_text(
        "GROUP SECURITY CENTER\n\n"
        f"Protection: {'LOCKDOWN' if row['lockdown'] else 'ACTIVE'}\n"
        f"Anti-Spam: {'ON' if row['anti_spam'] else 'OFF'}\n"
        f"Anti-Links: {'ON' if row['anti_links'] else 'OFF'}\n"
        f"Explicit Protection: {'ON' if row['explicit_protection'] else 'ON'}\n"
        f"Anti-Raid: {'ON' if row['raid_protection'] else 'OFF'}\n"
        f"Default mute: {row['default_mute_minutes']} minutes"
    )

async def lockdown(update, context):
    if not await owner_only(update, context): return
    await context.bot_data["db"].set_lockdown(update.effective_chat.id, True, context.bot_data["settings"].default_mute_minutes)
    await update.effective_message.reply_text("🔒 Security lockdown enabled.")

async def lockdown_off(update, context):
    if not await owner_only(update, context): return
    await context.bot_data["db"].set_lockdown(update.effective_chat.id, False, context.bot_data["settings"].default_mute_minutes)
    await update.effective_message.reply_text("🔓 Security lockdown disabled.")

async def mute(update, context):
    if not await owner_only(update, context): return
    if not context.args:
        await update.effective_message.reply_text("Usage: /mute USER_ID [minutes] [reason]"); return
    try:
        user_id = uid(context.args[0])
        minutes = int(context.args[1]) if len(context.args) > 1 else 60
    except ValueError:
        await update.effective_message.reply_text("Invalid user ID or duration."); return
    reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Manual moderation"
    engine = context.bot_data["engine"]
    if await engine.is_admin(update.effective_chat.id, user_id):
        await update.effective_message.reply_text("Refusing: target is an administrator."); return
    try:
        await engine.restrict(update.effective_chat.id, user_id, minutes, reason, update.effective_user.id)
        await update.effective_message.reply_text(f"User {user_id} muted for {minutes} minutes.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Unable to mute: {type(exc).__name__}")

async def unmute(update, context):
    if not await owner_only(update, context): return
    if not context.args:
        await update.effective_message.reply_text("Usage: /unmute USER_ID"); return
    try:
        user_id = uid(context.args[0])
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user_id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            )
        )
        await context.bot_data["db"].action(update.effective_chat.id, user_id, update.effective_user.id, "unmute", "Owner override")
        await update.effective_message.reply_text(f"User {user_id} unmuted.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Unable to unmute: {type(exc).__name__}")

async def ban(update, context):
    if not await owner_only(update, context): return
    if not context.args:
        await update.effective_message.reply_text("Usage: /ban USER_ID [reason]"); return
    try: user_id = uid(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Invalid user ID."); return
    if await context.bot_data["engine"].is_admin(update.effective_chat.id, user_id):
        await update.effective_message.reply_text("Refusing: target is an administrator."); return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Manual moderation"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        await context.bot_data["db"].action(update.effective_chat.id, user_id, update.effective_user.id, "ban", reason)
        await update.effective_message.reply_text(f"User {user_id} banned.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Unable to ban: {type(exc).__name__}")

async def unban(update, context):
    if not await owner_only(update, context): return
    if not context.args:
        await update.effective_message.reply_text("Usage: /unban USER_ID"); return
    try:
        user_id = uid(context.args[0])
        await context.bot.unban_chat_member(update.effective_chat.id, user_id, only_if_banned=True)
        await context.bot_data["db"].action(update.effective_chat.id, user_id, update.effective_user.id, "unban", "Owner override")
        await update.effective_message.reply_text(f"User {user_id} unbanned.")
    except Exception as exc:
        await update.effective_message.reply_text(f"Unable to unban: {type(exc).__name__}")

async def history(update, context):
    if not await owner_only(update, context): return
    if not context.args:
        await update.effective_message.reply_text("Usage: /history USER_ID"); return
    try: user_id = uid(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Invalid user ID."); return
    rows = await context.bot_data["db"].history(update.effective_chat.id, user_id)
    if not rows:
        await update.effective_message.reply_text("No moderation history found."); return
    lines = ["SECURITY HISTORY", ""]
    for row in rows:
        lines.append(f"{row.get('created_at')} — {row.get('action')} — {row.get('reason') or '-'}")
    await update.effective_message.reply_text("\n".join(lines[:31]))
