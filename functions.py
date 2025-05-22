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

        # Register command handler
        @self.client.on_message(filters.private & filters.command("forward"))
        async def handle_forward_command(client: Client, message: Message):
            await self.handle_forward(message)

        # Start the client
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"{me.first_name} [@{me.username}] bot started")
        
        # Initialize with last message ID if available
        try:
            async for message in self.client.get_chat_history(SOURCE_CHANNEL, limit=1):
                self.last_forwarded_id = message.id
                logger.info(f"Initial last message ID: {self.last_forwarded_id}")
        except RPCError as e:
            logger.error(f"Couldn't get initial message ID: {e}")
            self.last_forwarded_id = 0
            
        self.initialized = True

    async def scan_and_forward_messages(self):
        """Scan for new messages and forward them"""
        self.forwarding_active = True
        messages_to_forward = []
        
        try:
            # Scan for new messages (up to 1000 messages back)
            async for message in self.client.get_chat_history(
                SOURCE_CHANNEL, 
                limit=1000,
                offset_id=self.last_forwarded_id
            ):
                if message.id <= self.last_forwarded_id:
                    continue
                messages_to_forward.append(message)
            
            # Sort messages in chronological order (oldest first)
            messages_to_forward.sort(key=lambda m: m.id)
            
            # Forward messages in order
            for message in messages_to_forward:
                text = message.text or message.caption or ""
                subject = matcher.find_subject(text)
                
                if subject and subject in DESTINATION_CHANNELS:
                    try:
                        await message.copy(DESTINATION_CHANNELS[subject])
                        self.last_forwarded_id = message.id
                        logger.info(f"Forwarded message {message.id} to {subject}")
                    except RPCError as e:
                        logger.error(f"Error forwarding message {message.id}: {e}")
                        continue
            
            return len(messages_to_forward)
            
        finally:
            self.forwarding_active = False

    async def handle_forward(self, message: Message):
        """Handle the /forward command"""
        if message.from_user.id != YOUR_USER_ID:
            return await message.reply("❌ Unauthorized")
        
        if self.forwarding_active:
            return await message.reply("⏳ Forwarding in progress...")
        
        await message.reply("⏳ Scanning for new messages...")
        
        try:
            count = await self.scan_and_forward_messages()
            if count > 0:
                await message.reply(f"✅ Successfully forwarded {count} new messages")
            else:
                await message.reply("ℹ️ No new messages found since last forward")
        except Exception as e:
            logger.error(f"Error during forwarding: {e}")
            await message.reply("⚠️ An error occurred during forwarding")

    async def run(self):
        """Main bot loop"""
        await self.initialize_client()
        
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)  # Just keep the bot alive

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
