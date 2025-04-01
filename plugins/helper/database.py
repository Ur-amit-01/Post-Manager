import motor.motor_asyncio
from config import DB_URL, DB_NAME

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.user  # Collection for users
        self.channels = self.db.channels  # Collection for channels
        self.formatting = self.db.formatting  # Collection for formatting templates
        self.admins = self.db.admins  # Collection for admins
        self.posts = self.db.posts  # Collection for posts

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

    #============ Post System ============#
    async def save_post(self, post_id, messages):
        """
        Save a post with a unique ID.
        :param post_id: Unique ID for the post
        :param messages: List of dictionaries containing channel_id and message_id
        """
        try:
            await self.posts.update_one(
                {"_id": post_id},
                {"$set": {"messages": messages}},
                upsert=True
            )
        except Exception as e:
            print(f"Error saving post: {e}")

    async def get_post(self, post_id):
        """
        Retrieve a post by its ID.
        :param post_id: Unique ID of the post
        :return: List of dictionaries containing channel_id and message_id
        """
        try:
            post = await self.posts.find_one({"_id": post_id})
            return post.get("messages", []) if post else []
        except Exception as e:
            print(f"Error retrieving post: {e}")
            return []

    async def delete_post(self, post_id):
        """
        Delete a post by its ID.
        :param post_id: Unique ID of the post
        """
        try:
            await self.posts.delete_one({"_id": post_id})
        except Exception as e:
            print(f"Error deleting post: {e}")

    async def get_all_posts(self):
        """
        Retrieve all posts.
        :return: List of all posts
        """
        try:
            return [post async for post in self.posts.find({})]
        except Exception as e:
            print(f"Error retrieving posts: {e}")
            return []

# Initialize the database
db = Database(DB_URL, DB_NAME)
