from pymongo import MongoClient
from config import MONGO_URI

class Database:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.bots = self.db['bots']
        self.users = self.db['users']
        self.channels = self.db['channels']

    # Bot management
    def add_bot(self, bot_id, token, owner_id):
        self.bots.update_one(
            {"_id": bot_id},
            {"$set": {"token": token, "owner_id": owner_id}},
            upsert=True
        )

    def get_bot(self, bot_id):
        return self.bots.find_one({"_id": bot_id})

    def get_all_bots(self):
        return list(self.bots.find())

    def add_admin(self, bot_id, admin_id):
        self.bots.update_one(
            {"_id": bot_id},
            {"$addToSet": {"admins": admin_id}}
        )

    def remove_admin(self, bot_id, admin_id):
        self.bots.update_one(
            {"_id": bot_id},
            {"$pull": {"admins": admin_id}}
        )

    def is_admin(self, bot_id, user_id, global_admins):
        if user_id in global_admins:
            return True
        bot = self.get_bot(bot_id)
        if bot:
            if user_id == bot.get('owner_id') or user_id in bot.get('admins', []):
                return True
        return False

    def is_owner(self, bot_id, user_id, global_admins):
        if user_id in global_admins:
            return True
        bot = self.get_bot(bot_id)
        if bot:
            if user_id == bot.get('owner_id'):
                return True
        return False

    # User management
    def update_user(self, bot_id, user_id, name):
        self.users.update_one(
            {"_id": f"{bot_id}_{user_id}"},
            {"$set": {"bot_id": bot_id, "user_id": user_id, "name": name}},
            upsert=True
        )

    def get_user_count(self, bot_id):
        return self.users.count_documents({"bot_id": bot_id})

    def get_users(self, bot_id):
        return self.users.find({"bot_id": bot_id})

    # Channel management
    def update_channel(self, bot_id, chat_id, title, username, chat_type):
        self.channels.update_one(
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

    def delete_channel(self, bot_id, chat_id):
        return self.channels.delete_one({"_id": f"{bot_id}_{chat_id}"})

    def get_channel(self, bot_id, chat_id=None, username=None):
        if chat_id:
            return self.channels.find_one({"_id": f"{bot_id}_{chat_id}"})
        if username:
            if username.startswith("@"):
                username = username[1:]
            return self.channels.find_one({"bot_id": bot_id, "username": username})
        return None

    def get_all_channels(self, bot_id):
        return list(self.channels.find({"bot_id": bot_id}))

    def get_channel_count(self, bot_id):
        return self.channels.count_documents({"bot_id": bot_id})

db = Database(MONGO_URI, "invite_bot")
