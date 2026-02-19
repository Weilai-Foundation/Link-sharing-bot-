from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler
from pyrogram.errors import TokenInvalid
import asyncio
from datetime import datetime, timedelta, timezone

from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, START_PIC, LINK_PIC
from database import db
from utils import encode_channel_id, decode_channel_id

# Global list to store all clients
running_clients = []

# --- Filters ---

async def is_admin_filter(_, client, message: Message):
    return db.is_admin(client.me.id, message.from_user.id, ADMINS)

async def is_owner_filter(_, client, message: Message):
    return db.is_owner(client.me.id, message.from_user.id, ADMINS)

is_admin = filters.create(is_admin_filter)
is_owner = filters.create(is_owner_filter)

# --- Handlers ---

async def start_handler(client: Client, message: Message):
    db.update_user(client.me.id, message.from_user.id, message.from_user.first_name)
    args = message.text.split(" ", 1)
    start_text = ("<b><blockquote>𝖡𝖺𝗄𝗄𝖺 {mention}!\n\n𝖨’𝗆 𝗍𝗁𝖾 𝖢𝗁𝖺𝗇𝗇𝖾𝗅 𝖫𝗂𝗇𝗄 𝖡𝗈𝗍 — 𝖨 𝖼𝗋𝖾𝖺𝗍𝖾 𝗌𝗆𝖺𝗋𝗍 𝗋𝖾𝖽𝗂𝗋𝖾𝖼𝗍 𝗅𝗂𝗇𝗄𝗌 𝖿𝗈𝗋 𝗒𝗈𝗎𝗋 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆 𝖼𝗁𝖺𝗇𝗇𝖾𝗅𝗌 𝗍𝗈 𝗁𝖾𝗅𝗉 𝖺𝗏𝗈𝗂𝖽 𝖼𝗈𝗉𝗒𝗋𝗂𝗀𝗁𝗍 𝗉𝗋𝗈𝖻𝗅𝖾𝗆𝗌 𝖺𝗇𝖽 𝗄𝖾𝖾𝗉 𝗍𝗁𝗂𝗇𝗀𝗌 𝗌𝖺𝖿𝖾.</blockquote></b>").format(mention=message.from_user.mention)
    if len(args) == 1:
        return await message.reply_photo(
            START_PIC,
            caption=start_text
        )
    param = args[1]
    is_req = False
    if param.startswith("req_"):
        is_req = True
        param = param[4:]
    try:
        channel_id = decode_channel_id(param)
    except Exception:
        return await message.reply("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗌𝗍𝖺𝗋𝗍 𝗉𝖺𝗋𝖺𝗆𝖾𝗍𝖾𝗋.")

    ch = db.get_channel(client.me.id, chat_id=channel_id)
    if not ch:
        return await message.reply("𝖳𝗁𝗂𝗌 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗂𝗌 𝗇𝗈𝗍 𝗋𝖾𝗀𝗂𝗌𝗍𝖾𝗋𝖾𝖽 𝗐𝗂𝗍𝗁 𝗍𝗁𝖾 𝖻𝗈𝗍.")

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
            text = "𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝖩𝗈𝗂𝗇: 𝗉𝗈𝗐𝖾𝗋𝖾𝖽 𝖻𝗒 @Bots_Nation\n<i>𝖳𝗁𝗂𝗌 𝗅𝗂𝗇𝗄 𝗋𝖾𝗊𝗎𝗂𝗋𝖾𝗌 𝖺𝖽𝗆𝗂𝗇 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅. 𝖮𝗇𝗅𝗒 𝗒𝗈𝗎 𝖼𝖺𝗇 𝗎𝗌𝖾 𝗂𝗍.</i>"
            pic = LINK_PIC or START_PIC
            if pic:
                sent = await message.reply_photo(
                    pic,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("「𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝖩𝗈𝗂𝗇」", url=invite.invite_link)]]
                    )
                )
            else:
                sent = await message.reply(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("「𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝖩𝗈𝗂𝗇」", url=invite.invite_link)]]
                    ),
                    disable_web_page_preview=True
                )
            await asyncio.sleep(600)
            try:
                await client.revoke_chat_invite_link(channel_id, invite.invite_link)
            except:
                pass
            try:
                await sent.delete()
            except:
                pass
        else:
            invite = await client.create_chat_invite_link(
                chat_id=channel_id,
                expire_date=datetime.now(timezone.utc) + timedelta(minutes=10),
                member_limit=1
            )
            text = "𝖧𝖾𝗋𝖾 𝗂𝗌 𝗒𝗈𝗎𝗋 𝗅𝗂𝗇𝗄! 𝖢𝗅𝗂𝖼𝗄 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗉𝗋𝗈𝖼𝖾𝖾𝗅: 𝗉𝗈𝗐𝖾𝗋𝖾𝖽 𝖻𝗒 @Bots_Nation"
            pic = LINK_PIC or START_PIC
            if pic:
                sent = await message.reply_photo(
                    pic,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("「𝖩𝗈𝗂𝗇 𝖢𝗁𝖺𝗇𝗇𝖾𝗅」", url=invite.invite_link)]]
                    )
                )
            else:
                sent = await message.reply(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("「𝖩𝗈𝗂𝗇 𝖢𝗁𝖺𝗇𝗇𝖾𝗅」", url=invite.invite_link)]]
                    ),
                    disable_web_page_preview=True
                )
            await asyncio.sleep(600)
            try:
                await client.revoke_chat_invite_link(channel_id, invite.invite_link)
            except:
                pass
            try:
                await sent.delete()
            except:
                pass
    except Exception as e:
        await message.reply(f"𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝗂𝗇𝗏𝗂𝗍𝖾: {e}")

