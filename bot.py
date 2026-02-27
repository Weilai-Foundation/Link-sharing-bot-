from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, BotCommand, ChatJoinRequest
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, ChatJoinRequestHandler
from pyrogram.errors import TokenInvalid, FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid
import asyncio
from datetime import datetime, timedelta, timezone

from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, START_PIC, LINK_PIC
from database import db
from utils import encode_channel_id, decode_channel_id, font_style, get_shortlink
from broadcast_handler import broadcast_handler

BOT_COMMANDS = [
    BotCommand("start", font_style("𝖲𝗍𝖺𝗋𝗍 𝗍𝗁𝖾 𝖻𝗈𝗍")),
    BotCommand("setchannel", font_style("𝖱𝖾𝗀𝗂𝗌𝗍𝖾𝗋 𝖺 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉")),
    BotCommand("delchannel", font_style("𝖱𝖾𝗆𝗈𝗐𝖾 𝖺 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉")),
    BotCommand("channelpost", font_style("𝖦𝖾𝗍 𝗍𝖾𝗆𝗉𝗈𝗋𝖺𝗋𝗒 𝗃𝗈𝗂𝗇 𝗅𝗂𝗇𝗄𝗌")),
    BotCommand("reqpost", font_style("𝖦𝖾𝗍 𝗋𝖾𝗊𝗎𝖾𝗌𝗍-𝗍𝗈-𝗃𝗈𝗂𝗇 𝗅𝗂𝗇𝗄𝗌")),
    BotCommand("broadcast", font_style("𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 (𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾)")),
    BotCommand("users", font_style("𝖦𝖾𝗍 𝗍𝗈𝗍𝖺𝗅 𝗎𝗌𝖾𝗋 𝖼𝗈𝗎𝗇𝗍")),
    BotCommand("stats", font_style("𝖦𝖾𝗍 𝖻𝗈𝗍 𝗌𝗍𝖺𝗍𝗂𝗌𝗍𝗂𝖼𝗌")),
    BotCommand("clone", font_style("𝖢𝗅𝗈𝗇𝖾 𝖺 𝗇𝖾𝗐 𝖻𝗈𝗍")),
    BotCommand("mybots", font_style("𝖫𝗂𝗌𝗍 𝗒𝗈𝗎𝗋 𝖼𝗅𝗈𝗇𝖾𝖽 𝖻𝗈𝗍𝗌")),
    BotCommand("addadmin", font_style("𝖠𝖽𝖽 𝖺𝖽𝗆𝗂𝗇 𝗍𝗈 𝗍𝗁𝗂𝗌 𝖻𝗈𝗍")),
    BotCommand("remadmin", font_style("𝖱𝖾𝗆𝗈𝗐𝖾 𝖺𝖽𝗆𝗂𝗇 𝖿𝗋𝗈𝗆 𝗍𝗁𝗂𝗌 𝖻𝗈𝗍"))
]

# Global list to store all clients
running_clients = []
MASTER_BOT_ID = None

# --- Filters ---

async def is_admin_filter(_, client, message: Message):
    return await db.is_admin(client.me.id, message.from_user.id, ADMINS)

async def is_owner_filter(_, client, message: Message):
    return await db.is_owner(client.me.id, message.from_user.id, ADMINS)

async def is_main_owner_filter(_, client, message: Message):
    return message.from_user.id in ADMINS

is_admin = filters.create(is_admin_filter)
is_owner = filters.create(is_owner_filter)
is_main_owner = filters.create(is_main_owner_filter)

# --- Helper Functions for Buttons ---

def get_start_keyboard(is_admin=False, settings=None):
    """Returns the inline keyboard for start message with About and Help buttons"""
    if settings is None:
        settings = {}

    channel_url = settings.get("channel_url", "https://t.me/Vecna_Bots")
    support_url = settings.get("support_url", "https://t.me/Vecna_Suppprt")

    buttons = [
        [
            InlineKeyboardButton(font_style("📚 About"), callback_data="about"),
            InlineKeyboardButton(font_style("❓ Help"), callback_data="help")
        ],
        [
            InlineKeyboardButton(font_style("📢 Channel"), url=channel_url),
            InlineKeyboardButton(font_style("👥 Support"), url=support_url)
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(font_style("⚙️ Settings"), callback_data="settings")])
    return InlineKeyboardMarkup(buttons)

