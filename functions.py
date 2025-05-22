import logging
from pyrogram import Client, filters, enums
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

    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"{me.first_name} Forward Bot Started")
        
        # Initialize by getting the last message from the channel
        try:
            async for message in self.get_chat_history(SOURCE_CHANNEL, limit=1):
                self.last_forwarded_id = message.id
                logger.info(f"Initial last message ID: {self.last_forwarded_id}")
        except Exception as e:
            logger.error(f"Error initializing last message ID: {e}")

    async def process_new_messages(self):
        """Process new messages since last forwarded ID"""
        self.forwarding_active = True
        try:
            messages_to_forward = []
            
            # Get messages in reverse chronological order (newest first)
            async for message in self.get_chat_history(SOURCE_CHANNEL):
                if message.id <= self.last_forwarded_id:
                    break
                messages_to_forward.append(message)
            
            # Forward in chronological order (oldest first)
            for message in reversed(messages_to_forward):
                text = message.text or message.caption or ""
                subject = matcher.find_subject(text)
                
                if subject and subject in DESTINATION_CHANNELS:
                    try:
                        await message.copy(DESTINATION_CHANNELS[subject])
                        self.last_forwarded_id = message.id
                        logger.info(f"Forwarded message {message.id} to {subject}")
                    except Exception as e:
                        logger.error(f"Error forwarding message {message.id}: {e}")
            
            return len(messages_to_forward)
        finally:
            self.forwarding_active = False

    @Client.on_message(filters.chat(SOURCE_CHANNEL))
    async def handle_new_message(self, client: Client, message: Message):
        """Handle new messages in the source channel"""
        if self.forwarding_active:
            return
            
        text = message.text or message.caption or ""
        subject = matcher.find_subject(text)
        
        if subject and subject in DESTINATION_CHANNELS:
            try:
                await message.copy(DESTINATION_CHANNELS[subject])
                self.last_forwarded_id = message.id
                logger.info(f"Forwarded message {message.id} to {subject}")
            except Exception as e:
                logger.error(f"Error forwarding message {message.id}: {e}")

    @Client.on_message(filters.private & filters.command("forward"))
    async def handle_forward_command(self, client: Client, message: Message):
        """Handle manual forward command"""
        if message.from_user.id != 2031106491:  # Replace with your user ID
            return await message.reply("❌ Unauthorized")
        
        if self.forwarding_active:
            return await message.reply("⏳ Forwarding in progress...")
        
        await message.reply("⏳ Processing new messages...")
        count = await self.process_new_messages()
        await message.reply(f"✅ Forwarded {count} new messages")

if __name__ == "__main__":
    bot = ForwardBot()
    bot.run()