async def broadcast_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply("𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗈 𝖻𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝗂𝗍.")

    users = db.get_users(client.me.id)
    success, failed = 0, 0
    for user in users:
        try:
            await client.copy_message(user['user_id'], message.chat.id, message.reply_to_message.id)
            success += 1
        except:
            failed += 1
    await message.reply(f"𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝖼𝗈𝗆𝗉𝗅𝖾𝗍𝖾𝖽.\n𝖲𝖾𝗇𝗍: {success}\n𝖥𝖺𝗂𝗅𝖾𝖽: {failed}")

async def users_list_handler(client: Client, message: Message):
    count = db.get_user_count(client.me.id)
    await message.reply(f"𝖳𝗈𝗍𝖺𝗅 𝗎𝗌𝖾𝗋𝗌: {count}")

async def set_channel_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("𝖴𝗌𝖺𝗀𝖾: /setchannel @username 𝗈𝗋 /setchannel -1001234567890")

    target = message.command[1]
    if target.startswith("@"):
        chat_ref = target
    else:
        try:
            chat_ref = int(target)
        except ValueError:
            return await message.reply("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗂𝖽𝖾𝗇𝗍𝗂𝖿𝗂𝖾𝗋.")

    try:
        chat = await client.get_chat(chat_ref)
        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP]:
            return await message.reply(
                f"𝖴𝗇𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽 𝖼𝗁𝖺𝗍 𝗍𝗒𝗉𝖾: `{chat.type}`.\n"
                "𝖮𝗇𝗅𝗒 𝖼𝗁𝖺𝗇𝗇𝖾𝗅𝗌, 𝗀𝗋𝗈𝗎𝗉𝗌, 𝖺𝗇𝖽 𝗌𝗎𝗉𝖾𝗋𝗀𝗋𝗈𝗎𝗉𝗌 𝖺𝗋𝖾 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽.\n"
                "𝖬𝖺𝗄𝖾 𝗌𝗎𝗋𝖾 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗂𝗌 𝖺 𝗆𝖾𝗆𝖻𝖾𝗋/𝖺𝖽𝗆𝗂𝗇 𝗈𝖿 𝗍𝗁𝖾 𝗍𝖺𝗋𝗀𝖾𝗍."
            )
        db.update_channel(client.me.id, chat.id, chat.title, chat.username, str(chat.type))
        await message.reply(
            f"{chat.type.name.title()} '{chat.title}' 𝗋𝖾𝗀𝗂𝗌𝗍𝖾𝗋𝖾𝖽.\n"
            f"𝖨𝖣: `{chat.id}`\n"
            f"𝖴𝗌𝖾𝗋𝗇𝖺𝗆𝖾: @{chat.username if chat.username else 'N/A'}"
        )
    except Exception as e:
        await message.reply(
            f"𝖤𝗋𝗋𝗈𝗋: {e}\n"
            "𝖬𝖺𝗄𝖾 𝗌𝗎𝗋𝖾 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗂𝗌 𝖺 𝗆𝖾𝗆𝖻𝖾𝗋/𝖺𝖽𝗆𝗂𝗇 𝗈𝖿 𝗍𝗁𝖾 𝗍𝖺𝗋𝗀𝖾𝗍 𝖺𝗇𝖽 𝗍𝗁𝖾 𝖨𝖣/𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾 𝗂𝗌 𝖼𝗈𝗋𝗋𝖾𝖼𝗍."
        )

