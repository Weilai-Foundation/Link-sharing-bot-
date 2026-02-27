from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.errors import TokenInvalid, FloodWait
import asyncio
from datetime import datetime, timedelta, timezone

from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, START_PIC, LINK_PIC
from database import db
from utils import encode_channel_id, decode_channel_id, font_style

# Global list to store all clients
running_clients = []

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

def get_settings_keyboard():
    """Returns the keyboard for settings menu"""
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
        await callback_query.message.edit_caption(
            caption=about_text,
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
        await callback_query.message.edit_caption(
            caption=help_text,
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
        await callback_query.message.edit_caption(
            caption=start_text,
            reply_markup=get_start_keyboard(is_admin=is_adm, settings=settings)
        )
    
    elif data == "settings":
        await callback_query.message.edit_caption(
            caption=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard()
        )

    elif data == "remove_pic":
        await callback_query.message.edit_caption(
            caption=font_style("<b>🗑️ Remove Picture</b>\n\nChoose which picture you want to remove:"),
            reply_markup=get_remove_pic_keyboard()
        )

    elif data.startswith("del_"):
        key = "start_pic" if "start_pic" in data else "link_pic"
        await db.unset_bot_setting(client.me.id, key)
        await callback_query.answer(font_style(f"✅ Successfully removed {key.replace('_', ' ').title()}!"), show_alert=True)
        await callback_query.message.edit_caption(
            caption=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard()
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
            "set_link_pic": "Send the new Link Pic URL or photo."
        }

        prompt_text = prompts.get(data, "Send the new value.")

        await callback_query.message.reply_text(
            font_style(f"<b>{prompt_text}</b>\n\nUse /cancel to abort."),
            reply_markup=ForceReply(selective=True)
        )

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
            text = settings.get("btn_text")
            if text:
                text = font_style(text)
            else:
                text = font_style("Request to Join: powered by @Vecna_Bots\n<i>This link requires admin approval. Only you can use it.</i>")

            pic = settings.get("link_pic", settings.get("start_pic", LINK_PIC or START_PIC))

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
                        [[InlineKeyboardButton(btn_name, url=invite.invite_link)]]
                    )
                )
            else:
                sent = await message.reply(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(btn_name, url=invite.invite_link)]]
                    ),
                    disable_web_page_preview=True
                )

            expire_time = settings.get("expire_time", 10)
            await asyncio.sleep(expire_time * 60)
            try:
                await client.revoke_chat_invite_link(channel_id, invite.invite_link)
            except:
                pass
            try:
                await sent.delete()
            except:
                pass
        else:
            expire_time = settings.get("expire_time", 10)
            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                expire_date=datetime.now(timezone.utc) + timedelta(minutes=expire_time),
                member_limit=1
            )
            text = settings.get("btn_text")
            if text:
                text = font_style(text)
            else:
                text = font_style("Here is your link! Click below to proceed: powered by :- @Vecna_Bots ")

            pic = settings.get("link_pic", settings.get("start_pic", LINK_PIC or START_PIC))

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
                        [[InlineKeyboardButton(btn_name, url=invite.invite_link)]]
                    )
                )
            else:
                sent = await message.reply(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(btn_name, url=invite.invite_link)]]
                    ),
                    disable_web_page_preview=True
                )
            await asyncio.sleep(expire_time * 60)
            try:
                await client.revoke_chat_invite_link(channel_id, invite.invite_link)
            except:
                pass
            try:
                await sent.delete()
            except:
                pass
    except Exception as e:
        await message.reply(font_style(f"Failed to generate invite: {e}"))

async def broadcast_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply(font_style("Reply to a message to broadcast it."))

    msg = await message.reply(font_style("Broadcasting..."))
    users = await db.get_users(client.me.id)
    success, failed = 0, 0

    async for user in users:
        try:
            await client.copy_message(user['user_id'], message.chat.id, message.reply_to_message.id)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.copy_message(user['user_id'], message.chat.id, message.reply_to_message.id)
            success += 1
        except Exception:
            failed += 1

        if (success + failed) % 20 == 0:
            try:
                await msg.edit(font_style(f"Broadcasting...\n\nSent: {success}\nFailed: {failed}"))
            except Exception:
                pass

    await msg.edit(font_style(f"<b>Broadcast completed.</b>\n\nTotal: {success + failed}\nSent: {success}\nFailed: {failed}"))

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
        await message.reply(font_style(
            f"{chat.type.name.title()} '{chat.title}' registered.\n"
            f"ID: `{chat.id}`\n"
            f"Username: @{chat.username if chat.username else 'N/A'}"
        ))
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
    
    text = font_style("<b>Cloned Bots:</b>\n\n")
    for i, bot in enumerate(bots, 1):
        username = bot.get('username', 'Unknown')
        text += font_style(f"{i}. @{username}\n")
    
    await message.reply(text)

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
    if pic:
        await message.reply_photo(
            pic,
            caption=font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard()
        )
    else:
        await message.reply(
            font_style("<b>⚙️ Bot Settings</b>\n\nChoose what you want to configure:"),
            reply_markup=get_settings_keyboard()
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

def register_all_handlers(client: Client):
    client.add_handler(MessageHandler(start_handler, filters.command("start")))
    client.add_handler(CallbackQueryHandler(callback_query_handler))
    client.add_handler(MessageHandler(settings_input_handler, filters.reply & filters.private))
    client.add_handler(MessageHandler(settings_handler, filters.command("settings") & filters.private & is_owner))
    client.add_handler(MessageHandler(clone_handler, filters.command("clone") & filters.private))
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

async def main():
    # Start Master Bot
    master_bot = Client(
        "master_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    register_all_handlers(master_bot)
    await master_bot.start()
    running_clients.append(master_bot)
    await db.add_bot(master_bot.me.id, BOT_TOKEN, ADMINS[0], master_bot.me.username)
    print(f"Master Bot @{master_bot.me.username} started.")

    # Start Cloned Bots
    bots = await db.get_all_bots()
    for bot in bots:
        if bot['token'] == BOT_TOKEN:
            continue
        try:
            client = Client(
                name=f"bot_{bot['_id']}",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=bot['token']
            )
            register_all_handlers(client)
            await client.start()
            running_clients.append(client)
            print(f"Cloned Bot @{client.me.username} started.")
        except Exception as e:
            print(f"Failed to start bot {bot['_id']}: {e}")

    await idle()

    # Stop all clients on exit
    for client in running_clients:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
