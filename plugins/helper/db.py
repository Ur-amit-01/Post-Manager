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
        self.admins = self.db.admins
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
            is_admin=False,
            is_banned=False,
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

    async def set_admin(self, user_id: int, is_admin: bool = True):
        await self.col.update_one(
            {'_id': int(user_id)},
            {'$set': {'is_admin': is_admin}}
        )

    async def ban_user(self, user_id: int, is_banned: bool = True):
        await self.col.update_one(
            {'_id': int(user_id)},
            {'$set': {'is_banned': is_banned}}
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

    # ============ Admin Panel Methods ============ #
    async def get_bot_stats(self) -> Dict[str, Union[int, float, str]]:
        """Get comprehensive statistics for admin panel"""
        return {
            "total_users": await self.total_users_count(),
            "total_channels": await self.channels.count_documents({}),
            "total_posts": await self.posts.count_documents({}),
            "active_posts": await self.posts.count_documents({"status": "active"}),
            "storage_usage": await self.get_storage_usage(),
            "uptime": await self.get_uptime(),
            "avg_post_time": await self.get_avg_post_time(),
            "success_rate": await self.get_success_rate()
        }

    async def get_storage_usage(self) -> float:
        """Get database storage usage in MB"""
        stats = await self.db.command("dbStats")
        return round(stats["dataSize"] / (1024 * 1024), 2)

    async def get_uptime(self) -> str:
        """Get bot uptime from settings"""
        setting = await self.settings.find_one({"key": "start_time"})
        if setting:
            uptime = datetime.now() - setting["value"]
            return str(uptime).split(".")[0]
        return "Not available"

    async def get_avg_post_time(self) -> float:
        """Calculate average post processing time"""
        result = await self.posts.aggregate([
            {"$match": {"processing_time": {"$exists": True}}},
            {"$group": {"_id": None, "avg_time": {"$avg": "$processing_time"}}}
        ]).to_list(length=1)
        return round(result[0]["avg_time"], 2) if result else 0.0

    async def get_success_rate(self) -> float:
        """Calculate post success rate"""
        total = await self.posts.count_documents({})
        if total == 0:
            return 100.0
        success = await self.posts.count_documents({"status": "completed"})
        return round((success / total) * 100, 2)

    async def get_post_activity(self, days: int = 7) -> List[Dict]:
        """Get post activity for last N days"""
        return await self.posts.aggregate([
            {"$match": {"timestamp": {"$gte": datetime.now() - timedelta(days=days)}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}},
            {"$project": {"date": "$_id", "count": 1, "_id": 0}}
        ]).to_list(length=None)

    async def get_channel_stats(self, limit: int = 10) -> List[Dict]:
        """Get channel statistics ordered by post count"""
        return await self.channels.find(
            {},
            {"_id": 1, "name": 1, "post_count": 1, "last_post": 1}
        ).sort("post_count", -1).limit(limit).to_list(length=limit)

    async def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent system activity"""
        return await self.logs.find(
            {},
            {"_id": 0, "timestamp": 1, "action": 1, "details": 1}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)

    async def log_error(self, error: str):
        """Log errors to database"""
        await self.logs.insert_one({
            "type": "error",
            "timestamp": datetime.now(),
            "message": error
        })

    async def log_action(self, action: str, details: str = ""):
        """Log admin actions to database"""
        await self.logs.insert_one({
            "type": "action",
            "timestamp": datetime.now(),
            "action": action,
            "details": details
        })

    async def backup_database(self):
        """Create a database backup record"""
        await self.settings.update_one(
            {"key": "last_backup"},
            {"$set": {"value": datetime.now()}},
            upsert=True
        )
        await self.log_action("database_backup")

# Initialize the database
db = Database(DB_URL, DB_NAME)