def get_back_button_keyboard():
    """Returns keyboard with back button to return to start menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(font_style("🔙 Back to Start"), callback_data="back_to_start")]
    ])

def get_settings_keyboard(settings=None):
    """Returns the keyboard for settings menu"""
    if settings is None:
        settings = {}

    auto_approve = settings.get("auto_approve", False)
    approve_text = "Auto Approve: ✅ On" if auto_approve else "Auto Approve: ❌ Off"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(font_style("📝 Start Message"), callback_data="set_start_msg")],
        [InlineKeyboardButton(font_style("ℹ️ Help Message"), callback_data="set_help_msg")],
        [InlineKeyboardButton(font_style("🖼️ Start Image URL"), callback_data="set_start_pic")],
        [InlineKeyboardButton(font_style("🔘 Button Name"), callback_data="set_btn_name")],
        [InlineKeyboardButton(font_style("📄 Button Text"), callback_data="set_btn_text")],
        [InlineKeyboardButton(font_style("📚 About Text"), callback_data="set_about_text")],
        [InlineKeyboardButton(font_style("👥 Support URL"), callback_data="set_support_url")],
        [InlineKeyboardButton(font_style("📢 Channel URL"), callback_data="set_channel_url")],
        [
            InlineKeyboardButton(font_style("⏳ Time Expire"), callback_data="set_expire_time"),
            InlineKeyboardButton(font_style("🔗 Link Pic URL"), callback_data="set_link_pic")
        ],
        [InlineKeyboardButton(font_style(approve_text), callback_data="toggle_auto_approve")],
        [
            InlineKeyboardButton(font_style("🔗 Shortener API"), callback_data="set_shortener_api"),
            InlineKeyboardButton(font_style("🌐 Shortener URL"), callback_data="set_shortener_url")
        ],
        [InlineKeyboardButton(font_style("🗑️ Remove Pic"), callback_data="remove_pic")],
        [InlineKeyboardButton(font_style("🔙 Back"), callback_data="back_to_start")]
    ])

def get_remove_pic_keyboard():
    """Returns keyboard with remove picture options"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(font_style("🔗 Link Pic"), callback_data="del_link_pic")],
        [InlineKeyboardButton(font_style("🖼️ Start Img"), callback_data="del_start_pic")],
        [InlineKeyboardButton(font_style("🔙 Back"), callback_data="settings")]
    ])

async def edit_message(message: Message, text: str, reply_markup: InlineKeyboardMarkup = None):
    """Helper function to edit message whether it has media or not"""
    if message.photo or message.animation or message.video or message.document:
        return await message.edit_caption(caption=text, reply_markup=reply_markup)
    return await message.edit_text(text=text, reply_markup=reply_markup)

# --- Callback Query Handler ---

