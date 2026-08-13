from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

HELP_TEXT = {
    "security": (
        "🔐 <b>Security Commands</b>\n\n"
        "/security\nDisplays the current security status of the group.\n\n"
        "/lockdown\nActivates emergency lockdown for non-admin members.\n\n"
        "/lockdown_off\nDisables emergency lockdown."
    ),
    "moderation": (
        "👮 <b>Moderation Commands</b>\n\n"
        "/mute USER_ID [minutes] [reason]\nTemporarily restricts a member.\n\n"
        "/unmute USER_ID\nRemoves an active mute.\n\n"
        "/ban USER_ID [reason]\nBans a member from the group.\n\n"
        "/unban USER_ID\nRemoves a member's ban."
    ),
    "protection": (
        "🛡️ <b>Automatic Protection</b>\n\n"
        "• Anti-Spam — detects flooding and repeated messages.\n"
        "• Anti-Link — detects Telegram invite links.\n"
        "• Anti-Raid — security controls for suspicious activity.\n"
        "• Emergency Lockdown — restricts normal members during incidents.\n"
        "• Content Guard — hook for an external media classifier."
    ),
    "bots": (
        "🤖 <b>Bot Security</b>\n\n"
        "The bot monitors bot additions and administrator promotions.\n\n"
        "The owner receives a security alert with the actor, bot and new status.\n"
        "Bot events are also stored in MongoDB.\n\n"
        "⚠️ Telegram does not provide a native permission that lets one bot "
        "override all other group administrators."
    ),
    "logs": (
        "📋 <b>Logs & History</b>\n\n"
        "/history USER_ID\nShows stored moderation actions for a member.\n\n"
        "Security incidents and moderation actions are persisted in MongoDB."
    ),
    "settings": (
        "⚙️ <b>Settings</b>\n\n"
        "/security\nView the current protection configuration.\n\n"
        "/lockdown\nEnable emergency lockdown.\n\n"
        "/lockdown_off\nDisable emergency lockdown.\n\n"
        "A full inline settings panel can be added for owner-only configuration."
    ),
}

def help_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔐 Security", callback_data="help:security"),
            InlineKeyboardButton("👮 Moderation", callback_data="help:moderation"),
        ],
        [
            InlineKeyboardButton("🛡️ Protection", callback_data="help:protection"),
            InlineKeyboardButton("🤖 Bot Security", callback_data="help:bots"),
        ],
        [
            InlineKeyboardButton("📋 Logs & History", callback_data="help:logs"),
            InlineKeyboardButton("⚙️ Settings", callback_data="help:settings"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="help:home")],
    ])

def home_keyboard(bot_username: str | None):
    add_url = (
        f"https://t.me/{bot_username}?startgroup=true"
        if bot_username else None
    )
    rows = []
    if add_url:
        rows.append([InlineKeyboardButton("➕ ADD ME TO YOUR GROUP", url=add_url)])
    rows.append([InlineKeyboardButton("🛟 HELP", callback_data="help:home")])
    return InlineKeyboardMarkup(rows)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_username = context.bot.username

    text = (
        "🛡️ <b>TELEGRAM GROUP SECURITY</b>\n\n"
        "Welcome to the Security Bot.\n\n"
        "Advanced protection against spam, raids, "
        "malicious links and unwanted activity.\n\n"
        "Choose an option below 👇"
    )
    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=home_keyboard(bot_username),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🛡️ <b>SECURITY BOT — HELP</b>\n\n"
        "Select a category to learn how each command and protection works.",
        parse_mode="HTML",
        reply_markup=help_keyboard(),
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]

    if key == "home":
        await query.edit_message_text(
            "🛡️ <b>SECURITY BOT — HELP</b>\n\n"
            "Select a category to learn how each command and protection works.",
            parse_mode="HTML",
            reply_markup=help_keyboard(),
        )
        return

    text = HELP_TEXT.get(key)
    if not text:
        return

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Help", callback_data="help:home")]
        ]),
    )
