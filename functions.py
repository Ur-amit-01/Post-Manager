import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *
import os
from datetime import datetime
import time
from motor.motor_asyncio import AsyncIOMotorClient
from plugins.Sorting import matcher

# Enhanced logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('forwarder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
USER_SESSION_STRING = "BQFP49AAtzdWt9MoyTVPRh5hxO9J1Vus4_aSBlFfyDpiTE6zf9H5bsfBN58oqA8PbosjbTAx2dHwNERrUgOgcB1i82LQL_T31f3gPBfoKjMUO1E_ZTqgTmOgT0x_TSOUpdwdD3zH0d6Jg9hqqOKEVHuCgovoXojycULckICCDWlXu9BJ6jn6KkmBtvgJyZ5wU6wg-qoqTHZYof0tn-pbkMWLd9IkklXTJrY2rqceDJHiqPfTtgDLU1BF1VvSb8YnHKog2YMHpAK68DYyHJHdEdjxbC_i8TS4p0GP46hV7DybCqEpOz2OyfDreRrKov3JtguQua-Fbz0pCx3JRvQzsQOjOoaZgQAAAAGVhUI_AA"
YOUR_USER_ID = 2031106491

# Channel configurations
CHANNEL_CONFIGS = {
    "Yakeen 1.0": {
        "SOURCE": -1002027394591,
        "DESTINATIONS": {
            'Physics': -1002611033664,
            'Inorganic Chemistry': -1002530766847,
            'Organic Chemistry': -1002623306070,
            'Physical Chemistry': -1002533864126,
            'Botany': -1002537691102,
            'Zoology': -1002549422245
        }
    },
    "Yakeen 2.0": {
        "SOURCE": -1002027394591,
        "DESTINATIONS": {
            'Physics': -1002611033664,
            'Inorganic Chemistry': -1002530766847,
            'Organic Chemistry': -1002623306070,
            'Physical Chemistry': -1002533864126,
            'Botany': -1002537691102,
            'Zoology': -1002549422245
        }
    },
    "Yakeen 3.0": {
        "SOURCE": -1002027394591,
        "DESTINATIONS": {
            'Physics': -1002611033664,
            'Inorganic Chemistry': -1002530766847,
            'Organic Chemistry': -1002623306070,
            'Physical Chemistry': -1002533864126,
            'Botany': -1002537691102,
            'Zoology': -1002549422245
        }
    }
}