async def callback_query_handler(client: Client, callback_query):
    """Handle callback queries from inline buttons"""
    data = callback_query.data
    
    settings = await db.get_bot_settings(client.me.id)

    if data == "about":
        about_text = settings.get("about_text")
        if about_text:
            about_text = font_style(about_text)
        else:
            about_text = font_style(
                "<b>ℹ️ About This Bot</b>\n\n"
                "<b>Channel Link Bot</b> - A powerful bot that creates smart redirect links for your Telegram channels and groups.\n\n"
                "<b>Features:</b>\n"
                "• Create temporary join links (10-minute expiry)\n"
                "• Create request-to-join links (admin approval required)\n"
                "• Support for channels, groups, and supergroups\n"
                "• Multi-bot cloning support (up to 100 bots)\n"
                "• Admin management system\n\n"
                "<b>Developer:</b> @Vecna_Bots\n"
                "<b>Powered by:</b> @Vecna_Bots"
            )
        await edit_message(
            callback_query.message,
            text=about_text,
            reply_markup=get_back_button_keyboard()
        )
    
    elif data == "help":
        help_text = settings.get("help_msg")
        if help_text:
            help_text = font_style(help_text)
        else:
            help_text = font_style(
                "<b>❓ Help & Commands</b>\n\n"
                "<b>User Commands:</b>\n"
                "• /start - Start the bot\n\n"
                "<b>Admin Commands:</b>\n"
                "• /setchannel [@username/id] - Register a channel/group\n"
                "• /delchannel [@username/id] - Remove a channel/group\n"
                "• /channelpost - Get all temporary join links\n"
                "• /channelpost [@username/id] - Get specific channel link\n"
                "• /reqpost - Get all request-to-join links\n"
                "• /reqpost [@username/id] - Get specific request link\n"
                "• /broadcast - Broadcast message (reply to a message)\n"
                "• /users - Get total user count\n"
                "• /stats - Get bot statistics\n"
                "• /bots - List all cloned bots\n\n"
                "<b>Owner Commands:</b>\n"
                "• /clone [bot_token] - Clone a new bot\n"
                "• /addadmin [user_id] - Add admin to this bot\n"
                "• /remadmin [user_id] - Remove admin from this bot\n"
                "• /admin_list - List all admins\n"
                "• /settings - Configure bot settings\n\n"
                "<b>How to Use:</b>\n"
                "1. Add bot as admin to your channel/group\n"
                "2. Register it using /setchannel\n"
                "3. Generate links using /channelpost or /reqpost\n"
                "4. Share the generated links with users"
            )
        await edit_message(
            callback_query.message,
            text=help_text,
            reply_markup=get_back_button_keyboard()
        )
    
    elif data == "back_to_start":
        start_text = settings.get("start_msg")
        if start_text:
            start_text = font_style(start_text)
        else:
            start_text = font_style("<b><blockquote>Bakka {mention}!\n\nI’m the Channel Link Bot — I create smart redirect links for your Telegram channels to help avoid copyright problems and keep things safe.</blockquote></b>")
        start_text = start_text.format(mention=callback_query.from_user.mention)
        is_adm = await db.is_admin(client.me.id, callback_query.from_user.id, ADMINS)
        await edit_message(
            callback_query.message,
            text=start_text,
            reply_markup=get_start_keyboard(is_admin=is_adm, settings=settings)
        )
    
    elif data == "settings":
        await edit_message(
            callback_query.message,
            text=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard(settings=settings)
        )

    elif data.startswith("renew_bot_"):
        bot_id = int(data.split("_")[-1])
        token = await db.create_renewal_token(bot_id, callback_query.from_user.id)

        master_bot = await db.get_bot(running_clients[0].me.id)
        master_username = master_bot.get('username')
        renewal_link = f"https://t.me/{master_username}?start=renew_{token}"

        # Shorten renewal link if master shortener is set
        m_api = await db.get_global_setting("master_shortener_api")
        m_url = await db.get_global_setting("master_shortener_url")
        if m_api and m_url:
            renewal_link = await get_shortlink(renewal_link, m_url, m_api)

        await callback_query.message.reply_text(
            font_style(
                f"<b>♻️ Bot Renewal</b>\n\n"
                f"To renew your bot for another 7 days, please click the button below and follow the instructions.\n\n"
                f"🔗 <b>Renewal Link:</b> {renewal_link}"
            ),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(font_style("🚀 Renew Now"), url=renewal_link)]])
        )

    elif data == "toggle_auto_approve":
        current_approve = settings.get("auto_approve", False)
        new_approve = not current_approve
        await db.update_bot_setting(client.me.id, "auto_approve", new_approve)
        settings["auto_approve"] = new_approve
        await edit_message(
            callback_query.message,
            text=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard(settings=settings)
        )

    elif data == "remove_pic":
        await edit_message(
            callback_query.message,
            text=font_style("<b>🗑️ Remove Picture</b>\n\nChoose which picture you want to remove:"),
            reply_markup=get_remove_pic_keyboard()
        )

    elif data.startswith("del_"):
        key = "start_pic" if "start_pic" in data else "link_pic"
        await db.update_bot_setting(client.me.id, key, "none")
        await callback_query.answer(font_style(f"✅ Successfully removed {key.replace('_', ' ').title()}!"), show_alert=True)
        settings = await db.get_bot_settings(client.me.id)
        await edit_message(
            callback_query.message,
            text=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard(settings=settings)
        )

    elif data.startswith("set_"):
        prompts = {
            "set_start_msg": "Send the new Start Message.",
            "set_help_msg": "Send the new Help Message.",
            "set_start_pic": "Send the new Start Image URL or photo.",
            "set_btn_name": "Send the new Button Name.",
            "set_btn_text": "Send the new Button Text (Caption).",
            "set_about_text": "Send the new About Text.",
            "set_support_url": "Send the new Support Group URL.",
            "set_channel_url": "Send the new Channel URL.",
            "set_expire_time": "Send the new Invite Link Expire Time (in minutes).",
            "set_link_pic": "Send the new Link Pic URL or photo.",
            "set_shortener_api": "Send the new Shortener API Key.",
            "set_shortener_url": "Send the new Shortener URL (e.g., https://shrinkme.io/api)."
        }

        prompt_text = prompts.get(data, "Send the new value.")

        await callback_query.message.reply_text(
            font_style(f"<b>{prompt_text}</b>\n\nUse /cancel to abort."),
            reply_markup=ForceReply(selective=True)
        )

    elif data == "bots_back":
        bots = await db.get_all_bots()
        cloned_bots = [bot for bot in bots if bot['_id'] != MASTER_BOT_ID]
        if not cloned_bots:
            return await edit_message(callback_query.message, font_style("No cloned bots found."))

        text = font_style("<b>🤖 Cloned Bots Management</b>\n\nSelect a bot to view details and manage it:")
        buttons = []
        now = datetime.now(timezone.utc)
        for bot in cloned_bots:
            username = bot.get('username', 'Unknown')
            expiry = bot.get('expiry')
            is_deactivated = bot.get('is_deactivated', False)
            status_icon = "❌" if is_deactivated else "✅"
            if expiry:
                if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry < now and not is_deactivated: status_icon = "⌛"
            buttons.append([InlineKeyboardButton(font_style(f"{status_icon} @{username}"), callback_data=f"view_bot_{bot['_id']}")])
        await edit_message(callback_query.message, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("view_bot_"):
        if callback_query.from_user.id not in ADMINS:
            return await callback_query.answer(font_style("❌ Access denied."), show_alert=True)

        bot_id = int(data.split("_")[-1])
        bot = await db.get_bot(bot_id)
        if not bot:
            return await callback_query.answer(font_style("Bot not found."), show_alert=True)

        user_count = await db.get_user_count(bot_id)
        channel_count = await db.get_channel_count(bot_id)
        now = datetime.now(timezone.utc)
        expiry = bot.get('expiry')
        is_deactivated = bot.get('is_deactivated', False)

        status = "✅ Active"
        if is_deactivated:
            status = "❌ Deactivated"
        elif expiry:
            if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now: status = "⌛ Expired"

        text = font_style(
            f"<b>🤖 Bot Information: @{bot.get('username', 'Unknown')}</b>\n\n"
            f"<b>🆔 Bot ID:</b> <code>{bot_id}</code>\n"
            f"<b>👤 Owner ID:</b> <code>{bot.get('owner_id')}</code>\n"
            f"<b>📊 Status:</b> {status}\n"
            f"<b>📅 Expiry:</b> {expiry.strftime('%Y-%m-%d %H:%M:%S') if expiry else 'Never'} UTC\n"
            f"<b>👥 Total Users:</b> {user_count}\n"
            f"<b>📢 Total Channels:</b> {channel_count}"
        )

        buttons = []
        # Only Master Bot and Main Owners can deactivate/activate
        if client.me.id == MASTER_BOT_ID and callback_query.from_user.id in ADMINS:
            toggle_text = "🚀 Activate" if is_deactivated else "🛑 Deactivate"
            buttons.append([InlineKeyboardButton(font_style(toggle_text), callback_data=f"toggle_bot_{bot_id}")])

        buttons.append([InlineKeyboardButton(font_style("🔙 Back"), callback_data="bots_back")])
        await edit_message(callback_query.message, text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("toggle_bot_"):
        if callback_query.from_user.id not in ADMINS or client.me.id != MASTER_BOT_ID:
            return await callback_query.answer(font_style("Only Master Bot and Global Admins can perform this action."), show_alert=True)

        bot_id = int(data.split("_")[-1])
        bot = await db.get_bot(bot_id)
        if not bot:
            return await callback_query.answer(font_style("Bot not found."), show_alert=True)

        new_status = not bot.get('is_deactivated', False)
        await db.update_bot_status(bot_id, new_status)

        alert_msg = "Bot activated and started."
        if new_status:  # Deactivated
            for c in running_clients:
                if c.me.id == bot_id:
                    await c.stop()
                    running_clients.remove(c)
                    break
            alert_msg = "Bot deactivated and stopped."
        else:  # Activated
            expiry = bot.get('expiry')
            now = datetime.now(timezone.utc)
            if expiry:
                if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry < now:
                    alert_msg = "Bot expiry is past. Cannot start."
                else:
                    await start_bot(f"bot_{bot_id}", bot['token'])
            else:
                await start_bot(f"bot_{bot_id}", bot['token'])

        await callback_query.answer(font_style(alert_msg), show_alert=True)

        # Manually refresh the bot view to avoid recursive call and double answer
        bot = await db.get_bot(bot_id)
        user_count = await db.get_user_count(bot_id)
        channel_count = await db.get_channel_count(bot_id)
        now = datetime.now(timezone.utc)
        expiry = bot.get('expiry')
        is_deactivated = bot.get('is_deactivated', False)

        status = "✅ Active"
        if is_deactivated:
            status = "❌ Deactivated"
        elif expiry:
            if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now: status = "⌛ Expired"

        text = font_style(
            f"<b>🤖 Bot Information: @{bot.get('username', 'Unknown')}</b>\n\n"
            f"<b>🆔 Bot ID:</b> <code>{bot_id}</code>\n"
            f"<b>👤 Owner ID:</b> <code>{bot.get('owner_id')}</code>\n"
            f"<b>📊 Status:</b> {status}\n"
            f"<b>📅 Expiry:</b> {expiry.strftime('%Y-%m-%d %H:%M:%S') if expiry else 'Never'} UTC\n"
            f"<b>👥 Total Users:</b> {user_count}\n"
            f"<b>📢 Total Channels:</b> {channel_count}"
        )
        toggle_text = "🚀 Activate" if is_deactivated else "🛑 Deactivate"
        buttons = [
            [InlineKeyboardButton(font_style(toggle_text), callback_data=f"toggle_bot_{bot_id}")],
            [InlineKeyboardButton(font_style("🔙 Back"), callback_data="bots_back")]
        ]
        await edit_message(callback_query.message, text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    await callback_query.answer()

# --- Handlers ---

async def start_handler(client: Client, message: Message):
    await db.update_user(client.me.id, message.from_user.id, message.from_user.first_name)
    args = message.text.split(" ", 1)
    settings = await db.get_bot_settings(client.me.id)
    start_text = settings.get("start_msg")
    if start_text:
        start_text = font_style(start_text)
    else:
        start_text = font_style("<b><blockquote>Bakka {mention}!\n\nI’m the Channel Link Bot — I create smart redirect links for your Telegram channels to help avoid copyright problems and keep things safe.</blockquote></b>")
    start_text = start_text.format(mention=message.from_user.mention)
    
    if len(args) == 1:
        # Main start message with About and Help buttons
        is_adm = await db.is_admin(client.me.id, message.from_user.id, ADMINS)
        pic = settings.get("start_pic", START_PIC)
        if pic == "none":
            pic = None
        if pic:
            return await message.reply_photo(
                pic,
                caption=start_text,
                reply_markup=get_start_keyboard(is_admin=is_adm, settings=settings)
            )
        else:
            return await message.reply(
                start_text,
                reply_markup=get_start_keyboard(is_admin=is_adm, settings=settings),
                disable_web_page_preview=True
            )
    
    # Handle deep linking (existing code)
    param = args[1]

    if param.startswith("renew_"):
        if client.me.id != running_clients[0].me.id:
             return await message.reply(font_style("❌ Renewal can only be done through the Master Bot."))

        token = param[6:]
        res = await db.verify_renewal_token(token)
        if not res:
            return await message.reply(font_style("❌ Invalid or expired renewal token."))

        bot_id = res['bot_id']
        bot_data = await db.get_bot(bot_id)
        if not bot_data:
            return await message.reply(font_style("❌ Bot data not found."))

        new_expiry = datetime.now(timezone.utc) + timedelta(days=7)
        await db.update_bot_expiry(bot_id, new_expiry)

        # Try to restart the bot if it's not running
        is_running = False
        for c in running_clients:
            if c.me.id == bot_id:
                is_running = True
                break

        if not is_running:
            await start_bot(f"bot_{bot_id}", bot_data['token'])

        return await message.reply(font_style(
            f"✅ <b>Bot Renewed!</b>\n\n"
            f"Bot: @{bot_data.get('username')}\n"
            f"New Expiry: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ))

    is_req = False
    if param.startswith("req_"):
        is_req = True
        param = param[4:]
    try:
        channel_id = decode_channel_id(param)
    except Exception:
        return await message.reply(font_style("Invalid start parameter."))

    ch = await db.get_channel(client.me.id, chat_id=channel_id)
    if not ch:
        return await message.reply(font_style("This channel is not registered with the bot."))

    try:
        expire_time = settings.get("expire_time", 10)
        if is_req:
            link_name = f"req_{channel_id}_{message.from_user.id}"
            try:
                prev_links = await client.get_chat_invite_links(channel_id, admin_id=client.me.id)
                for l in prev_links:
                    if l.creates_join_request and l.name == link_name:
                        await client.revoke_chat_invite_link(channel_id, l.invite_link)
            except Exception:
                pass
            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                creates_join_request=True,
                name=link_name
            )
            invite_link = invite.invite_link

            # Shortening logic
            short_api = settings.get("shortener_api") or await db.get_global_setting("master_shortener_api")
            short_url = settings.get("shortener_url") or await db.get_global_setting("master_shortener_url")

            if short_api and short_url:
                invite_link = await get_shortlink(invite_link, short_url, short_api)
            text = settings.get("btn_text")
            if text:
                text = font_style(text)
            else:
                text = font_style("Request to Join: powered by @Vecna_Bots\n<i>This link requires admin approval. Only you can use it.</i>")

            pic = settings.get("link_pic", settings.get("start_pic", LINK_PIC or START_PIC))
            if pic == "none":
                pic = None

            btn_name = settings.get("btn_name")
            if btn_name:
                btn_name = font_style(btn_name)
            else:
                btn_name = font_style("「Request to Join」")
            if pic:
                sent = await message.reply_photo(
                    pic,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(btn_name, url=invite_link)]]
                    )
                )
            else:
                sent = await message.reply(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(btn_name, url=invite_link)]]
                    ),
                    disable_web_page_preview=True
                )
            asyncio.create_task(revoke_and_delete(client, channel_id, invite.invite_link, sent, expire_time))
        else:
            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                expire_date=datetime.now(timezone.utc) + timedelta(minutes=expire_time),
                member_limit=1
            )
            invite_link = invite.invite_link

            # Shortening logic
            short_api = settings.get("shortener_api") or await db.get_global_setting("master_shortener_api")
            short_url = settings.get("shortener_url") or await db.get_global_setting("master_shortener_url")

            if short_api and short_url:
                invite_link = await get_shortlink(invite_link, short_url, short_api)
            text = settings.get("btn_text")
            if text:
                text = font_style(text)
            else:
                text = font_style("Here is your link! Click below to proceed: powered by :- @Vecna_Bots ")

            pic = settings.get("link_pic", settings.get("start_pic", LINK_PIC or START_PIC))
            if pic == "none":
                pic = None

            btn_name = settings.get("btn_name")
            if btn_name:
                btn_name = font_style(btn_name)
            else:
                btn_name = font_style("「Join Channel」")
            if pic:
                sent = await message.reply_photo(
                    pic,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(btn_name, url=invite_link)]]
                    )
                )
            else:
                sent = await message.reply(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(btn_name, url=invite_link)]]
                    ),
                    disable_web_page_preview=True
                )
            asyncio.create_task(revoke_and_delete(client, channel_id, invite.invite_link, sent, expire_time))
    except Exception as e:
        await message.reply(font_style(f"Failed to generate invite: {e}"))