async def delete_channel_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("𝖴𝗌𝖺𝗀𝖾: /delchannel @username 𝗈𝗋 /delchannel -1001234567890")

    target = message.command[1]
    if target.startswith("@"):
        chat_ref = target
    else:
        try:
            chat_ref = int(target)
        except ValueError:
            return await message.reply("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗂𝖽𝖾𝗇𝗍𝗂𝖿𝗂𝖾𝗋.")

    try:
        chat = await client.get_chat(chat_ref)
        result = db.delete_channel(client.me.id, chat.id)
        if result.deleted_count:
            await message.reply(f"{chat.type.name.title()} '{chat.title}' 𝗋𝖾𝗆𝗈𝗏𝖾𝖽.")
        else:
            await message.reply("𝖢𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.")
    except Exception as e:
        await message.reply(f"Error: {e}")

async def channel_post_handler(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) == 2:
        target = args[1]
        ch = None
        if target.startswith("@"):
            ch = db.get_channel(client.me.id, username=target)
        else:
            try:
                ch = db.get_channel(client.me.id, chat_id=int(target))
            except Exception:
                return await message.reply("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗂𝖽𝖾𝗇𝗍𝗂𝖿𝗂𝖾𝗋.")
        if not ch:
            return await message.reply("𝖢𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.")
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start={encoded}"
            await message.reply(
                f"𝖳𝖾𝗆𝗉𝗈𝗋𝖺𝗋𝗒 𝗃𝗈𝗂𝗇 𝗅𝗂𝗇𝗄 𝖿𝗈𝗋 <b>{ch.get('title', ch.get('username', ch['chat_id']))}</b>:\n"
                f"<a href='{link}'>𝖢𝗅𝗂𝖼𝗄 𝗁𝖾𝗋𝖾</a>",
                disable_web_page_preview=True
            )
        except Exception as e:
            await message.reply(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}")
        return

    registered = db.get_all_channels(client.me.id)
    links = []
    for ch in registered:
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start={encoded}"
            links.append(f"<b>{ch.get('title', ch.get('username', ch['chat_id']))}</b>: <a href='{link}'>𝖢𝗅𝗂𝖼𝗄 𝗁𝖾𝗋𝖾</a>")
        except Exception as e:
            links.append(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}")

    if not links:
        return await message.reply("𝖭𝗈 𝖼𝗁𝖺𝗇𝗇𝖾𝗅𝗌 𝗋𝖾𝗀𝗂𝗌𝗍𝖾𝗋𝖾𝖽.")
    await message.reply("\n".join(links), disable_web_page_preview=True)

async def req_post_handler(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) == 2:
        target = args[1]
        ch = None
        if target.startswith("@"):
            ch = db.get_channel(client.me.id, username=target)
        else:
            try:
                ch = db.get_channel(client.me.id, chat_id=int(target))
            except Exception:
                return await message.reply("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗂𝖽𝖾𝗇𝗍𝗂𝖿𝗂𝖾𝗋.")
        if not ch:
            return await message.reply("𝖢𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.")
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start=req_{encoded}"
            await message.reply(
                f"𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝗃𝗈𝗂𝗇 𝗅𝗂𝗇𝗄 𝖿𝗈𝗋 <b>{ch.get('title', ch.get('username', ch['chat_id']))}</b> (𝗋𝖾𝗊𝗎𝗂𝗋𝖾𝗌 𝖺𝖽𝗆𝗂𝗇 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅):\n"
                f"<a href='{link}'>𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝖩𝗈𝗂𝗇</a>\n\n"
                f"<i>𝖬𝖺𝗄𝖾 𝗌𝗎𝗋𝖾 '𝖠𝗉𝗉𝗋𝗈𝗏𝖾 𝗇𝖾𝗐 𝗆𝖾𝗆𝖻𝖾𝗋𝗌' 𝗂𝗌 𝖾𝗇𝖺𝖻𝗅𝖾𝖽 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗌𝖾𝗍𝗍𝗂𝗇𝗀𝗌 𝖿𝗈𝗋 𝗃𝗈𝗂𝗇 𝗋𝖾𝗊𝗎𝖾𝗌𝗍𝗌 𝗍𝗈 𝗐𝗈𝗋𝗄.</i>",
                disable_web_page_preview=True
            )
        except Exception as e:
            await message.reply(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}")
        return

    registered = db.get_all_channels(client.me.id)
    links = []
    for ch in registered:
        try:
            encoded = encode_channel_id(ch['chat_id'])
            link = f"https://t.me/{client.me.username}?start=req_{encoded}"
            links.append(
                f"<b>{ch.get('title', ch.get('username', ch['chat_id']))}</b>: <a href='{link}'>𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝖩𝗈𝗂𝗇</a> (𝗋𝖾𝗊𝗎𝗂𝗋𝖾𝗌 𝖺𝖽𝗆𝗂𝗇 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅)"
            )
        except Exception as e:
            links.append(f"❌ {ch.get('username', ch.get('title', ch['chat_id']))}: {e}")

    if not links:
        return await message.reply("𝖭𝗈 𝖼𝗁𝖺𝗇𝗇𝖾𝗅𝗌 𝗋𝖾𝗀𝗂𝗌𝗍𝖾𝗋𝖾𝖽.")
    await message.reply("\n".join(links) + "\n\n<i>𝖬𝖺𝗄𝖾 𝗌𝗎𝗋𝖾 '𝖠𝗉𝗉𝗋𝗈𝗏𝖾 𝗇𝖾𝗐 𝗆𝖾𝗆𝖻𝖾𝗋𝗌' 𝗂𝗌 𝖾𝗇𝖺𝖻𝗅𝖾𝖽 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗇𝗇𝖾𝗅/𝗀𝗋𝗈𝗎𝗉 𝗌𝖾𝗍𝗍𝗂𝗇𝗀𝗌 𝖿𝗈𝗋 𝗃𝗈𝗂𝗇 𝗋𝖾𝗊𝗎𝖾𝗌𝗍𝗌 𝗍𝗈 𝗐𝗈𝗋𝗄.</i>", disable_web_page_preview=True)

