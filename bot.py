import logging
import logging.config
from pyrogram import Client 
from config import *
from aiohttp import web
from plugins.Extra.web_support import web_server

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
        
        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")
        logging.info(f"{me.username} Back to action baby 🐥🔥")
        

    async def stop(self, *args):
        await super().stop()      
        logging.info("{me.first_name} Bot Stopped 🙄")

bot = Bot()
bot.run()

