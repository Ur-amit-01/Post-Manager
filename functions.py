import time 
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *
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
            self.mongo_client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.mongo_client["telegram_forwarder"]
            await self.mongo_client.server_info()
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def load_state(self, set_name):
        """Load the last forwarded ID from MongoDB"""
        try:
            doc = await self.db.state.find_one({"set_name": set_name})
            if doc:
                return doc["last_forwarded_id"]
            
            # Initialize with the last message ID if no state exists
            async for message in self.user_client.get_chat_history(
                CHANNEL_CONFIGS[set_name]["SOURCE"], 
                limit=1
            ):
                await self.save_state(set_name, message.id)
                return message.id
                
            return 0
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
        except Exception as e:
            logger.error(f"Error saving state for {set_name}: {e}")

    async def initialize(self):
        """Initialize clients and MongoDB - Minimal startup checks"""
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
            
            # Verify authorization (minimal check)
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

    async def get_new_messages_fast(self, source_channel, last_forwarded_id):
        """Fetch only new messages since last_forwarded_id"""
        try:
            messages = []
            async for message in self.user_client.get_chat_history(
                source_channel,
                limit=100,
                offset_id=last_forwarded_id
            ):
                if message.id > last_forwarded_id:
                    messages.append(message)
                else:
                    break
            
            return messages

        except Exception as e:
            logger.error(f"Error getting new messages: {e}")
            return []

    async def scan_and_forward(self, set_name):
        """Process new messages for a channel set"""
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

            # Process in chronological order (oldest first)
            for message in reversed(new_messages):
                try:
                    if message.service or (not message.text and not message.caption and not message.media):
                        continue
                    
                    text = message.text or message.caption or ""
                    subject = matcher.find_subject(text)
                    if not subject or subject not in destinations:
                        continue
                    
                    await self.bot_client.copy_message(
                        chat_id=destinations[subject],
                        from_chat_id=source_channel,
                        message_id=message.id
                    )
                    
                    await self.save_state(set_name, message.id)
                    forwarded_count += 1
                    await asyncio.sleep(0.3)  # Rate limit
                    
                except RPCError as e:
                    logger.error(f"Forward failed for {message.id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing {message.id}: {e}")

            return forwarded_count
            
        finally:
            self.forwarding_active = False
            logger.info(f"Completed forwarding for {set_name}: {forwarded_count}")

    async def handle_forward(self, message: Message):
        """Handle /forward command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("🚨 Access denied")
            
            if not self.initialized:
                return await message.reply("⚡ Initializing...")
            
            start_time = time.time()
            processing_msg = await message.reply("🔄 Processing...")
            
            total_forwarded = 0
            for set_name in CHANNEL_CONFIGS:
                count = await self.scan_and_forward(set_name)
                total_forwarded += count
            
            elapsed = time.time() - start_time
            await processing_msg.edit_text(
                f"✅ Forwarded {total_forwarded} messages\n"
                f"⏱️ Took {elapsed:.2f} seconds"
            )
            
        except Exception as e:
            await message.reply(f"⚠️ Error: {str(e)}")
            logger.error(f"Forward error: {e}")

    async def handle_channels(self, message: Message):
        """Handle /channels command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("🚨 Access denied")
            
            response = "📚 Configured Channels:\n\n"
            for set_name, config in CHANNEL_CONFIGS.items():
                try:
                    chat = await self.user_client.get_chat(config["SOURCE"])
                    source_name = chat.title
                except:
                    source_name = "Unknown"
                
                response += f"🔹 **{set_name}**\nSource: {source_name}\n"
                response += "Destinations:\n"
                
                for subject, channel_id in config["DESTINATIONS"].items():
                    try:
                        dest_chat = await self.bot_client.get_chat(channel_id)
                        dest_name = dest_chat.title
                    except:
                        dest_name = "Unknown"
                    response += f"- {subject}: {dest_name}\n"
                
                response += "\n"
            
            await message.reply(response)
            
        except Exception as e:
            await message.reply(f"⚠️ Error: {str(e)}")
            logger.error(f"Channels error: {e}")

    async def run(self):
        """Main bot loop - Minimal initialization"""
        await self.initialize()
        logger.info("Bot ready for commands")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    hybrid = HybridForwarder()
    try:
        asyncio.run(hybrid.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")

