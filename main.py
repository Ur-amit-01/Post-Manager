import asyncio
import logging
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, USER_SESSION_STRING
from database import Database
from forwarder import MessageForwarder
from handlers import CommandHandlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    # Initialize database
    db = await Database().connect()
    
    # Initialize clients
    user_client = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=USER_SESSION_STRING)
    bot_client = Client("forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    
    await user_client.start()
    await bot_client.start()
    
    # Initialize forwarder and handlers
    forwarder = MessageForwarder(user_client, bot_client, db)
    handlers = CommandHandlers(bot_client, forwarder, db)
    handlers.register_handlers()
    
    logger.info("Bot is running... ✅")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
