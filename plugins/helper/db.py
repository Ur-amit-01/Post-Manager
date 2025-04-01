import motor.motor_asyncio
from config import DB_URL, DB_NAME
from datetime import datetime
import json
from typing import Dict, List
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.user  # Collection for users
        self.channels = self.db.channels  # Collection for channels
        self.formatting = self.db.formatting  # Collection for formatting templates
        self.admins = self.db.admins  # Collection for admins
        self.posts = self.db.posts  # Collection for posts
        self.backups = self.db.backups  # New collection for backups

    #============ User System ============#
    def new_user(self, id):
        return dict(
            _id=int(id),
            file_id=None,
            caption=None,
            prefix=None,
            suffix=None,
            metadata=False,
            metadata_code="By :- @Madflix_Bots",
            join_date=datetime.now()
        )

    async def add_user(self, id):
        if not await self.is_user_exist(id):
            user = self.new_user(id)
            await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'_id': int(user_id)})

    #============ Channel System ============#
    async def add_channel(self, channel_id, channel_name=None):
        channel_id = int(channel_id)
        if not await self.is_channel_exist(channel_id):
            await self.channels.insert_one({
                "_id": channel_id, 
                "name": channel_name,
                "added_at": datetime.now()
            })
            return True
        return False

    async def delete_channel(self, channel_id):
        await self.channels.delete_one({"_id": int(channel_id)})

    async def is_channel_exist(self, channel_id):
        return await self.channels.find_one({"_id": int(channel_id)}) is not None

    async def get_all_channels(self):
        return [channel async for channel in self.channels.find({})]

    #============ Post System ============#
    async def save_post(self, post_id, messages):
        try:
            await self.posts.update_one(
                {"_id": post_id},
                {"$set": {
                    "messages": messages,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving post: {e}")

    async def get_post(self, post_id):
        try:
            post = await self.posts.find_one({"_id": post_id})
            return post.get("messages", []) if post else []
        except Exception as e:
            logger.error(f"Error retrieving post: {e}")
            return []

    async def delete_post(self, post_id):
        try:
            await self.posts.delete_one({"_id": post_id})
        except Exception as e:
            logger.error(f"Error deleting post: {e}")

    async def get_all_posts(self):
        try:
            return [post async for post in self.posts.find({})]
        except Exception as e:
            logger.error(f"Error retrieving posts: {e}")
            return []

    #============ Backup & Restore System ============#
    async def create_backup(self, backup_name: str = None) -> Dict:
        """
        Create a complete backup of all collections
        Returns backup data as dictionary
        """
        try:
            backup_data = {
                "metadata": {
                    "backup_time": datetime.now().isoformat(),
                    "backup_name": backup_name or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "database": DB_NAME
                },
                "users": [user async for user in self.col.find({})],
                "channels": [channel async for channel in self.channels.find({})],
                "posts": [post async for post in self.posts.find({})],
                "admins": [admin async for admin in self.admins.find({})],
                "formatting": [template async for template in self.formatting.find({})]
            }

            # Store backup in database
            await self.backups.insert_one({
                "_id": backup_data["metadata"]["backup_name"],
                "data": backup_data,
                "created_at": datetime.now()
            })

            return backup_data
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return {}

    async def restore_backup(self, backup_data: Dict) -> bool:
        """
        Restore database from backup data
        Returns True if successful, False otherwise
        """
        try:
            # Clear existing collections
            await self.col.delete_many({})
            await self.channels.delete_many({})
            await self.posts.delete_many({})
            await self.admins.delete_many({})
            await self.formatting.delete_many({})

            # Restore data
            if "users" in backup_data:
                await self.col.insert_many(backup_data["users"])
            if "channels" in backup_data:
                await self.channels.insert_many(backup_data["channels"])
            if "posts" in backup_data:
                await self.posts.insert_many(backup_data["posts"])
            if "admins" in backup_data:
                await self.admins.insert_many(backup_data["admins"])
            if "formatting" in backup_data:
                await self.formatting.insert_many(backup_data["formatting"])

            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def get_backup(self, backup_name: str) -> Dict:
        """Retrieve a backup by its name"""
        try:
            backup = await self.backups.find_one({"_id": backup_name})
            return backup.get("data", {}) if backup else {}
        except Exception as e:
            logger.error(f"Error getting backup: {e}")
            return {}

    async def list_backups(self) -> List[Dict]:
        """List all available backups"""
        try:
            return [
                {
                    "name": backup["_id"],
                    "created_at": backup["created_at"],
                    "size": len(str(backup["data"]))
                }
                async for backup in self.backups.find({})
            ]
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

# Initialize the database
db = Database(DB_URL, DB_NAME)
