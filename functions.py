import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *
import pickle
import os

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

STATE_FILE = "forwarder_state.pkl"

class HybridForwarder:
    def __init__(self):
        self.user_client = None
        self.bot_client = None
        self.last_forwarded_ids = {set_name: 0 for set_name in CHANNEL_CONFIGS}  # Track IDs per set
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
            else:
                logger.info("No state file found, starting fresh")
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
            logger.debug(f"State saved: {self.last_forwarded_ids}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    async def initialize(self):
        """Initialize both user and bot clients"""
        try:
            # Load previous state
            await self.load_state()

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

            # Initialize last_forwarded_ids if not set
            for set_name, config in CHANNEL_CONFIGS.items():
                if self.last_forwarded_ids[set_name] == 0:
                    try:
                        async for message in self.user_client.get_chat_history(config["SOURCE"], limit=1):
                            self.last_forwarded_ids[set_name] = message.id
                            logger.info(f"Initialized {set_name} last_forwarded_id to current latest message: {message.id}")
                            await self.save_state()
                            break
                    except Exception as e:
                        logger.error(f"Failed to get latest message ID for {set_name}: {e}")
                        raise

            # Register command handler
            @self.bot_client.on_message(filters.command("forward") & filters.private)
            async def forward_command(_, message: Message):
                await self.handle_forward(message)

            self.initialized = True
            logger.info("Hybrid bot initialized successfully")

        except Exception as e:
            logger.critical(f"Initialization failed: {e}")
            raise

    async def get_all_new_messages(self, source_channel, last_forwarded_id):
        """Get all messages newer than last_forwarded_id for a specific source channel"""
        new_messages = []
        try:
            # First get the current latest message ID
            current_latest_id = 0
            async for message in self.user_client.get_chat_history(source_channel, limit=1):
                current_latest_id = message.id
                break

            if current_latest_id <= last_forwarded_id:
                logger.info(f"No new messages available in channel {source_channel}")
                return []

            logger.info(f"Scanning for messages between {last_forwarded_id} and {current_latest_id} in channel {source_channel}")

            # Collect all messages newer than last_forwarded_id
            all_messages = []
            offset_id = 0  # Start from the newest message
            
            while True:
                batch = []
                async for message in self.user_client.get_chat_history(
                    source_channel,
                    limit=100,
                    offset_id=offset_id
                ):
                    batch.append(message)
                
                if not batch:
                    break
                    
                # Find where our last_forwarded_id is in this batch
                for i, msg in enumerate(batch):
                    if msg.id <= last_forwarded_id:
                        # We've reached messages we've already processed
                        new_messages = [m for m in batch[:i] if m.id > last_forwarded_id]
                        all_messages.extend(new_messages)
                        logger.info(f"Found {len(new_messages)} new messages in this batch")
                        return all_messages
                    
                # All messages in this batch are new
                all_messages.extend(batch)
                offset_id = batch[-1].id  # Move to next older batch
                
                # Small delay to avoid flooding
                await asyncio.sleep(0.5)

            return all_messages

        except Exception as e:
            logger.error(f"Error getting new messages from channel {source_channel}: {e}")
            return []

    async def scan_and_forward(self, set_name):
        """Scan for new messages and forward them for a specific channel set"""
        if self.forwarding_active:
            logger.warning("Forwarding already in progress")
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            config = CHANNEL_CONFIGS[set_name]
            source_channel = config["SOURCE"]
            destinations = config["DESTINATIONS"]
            last_forwarded_id = self.last_forwarded_ids[set_name]

            new_messages = await self.get_all_new_messages(source_channel, last_forwarded_id)
            if not new_messages:
                return 0

            # Process messages in chronological order (oldest first)
            for message in reversed(new_messages):
                try:
                    # Skip service messages (joins, pins, etc.)
                    if message.service:
                        logger.debug(f"Skipping service message ID {message.id}")
                        continue
                        
                    text = message.text or message.caption or ""
                    logger.debug(f"Processing message {message.id} with text: {text[:50]}...")
                    
                    # Skip if message is empty and has no media
                    if not text and not message.media:
                        logger.debug(f"Skipping empty message ID {message.id}")
                        continue
                    
                    subject = matcher.find_subject(text)
                    if not subject:
                        logger.debug(f"No subject found in message {message.id}")
                        continue
                        
                    if subject not in destinations:
                        logger.debug(f"Subject '{subject}' not in destination channels for {set_name}")
                        continue
                        
                    dest_channel = destinations[subject]
                    logger.info(f"Attempting to forward message {message.id} to {subject} (Channel: {dest_channel})")
                    
                    try:
                        await self.bot_client.copy_message(
                            chat_id=dest_channel,
                            from_chat_id=source_channel,
                            message_id=message.id
                        )
                        self.last_forwarded_ids[set_name] = message.id
                        forwarded_count += 1
                        logger.info(f"Successfully forwarded message {message.id}")
                        
                        # Save state after each successful forward
                        await self.save_state()
                        
                        # Small delay between forwards to avoid rate limits
                        await asyncio.sleep(1)
                        
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
        """Handle the /forward command"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                logger.warning(f"Unauthorized access attempt from {message.from_user.id}")
                return await message.reply("❌ Unauthorized")
            
            logger.info(f"Forward command received from {message.from_user.id}")
            
            if not self.initialized:
                return await message.reply("⚠️ Bot not fully initialized yet")
            
            await message.reply("**⏳ Scanning for new messages...**")
            
            response = ""
            for set_name in CHANNEL_CONFIGS:
                forwarded_count = await self.scan_and_forward(set_name)
                if forwarded_count > 0:
                    response += f"**✅ {set_name}: Forwarded {forwarded_count} message(s)\n**"
                else:
                    # Get current latest message ID for more informative response
                    current_latest_id = 0
                    async for msg in self.user_client.get_chat_history(CHANNEL_CONFIGS[set_name]["SOURCE"], limit=1):
                        current_latest_id = msg.id
                        break
                    
                    response += f"**ℹ️ {set_name}: No new messages (Current: {current_latest_id}, Last forwarded: {self.last_forwarded_ids[set_name]})\n**"
            
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error in handle_forward: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def run(self):
        """Main bot loop"""
        await self.initialize()
        
        if not self.initialized:
            logger.critical("Bot failed to initialize properly")
            return
            
        logger.info("Bot is running. Use /forward command to process new messages.")
        
        # Keep the bot running
        while True:
            try:
                await asyncio.sleep(3600)  # Sleep for 1 hour
            except asyncio.CancelledError:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

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
