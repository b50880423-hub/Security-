from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

def parse_user_id(arg):
    if not arg:
        raise ValueError("user id required")
    return int(arg)

async def require_owner(update, settings):
    return update.effective_user and update.effective_user.id == settings.owner_id

async def security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group","supergroup"):
        await update.message.reply_text("Use this command inside a group.")
        return
    row = await context.bot_data["db"].settings(update.effective_chat.id)
    await update.message.reply_text(
        "GROUP SECURITY CENTER\n\n"
        f"Protection: {'ACTIVE' if not row['lockdown'] else 'LOCKDOWN'}\n"
        f"Anti-Spam: {'ON' if row['anti_spam'] else 'OFF'}\n"
        f"Anti-Links: {'ON' if row['anti_links'] else 'OFF'}\n"
        f"Explicit Protection: {'ON' if row['explicit_protection'] else 'OFF'}\n"
        f"Anti-Raid: {'ON' if row['raid_protection'] else 'OFF'}\n"
        f"Default mute: {row['default_mute_minutes']} minutes"
    )

async def lockdown(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    chat_id = update.effective_chat.id
    db = context.bot_data["db"]
    await db.set_lockdown(chat_id, True)
    await update.message.reply_text("🔒 Security lockdown enabled.")

async def lockdown_off(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    await context.bot_data["db"].set_lockdown(update.effective_chat.id, False)
    await update.message.reply_text("🔓 Security lockdown disabled.")

async def mute(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    if not context.args:
        await update.message.reply_text("Usage: /mute USER_ID [minutes] [reason]")
        return
    uid = parse_user_id(context.args[0])
    minutes = int(context.args[1]) if len(context.args) > 1 else 60
    reason = " ".join(context.args[2:]) if len(context.args) > 2 else "Manual moderation"
    engine = context.bot_data["engine"]
    if await engine.is_admin(update.effective_chat.id, uid):
        await update.message.reply_text("Refusing: target is an administrator.")
        return
    await engine.restrict(update.effective_chat.id, uid, minutes, reason)
    await update.message.reply_text(f"User {uid} muted for {minutes} minutes.")

async def unmute(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unmute USER_ID")
        return
    uid = parse_user_id(context.args[0])
    await context.bot.restrict_chat_member(
        update.effective_chat.id, uid,
        permissions=ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )
    await context.bot_data["db"].action(update.effective_chat.id, uid, update.effective_user.id, "unmute", "Owner override")
    await update.message.reply_text(f"User {uid} unmuted.")

async def ban(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban USER_ID [reason]")
        return
    uid = parse_user_id(context.args[0])
    if await context.bot_data["engine"].is_admin(update.effective_chat.id, uid):
        await update.message.reply_text("Refusing: target is an administrator.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Manual moderation"
    await context.bot.ban_chat_member(update.effective_chat.id, uid)
    await context.bot_data["db"].action(update.effective_chat.id, uid, update.effective_user.id, "ban", reason)
    await update.message.reply_text(f"User {uid} banned.")

async def unban(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban USER_ID")
        return
    uid = parse_user_id(context.args[0])
    await context.bot.unban_chat_member(update.effective_chat.id, uid, only_if_banned=True)
    await context.bot_data["db"].action(update.effective_chat.id, uid, update.effective_user.id, "unban", "Owner override")
    await update.message.reply_text(f"User {uid} unbanned.")

async def history(update, context):
    if not await require_owner(update, context.bot_data["settings"]):
        return
    if not context.args:
        await update.message.reply_text("Usage: /history USER_ID")
        return
    uid = parse_user_id(context.args[0])
    rows = await context.bot_data["db"].history(update.effective_chat.id, uid)
    if not rows:
        await update.message.reply_text("No moderation history found.")
        return
    lines = ["SECURITY HISTORY", ""]
    for r in rows:
        lines.append(f"{r['created_at']} — {r['action']} — {r.get('reason') or '-'}")
    await update.message.reply_text("\n".join(lines[:31]))
