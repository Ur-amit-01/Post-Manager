import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from config import *
from plugins.Chapters import CHAPTER_DATA
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

    async def get_most_recent_message_id(self):
        """Get the most recent message ID from source channel"""
        try:
            async for message in self.get_chat_history(SOURCE_CHANNEL, limit=1):
                return message.id
        except Exception as e:
            logger.error(f"Error getting recent message ID: {e}")
            return 0

    async def get_new_messages(self):
        """Fetch new messages since last forwarded ID"""
        if self.last_forwarded_id == 0:
            self.last_forwarded_id = await self.get_most_recent_message_id()
            if self.last_forwarded_id == 0:
                return []
            logger.info(f"Initialized last_forwarded_id: {self.last_forwarded_id}")
            return []
        
        messages = []
        try:
            async for message in self.get_chat_history(SOURCE_CHANNEL):
                if message.id <= self.last_forwarded_id:
                    break
                messages.append(message)
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
        
        return messages[::-1]  # Return in chronological order

    async def forward_messages(self, messages: list):
        """Forward messages to appropriate channels"""
        self.forwarding_active = True
        forwarded_count = 0
        
        for message in messages:
            text = message.text or message.caption or ""
            subject = matcher.find_subject(text)
            
            if subject and subject in DESTINATION_CHANNELS:
                try:
                    await message.copy(DESTINATION_CHANNELS[subject])
                    if message.id > self.last_forwarded_id:
                        self.last_forwarded_id = message.id
                    forwarded_count += 1
                    logger.info(f"Forwarded message {message.id} to {subject}")
                except Exception as e:
                    logger.error(f"Error forwarding message {message.id}: {e}")
        
        self.forwarding_active = False
        return forwarded_count

    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"{me.first_name} Forward Bot Started")
        # Initialize last_forwarded_id
        self.last_forwarded_id = await self.get_most_recent_message_id()

    @Client.on_message(filters.private & filters.command("forward"))
    async def handle_forward(self, client: Client, message: Message):
        """Handle /forward command"""
        if message.from_user.id != 2031106491:  # Replace with your user ID
            return await message.reply("❌ Unauthorized")
        
        if self.forwarding_active:
            return await message.reply("**⏳ Forwarding in progress...**")
        
        await message.reply("**⏳ Fetching new messages...**")
        new_messages = await self.get_new_messages()
        
        if not new_messages:
            return await message.reply("⚠️ No new messages found")
        
        await message.reply(f"⏳ Forwarding {len(new_messages)} messages...")
        count = await self.forward_messages(new_messages)
        await message.reply(f"✅ Forwarded {count} messages")

if __name__ == "__main__":
    bot = ForwardBot()
    bot.run()
