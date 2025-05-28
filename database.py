from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URL

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(DB_URL)
            self.db = self.client["telegram_forwarder"]
            await self.client.server_info()
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to MongoDB: {e}")
    
    async def load_state(self, set_name):
        try:
            doc = await self.db.state.find_one({"set_name": set_name})
            return doc.get("last_forwarded_id", 0) if doc else 0
        except Exception as e:
            raise Exception(f"Error in load_state: {e}")
    
    async def save_state(self, set_name, last_id):
        try:
            await self.db.state.update_one(
                {"set_name": set_name},
                {"$set": {"last_forwarded_id": last_id}},
                upsert=True
            )
        except Exception as e:
            raise Exception(f"Error saving state: {e}")
