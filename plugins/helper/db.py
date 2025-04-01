import motor.motor_asyncio
from config import DB_URL, DB_NAME
from datetime import datetime
from typing import List, Dict, Union, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri: str, database_name: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        
        # Collections
        self.users = self.db.users
        self.channels = self.db.channels
        self.posts = self.db.posts
        self.admins = self.db.admins
        self.templates = self.db.templates
        self.backups = self.db.backups

    # ============ USER SYSTEM ============ #
    async def add_user(self, user_id: int) -> bool:
        """Add a new user to the database if not exists"""
        try:
            if not await self.is_user_exist(user_id):
                user_data = {
                    "_id": user_id,
                    "join_date": datetime.now(),
                    "last_active": datetime.now(),
                    "status": "active"
                }
                await self.users.insert_one(user_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False

    async def is_user_exist(self, user_id: int) -> bool:
        """Check if user exists in database"""
        try:
            return await self.users.find_one({"_id": user_id}) is not None
        except Exception as e:
            logger.error(f"Error checking user {user_id}: {e}")
            return False

    async def total_users_count(self) -> int:
        """Get total count of users"""
        try:
            return await self.users.count_documents({})
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self) -> List[Dict]:
        """Get all users from database"""
        try:
            return [user async for user in self.users.find({})]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user from database"""
        try:
            result = await self.users.delete_one({"_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    # ============ CHANNEL SYSTEM ============ #
    async def add_channel(self, channel_id: int, channel_name: str = None) -> bool:
        """Add a new channel to the database"""
        try:
            if not await self.is_channel_exist(channel_id):
                channel_data = {
                    "_id": channel_id,
                    "name": channel_name,
                    "added_at": datetime.now(),
                    "status": "active"
                }
                await self.channels.insert_one(channel_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding channel {channel_id}: {e}")
            return False

    async def is_channel_exist(self, channel_id: int) -> bool:
        """Check if channel exists in database"""
        try:
            return await self.channels.find_one({"_id": channel_id}) is not None
        except Exception as e:
            logger.error(f"Error checking channel {channel_id}: {e}")
            return False

    async def get_channel(self, channel_id: int) -> Optional[Dict]:
        """Get channel details by ID"""
        try:
            return await self.channels.find_one({"_id": channel_id})
        except Exception as e:
            logger.error(f"Error getting channel {channel_id}: {e}")
            return None

    async def get_all_channels(self) -> List[Dict]:
        """Get all channels from database"""
        try:
            return [channel async for channel in self.channels.find({})]
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def delete_channel(self, channel_id: int) -> bool:
        """Delete a channel from database"""
        try:
            result = await self.channels.delete_one({"_id": channel_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting channel {channel_id}: {e}")
            return False

    # ============ POST SYSTEM ============ #
    async def save_post(self, post_id: Union[int, str], messages: List[Dict]) -> bool:
        """Save or update a post in the database"""
        try:
            post_data = {
                "_id": post_id,
                "messages": messages,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            await self.posts.update_one(
                {"_id": post_id},
                {"$set": post_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving post {post_id}: {e}")
            return False

    async def get_post(self, post_id: Union[int, str]) -> Optional[Dict]:
        """Retrieve a post by its ID"""
        try:
            return await self.posts.find_one({"_id": post_id})
        except Exception as e:
            logger.error(f"Error getting post {post_id}: {e}")
            return None

    async def delete_post(self, post_id: Union[int, str]) -> bool:
        """Delete a post by its ID"""
        try:
            result = await self.posts.delete_one({"_id": post_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting post {post_id}: {e}")
            return False

    async def get_all_posts(self) -> List[Dict]:
        """Retrieve all posts from database"""
        try:
            return [post async for post in self.posts.find({})]
        except Exception as e:
            logger.error(f"Error getting posts: {e}")
            return []

    # ============ ADMIN SYSTEM ============ #
    async def add_admin(self, user_id: int) -> bool:
        """Add a new admin to the database"""
        try:
            if not await self.is_admin(user_id):
                await self.admins.insert_one({
                    "_id": user_id,
                    "added_at": datetime.now()
                })
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding admin {user_id}: {e}")
            return False

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        try:
            return await self.admins.find_one({"_id": user_id}) is not None
        except Exception as e:
            logger.error(f"Error checking admin {user_id}: {e}")
            return False

    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin privileges"""
        try:
            result = await self.admins.delete_one({"_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error removing admin {user_id}: {e}")
            return False

    # ============ BACKUP SYSTEM ============ #
    async def create_backup(self) -> Optional[Dict]:
        """Create a complete backup of the database"""
        try:
            backup_data = {
                "users": await self.get_all_users(),
                "channels": await self.get_all_channels(),
                "posts": await self.get_all_posts(),
                "admins": [admin async for admin in self.admins.find({})],
                "created_at": datetime.now()
            }
            
            # Store backup in database
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await self.backups.insert_one({
                "_id": backup_id,
                "data": backup_data,
                "created_at": datetime.now()
            })
            
            return backup_data
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    async def restore_backup(self, backup_data: Dict) -> bool:
        """Restore database from backup data"""
        try:
            # Clear existing data
            await self.users.delete_many({})
            await self.channels.delete_many({})
            await self.posts.delete_many({})
            await self.admins.delete_many({})
            
            # Insert backup data
            if "users" in backup_data:
                await self.users.insert_many(backup_data["users"])
            if "channels" in backup_data:
                await self.channels.insert_many(backup_data["channels"])
            if "posts" in backup_data:
                await self.posts.insert_many(backup_data["posts"])
            if "admins" in backup_data:
                await self.admins.insert_many(backup_data["admins"])
                
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False

# Initialize database connection
db = Database(DB_URL, DB_NAME)
