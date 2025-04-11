import motor.motor_asyncio
import time
from config import DB_URL, DB_NAME
from datetime import datetime
from typing import Dict, Optional, List

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        
        # Existing collections
        self.col = self.db.user
        self.channels = self.db.channels
        self.formatting = self.db.formatting
        self.admins = self.db.admins
        self.posts = self.db.posts        
        # New collections for bot cloning
        self.bot_clones = self.db.bot_clones
        self.clone_tokens = self.db.clone_tokens

    #============ Bot Clone System ============#
    async def add_bot_clone(self, user_id: int, bot_token: str, bot_username: str) -> bool:
        """Add a new bot clone to the database"""
        try:
            await self.bot_clones.update_one(
                {"user_id": user_id},
                {"$set": {
                    "bot_token": bot_token,
                    "bot_username": bot_username,
                    "created_at": datetime.now(),
                    "is_active": True
                }},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding bot clone: {e}")
            return False

    async def get_bot_clone(self, user_id: int) -> Optional[Dict]:
        """Get a user's bot clone information"""
        try:
            return await self.bot_clones.find_one({"user_id": user_id})
        except Exception as e:
            print(f"Error getting bot clone: {e}")
            return None

    async def delete_bot_clone(self, user_id: int) -> bool:
        """Remove a bot clone from the database"""
        try:
            result = await self.bot_clones.delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting bot clone: {e}")
            return False

    async def get_all_active_clones(self) -> List[Dict]:
        """Get all active bot clones"""
        try:
            return await self.bot_clones.find({"is_active": True}).to_list(None)
        except Exception as e:
            print(f"Error getting active clones: {e}")
            return []

    async def store_clone_token(self, user_id: int, token_data: Dict) -> bool:
        """Store temporary token data during clone creation"""
        try:
            await self.clone_tokens.update_one(
                {"user_id": user_id},
                {"$set": token_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error storing clone token: {e}")
            return False

    async def get_clone_token_data(self, user_id: int) -> Optional[Dict]:
        """Get temporary token data"""
        try:
            return await self.clone_tokens.find_one({"user_id": user_id})
        except Exception as e:
            print(f"Error getting clone token data: {e}")
            return None

    async def clear_clone_token(self, user_id: int) -> bool:
        """Clear temporary token data"""
        try:
            await self.clone_tokens.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            print(f"Error clearing clone token: {e}")
            return False

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


# Initialize the database
db = Database(DB_URL, DB_NAME)
