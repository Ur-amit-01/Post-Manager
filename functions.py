import os
import asyncio
from typing import Dict, List
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import RPCError
import logging
from config import *
# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

YOUR_USER_ID = 2031106491  # Your Telegram User ID

# Channel IDs
SOURCE_CHANNEL = -1002027394591  # Main channel to monitor
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
        self.message_queue: Dict[str, List[Message]] = {subject: [] for subject in DESTINATION_CHANNELS.keys()}
        self.last_forwarded_id = 0
        self.forwarding_active = False
        self.initialized = False
        self.client = None

    async def initialize(self):
        """Initialize the Pyrogram client and bot state"""
        self.client = Client(
            "forward_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=100,
            sleep_threshold=10
        )

        @self.client.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.command("forward"))
        async def queue_content(client: Client, message: Message):
            """Queue messages when they arrive in source channel"""
            if self.forwarding_active:
                return
                
            text = message.text or message.caption or ""
            subject = matcher.find_subject(text)
            
            if subject and subject in self.message_queue:
                self.message_queue[subject].append(message)
                logger.info(f"Queued message for {subject} (Total: {len(self.message_queue[subject])})")
                
                # Update last seen ID
                if message.id > self.last_forwarded_id:
                    self.last_forwarded_id = message.id

        @self.client.on_message(filters.private & filters.command("forward"))
        async def start_forwarding(client: Client, message: Message):
            """Handle /forward command in DM"""
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("❌ Unauthorized")
            
            if not self.initialized:
                await message.reply("⏳ Initializing bot...")
                if not await self.initialize_bot_state():
                    return await message.reply("⚠️ Failed to initialize bot")
            
            await self.process_forward_command(message)

        # Start the client
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"{me.first_name} [@{me.username}] bot started")
        
        # Initialize bot state
        await self.initialize_bot_state()

    async def initialize_bot_state(self):
        """Initialize the bot's state with the latest message ID"""
        try:
            async for message in self.client.get_chat_history(SOURCE_CHANNEL, limit=1):
                self.last_forwarded_id = message.id
                logger.info(f"Initialized last_forwarded_id: {self.last_forwarded_id}")
                self.initialized = True
                return True
            
            logger.warning("No messages found in source channel during initialization")
            self.initialized = True
            return True
        except RPCError as e:
            logger.error(f"Initialization error: {e}")
            return False

    async def get_new_messages(self):
        """Fetch new messages since last forwarded ID"""
        messages = []
        try:
            async for message in self.client.get_chat_history(SOURCE_CHANNEL, limit=100):  # Max 100 recent
                if message.id <= self.last_forwarded_id:
                    continue
                messages.append(message)
        except RPCError as e:
            logger.error(f"Error fetching messages: {e}")
        
        return messages[::-1]  # Return in chronological order

    async def forward_queued_messages(self):
        """Forward all queued messages in correct order"""
        self.forwarding_active = True
        total_forwarded = 0
        
        try:
            for subject, messages in self.message_queue.items():
                if messages and subject in DESTINATION_CHANNELS:
                    dest_channel = DESTINATION_CHANNELS[subject]
                    try:
                        for message in messages:
                            await message.copy(dest_channel)
                            if message.id > self.last_forwarded_id:
                                self.last_forwarded_id = message.id
                        
                        total_forwarded += len(messages)
                        logger.info(f"Forwarded {len(messages)} messages to {subject}")
                        
                        await self.client.send_message(
                            dest_channel,
                            f"✅ {len(messages)} messages forwarded",
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                    except RPCError as e:
                        logger.error(f"Error forwarding to {subject}: {e}")
            
            # Clear queues after forwarding
            for subject in self.message_queue:
                self.message_queue[subject].clear()
            
            return total_forwarded
        finally:
            self.forwarding_active = False

    async def process_forward_command(self, message: Message):
        """Process the /forward command"""
        if self.forwarding_active:
            return await message.reply("⏳ Forwarding in progress...")
        
        # First check queued messages
        total_queued = sum(len(q) for q in self.message_queue.values())
        
        if total_queued == 0:
            await message.reply("⏳ Fetching new messages...")
            new_messages = await self.get_new_messages()
            
            if not new_messages:
                return await message.reply("⚠️ No new messages to forward.")
                
            # Queue new messages
            for msg in new_messages:
                text = msg.text or msg.caption or ""
                subject = matcher.find_subject(text)
                if subject and subject in self.message_queue:
                    self.message_queue[subject].append(msg)
            
            total_queued = sum(len(q) for q in self.message_queue.values())
        
        await message.reply(f"⏳ Forwarding {total_queued} messages...")
        total_forwarded = await self.forward_queued_messages()
        await message.reply(f"✅ {total_forwarded} messages forwarded successfully!")

    async def run(self):
        """Run the bot indefinitely"""
        await self.initialize()
        while True:
            await asyncio.sleep(3600)  # Periodic tasks can go here
            queued = sum(len(q) for q in self.message_queue.values())
            if queued > 0:
                logger.info(f"Queue status: {queued} messages waiting")

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

