import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *
from motor.motor_asyncio import AsyncIOMotorClient
from plugins.Sorting import matcher
import time

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
USER_SESSION_STRING = "BQFP49AAiVku9pI3VZylmYZ-LJi7gUSLC7iM873LFaQtV7ozu83PEvi3N6ypHhtLaSfTDW9CC7YMK5W6jwgFuJ0ThauW7GnSgkDR7ERtmJtGptXcgA0SX3eWvRepBMWfD3jhGTOK5CveP7UYp5JHsMDMeBAkmwic0R9YWXkwU8jl-bOO8pWisoZkjqOX2-kVacxifW9ZRe52O8zmNB3dF_VTcRCGvp58ZfzaJLHT5lE4_T_TVuHqZK9YUzzstNAHN7yDVZZc49kpRTaGeMhCxjCuSyGDO7iP0NCqzd-DJDr3qe7DT-WfhfqgNMjqoC1BjB5Ksm7qxGK10rPzfqU6vz_5bZSEnQAAAAGVhUI_AA"
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
            await self.mongo_client.server_info()
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def get_last_message_id(self, source_channel):
        """Get the latest message ID from a channel"""
        try:
            async for message in self.user_client.get_chat_history(source_channel, limit=1):
                return message.id
            return 0
        except Exception as e:
            logger.error(f"Error getting last message ID: {e}")
            return 0

    async def load_state(self, set_name):
        """Load or initialize the last forwarded ID"""
        try:
            # Try to load from MongoDB
            doc = await self.db.state.find_one({"set_name": set_name})
            if doc:
                return doc.get("last_forwarded_id", 0)
            
            # Initialize with current last message ID if no record exists
            source_channel = CHANNEL_CONFIGS[set_name]["SOURCE"]
            last_id = await self.get_last_message_id(source_channel)
            await self.save_state(set_name, last_id)
            return last_id
            
        except Exception as e:
            logger.error(f"Error in load_state: {e}")
            return 0

    async def save_state(self, set_name, last_id):
        """Save the current state to MongoDB"""
        try:
            await self.db.state.update_one(
                {"set_name": set_name},
                {"$set": {"last_forwarded_id": last_id}},
                upsert=True
            )
            logger.debug(f"Saved state for {set_name}: {last_id}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    async def get_new_messages(self, source_channel, last_forwarded_id):
        """Get messages newer than last_forwardeded_id"""
        try:
            messages = []
            current_last_id = await self.get_last_message_id(source_channel)
            
            if last_forwarded_id >= current_last_id:
                logger.info(f"No new messages (last: {last_forwarded_id}, current: {current_last_id})")
                return []
            
            logger.info(f"Fetching messages between {last_forwarded_id} and {current_last_id}")
            
            # Fetch messages in reverse order (newest first)
            all_messages = []
            async for message in self.user_client.get_chat_history(
                source_channel,
                limit=None,  # Get all available messages
            ):
                if message.id > last_forwarded_id:
                    all_messages.append(message)
                elif message.id <= last_forwarded_id:
                    break
                
                # Small delay to avoid flooding
                #await asyncio.sleep(0.1)

            messages = sorted(all_messages, key=lambda m: m.id)
            logger.info(f"Found {len(messages)} new messages")
            return messages

        except Exception as e:
            logger.error(f"Error getting new messages: {e}")
            return []

    async def initialize(self):
        """Initialize clients and MongoDB"""
        try:
            await self.init_mongo()

            self.user_client = Client(
                "user_account",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=USER_SESSION_STRING,
                in_memory=True
            )

            self.bot_client = Client(
                "forward_bot",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN
            )

            await self.user_client.start()
            await self.bot_client.start()
            
            # Verify authorization
            user_me = await self.user_client.get_me()
            bot_me = await self.bot_client.get_me()
            logger.info(f"User: @{user_me.username}, Bot: @{bot_me.username}")

            # Register command handlers
            @self.bot_client.on_message(filters.command("forward") & filters.private)
            async def forward_command(_, message: Message):
                await self.handle_forward(message)

            @self.bot_client.on_message(filters.command("channels") & filters.private)
            async def channels_command(_, message: Message):
                await self.handle_channels(message)

            self.initialized = True
            logger.info("Bot initialized successfully")

        except Exception as e:
            logger.critical(f"Initialization failed: {e}")
            raise

    async def scan_and_forward(self, set_name):
        """Process new messages for forwarding"""
        if self.forwarding_active:
            logger.warning("Forwarding already in progress")
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            config = CHANNEL_CONFIGS[set_name]
            source_channel = config["SOURCE"]
            destinations = config["DESTINATIONS"]
            
            # Get the last processed ID
            last_forwarded_id = await self.load_state(set_name)
            logger.info(f"Last forwarded ID for {set_name}: {last_forwarded_id}")
            
            # Get new messages
            new_messages = await self.get_new_messages(source_channel, last_forwarded_id)
            if not new_messages:
                logger.info(f"No new messages for {set_name}")
                return 0
                
            logger.info(f"Found {len(new_messages)} new messages for {set_name}")
            
            # Process in chronological order (oldest first)
            for message in reversed(new_messages):
                try:
                    # Skip service messages and empty messages
                    if message.service or (not message.text and not message.caption and not message.media):
                        continue
                    
                    text = message.text or message.caption or ""
                    subject = matcher.find_subject(text)
                    if not subject or subject not in destinations:
                        logger.debug(f"Skipping message {message.id} - no matching subject")
                        continue
                    
                    # Forward the message
                    await self.bot_client.copy_message(
                        chat_id=destinations[subject],
                        from_chat_id=source_channel,
                        message_id=message.id
                    )
                    
                    # Update the last forwarded ID
                    await self.save_state(set_name, message.id)
                    forwarded_count += 1
                    logger.info(f"Forwarded message {message.id} to {subject}")
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                    
                except RPCError as e:
                    logger.error(f"Failed to forward message {message.id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {e}")

            return forwarded_count
            
        finally:
            self.forwarding_active = False
            logger.info(f"Completed forwarding for {set_name}: {forwarded_count} messages")

    async def handle_forward(self, message: Message):
        """Handle the /forward command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("🚨 Access denied")
            
            if not self.initialized:
                return await message.reply("⚡ Bot initializing...")
            
            start_time = time.time()
            processing_msg = await message.reply("🔄 Processing forwarding request...")
            
            total_forwarded = 0
            for set_name in CHANNEL_CONFIGS:
                count = await self.scan_and_forward(set_name)
                total_forwarded += count
            
            elapsed = time.time() - start_time
            response = (
                f"📊 **Forwarding Complete**\n\n"
                f"✅ Forwarded: {total_forwarded} messages\n"
                f"⏱️ Time taken: {elapsed:.2f} seconds\n\n"
            )
            
            # Add details for each channel set
            for set_name in CHANNEL_CONFIGS:
                last_id = await self.load_state(set_name)
                current_id = await self.get_last_message_id(CHANNEL_CONFIGS[set_name]["SOURCE"])
                
                response += (
                    f"🔹 **{set_name}**\n"
                    f"Last forwarded ID: `{last_id}`\n"
                    f"Current last ID: `{current_id}`\n\n"
                )
            
            await processing_msg.edit_text(response)
            
        except Exception as e:
            await message.reply(f"⚠️ Error during forwarding: {str(e)}")
            logger.error(f"Forward error: {e}")

    async def handle_channels(self, message: Message):
        """Handle the /channels command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("🚨 Access denied")
            
            response = "📚 **Configured Channels**\n\n"
            for set_name, config in CHANNEL_CONFIGS.items():
                try:
                    chat = await self.user_client.get_chat(config["SOURCE"])
                    source_name = chat.title
                except:
                    source_name = "Unknown"
                
                response += f"🔷 **{set_name}**\n"
                response += f"Source: {source_name} (`{config['SOURCE']}`)\n"
                response += "Destinations:\n"
                
                for subject, channel_id in config["DESTINATIONS"].items():
                    try:
                        dest_chat = await self.bot_client.get_chat(channel_id)
                        dest_name = dest_chat.title
                    except:
                        dest_name = "Unknown"
                    response += f"• {subject}: {dest_name} (`{channel_id}`)\n"
                
                response += "\n"
            
            await message.reply(response)
            
        except Exception as e:
            await message.reply(f"⚠️ Error listing channels: {str(e)}")
            logger.error(f"Channels error: {e}")

    async def run(self):
        """Main bot loop"""
        await self.initialize()
        logger.info("Bot is ready and waiting for commands")
        
        while True:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    hybrid = HybridForwarder()
    try:
        asyncio.run(hybrid.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