class HybridForwarder:
    def __init__(self):
        self.user_client = None
        self.bot_client = None
        self.mongo_client = None
        self.db = None
        self.forwarding_active = False
        self.initialized = False
        self.start_time = time.time()

    async def init_mongo(self):
        """Initialize MongoDB connection"""
        try:
            self.mongo_client = AsyncIOMotorClient(DB_URL)
            self.db = self.mongo_client["telegram_forwarder"]
            await self.mongo_client.server_info()  # Test connection
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def load_state(self, set_name):
        """Load the last forwarded ID from MongoDB"""
        try:
            doc = await self.db.state.find_one({"set_name": set_name})
            return doc["last_forwarded_id"] if doc else 0
        except Exception as e:
            logger.error(f"Error loading state for {set_name}: {e}")
            return 0

    async def save_state(self, set_name, last_id):
        """Save the current state to MongoDB"""
        try:
            await self.db.state.update_one(
                {"set_name": set_name},
                {"$set": {"last_forwarded_id": last_id}},
                upsert=True
            )
            logger.debug(f"State saved for {set_name}: {last_id}")
        except Exception as e:
            logger.error(f"Error saving state for {set_name}: {e}")

    async def initialize(self):
        """Initialize clients and MongoDB"""
        try:
            # Initialize MongoDB first
            await self.init_mongo()

            # User client (uses session string)
            self.user_client = Client(
                "user_account",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=USER_SESSION_STRING,
                in_memory=True
            )

            # Bot client (uses bot token)
            self.bot_client = Client(
                "forward_bot",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN
            )

            # Start both clients
            await self.user_client.start()
            await self.bot_client.start()
            
            # Verify authorization
            user_me = await self.user_client.get_me()
            bot_me = await self.bot_client.get_me()
            logger.info(f"User account: @{user_me.username} (ID: {user_me.id})")
            logger.info(f"Bot account: @{bot_me.username} (ID: {bot_me.id})")

            # Register command handlers
            @self.bot_client.on_message(filters.command("forward") & filters.private)
            async def forward_command(_, message: Message):
                await self.handle_forward(message)

            @self.bot_client.on_message(filters.command("channels") & filters.private)
            async def channels_command(_, message: Message):
                await self.handle_channels(message)

            self.initialized = True
            logger.info("Hybrid bot initialized successfully")

        except Exception as e:
            logger.critical(f"Initialization failed: {e}")
            raise

    async def get_new_messages_fast(self, source_channel, last_forwarded_id):
        """Optimized message fetching using offset and limit"""
        try:
            messages = []
            current_id = 0
            
            # Get the most recent message first to establish current_id
            async for message in self.user_client.get_chat_history(source_channel, limit=1):
                current_id = message.id
                if current_id > last_forwarded_id:
                    messages.append(message)
                break
            
            if not messages:
                return []
            
            # Fetch messages in batches until we reach last_forwarded_id
            while True:
                batch = []
                async for message in self.user_client.get_chat_history(
                    source_channel,
                    limit=100,
                    offset=len(messages),
                    offset_id=current_id
                ):
                    if message.id <= last_forwarded_id:
                        return messages
                    batch.append(message)
                
                if not batch:
                    break
                
                messages.extend(batch)
                current_id = batch[-1].id
                
                # Small delay to prevent flooding
                await asyncio.sleep(0.1)
            
            return messages

        except Exception as e:
            logger.error(f"Error getting new messages: {e}")
            return []

    async def scan_and_forward(self, set_name):
        """Optimized scanning and forwarding"""
        if self.forwarding_active:
            logger.warning("Forwarding already in progress")
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            config = CHANNEL_CONFIGS[set_name]
            source_channel = config["SOURCE"]
            destinations = config["DESTINATIONS"]
            last_forwarded_id = await self.load_state(set_name)

            new_messages = await self.get_new_messages_fast(source_channel, last_forwarded_id)
            if not new_messages:
                return 0

            # Process messages in chronological order (oldest first)
            for message in reversed(new_messages):
                try:
                    # Skip service messages and empty messages quickly
                    if message.service or (not message.text and not message.caption and not message.media):
                        continue
                    
                    text = message.text or message.caption or ""
                    subject = matcher.find_subject(text)
                    if not subject or subject not in destinations:
                        continue
                    
                    # Forward the message
                    await self.bot_client.copy_message(
                        chat_id=destinations[subject],
                        from_chat_id=source_channel,
                        message_id=message.id
                    )
                    
                    # Update state after each successful forward
                    await self.save_state(set_name, message.id)
                    forwarded_count += 1
                    
                    # Minimal delay between forwards
                    await asyncio.sleep(0.3)
                    
                except RPCError as e:
                    logger.error(f"Failed to forward message {message.id}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {e}")
                    continue

            return forwarded_count
            
        finally:
            self.forwarding_active = False
            logger.info(f"Forwarding completed for {set_name}. Total forwarded: {forwarded_count}")

    async def handle_forward(self, message: Message):
        """Handle the /forward command with improved response"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                await message.reply("🚨 **ACCESS DENIED** 🚨\n\n`Unauthorized user detected`")
                return
            
            if not self.initialized:
                await message.reply("⚡ **SYSTEM INITIALIZATION REQUIRED**")
                return
            
            processing_msg = await message.reply("🛰️ **SCANNING CHANNELS**\n\n`Processing request...`")
            
            response = "📡 **FORWARDING REPORT**\n\n"
            total_forwarded = 0
            
            for set_name in CHANNEL_CONFIGS:
                start_time = time.time()
                forwarded_count = await self.scan_and_forward(set_name)
                elapsed = time.time() - start_time
                
                if forwarded_count > 0:
                    response += f"✅ **{set_name}**\n`Forwarded:` {forwarded_count} messages\n`Time:` {elapsed:.2f}s\n\n"
                    total_forwarded += forwarded_count
                else:
                    last_id = await self.load_state(set_name)
                    async for msg in self.user_client.get_chat_history(CHANNEL_CONFIGS[set_name]["SOURCE"], limit=1):
                        current_id = msg.id
                        break
                    response += f"ℹ️ **{set_name}**\n`Status:` Up to date\n`Last ID:` {last_id}\n`Current ID:` {current_id}\n\n"
            
            response += f"✨ **TOTAL FORWARDED:** {total_forwarded} messages\n"
            response += f"⏱️ **PROCESS TIME:** {time.time() - self.start_time:.2f}s"
            
            await processing_msg.edit_text(response)
            
        except Exception as e:
            error_msg = f"""
⚠️ **ERROR** ⚠️

`{type(e).__name__}: {str(e)}`
"""
            await message.reply(error_msg)
            logger.error(f"Error in handle_forward: {e}")

    async def handle_channels(self, message: Message):
        """Handle /channels command to list all configured channels"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                await message.reply("🚨 **ACCESS DENIED**")
                return
            
            response = "📚 **CHANNEL CONFIGURATIONS**\n\n"
            
            for set_name, config in CHANNEL_CONFIGS.items():
                try:
                    chat = await self.user_client.get_chat(config["SOURCE"])
                    source_name = chat.title
                except:
                    source_name = "Unknown"
                
                response += f"🔷 **{set_name}**\n"
                response += f"`Source:` {source_name} (`{config['SOURCE']}`)\n"
                response += "`Destinations:`\n"
                
                for subject, channel_id in config["DESTINATIONS"].items():
                    try:
                        dest_chat = await self.bot_client.get_chat(channel_id)
                        dest_name = dest_chat.title
                    except:
                        dest_name = "Unknown"
                    response += f"  • {subject}: {dest_name} (`{channel_id}`)\n"
                
                response += "\n"
            
            await message.reply(response)
            
        except Exception as e:
            await message.reply(f"⚠️ Error listing channels: {str(e)}")
            logger.error(f"Error in handle_channels: {e}")

    async def run(self):
        """Main bot loop"""
        await self.initialize()
        
        if not self.initialized:
            logger.critical("Bot failed to initialize properly")
            return
            
        logger.info("Bot is running. Commands: /forward, /channels")
        
        # Keep the bot running
        while True:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    hybrid = HybridForwarder()
    try:
        asyncio.run(hybrid.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
