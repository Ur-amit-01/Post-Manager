import logging
import logging.config
from pyrogram import Client 
from config import *
from aiohttp import web
from plugins.Extra.web_support import web_server
from plugins.Post.Posting import restore_pending_deletions
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import the database connection properly
from plugins.helper.db import db

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
        # Initialize scheduler but don't start it yet
        self.scheduler = AsyncIOScheduler()

    async def initialize_daily_scheduler(self):
        """Initialize all scheduled posts on bot startup"""
        from plugins.daily_scheduler import schedule_daily_post  # Import here to avoid circular imports
        
        # Use the properly imported db connection
        active_posts = await db.daily_posts.find({"schedule.is_active": True}).to_list(None)
        for post in active_posts:
            await schedule_daily_post(self, post["_id"])
        logging.info(f"Initialized {len(active_posts)} daily posts")

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start web server
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()
        
        # Restore pending deletions
        await restore_pending_deletions(self)
        
        # Start the scheduler now that we have a running event loop
        self.scheduler.start()
        
        # Initialize daily scheduler
        await self.initialize_daily_scheduler()
        
        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")
        logging.info("Pending deletions restored successfully")
        logging.info("Daily scheduler initialized")

    async def stop(self, *args):
        # Shutdown scheduler gracefully
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        await super().stop()      
        logging.info("Bot Stopped 🙄")

bot = Bot()
bot.run()
