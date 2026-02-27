import asyncio
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid
from database import db
from utils import font_style

async def broadcast_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply(font_style("Reply to a message to broadcast it."))

    msg = await message.reply(font_style("⚡ Broadcasting..."))
    users = await db.get_users(client.me.id)
    total = await db.get_user_count(client.me.id)
    success, failed = 0, 0

    async for user in users:
        user_id = user['user_id']
        tries = 0
        done = False
        while tries < 3 and not done:
            try:
                await client.copy_message(user_id, message.chat.id, message.reply_to_message.id)
                success += 1
                done = True
            except FloodWait as e:
                await asyncio.sleep(e.value)
                tries += 1
            except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
                await db.delete_user(client.me.id, user_id)
                failed += 1
                done = True
            except Exception:
                failed += 1
                done = True

        if not done: # Reached max retries for FloodWait
            failed += 1

        if (success + failed) % 20 == 0:
            percentage = (success + failed) * 100 / total if total > 0 else 0
            try:
                await msg.edit(font_style(
                    f"⚡ Broadcasting...\n\n"
                    f"✅ Sent: {success}\n"
                    f"❌ Failed: {failed}\n"
                    f"📊 Progress: {percentage:.1f}%"
                ))
            except Exception:
                pass

    await msg.edit(font_style(
        f"<b>✅ Broadcast Completed!</b>\n\n"
        f"👥 Total Users: {total}\n"
        f"🎉 Successful: {success}\n"
        f"🚫 Failed: {failed}"
    ))
