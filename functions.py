import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *
import pickle
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

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
USER_SESSION_STRING = "BQFP49AAn6jgY8Wwp8nhPAiF1PoD6hVxl0HWUtx8AldMjcpUOpkB0jI63t8aRNmAHQ_CWyU7CPZCiQVSOFMeL-5pLl2Z2D18R7uJx52rivl46MEe1i9aFC9gUxXRHChvUgAJWTAyytSg_BVKb8LhAKnPvNQoeV8znsy6U0wtEHY9a_lu04-fxzB5mAWZDrS12HGbkZvsocaEHgMLiGUl3q83bThYzHAciMjgzKxNiKB7VeLsyy5Ua01Ndh2uRP1KL43sp-KtF9wSw4wNV-LGtAGnMhDBG8_0Yt3zKIBk21KtM7BGsZZinxdgfs3sU53EmoAk61B8YEJ5MfAikBSRI00B8Ng4AAAAAAGVhUI_AA"
YOUR_USER_ID = 2031106491

# Channel configurations
CHANNEL_CONFIGS = {
    "SET_1": {
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
STATS_FILE = "forwarder_stats.pkl"

class HybridForwarder:
    def __init__(self):
        self.user_client = None
        self.bot_client = None
        self.last_forwarded_ids = {set_name: 0 for set_name in CHANNEL_CONFIGS}
        self.forwarding_active = {set_name: False for set_name in CHANNEL_CONFIGS}
        self.initialized = False
        self.stats = {
            'total_forwarded': 0,
            'set_stats': {set_name: {'forwarded': 0, 'last_run': None} for set_name in CHANNEL_CONFIGS},
            'subject_stats': defaultdict(int),
            'hourly_stats': defaultdict(int),
            'errors': 0
        }
        self.start_time = time.time()

    async def load_state(self):
        """Load the last forwarded IDs and statistics from files"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'rb') as f:
                    state = pickle.load(f)
                    for set_name in CHANNEL_CONFIGS:
                        self.last_forwarded_ids[set_name] = state.get(set_name, {}).get('last_forwarded_id', 0)
                    logger.info(f"Loaded state: {self.last_forwarded_ids}")
            
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'rb') as f:
                    self.stats = pickle.load(f)
                    logger.info("Loaded statistics")
        except Exception as e:
            logger.error(f"Error loading state/stats: {e}")
            for set_name in CHANNEL_CONFIGS:
                self.last_forwarded_ids[set_name] = 0
            self.stats = {
                'total_forwarded': 0,
                'set_stats': {set_name: {'forwarded': 0, 'last_run': None} for set_name in CHANNEL_CONFIGS},
                'subject_stats': defaultdict(int),
                'hourly_stats': defaultdict(int),
                'errors': 0
            }

    async def save_state(self):
        """Save the current state and statistics to files"""
        try:
            state = {}
            for set_name in CHANNEL_CONFIGS:
                state[set_name] = {
                    'last_forwarded_id': self.last_forwarded_ids[set_name]
                }
            with open(STATE_FILE, 'wb') as f:
                pickle.dump(state, f)
            
            with open(STATS_FILE, 'wb') as f:
                pickle.dump(self.stats, f)
                
            logger.debug("State and statistics saved")
        except Exception as e:
            logger.error(f"Error saving state/stats: {e}")

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

            # Register command handlers
            @self.bot_client.on_message(filters.command("forward") & filters.private)
            async def forward_command(_, message: Message):
                await self.handle_forward(message)

            @self.bot_client.on_message(filters.command("stats") & filters.private)
            async def stats_command(_, message: Message):
                await self.handle_stats(message)

            @self.bot_client.on_message(filters.command("status") & filters.private)
            async def status_command(_, message: Message):
                await self.handle_status(message)

            self.initialized = True
            logger.info("Hybrid bot initialized successfully")

        except Exception as e:
            logger.critical(f"Initialization failed: {e}")
            raise

    async def get_new_messages_batch(self, source_channel: int, last_forwarded_id: int) -> List[Message]:
        """Get a batch of new messages since last_forwarded_id"""
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
            logger.error(f"Error getting messages from channel {source_channel}: {e}")
            return []

    async def scan_and_forward(self, set_name: str) -> Tuple[int, int]:
        """Scan for new messages and forward them for a specific channel set"""
        if self.forwarding_active[set_name]:
            logger.warning(f"Forwarding already in progress for {set_name}")
            return 0, 0
        
        self.forwarding_active[set_name] = True
        forwarded_count = 0
        processed_count = 0
        current_hour = datetime.now().hour
        
        try:
            config = CHANNEL_CONFIGS[set_name]
            source_channel = config["SOURCE"]
            destinations = config["DESTINATIONS"]
            last_forwarded_id = self.last_forwarded_ids[set_name]

            # Get current latest message ID
            current_latest_id = 0
            async for message in self.user_client.get_chat_history(source_channel, limit=1):
                current_latest_id = message.id
                break

            if current_latest_id <= last_forwarded_id:
                logger.info(f"No new messages available in channel {source_channel}")
                return 0, 0

            logger.info(f"Processing messages between {last_forwarded_id} and {current_latest_id} in {set_name}")

            # Process messages in batches
            while True:
                messages = await self.get_new_messages_batch(source_channel, last_forwarded_id)
                if not messages:
                    break
                
                # Process messages in chronological order (oldest first)
                for message in reversed(messages):
                    processed_count += 1
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
                            
                            # Update statistics
                            self.stats['total_forwarded'] += 1
                            self.stats['set_stats'][set_name]['forwarded'] += 1
                            self.stats['subject_stats'][subject] += 1
                            self.stats['hourly_stats'][current_hour] += 1
                            
                            logger.info(f"Successfully forwarded message {message.id}")
                            
                            # Small delay between forwards to avoid rate limits
                            await asyncio.sleep(0.5)
                            
                        except RPCError as e:
                            logger.error(f"Failed to forward message {message.id}: {e}")
                            self.stats['errors'] += 1
                            continue
                            
                    except Exception as e:
                        logger.error(f"Error processing message {message.id}: {e}")
                        self.stats['errors'] += 1
                        continue
                
                # Update last processed ID
                last_forwarded_id = messages[0].id  # Newest message in this batch
                
                # Save state periodically
                if processed_count % 10 == 0:
                    await self.save_state()
                    
                # Small delay between batches
                await asyncio.sleep(1)

            # Update last run time
            self.stats['set_stats'][set_name]['last_run'] = datetime.now().isoformat()
            
            return forwarded_count, processed_count
            
        finally:
            self.forwarding_active[set_name] = False
            await self.save_state()
            logger.info(f"Forwarding completed for {set_name}. Forwarded: {forwarded_count}, Processed: {processed_count}")

    async def handle_forward(self, message: Message):
        """Handle the /forward command with parallel processing"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                logger.warning(f"Unauthorized access attempt from {message.from_user.id}")
                return await message.reply("❌ Unauthorized")
            
            logger.info(f"Forward command received from {message.from_user.id}")
            
            if not self.initialized:
                return await message.reply("⚠️ Bot not fully initialized yet")
            
            status_msg = await message.reply("🚀 Starting parallel processing for all channel sets...")
            
            # Create tasks for all sets
            tasks = []
            for set_name in CHANNEL_CONFIGS:
                tasks.append(self.scan_and_forward(set_name))
            
            # Run all tasks in parallel
            results = await asyncio.gather(*tasks)
            
            # Prepare detailed response
            response = "📊 Forwarding Results:\n\n"
            total_forwarded = 0
            total_processed = 0
            
            for set_name, (forwarded, processed) in zip(CHANNEL_CONFIGS.keys(), results):
                efficiency = 0.0
                if processed > 0:
                    efficiency = (forwarded / processed) * 100
                
                response += (
                    f"🔹 *{set_name}:*\n"
                    f"   - Processed: `{processed}` messages\n"
                    f"   - Forwarded: `{forwarded}` messages\n"
                    f"   - Efficiency: `{efficiency:.1f}%`\n\n"
                )
                
                total_forwarded += forwarded
                total_processed += processed
            
            # Add summary
            overall_efficiency = 0.0
            if total_processed > 0:
                overall_efficiency = (total_forwarded / total_processed) * 100
                
            response += (
                f"✨ *Summary*\n"
                f"Total Processed: `{total_processed}`\n"
                f"Total Forwarded: `{total_forwarded}`\n"
                f"Overall Efficiency: `{overall_efficiency:.1f}%`"
            )
            
            await status_msg.edit_text(response)
            
        except Exception as e:
            logger.error(f"Error in handle_forward: {e}")
            self.stats['errors'] += 1
            await message.reply(f"⚠️ Error: {str(e)}")

    async def handle_stats(self, message: Message):
        """Handle the /stats command with detailed statistics"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("❌ Unauthorized")
                
            uptime_seconds = int(time.time() - self.start_time)
            uptime_str = f"{uptime_seconds//3600}h {(uptime_seconds%3600)//60}m"
            
            # Prepare subject stats
            subject_stats = sorted(self.stats['subject_stats'].items(), key=lambda x: x[1], reverse=True)
            subject_text = "\n".join(f"  - {sub}: {count}" for sub, count in subject_stats[:5])
            
            # Prepare hourly stats
            hourly_stats = sorted(self.stats['hourly_stats'].items(), key=lambda x: x[1], reverse=True)
            hourly_text = "\n".join(f"  - {hour:02d}:00 - {hour+1:02d}:00: {count}" for hour, count in hourly_stats[:3])
            
            response = (
                "📈 *Bot Statistics*\n\n"
                f"⏱ Uptime: `{uptime_str}`\n"
                f"🔄 Total Forwarded: `{self.stats['total_forwarded']}`\n"
                f"⚠️ Total Errors: `{self.stats['errors']}`\n\n"
                "📚 *Top Subjects*\n"
                f"{subject_text}\n\n"
                "⏰ *Busiest Hours*\n"
                f"{hourly_text}\n\n"
                "Use /status for current channel status"
            )
            
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error in handle_stats: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def handle_status(self, message: Message):
        """Handle the /status command with current channel status"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                return await message.reply("❌ Unauthorized")
                
            response = "📡 *Current Channel Status*\n\n"
            
            # Get current status for each set
            for set_name in CHANNEL_CONFIGS:
                config = CHANNEL_CONFIGS[set_name]
                last_run = self.stats['set_stats'][set_name]['last_run']
                last_run_str = datetime.fromisoformat(last_run).strftime("%Y-%m-%d %H:%M") if last_run else "Never"
                
                # Get current latest message ID
                current_latest_id = 0
                try:
                    async for msg in self.user_client.get_chat_history(config["SOURCE"], limit=1):
                        current_latest_id = msg.id
                        break
                except Exception as e:
                    logger.error(f"Error getting latest message for {set_name}: {e}")
                    current_latest_id = "Error"
                
                waiting_count = "N/A"
                if isinstance(current_latest_id, int) and isinstance(self.last_forwarded_ids[set_name], int):
                    waiting_count = current_latest_id - self.last_forwarded_ids[set_name]
                
                response += (
                    f"🔹 *{set_name}:*\n"
                    f"  - Last Run: `{last_run_str}`\n"
                    f"  - Last Forwarded ID: `{self.last_forwarded_ids[set_name]}`\n"
                    f"  - Current Latest ID: `{current_latest_id}`\n"
                    f"  - Messages Waiting: `{waiting_count}`\n\n"
                )
            
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error in handle_status: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def run(self):
        """Main bot loop"""
        await self.initialize()
        
        if not self.initialized:
            logger.critical("Bot failed to initialize properly")
            return
            
        logger.info("Bot is running. Commands available: /forward, /stats, /status")
        
        # Keep the bot running
        while True:
            try:
                await asyncio.sleep(3600)  # Sleep for 1 hour
            except asyncio.CancelledError:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                self.stats['errors'] += 1
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

