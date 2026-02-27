from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
from config import MONGO_URI

class Database:
    def __init__(self, uri, db_name):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.bots = self.db['bots']
        self.users = self.db['users']
        self.channels = self.db['channels']
        self.settings = self.db['settings']
        self.tokens = self.db['tokens']
        self._settings_cache = {}

    # Bot management
    async def add_bot(self, bot_id, token, owner_id, username):
        expiry = datetime.now(timezone.utc) + timedelta(days=7)
        await self.bots.update_one(
            {"_id": bot_id},
            {"$set": {
                "token": token,
                "owner_id": owner_id,
                "username": username,
                "expiry": expiry,
                "is_deactivated": False
            }},
            upsert=True
        )

    async def update_bot_status(self, bot_id, is_deactivated):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$set": {"is_deactivated": is_deactivated}}
        )

    async def get_bot(self, bot_id):
        return await self.bots.find_one({"_id": bot_id})

    async def get_all_bots(self):
        return await self.bots.find().to_list(length=None)

    async def get_owner_bots(self, owner_id):
        return await self.bots.find({"owner_id": owner_id}).to_list(length=None)

    async def update_bot_expiry(self, bot_id, expiry_date):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$set": {"expiry": expiry_date}}
        )

    async def get_bot_count(self):
        return await self.bots.count_documents({})

    async def get_bot_settings(self, bot_id):
        if bot_id in self._settings_cache:
            return self._settings_cache[bot_id]

        bot = await self.get_bot(bot_id)
        if bot:
            settings = bot.get('settings', {})
            self._settings_cache[bot_id] = settings
            return settings
        return {}

    async def update_bot_setting(self, bot_id, key, value):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$set": {f"settings.{key}": value}}
        )
        if bot_id in self._settings_cache:
            self._settings_cache[bot_id][key] = value

    async def unset_bot_setting(self, bot_id, key):
        await self.bots.update_one(
            {"_id": bot_id},
            {"$unset": {f"settings.{key}": ""}}
        )
        if bot_id in self._settings_cache:
            self._settings_cache[bot_id].pop(key, None)

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

    async def delete_user(self, bot_id, user_id):
        return await self.users.delete_one({"_id": f"{bot_id}_{user_id}"})

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

    # Global settings
    async def set_global_setting(self, key, value):
        await self.settings.update_one(
            {"_id": key},
            {"$set": {"value": value}},
            upsert=True
        )

    async def get_global_setting(self, key):
        setting = await self.settings.find_one({"_id": key})
        return setting["value"] if setting else None

    # Token management
    async def create_renewal_token(self, bot_id, user_id):
        import uuid
        token = str(uuid.uuid4())
        await self.tokens.insert_one({
            "token": token,
            "bot_id": bot_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc)
        })
        # Ensure TTL index
        await self.tokens.create_index("created_at", expireAfterSeconds=600)
        return token

    async def verify_renewal_token(self, token):
        res = await self.tokens.find_one({"token": token})
        if res:
            await self.tokens.delete_one({"token": token})
            return res
        return None

db = Database(MONGO_URI, "invite_bot")
