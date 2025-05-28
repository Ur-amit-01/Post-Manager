import asyncio
from pyrogram import Client
from config import *
from database import DatabaseManager
from forwarder import MessageForwarder
from handlers import CommandHandlers
from logging_config import setup_logging

class HybridForwarder:
    def __init__(self):
        self.logger = setup_logging()
        self.user_client = None
        self.bot_client = None
        self.db_manager = DatabaseManager()
        self.forwarder = None
        self.handlers = None
    
    async def initialize_clients(self):
        self.user_client = Client(
            "user_account",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=SESSION_STRING,
            in_memory=True
        )
        
        self.bot_client = Client(
            "forward_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        
        await self.user_client.start()
        await self.bot_client.start()
        
        user_me = await self.user_client.get_me()
        bot_me = await self.bot_client.get_me()
        self.logger.info(f"User: @{user_me.username}, Bot: @{bot_me.username}")
    
    async def initialize(self):
        try:
            await self.db_manager.connect()
            await self.initialize_clients()
            
            self.forwarder = MessageForwarder(self.user_client, self.bot_client, self.db_manager)
            self.handlers = CommandHandlers(self.bot_client, self.forwarder, self.user_client, config)
            self.handlers.register_handlers()
            
            self.logger.info("Bot initialized successfully")
            return True
        except Exception as e:
            self.logger.critical(f"Initialization failed: {e}")
            raise
    
    async def run(self):
        await self.initialize()
        self.logger.info("Bot is ready and waiting for commands")
        
        while True:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                self.logger.info("Shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    hybrid = HybridForwarder()
    try:
        asyncio.run(hybrid.run())
    except KeyboardInterrupt:
        hybrid.logger.info("Bot stopped by user")
    except Exception as e:
        hybrid.logger.critical(f"Fatal error: {e}")
