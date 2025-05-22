import asyncio
import logging
from typing import Dict, List
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

YOUR_USER_ID = 2031106491  # Your Telegram User ID

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

class ForwardingBot:
    def __init__(self):
        self.client = None
        self.last_forwarded_id = 0
        self.forwarding_active = False
        self.pending_messages: Dict[int, Message] = {}  # Store messages by ID
        self.initialized = False

    async def initialize_client(self):
        """Initialize the Pyrogram client"""
        self.client = Client(
            "forward_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=100,
            sleep_threshold=10
        )

        @self.client.on_message(filters.chat(SOURCE_CHANNEL))
        async def store_message(client: Client, message: Message):
            """Store new messages as they arrive"""
            if message.id > self.last_forwarded_id:
                self.pending_messages[message.id] = message
                logger.info(f"Stored message {message.id} (Total pending: {len(self.pending_messages)})")

        @self.client.on_message(filters.private & filters.command("forward"))
        async def handle_forward_command(client: Client, message: Message):
            """Handle /forward command"""
            await self.process_forward_command(message)

        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"{me.first_name} [@{me.username}] bot started")
        
        # Try to get the most recent message (if any exist)
        try:
            async for msg in self.client.get_chat_history(SOURCE_CHANNEL, limit=1):
                self.last_forwarded_id = msg.id
                logger.info(f"Initialized with last message ID: {self.last_forwarded_id}")
        except RPCError as e:
            logger.warning(f"Couldn't get initial message: {e}")
        
        self.initialized = True

    async def process_pending_messages(self):
        """Process and forward all pending messages in order"""
        if not self.pending_messages:
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            # Sort messages by ID (chronological order)
            sorted_messages = sorted(self.pending_messages.values(), key=lambda m: m.id)
            
            for message in sorted_messages:
                text = message.text or message.caption or ""
                subject = matcher.find_subject(text)
                
                if subject and subject in DESTINATION_CHANNELS:
                    try:
                        await message.copy(DESTINATION_CHANNELS[subject])
                        self.last_forwarded_id = message.id
                        forwarded_count += 1
                        logger.info(f"Forwarded message {message.id} to {subject}")
                    except RPCError as e:
                        logger.error(f"Error forwarding message {message.id}: {e}")
                        continue
            
            # Clear forwarded messages from pending
            self.pending_messages = {
                id: msg for id, msg in self.pending_messages.items() 
                if id > self.last_forwarded_id
            }
            
            return forwarded_count
        finally:
            self.forwarding_active = False

    async def process_forward_command(self, message: Message):
        """Handle the /forward command"""
        if message.from_user.id != YOUR_USER_ID:
            return await message.reply("❌ Unauthorized")
        
        if self.forwarding_active:
            return await message.reply("⏳ Forwarding in progress...")
        
        await message.reply(f"⏳ Processing {len(self.pending_messages)} pending messages...")
        count = await self.process_pending_messages()
        
        if count > 0:
            await message.reply(f"✅ Successfully forwarded {count} messages")
        else:
            await message.reply("ℹ️ No new messages to forward")

    async def run(self):
        """Main bot loop"""
        await self.initialize_client()
        while True:
            await asyncio.sleep(3600)  # Keep the bot running

# Import your matcher after the class definition
from plugins.Sorting import matcher

if __name__ == "__main__":
    bot = ForwardingBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
