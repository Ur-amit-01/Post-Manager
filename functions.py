import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
from plugins.Sorting import matcher

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Channel IDs
SOURCE_CHANNEL = -1002027394591
DESTINATION_CHANNELS = {
    'Physics': -1002611033664,
    'Inorganic Chemistry': -1002530766847,
    'Organic Chemistry': -1002623306070,
    'Physical Chemistry': -1002533864126,
    'Botany': -1002537691102,
    'Zoology': -1002549422245
}

class ForwardBot(Client):
    def __init__(self):
        super().__init__(
            name="forward_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            sleep_threshold=5
        )
        self.last_forwarded_id = 0
        self.forwarding_active = False
        self.initialized = False

    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"{me.first_name} Forward Bot Started")
        self.initialized = True

    async def process_message(self, message: Message):
        """Process and forward a single message"""
        text = message.text or message.caption or ""
        subject = matcher.find_subject(text)
        
        if subject and subject in DESTINATION_CHANNELS:
            try:
                await message.copy(DESTINATION_CHANNELS[subject])
                self.last_forwarded_id = message.id
                logger.info(f"Forwarded message {message.id} to {subject}")
                return True
            except Exception as e:
                logger.error(f"Error forwarding message {message.id}: {e}")
        return False

    @Client.on_message(filters.chat(SOURCE_CHANNEL))
    async def handle_new_message(self, client: Client, message: Message):
        """Handle new messages in real-time"""
        if not self.initialized or self.forwarding_active:
            return
            
        await self.process_message(message)

    @Client.on_message(filters.private & filters.command("forward"))
    async def handle_forward_command(self, client: Client, message: Message):
        """Handle manual forward command (for recent messages)"""
        if message.from_user.id != 2031106491:  # Replace with your user ID
            return await message.reply("❌ Unauthorized")
        
        if self.forwarding_active:
            return await message.reply("⏳ Forwarding in progress...")
        
        self.forwarding_active = True
        try:
            await message.reply("⏳ Checking for recent messages...")
            
            # Can only access recent messages (limited by Telegram)
            count = 0
            async for msg in client.get_chat_history(SOURCE_CHANNEL, limit=100):  # Max 100 recent
                if msg.id <= self.last_forwarded_id:
                    continue
                if await self.process_message(msg):
                    count += 1
            
            await message.reply(f"✅ Forwarded {count} new messages")
        except Exception as e:
            logger.error(f"Error in forward command: {e}")
            await message.reply("⚠️ Error processing messages")
        finally:
            self.forwarding_active = False

if __name__ == "__main__":
    bot = ForwardBot()
    bot.run()
