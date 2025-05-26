import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *
import pickle
import os

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
USER_SESSION_STRING = "BQFP49AAn6jgY8Wwp8nhPAiF1PoD6hVxl0HWUtx8AldMjcpUOpkB0jI63t8aRNmAHQ_CWyU7CPZCiQVSOFMeL-5pLl2Z2D18R7uJx52rivl46MEe1i9aFC9gUxXRHChvUgAJWTAyytSg_BVKb8LhAKnPvNQoeV8znsy6U0wtEHY9a_lu04-fxzB5mAWZDrS12HGbkZvsocaEHgMLiGUl3q83bThYzHAciMjgzKxNiKB7VeLsyy5Ua01Ndh2uRP1KL43sp-KtF9wSw4wNV-LGtAGnMhDBG8_0Yt3zKIBk21KtM7BGsZZinxdgfs3sU53EmoAk61B8YEJ5MfAikBSRI00B8Ng4AAAAAAGVhUI_AA"
YOUR_USER_ID = 2031106491

# Channel configurations
CHANNEL_CONFIGS = {
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
    "SET_2": {
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
    "SET_3": {
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

STATE_FILE = "forwarder_state.pkl"

class HybridForwarder:
    def __init__(self):
        self.user_client = None
        self.bot_client = None
        self.last_forwarded_ids = {set_name: 0 for set_name in CHANNEL_CONFIGS}
        self.forwarding_active = False
        self.initialized = False

    async def load_state(self):
        """Load the last forwarded IDs from file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'rb') as f:
                    state = pickle.load(f)
                    for set_name in CHANNEL_CONFIGS:
                        self.last_forwarded_ids[set_name] = state.get(set_name, {}).get('last_forwarded_id', 0)
                    logger.info(f"Loaded state: {self.last_forwarded_ids}")
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            for set_name in CHANNEL_CONFIGS:
                self.last_forwarded_ids[set_name] = 0

    async def save_state(self):
        """Save the current state to file"""
        try:
            state = {}
            for set_name in CHANNEL_CONFIGS:
                state[set_name] = {
                    'last_forwarded_id': self.last_forwarded_ids[set_name]
                }
            with open(STATE_FILE, 'wb') as f:
                pickle.dump(state, f)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    async def initialize(self):
        """Initialize both user and bot clients"""
        try:
            await self.load_state()

            # User client
            self.user_client = Client(
                "user_account",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=USER_SESSION_STRING,
                in_memory=True
            )

            # Bot client
            self.bot_client = Client(
                "forward_bot",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN
            )

            await self.user_client.start()
            await self.bot_client.start()
            
            user_me = await self.user_client.get_me()
            bot_me = await self.bot_client.get_me()
            logger.info(f"User account: @{user_me.username} (ID: {user_me.id})")
            logger.info(f"Bot account: @{bot_me.username} (ID: {bot_me.id})")

            # Initialize last_forwarded_ids
            for set_name, config in CHANNEL_CONFIGS.items():
                if self.last_forwarded_ids[set_name] == 0:
                    async for message in self.user_client.get_chat_history(config["SOURCE"], limit=1):
                        self.last_forwarded_ids[set_name] = message.id
                        logger.info(f"Initialized {set_name} last_forwarded_id: {message.id}")
                        await self.save_state()
                        break

            # Command handlers
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

    async def get_new_messages(self, source_channel, last_forwarded_id):
        """Get new messages since last_forwarded_id"""
        new_messages = []
        try:
            current_latest_id = 0
            async for message in self.user_client.get_chat_history(source_channel, limit=1):
                current_latest_id = message.id
                break

            if current_latest_id <= last_forwarded_id:
                return []

            async for message in self.user_client.get_chat_history(
                source_channel,
                limit=100,
                offset_id=last_forwarded_id
            ):
                if message.id > last_forwarded_id:
                    new_messages.append(message)
                else:
                    break

            return new_messages
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    async def scan_and_forward(self, set_name):
        """Scan and forward messages for a set"""
        if self.forwarding_active:
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            config = CHANNEL_CONFIGS[set_name]
            source_channel = config["SOURCE"]
            destinations = config["DESTINATIONS"]
            last_id = self.last_forwarded_ids[set_name]

            messages = await self.get_new_messages(source_channel, last_id)
            if not messages:
                return 0

            for message in reversed(messages):
                try:
                    if message.service or (not message.text and not message.media):
                        continue
                        
                    text = message.text or message.caption or ""
                    subject = matcher.find_subject(text)
                    
                    if subject and subject in destinations:
                        await self.bot_client.copy_message(
                            chat_id=destinations[subject],
                            from_chat_id=source_channel,
                            message_id=message.id
                        )
                        self.last_forwarded_ids[set_name] = message.id
                        forwarded_count += 1
                        await self.save_state()
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error forwarding message: {e}")
                    continue

            return forwarded_count
            
        finally:
            self.forwarding_active = False

    async def handle_forward(self, message: Message):
        """Handle /forward command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("❌ Unauthorized")
            
            status_msg = await message.reply("**⏳ Processing...**")
            
            total_forwarded = 0
            for set_name in CHANNEL_CONFIGS:
                count = await self.scan_and_forward(set_name)
                total_forwarded += count
            
            await status_msg.edit_text(f"**✅ Forwarded {total_forwarded} messages**")
            
        except Exception as e:
            logger.error(f"Error in handle_forward: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def handle_channels(self, message: Message):
        """Handle /channels command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("❌ Unauthorized")
            
            response = "📡 Connected Channels:\n\n"
            for set_name, config in CHANNEL_CONFIGS.items():
                response += f"🔹 *{set_name}:*\n"
                response += f"  - Source: `{config['SOURCE']}`\n"
                response += "  - Destinations:\n"
                for subject, channel_id in config['DESTINATIONS'].items():
                    response += f"    - {subject}: `{channel_id}`\n"
                response += "\n"
            
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error in handle_channels: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def run(self):
        """Main bot loop"""
        await self.initialize()
        
        if not self.initialized:
            logger.critical("Bot failed to initialize")
            return
            
        logger.info("Bot is running. Commands: /forward, /channels")
        
        while True:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(60)

# Import matcher
from plugins.Sorting import matcher

if __name__ == "__main__":
    hybrid = HybridForwarder()
    try:
        asyncio.run(hybrid.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
