import motor.motor_asyncio
import time
from config import DB_URL, DB_NAME
from datetime import datetime

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.user  # Collection for users
        self.channels = self.db.channels  # Collection for channels
        self.formatting = self.db.formatting  # Collection for formatting templates
        self.admins = self.db.admins  # Collection for admins
        self.posts = self.db.posts  # Collection for posts
        self.daily_posts = self.db.daily_posts  # New collection for daily posts
        self.temp_daily = self.db.temp_daily  # Temporary storage for daily post creation

    #============ User System ============#
    def new_user(self, id):
        return dict(
            _id=int(id),
            file_id=None,
            caption=None,
            prefix=None,
            suffix=None,
            metadata=False,
            metadata_code="By :- @Madflix_Bots"
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
            await self.channels.insert_one({"_id": channel_id, "name": channel_name})
            return True
        return False

    async def delete_channel(self, channel_id):
        await self.channels.delete_one({"_id": int(channel_id)})

    async def is_channel_exist(self, channel_id):
        return await self.channels.find_one({"_id": int(channel_id)}) is not None

    async def get_all_channels(self):
        return [channel async for channel in self.channels.find({})]

    #============ Regular Post System ============#
    async def save_post(self, post_data):
        try:
            await self.posts.update_one(
                {"post_id": post_data["post_id"]},
                {"$set": post_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving post: {e}")
            return False

    async def get_post(self, post_id):
        try:
            return await self.posts.find_one({"post_id": post_id})
        except Exception as e:
            print(f"Error retrieving post: {e}")
            return None

    async def delete_post(self, post_id):
        try:
            await self.posts.delete_one({"post_id": post_id})
            return True
        except Exception as e:
            print(f"Error deleting post: {e}")
            return False

    async def get_pending_deletions(self):
        try:
            return await self.posts.find({
                "delete_after": {"$gt": time.time()}
            }).to_list(None)
        except Exception as e:
            print(f"Error getting pending deletions: {e}")
            return []

    async def remove_channel_post(self, post_id, channel_id):
        try:
            result = await self.posts.update_one(
                {"post_id": post_id},
                {"$pull": {"channels": {"channel_id": channel_id}}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error removing channel post: {e}")
            return False

    async def get_post_channels(self, post_id):
        try:
            post = await self.posts.find_one({"post_id": post_id})
            return post.get("channels", []) if post else []
        except Exception as e:
            print(f"Error getting post channels: {e}")
            return []

    async def get_all_posts(self):
        try:
            return [post async for post in self.posts.find({})]
        except Exception as e:
            print(f"Error retrieving posts: {e}")
            return []

    #============ Daily Post System ============#
    async def create_daily_post(self, user_id, content, post_time, delete_after=0):
        """Create a new daily post entry"""
        try:
            post_id = f"daily_{user_id}_{int(time.time())}"
            post_data = {
                "_id": post_id,
                "user_id": user_id,
                "content": content,
                "schedule": {
                    "post_time": post_time,  # Format: "HH:MM"
                    "delete_after": delete_after,  # In seconds
                    "is_active": True,
                    "last_posted": 0  # Timestamp
                }
            }
            await self.daily_posts.insert_one(post_data)
            return post_id
        except Exception as e:
            print(f"Error creating daily post: {e}")
            return None

    async def get_daily_post(self, post_id):
        """Get a specific daily post"""
        try:
            return await self.daily_posts.find_one({"_id": post_id})
        except Exception as e:
            print(f"Error getting daily post: {e}")
            return None

    async def get_user_daily_posts(self, user_id):
        """Get all daily posts for a user"""
        try:
            return [post async for post in self.daily_posts.find({"user_id": user_id})]
        except Exception as e:
            print(f"Error getting user daily posts: {e}")
            return []

    async def toggle_daily_post_status(self, post_id, is_active):
        """Pause or resume a daily post"""
        try:
            await self.daily_posts.update_one(
                {"_id": post_id},
                {"$set": {"schedule.is_active": is_active}}
            )
            return True
        except Exception as e:
            print(f"Error toggling daily post status: {e}")
            return False

    async def delete_daily_post(self, post_id):
        """Delete a daily post"""
        try:
            await self.daily_posts.delete_one({"_id": post_id})
            return True
        except Exception as e:
            print(f"Error deleting daily post: {e}")
            return False

    async def update_last_posted_time(self, post_id):
        """Update the last posted timestamp"""
        try:
            await self.daily_posts.update_one(
                {"_id": post_id},
                {"$set": {"schedule.last_posted": time.time()}}
            )
            return True
        except Exception as e:
            print(f"Error updating last posted time: {e}")
            return False

    async def get_active_daily_posts(self):
        """Get all active daily posts"""
        try:
            return [post async for post in self.daily_posts.find({
                "schedule.is_active": True
            })]
        except Exception as e:
            print(f"Error getting active daily posts: {e}")
            return []

    #============ Temporary Storage for Daily Post Creation ============#
    async def save_temp_daily(self, user_id, data):
        """Save temporary data during daily post creation"""
        try:
            await self.temp_daily.update_one(
                {"user_id": user_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving temp daily data: {e}")
            return False

    async def get_temp_daily(self, user_id):
        """Get temporary data for daily post creation"""
        try:
            return await self.temp_daily.find_one({"user_id": user_id})
        except Exception as e:
            print(f"Error getting temp daily data: {e}")
            return None

    async def clear_temp_daily(self, user_id):
        """Clear temporary data after post creation"""
        try:
            await self.temp_daily.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            print(f"Error clearing temp daily data: {e}")
            return False

# Initialize the database
db = Database(DB_URL, DB_NAME)