async def stats_handler(client: Client, message: Message):
    user_count = db.get_user_count(client.me.id)
    channel_count = db.get_channel_count(client.me.id)
    await message.reply(f"𝖴𝗌𝖾𝗋𝗌: {user_count}\n𝖢𝗁𝖺𝗇𝗇𝖾𝗅𝗌: {channel_count}")

# --- Clone & Admin Commands ---

async def clone_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("𝖴𝗌𝖺𝗀𝖾: /clone BOT_TOKEN")

    token = message.command[1]
    try:
        # Use in_memory=True to avoid session file conflicts
        temp_client = Client(f"temp_{message.from_user.id}", api_id=API_ID, api_hash=API_HASH, bot_token=token, in_memory=True)
        await temp_client.start()
        bot_info = await temp_client.get_me()
        await temp_client.stop()

        db.add_bot(bot_info.id, token, message.from_user.id)

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

        await message.reply(f"✅ Bot @{bot_info.username} successfully cloned and started!")
    except TokenInvalid:
        await message.reply("❌ Invalid bot token.")
    except Exception as e:
        await message.reply(f"❌ Error during cloning: {e}")

async def add_admin_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("𝖴𝗌𝖺𝗀𝖾: /addadmin USER_ID")

    try:
        admin_id = int(message.command[1])
        db.add_admin(client.me.id, admin_id)
        await message.reply(f"✅ User {admin_id} added as admin for this bot.")
    except ValueError:
        await message.reply("❌ User ID must be an integer.")

async def rem_admin_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply("𝖴𝗌𝖺𝗀𝖾: /remadmin USER_ID")

    try:
        admin_id = int(message.command[1])
        db.remove_admin(client.me.id, admin_id)
        await message.reply(f"✅ User {admin_id} removed from admins for this bot.")
    except ValueError:
        await message.reply("❌ User ID must be an integer.")

# --- Initialization ---

def register_all_handlers(client: Client):
    client.add_handler(MessageHandler(start_handler, filters.command("start")))
    client.add_handler(MessageHandler(clone_handler, filters.command("clone") & filters.private))
    client.add_handler(MessageHandler(add_admin_handler, filters.command("addadmin") & filters.private & is_owner))
    client.add_handler(MessageHandler(rem_admin_handler, filters.command("remadmin") & filters.private & is_owner))
    client.add_handler(MessageHandler(set_channel_handler, filters.command("setchannel") & filters.private & is_admin))
    client.add_handler(MessageHandler(delete_channel_handler, filters.command("delchannel") & filters.private & is_admin))
    client.add_handler(MessageHandler(channel_post_handler, filters.command("channelpost") & filters.private & is_admin))
    client.add_handler(MessageHandler(req_post_handler, filters.command("reqpost") & filters.private & is_admin))
    client.add_handler(MessageHandler(broadcast_handler, filters.command("broadcast") & filters.private & is_admin))
    client.add_handler(MessageHandler(users_list_handler, filters.command("users") & filters.private & is_admin))
    client.add_handler(MessageHandler(stats_handler, filters.command("stats") & filters.private & is_admin))

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
    print(f"Master Bot @{master_bot.me.username} started.")

    # Start Cloned Bots
    bots = db.get_all_bots()
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
