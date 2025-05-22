import os
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

# Configuration - Replace these with your actual values

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
        self.client = None
        self.message_queue: Dict[str, List[Message]] = {subject: [] for subject in DESTINATION_CHANNELS.keys()}
        self.last_forwarded_id = 0
        self.forwarding_active = False
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

        # Register handlers
        @self.client.on_message(filters.chat(SOURCE_CHANNEL))
        async def handle_new_message(client: Client, message: Message):
            await self.queue_message(message)

        @self.client.on_message(filters.private & filters.command("forward"))
        async def handle_forward_command(client: Client, message: Message):
            await self.handle_forward(message)

        # Start the client
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"{me.first_name} [@{me.username}] bot started")
        self.initialized = True

    async def queue_message(self, message: Message):
        """Queue new messages as they arrive"""
        if self.forwarding_active:
            return
            
        text = message.text or message.caption or ""
        subject = matcher.find_subject(text)
        
        if subject and subject in self.message_queue:
            self.message_queue[subject].append(message)
            logger.info(f"Queued message for {subject} (Total: {len(self.message_queue[subject])})")
            self.last_forwarded_id = max(self.last_forwarded_id, message.id)

    async def forward_messages(self):
        """Forward all queued messages"""
        self.forwarding_active = True
        total_forwarded = 0
        
        try:
            for subject, messages in self.message_queue.items():
                if not messages or subject not in DESTINATION_CHANNELS:
                    continue
                
                dest_channel = DESTINATION_CHANNELS[subject]
                successful_forwards = 0
                
                for message in messages:
                    try:
                        await message.copy(dest_channel)
                        successful_forwards += 1
                        self.last_forwarded_id = max(self.last_forwarded_id, message.id)
                    except RPCError as e:
                        logger.error(f"Error forwarding message {message.id}: {e}")
                
                if successful_forwards > 0:
                    logger.info(f"Forwarded {successful_forwards} messages to {subject}")
                    total_forwarded += successful_forwards
                    
                    try:
                        await self.client.send_message(
                            dest_channel,
                            f"✅ {successful_forwards} messages forwarded",
                            parse_mode=enums.ParseMode.MARKDOWN
                        )
                    except RPCError as e:
                        logger.error(f"Error sending confirmation: {e}")
                
                # Clear the queue for this subject
                self.message_queue[subject].clear()
            
            return total_forwarded
        finally:
            self.forwarding_active = False

    async def handle_forward(self, message: Message):
        """Handle the /forward command"""
        if message.from_user.id != YOUR_USER_ID:
            return await message.reply("❌ Unauthorized")
        
        if self.forwarding_active:
            return await message.reply("⏳ Forwarding in progress...")
        
        # Check if there are queued messages
        total_queued = sum(len(q) for q in self.message_queue.values())
        
        if total_queued == 0:
            await message.reply("ℹ️ No queued messages to forward. New messages will be forwarded automatically as they arrive.")
        else:
            await message.reply(f"⏳ Forwarding {total_queued} queued messages...")
            total_forwarded = await self.forward_messages()
            await message.reply(f"✅ {total_forwarded} messages forwarded successfully!")

    async def run(self):
        """Main bot loop"""
        await self.initialize_client()
        
        # Keep the bot running
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
        raise

