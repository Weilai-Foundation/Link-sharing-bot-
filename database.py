from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

class Database:
    def __init__(self, uri, db_name):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.bots = self.db['bots']
        self.users = self.db['users']
        self.channels = self.db['channels']

    # Bot management
    async def add_bot(self, bot_id, token, owner_id, username):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$set": {"token": token, "owner_id": owner_id, "username": username}},
            upsert=True
        )

    async def get_bot(self, bot_id):
        return await self.bots.find_one({"_id": bot_id})

    async def get_all_bots(self):
        return await self.bots.find().to_list(length=None)

    async def get_bot_count(self):
        return await self.bots.count_documents({})

    async def get_bot_settings(self, bot_id):
        bot = await self.get_bot(bot_id)
        if bot:
            return bot.get('settings', {})
        return {}

    async def update_bot_setting(self, bot_id, key, value):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$set": {f"settings.{key}": value}}
        )

    async def unset_bot_setting(self, bot_id, key):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$unset": {f"settings.{key}": ""}}
        )

    async def add_admin(self, bot_id, admin_id):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$addToSet": {"admins": admin_id}},
            upsert=True
        )

    async def remove_admin(self, bot_id, admin_id):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$pull": {"admins": admin_id}},
            upsert=True
        )

    async def is_admin(self, bot_id, user_id, global_admins):
        if user_id in global_admins:
            return True
        bot = await self.get_bot(bot_id)
        if bot:
            if user_id == bot.get('owner_id') or user_id in bot.get('admins', []):
                return True
        return False

    async def is_owner(self, bot_id, user_id, global_admins):
        if user_id in global_admins:
            return True
        bot = await self.get_bot(bot_id)
        if bot:
            if user_id == bot.get('owner_id'):
                return True
        return False

    # User management
    async def update_user(self, bot_id, user_id, name):
        await self.users.update_one(
            {"_id": f"{bot_id}_{user_id}"},
            {"$set": {"bot_id": bot_id, "user_id": user_id, "name": name}},
            upsert=True
        )

    async def get_user_count(self, bot_id):
        return await self.users.count_documents({"bot_id": bot_id})

    async def get_users(self, bot_id):
        return self.users.find({"bot_id": bot_id})

    # Channel management
    async def update_channel(self, bot_id, chat_id, title, username, chat_type):
        await self.channels.update_one(
            {"_id": f"{bot_id}_{chat_id}"},
            {"$set": {
                "bot_id": bot_id,
                "chat_id": chat_id,
                "title": title,
                "username": username,
                "type": chat_type
            }},
            upsert=True
        )

    async def delete_channel(self, bot_id, chat_id):
        return await self.channels.delete_one({"_id": f"{bot_id}_{chat_id}"})

    async def get_channel(self, bot_id, chat_id=None, username=None):
        if chat_id:
            return await self.channels.find_one({"_id": f"{bot_id}_{chat_id}"})
        if username:
            if username.startswith("@"):
                username = username[1:]
            return await self.channels.find_one({"bot_id": bot_id, "username": username})
        return None

    async def get_all_channels(self, bot_id):
        return await self.channels.find({"bot_id": bot_id}).to_list(length=None)

    async def get_channel_count(self, bot_id):
        return await self.channels.count_documents({"bot_id": bot_id})

db = Database(MONGO_URI, "invite_bot")
