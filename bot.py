import os
import logging
import logging.config
from pyrogram import Client
from config import *
from plugins.Post.Posting import restore_pending_deletions

# Support multiple admin IDs
ADMIN_IDS = [int(x) for x in os.environ.get("AMIT", "2031106491").split()]

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
        self.admin_panel = None  # Initialize as None first

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username

        await restore_pending_deletions(self)

        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")
        logging.info(f"{me.first_name} Pending deletions restored successfully.")

        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await self.send_message(
                    admin_id,
                    "**Back online, baby 🎀🥹**\n"
                    "**Don’t even think about using another bot... I'm all yours! 😤❤️**")
                
            except Exception as e:
                logging.warning(f"Failed to send restart notification to {admin_id}: {e}")

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot Stopped 🙄")

bot = Bot()
bot.run()
