from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URL, DB_NAME

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Initialize MongoDB connection"""
        self.client = AsyncIOMotorClient(DB_URL)
        self.db = self.client[DB_NAME]
        await self.client.server_info()  # Test connection
        return self

    async def get_state(self, set_name):
        """Get the last forwarded ID for a channel set"""
        doc = await self.db.state.find_one({"set_name": set_name})
        return doc.get("last_forwarded_id", 0) if doc else 0

    async def save_state(self, set_name, last_id):
        """Save the current state to MongoDB"""
        await self.db.state.update_one(
            {"set_name": set_name},
            {"$set": {"last_forwarded_id": last_id}},
            upsert=True
        )
