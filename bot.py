import logging
import logging.config
import asyncio
from pyrogram import Client 
from config import *
from aiohttp import web
from plugins.Extra.web_support import web_server  # Import your existing function
from plugins.functions import *

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="renamer",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start your background task here
        self.queue_task = asyncio.create_task(check_queue_status())
        
        # Start web server
        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")

    async def stop(self, *args):
        # Cancel the background task when stopping
        self.queue_task.cancel()
        try:
            await self.queue_task
        except asyncio.CancelledError:
            pass
            
        await super().stop()      
        logging.info(f"{me.first_name} Bot Stopped 🙄")

async def main():
    bot = Bot()
    await bot.start()
    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Error: {e}")
