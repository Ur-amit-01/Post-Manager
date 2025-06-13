import motor.motor_asyncio
import time
from datetime import datetime
from config import DB_URL, DB_NAME
from typing import List, Dict, Optional, Union
import math

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.user
        self.channels = self.db.channels
        self.formatting = self.db.formatting
        self.admins = self.db.admins  # Dedicated admin collection
        self.posts = self.db.posts
        self.settings = self.db.settings
        self.logs = self.db.logs

    # ============ User System ============ #
    def new_user(self, id):
        return dict(
            _id=int(id),
            file_id=None,
            caption=None,
            prefix=None,
            suffix=None,
            metadata=False,
            metadata_code="By :- @Madflix_Bots",
            join_date=datetime.now(),
            last_active=datetime.now()
        )

    async def add_user(self, id):
        if not await self.is_user_exist(id):
            user = self.new_user(id)
            await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'_id': int(id)})
        return bool(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def get_all_users(self):
        return [user async for user in self.col.find({})]

    async def delete_user(self, user_id):
        await self.col.delete_many({'_id': int(user_id)})

    # ============ Admin System ============ #
    async def add_admin(self, user_id: int, admin_data: Optional[Dict] = None):
        """Add or update an admin with additional metadata"""
        admin_data = admin_data or {}
        admin_data.update({
            "_id": user_id,
            "is_admin": True,
            "added_at": datetime.now(),
            "last_active": datetime.now()
        })
        await self.admins.update_one(
            {"_id": user_id},
            {"$set": admin_data},
            upsert=True
        )

    async def remove_admin(self, user_id: int):
        """Remove admin privileges"""
        await self.admins.delete_one({"_id": user_id})

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin with proper error handling"""
        try:
            admin = await self.admins.find_one({"_id": user_id})
            return admin is not None and admin.get("is_admin", False)
        except Exception as e:
            await self.log_error(f"Admin check error for {user_id}: {e}")
            return False

    async def get_admin(self, user_id: int) -> Optional[Dict]:
        """Get full admin data"""
        return await self.admins.find_one({"_id": user_id})

    async def get_all_admins(self) -> List[Dict]:
        """List all admins with their details"""
        return [admin async for admin in self.admins.find({"is_admin": True})]

    async def update_admin_activity(self, user_id: int):
        """Update admin's last active time"""
        await self.admins.update_one(
            {"_id": user_id},
            {"$set": {"last_active": datetime.now()}}
        )

    # ============ Channel System ============ #
    async def add_channel(self, channel_id, channel_name=None):
        channel_id = int(channel_id)
        if not await self.is_channel_exist(channel_id):
            await self.channels.insert_one({
                "_id": channel_id, 
                "name": channel_name,
                "added_date": datetime.now(),
                "post_count": 0,
                "last_post": None
            })
            return True
        return False

    async def delete_channel(self, channel_id):
        await self.channels.delete_one({"_id": int(channel_id)})

    async def is_channel_exist(self, channel_id):
        return await self.channels.find_one({"_id": int(channel_id)}) is not None

    async def get_all_channels(self):
        return [channel async for channel in self.channels.find({})]

    async def increment_channel_post(self, channel_id):
        await self.channels.update_one(
            {"_id": int(channel_id)},
            {
                "$inc": {"post_count": 1},
                "$set": {"last_post": datetime.now()}
            }
        )

    # ============ Post System ============ #
    async def save_post(self, post_data):
        post_data["timestamp"] = datetime.now()
        try:
            await self.posts.update_one(
                {"post_id": post_data["post_id"]},
                {"$set": post_data},
                upsert=True
            )
            return True
        except Exception as e:
            await self.log_error(f"Error saving post: {e}")
            return False

    async def get_post(self, post_id):
        try:
            return await self.posts.find_one({"post_id": post_id})
        except Exception as e:
            await self.log_error(f"Error retrieving post: {e}")
            return None

    async def delete_post(self, post_id):
        try:
            await self.posts.delete_one({"post_id": post_id})
            return True
        except Exception as e:
            await self.log_error(f"Error deleting post: {e}")
            return False

    async def get_pending_deletions(self):
        try:
            return await self.posts.find({
                "delete_after": {"$gt": time.time()}
            }).to_list(None)
        except Exception as e:
            await self.log_error(f"Error getting pending deletions: {e}")
            return []

    async def remove_channel_post(self, post_id, channel_id):
        try:
            result = await self.posts.update_one(
                {"post_id": post_id},
                {"$pull": {"channels": {"channel_id": channel_id}}}
            )
            return result.modified_count > 0
        except Exception as e:
            await self.log_error(f"Error removing channel post: {e}")
            return False

    async def get_post_channels(self, post_id):
        try:
            post = await self.posts.find_one({"post_id": post_id})
            return post.get("channels", []) if post else []
        except Exception as e:
            await self.log_error(f"Error getting post channels: {e}")
            return []

    async def get_all_posts(self, limit: int = 0, skip: int = 0):
        try:
            return [post async for post in self.posts.find({}).skip(skip).limit(limit)]
        except Exception as e:
            await self.log_error(f"Error retrieving posts: {e}")
            return []

    # ============ Utility Methods ============ #
    async def log_error(self, error_message: str):
        """Log errors to database"""
        try:
            await self.logs.insert_one({
                "error": error_message,
                "timestamp": datetime.now()
            })
        except Exception as e:
            print(f"Failed to log error: {e}")

    async def cleanup_inactive_admins(self, days_inactive=30):
        """Remove admins inactive for specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_inactive)
        result = await self.admins.delete_many({
            "last_active": {"$lt": cutoff_date}
        })
        return result.deleted_count

# Initialize the database
db = Database(DB_URL, DB_NAME)