async def revoke_and_delete(client, channel_id, invite_link, message, expire_time):
    await asyncio.sleep(expire_time * 60)
    try:
        await client.revoke_chat_invite_link(channel_id, invite_link)
    except:
        pass
    try:
        await message.delete()
    except:
        pass

async def join_request_handler(client: Client, chat_join_request: ChatJoinRequest):
    settings = await db.get_bot_settings(client.me.id)
    if settings.get("auto_approve", False):
        try:
            await client.approve_chat_join_request(chat_join_request.chat.id, chat_join_request.from_user.id)
        except Exception as e:
            print(f"Error approving join request: {e}")

async def users_list_handler(client: Client, message: Message):
    count = await db.get_user_count(client.me.id)
    await message.reply(font_style(f"Total users: {count}"))

async def set_channel_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply(font_style("Usage: /setchannel @username or /setchannel -1001234567890"))

    target = message.command[1]
    if target.startswith("@"):
        chat_ref = target
    else:
        try:
            chat_ref = int(target)
        except ValueError:
            return await message.reply(font_style("Invalid channel/group identifier."))

    try:
        chat = await client.get_chat(chat_ref)
        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP]:
            return await message.reply(font_style(
                f"Unsupported chat type: `{chat.type}`.\n"
                "Only channels, groups, and supergroups are supported.\n"
                "Make sure the bot is a member/admin of the target."
            ))
        await db.update_channel(client.me.id, chat.id, chat.title, chat.username, str(chat.type))

        encoded = encode_channel_id(chat.id)
        reply_text = (
            f"✅ Cʜᴀɴɴᴇʟ {chat.title} ({chat.id}) ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ.\n\n"
            f"🔗 Nᴏʀᴍᴀʟ Lɪɴᴋ: https://t.me/{client.me.username}?start={encoded}\n"
            f"🔗 Rᴇǫᴜᴇsᴛ Lɪɴᴋ: https://t.me/{client.me.username}?start=req_{encoded}"
        )
        await message.reply(
            font_style(reply_text),
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply(font_style(
            f"Error: {e}\n"
            "Make sure the bot is a member/admin of the target and the ID/username is correct."
        ))

async def delete_channel_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply(font_style("Usage: /delchannel @username or /delchannel -1001234567890"))

    target = message.command[1]
    if target.startswith("@"):
        chat_ref = target
    else:
        try:
            chat_ref = int(target)
        except ValueError:
            return await message.reply(font_style("Invalid channel/group identifier."))

    try:
        chat = await client.get_chat(chat_ref)
        result = await db.delete_channel(client.me.id, chat.id)
        if result.deleted_count:
            await message.reply(font_style(f"{chat.type.name.title()} '{chat.title}' removed."))
        else:
            await message.reply(font_style("Channel/group not found."))
    except Exception as e:
        await message.reply(font_style(f"Error: {e}"))

async def channel_post_handler(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) == 2:
        target = args[1]
        ch = None
        if target.startswith("@"):
            ch = await db.get_channel(client.me.id, username=target)
        else:
            try:
                ch = await db.get_channel(client.me.id, chat_id=int(target))
            except Exception:
                return await message.reply(font_style("Invalid channel/group identifier."))
        if not ch:
            return await message.reply(font_style("Channel/group not found."))
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start={encoded}"
            await message.reply(font_style(
                f"Temporary join link for <b>{ch.get('title', ch.get('username', ch['chat_id']))}</b>:\n"
                f"<a href='{link}'>Click here</a>"
            ),
                disable_web_page_preview=True
            )
        except Exception as e:
            await message.reply(font_style(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}"))
        return

    registered = await db.get_all_channels(client.me.id)
    links = []
    for ch in registered:
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start={encoded}"
            links.append(font_style(f"<b>{ch.get('title', ch.get('username', ch['chat_id']))}</b>: <a href='{link}'>Click here</a>"))
        except Exception as e:
            links.append(font_style(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}"))

    if not links:
        return await message.reply(font_style("No channels registered."))
    await message.reply("\n".join(links), disable_web_page_preview=True)

async def req_post_handler(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) == 2:
        target = args[1]
        ch = None
        if target.startswith("@"):
            ch = await db.get_channel(client.me.id, username=target)
        else:
            try:
                ch = await db.get_channel(client.me.id, chat_id=int(target))
            except Exception:
                return await message.reply(font_style("Invalid channel/group identifier."))
        if not ch:
            return await message.reply(font_style("Channel/group not found."))
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start=req_{encoded}"
            await message.reply(font_style(
                f"Request join link for <b>{ch.get('title', ch.get('username', ch['chat_id']))}</b> (requires admin approval):\n"
                f"<a href='{link}'>Request to Join</a>\n\n"
                f"<i>Make sure 'Approve new members' is enabled in the channel/group settings for join requests to work.</i>"
            ),
                disable_web_page_preview=True
            )
        except Exception as e:
            await message.reply(font_style(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}"))
        return

    registered = await db.get_all_channels(client.me.id)
    links = []
    for ch in registered:
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start=req_{encoded}"
            links.append(font_style(
                f"<b>{ch.get('title', ch.get('username', ch['chat_id']))}</b>: <a href='{link}'>Request to Join</a> (requires admin approval)"
            ))
        except Exception as e:
            links.append(font_style(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}"))

    if not links:
        return await message.reply(font_style("No channels registered."))
    await message.reply("\n".join(links) + font_style("\n\n<i>Make sure 'Approve new members' is enabled in the channel/group settings for join requests to work.</i>"), disable_web_page_preview=True)

async def stats_handler(client: Client, message: Message):
    user_count = await db.get_user_count(client.me.id)
    channel_count = await db.get_channel_count(client.me.id)
    await message.reply(font_style(f"Users: {user_count}\nChannels: {channel_count}"))

async def bots_handler(client: Client, message: Message):
    bots = await db.get_all_bots()
    if not bots:
        return await message.reply(font_style("No bots cloned yet."))
    
    cloned_bots = [bot for bot in bots if bot['_id'] != MASTER_BOT_ID]
    if not cloned_bots:
        return await message.reply(font_style("No cloned bots found."))

    text = font_style("<b>🤖 Cloned Bots Management</b>\n\nSelect a bot to view details and manage it:")

    buttons = []
    now = datetime.now(timezone.utc)
    for bot in cloned_bots:
        username = bot.get('username', 'Unknown')
        expiry = bot.get('expiry')
        is_deactivated = bot.get('is_deactivated', False)

        status_icon = "❌" if is_deactivated else "✅"
        if expiry:
            if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now and not is_deactivated:
                status_icon = "⌛"

        buttons.append([InlineKeyboardButton(font_style(f"{status_icon} @{username}"), callback_data=f"view_bot_{bot['_id']}")])
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))

async def my_bots_handler(client: Client, message: Message):
    bots = await db.get_owner_bots(message.from_user.id)
    if not bots:
        return await message.reply(font_style("You haven't cloned any bots yet."))

    text = font_style("<b>🤖 Your Cloned Bots</b>\n\n")
    now = datetime.now(timezone.utc)
    buttons = []
    for bot in bots:
        username = bot.get('username', 'Unknown')
        expiry = bot.get('expiry')
        status = "✅ Active"
        if expiry:
            if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now: status = "❌ Expired"

        text += font_style(f"<b>Bot:</b> @{username}\n")
        text += font_style(f"<b>Status:</b> {status}\n")
        if expiry:
            text += font_style(f"<b>Expiry:</b> {expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")

        buttons.append([InlineKeyboardButton(font_style(f"Renew @{username}"), callback_data=f"renew_bot_{bot['_id']}")])

    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))

async def master_settings_handler(client: Client, message: Message):
    m_api = await db.get_global_setting("master_shortener_api")
    m_url = await db.get_global_setting("master_shortener_url")

    text = font_style(
        "<b>🌍 Global Master Settings</b>\n\n"
        f"<b>Shortener API:</b> <code>{m_api or 'Not Set'}</code>\n"
        f"<b>Shortener URL:</b> <code>{m_url or 'Not Set'}</code>\n\n"
        "To update, use:\n"
        "/set_master_api [key]\n"
        "/set_master_url [url]"
    )
    await message.reply(text)

async def set_master_api_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply(font_style("Usage: /set_master_api [key]"))
    val = message.command[1]
    await db.set_global_setting("master_shortener_api", val)
    await message.reply(font_style(f"✅ Master Shortener API set to: <code>{val}</code>"))

async def set_master_url_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply(font_style("Usage: /set_master_url [url]"))
    val = message.command[1]
    await db.set_global_setting("master_shortener_url", val)
    await message.reply(font_style(f"✅ Master Shortener URL set to: <code>{val}</code>"))

# --- Clone & Admin Commands ---

async def clone_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply(font_style("Usage: /clone BOT_TOKEN"))

    bot_count = await db.get_bot_count()
    if bot_count >= 100:
        return await message.reply(font_style("❌ Cloning limit reached (100 bots)."))

    token = message.command[1]
    try:
        # Use in_memory=True to avoid session file conflicts
        temp_client = Client(f"temp_{message.from_user.id}", api_id=API_ID, api_hash=API_HASH, bot_token=token, in_memory=True)
        await temp_client.start()
        bot_info = await temp_client.get_me()
        await temp_client.stop()

        await db.add_bot(bot_info.id, token, message.from_user.id, bot_info.username)

        # Start the new client
        new_client = Client(
            name=f"bot_{bot_info.id}",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token
        )
        register_all_handlers(new_client)
        await new_client.start()
        await set_commands(new_client)
        running_clients.append(new_client)

        await message.reply(font_style(f"✅ Bot @{bot_info.username} successfully cloned and started!"))
    except TokenInvalid:
        await message.reply(font_style("❌ Invalid bot token."))
    except Exception as e:
        await message.reply(font_style(f"❌ Error during cloning: {e}"))

async def add_admin_handler(client: Client, message: Message):
    if message.reply_to_message:
        admin_id = message.reply_to_message.from_user.id
    elif len(message.command) == 2:
        try:
            admin_id = int(message.command[1])
        except ValueError:
            return await message.reply(font_style("❌ User ID must be an integer."))
    else:
        return await message.reply(font_style("Usage: /addadmin USER_ID or reply to a message."))

    await db.add_admin(client.me.id, admin_id)
    await message.reply(font_style(f"✅ User {admin_id} added as admin for this bot."))

async def rem_admin_handler(client: Client, message: Message):
    if message.reply_to_message:
        admin_id = message.reply_to_message.from_user.id
    elif len(message.command) == 2:
        try:
            admin_id = int(message.command[1])
        except ValueError:
            return await message.reply(font_style("❌ User ID must be an integer."))
    else:
        return await message.reply(font_style("Usage: /remadmin USER_ID or reply to a message."))

    await db.remove_admin(client.me.id, admin_id)
    await message.reply(font_style(f"✅ User {admin_id} removed from admins for this bot."))

async def settings_handler(client: Client, message: Message):
    settings = await db.get_bot_settings(client.me.id)
    pic = settings.get("start_pic", START_PIC)
    if pic == "none":
        pic = None
    if pic:
        await message.reply_photo(
            pic,
            caption=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard(settings=settings)
        )
    else:
        await message.reply(
            font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard(settings=settings)
        )

async def settings_input_handler(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_markup or not isinstance(message.reply_to_message.reply_markup, ForceReply):
        return

    if message.text == "/cancel":
        return await message.reply(font_style("❌ Operation cancelled."))

    prompt = message.reply_to_message.text
    key = None
    if font_style("Start Message") in prompt: key = "start_msg"
    elif font_style("Help Message") in prompt: key = "help_msg"
    elif font_style("Start Image URL") in prompt: key = "start_pic"
    elif font_style("Button Name") in prompt: key = "btn_name"
    elif font_style("Button Text") in prompt: key = "btn_text"
    elif font_style("About Text") in prompt: key = "about_text"
    elif font_style("Support Group URL") in prompt: key = "support_url"
    elif font_style("Channel URL") in prompt: key = "channel_url"
    elif font_style("Expire Time") in prompt: key = "expire_time"
    elif font_style("Link Pic URL") in prompt: key = "link_pic"
    elif font_style("Shortener API Key") in prompt: key = "shortener_api"
    elif font_style("Shortener URL") in prompt: key = "shortener_url"

    if key:
        value = message.text
        if (key == "start_pic" or key == "link_pic") and message.photo:
            value = message.photo.file_id

        if value is None and not ((key == "start_pic" or key == "link_pic") and message.photo):
            return await message.reply(font_style("❌ Please send a valid text message."))

        if key == "expire_time":
            try:
                value = int(value)
                if value <= 0: raise ValueError
            except ValueError:
                return await message.reply(font_style("❌ Please send a valid positive number for minutes."))

        await db.update_bot_setting(client.me.id, key, value)
        await message.reply(font_style(f"✅ Successfully updated {key.replace('_', ' ').title()}!"))

async def admin_list_handler(client: Client, message: Message):
    bot = await db.get_bot(client.me.id)
    if not bot:
        return await message.reply(font_style("❌ Bot not found in database."))

    owner_id = bot.get('owner_id')
    admins = bot.get('admins', [])

    text = font_style(f"<b>👑 Owner:</b> `{owner_id}`\n\n")
    if admins:
        text += font_style("<b>👤 Admins:</b>\n")
        for admin_id in admins:
            text += f"• `{admin_id}`\n"
    else:
        text += font_style("<i>No admins added to this bot.</i>")

    await message.reply(text)

# --- Initialization ---

async def set_commands(client: Client):
    try:
        await client.set_bot_commands(BOT_COMMANDS)
    except Exception as e:
        print(f"Failed to set commands for @{client.me.username}: {e}")

def register_all_handlers(client: Client):
    client.add_handler(ChatJoinRequestHandler(join_request_handler))
    client.add_handler(MessageHandler(start_handler, filters.command("start")))
    client.add_handler(CallbackQueryHandler(callback_query_handler))
    client.add_handler(MessageHandler(settings_input_handler, filters.reply & filters.private))
    client.add_handler(MessageHandler(settings_handler, filters.command("settings") & filters.private & is_owner))
    client.add_handler(MessageHandler(clone_handler, filters.command("clone") & filters.private))
    client.add_handler(MessageHandler(my_bots_handler, filters.command("mybots") & filters.private))
    client.add_handler(MessageHandler(add_admin_handler, filters.command("addadmin") & filters.private & is_owner))
    client.add_handler(MessageHandler(rem_admin_handler, filters.command("remadmin") & filters.private & is_owner))
    client.add_handler(MessageHandler(admin_list_handler, filters.command("admin_list") & filters.private & is_owner))
    client.add_handler(MessageHandler(set_channel_handler, filters.command("setchannel") & filters.private & is_admin))
    client.add_handler(MessageHandler(delete_channel_handler, filters.command("delchannel") & filters.private & is_admin))
    client.add_handler(MessageHandler(channel_post_handler, filters.command("channelpost") & filters.private & is_admin))
    client.add_handler(MessageHandler(req_post_handler, filters.command("reqpost") & filters.private & is_admin))
    client.add_handler(MessageHandler(broadcast_handler, filters.command("broadcast") & filters.private & is_admin))
    client.add_handler(MessageHandler(users_list_handler, filters.command("users") & filters.private & is_admin))
    client.add_handler(MessageHandler(stats_handler, filters.command("stats") & filters.private & is_admin))
    client.add_handler(MessageHandler(bots_handler, filters.command(["bots", "bot"]) & filters.private & is_main_owner))
    client.add_handler(MessageHandler(master_settings_handler, filters.command("master_settings") & filters.private & is_main_owner))
    client.add_handler(MessageHandler(set_master_api_handler, filters.command("set_master_api") & filters.private & is_main_owner))
    client.add_handler(MessageHandler(set_master_url_handler, filters.command("set_master_url") & filters.private & is_main_owner))

async def start_bot(name, bot_token, owner_id=None, username=None, is_master=False):
    try:
        client = Client(
            name=name,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=bot_token
        )
        register_all_handlers(client)
        await client.start()
        await set_commands(client)
        running_clients.append(client)

        if is_master:
            global MASTER_BOT_ID
            MASTER_BOT_ID = client.me.id
            await db.add_bot(client.me.id, bot_token, ADMINS[0], client.me.username)

        print(f"{'Master' if is_master else 'Cloned'} Bot @{client.me.username} started.")
        return client
    except Exception as e:
        print(f"Failed to start bot {name}: {e}")
        return None

async def main():
    # Start Master Bot
    master_bot = await start_bot("master_bot", BOT_TOKEN, is_master=True)

    # Start Cloned Bots
    bots = await db.get_all_bots()
    tasks = []
    now = datetime.now(timezone.utc)
    for bot in bots:
        if bot['token'] == BOT_TOKEN:
            continue

        if bot.get('is_deactivated', False):
            print(f"Skipping deactivated bot @{bot.get('username')} (ID: {bot.get('_id')})")
            continue

        # Expiry check
        expiry = bot.get("expiry")
        if expiry:
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                print(f"Skipping expired bot @{bot.get('username')} (ID: {bot.get('_id')})")
                continue

        tasks.append(start_bot(f"bot_{bot['_id']}", bot['token']))

    if tasks:
        await asyncio.gather(*tasks)

    await idle()

    # Stop all clients on exit
    for client in running_clients:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
