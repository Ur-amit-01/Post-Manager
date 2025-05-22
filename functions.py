import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *

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

USER_SESSION_STRING = "BQFP49AAn6jgY8Wwp8nhPAiF1PoD6hVxl0HWUtx8AldMjcpUOpkB0jI63t8aRNmAHQ_CWyU7CPZCiQVSOFMeL-5pLl2Z2D18R7uJx52rivl46MEe1i9aFC9gUxXRHChvUgAJWTAyytSg_BVKb8LhAKnPvNQoeV8znsy6U0wtEHY9a_lu04-fxzB5mAWZDrS12HGbkZvsocaEHgMLiGUl3q83bThYzHAciMjgzKxNiKB7VeLsyy5Ua01Ndh2uRP1KL43sp-KtF9wSw4wNV-LGtAGnMhDBG8_0Yt3zKIBk21KtM7BGsZZinxdgfs3sU53EmoAk61B8YEJ5MfAikBSRI00B8Ng4AAAAAAGVhUI_AA"
YOUR_USER_ID = 2031106491

SOURCE_CHANNEL = -1002027394591
DESTINATION_CHANNELS = {
    'Physics': -1002611033664,
    'Inorganic Chemistry': -1002530766847,
    'Organic Chemistry': -1002623306070,
    'Physical Chemistry': -1002533864126,
    'Botany': -1002537691102,
    'Zoology': -1002549422245
}

class HybridForwarder:
    def __init__(self):
        self.user_client = None
        self.bot_client = None
        self.last_forwarded_id = 0
        self.forwarding_active = False
        self.initialized = False

    async def initialize(self):
        """Initialize both user and bot clients with enhanced error handling"""
        try:
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

            # Start both clients with timeout
            await asyncio.wait_for(self.user_client.start(), timeout=30)
            await asyncio.wait_for(self.bot_client.start(), timeout=30)
            
            # Verify authorization
            user_me = await self.user_client.get_me()
            bot_me = await self.bot_client.get_me()
            logger.info(f"User account: @{user_me.username} (ID: {user_me.id})")
            logger.info(f"Bot account: @{bot_me.username} (ID: {bot_me.id})")

            # Verify channel access with more detailed checks
            try:
                user_chat = await self.user_client.get_chat(SOURCE_CHANNEL)
                logger.info(f"User has access to source channel: {user_chat.title} (ID: {user_chat.id})")
                
                # Verify bot is admin in destination channels
                for subject, channel_id in DESTINATION_CHANNELS.items():
                    try:
                        bot_chat = await self.bot_client.get_chat(channel_id)
                        member = await self.bot_client.get_chat_member(channel_id, bot_me.id)
                        if member.status not in ('administrator', 'creator'):
                            logger.error(f"Bot is not admin in {subject} channel!")
                            raise Exception(f"Bot needs admin rights in {subject} channel")
                        logger.info(f"Verified bot access to {subject} channel")
                    except RPCError as e:
                        logger.error(f"Bot access check failed for {subject}: {e}")
                        raise
                        
            except RPCError as e:
                logger.error(f"Channel access verification failed: {e}")
                raise

            # Get last message ID with improved reliability
            try:
                # First try getting the very last message
                last_msg = None
                async for msg in self.user_client.get_chat_history(SOURCE_CHANNEL, limit=1):
                    last_msg = msg
                    break
                
                if last_msg:
                    self.last_forwarded_id = last_msg.id
                    logger.info(f"Last message ID initialized to: {self.last_forwarded_id}")
                    
                    # Additional verification - get message by ID
                    try:
                        verify_msg = await self.user_client.get_messages(SOURCE_CHANNEL, last_msg.id)
                        if verify_msg:
                            logger.info(f"Message ID {last_msg.id} verification successful")
                        else:
                            logger.warning("Could not verify last message by ID")
                    except RPCError as e:
                        logger.warning(f"Message verification failed: {e}")
                else:
                    logger.warning("No messages found in source channel")
                    self.last_forwarded_id = 0
                    
            except RPCError as e:
                logger.error(f"Failed to get chat history: {e}")
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

    async def scan_and_forward(self):
        """Enhanced message scanning and forwarding with better reliability"""
        if self.forwarding_active:
            logger.warning("Forwarding already in progress")
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            logger.info(f"Scanning for new messages after ID: {self.last_forwarded_id}")
            
            # First verify we can see recent messages
            try:
                test_msg = None
                async for msg in self.user_client.get_chat_history(SOURCE_CHANNEL, limit=1):
                    test_msg = msg
                    break
                
                if not test_msg:
                    logger.error("Cannot fetch ANY messages from channel!")
                    return 0
                    
                logger.info(f"Most recent message in channel: ID={test_msg.id} (Current last_forwarded_id={self.last_forwarded_id})")
                
                if test_msg.id <= self.last_forwarded_id:
                    logger.info("No new messages (test message is older than last_forwarded_id)")
                    return 0
            except RPCError as e:
                logger.error(f"Failed to test channel access: {e}")
                return 0

            # Collect new messages with improved scanning
            new_messages = []
            try:
                # Scan in chunks to be more reliable
                chunk_size = 20
                offset = 0
                found_all = False
                
                while not found_all and offset < 200:  # Limit to 200 messages max per scan
                    logger.debug(f"Scanning chunk {offset//chunk_size + 1} (offset={offset})")
                    
                    chunk_messages = []
                    async for msg in self.user_client.get_chat_history(
                        SOURCE_CHANNEL,
                        limit=chunk_size,
                        offset=offset,
                        offset_id=self.last_forwarded_id
                    ):
                        if msg.id <= self.last_forwarded_id:
                            found_all = True
                            break
                        chunk_messages.append(msg)
                    
                    if not chunk_messages:
                        break
                        
                    new_messages.extend(chunk_messages)
                    offset += chunk_size
                    
                    # Small delay between chunks to avoid flooding
                    await asyncio.sleep(0.5)
                    
            except RPCError as e:
                logger.error(f"Failed to fetch chat history: {e}")
                return 0

            if not new_messages:
                logger.info("No new messages found in scan")
                return 0

            logger.info(f"Found {len(new_messages)} new messages to process")

            # Process messages in chronological order with better error handling
            for msg in reversed(new_messages):
                try:
                    # Skip service messages (joins, pins, etc.)
                    if msg.service:
                        logger.debug(f"Skipping service message ID {msg.id}")
                        continue
                        
                    text = msg.text or msg.caption or ""
                    logger.debug(f"Processing message {msg.id} with text: {text[:50]}...")
                    
                    # Skip if message is empty and has no media
                    if not text and not msg.media:
                        logger.debug(f"Skipping empty message ID {msg.id}")
                        continue
                    
                    subject = matcher.find_subject(text)
                    if not subject:
                        logger.debug(f"No subject found in message {msg.id}")
                        continue
                        
                    if subject not in DESTINATION_CHANNELS:
                        logger.debug(f"Subject '{subject}' not in destination channels")
                        continue
                        
                    dest_channel = DESTINATION_CHANNELS[subject]
                    logger.info(f"Attempting to forward message {msg.id} to {subject} (Channel: {dest_channel})")
                    
                    try:
                        # Additional verification before forwarding
                        msg_to_forward = await self.user_client.get_messages(SOURCE_CHANNEL, msg.id)
                        if not msg_to_forward:
                            logger.warning(f"Message {msg.id} not found when verifying")
                            continue
                            
                        await self.bot_client.copy_message(
                            chat_id=dest_channel,
                            from_chat_id=SOURCE_CHANNEL,
                            message_id=msg.id,
                            reply_to_message_id=None  # Explicitly disable reply
                        )
                        self.last_forwarded_id = msg.id
                        forwarded_count += 1
                        logger.info(f"Successfully forwarded message {msg.id}")
                        
                        # Small delay between forwards to avoid rate limits
                        await asyncio.sleep(1)
                        
                    except RPCError as e:
                        logger.error(f"Failed to forward message {msg.id}: {e}")
                        continue
                        
                except Exception as e:
                    logger.error(f"Error processing message {msg.id}: {e}")
                    continue

            return forwarded_count
            
        finally:
            self.forwarding_active = False
            logger.info(f"Forwarding completed. Total forwarded: {forwarded_count}")

    async def handle_forward(self, message: Message):
        """Enhanced command handler with better feedback"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                logger.warning(f"Unauthorized access attempt from {message.from_user.id}")
                return await message.reply("❌ Unauthorized")
            
            logger.info(f"Forward command received from {message.from_user.id}")
            
            if not self.initialized:
                return await message.reply("⚠️ Bot not fully initialized yet")
            
            await message.reply("⏳ Scanning for new messages...")
            forwarded_count = await self.scan_and_forward()
            
            if forwarded_count > 0:
                response = f"✅ Successfully forwarded {forwarded_count} message(s)\nLast forwarded ID: {self.last_forwarded_id}"
                logger.info(response)
            else:
                # Provide more detailed "no messages" response
                try:
                    last_msg = None
                    async for msg in self.user_client.get_chat_history(SOURCE_CHANNEL, limit=1):
                        last_msg = msg
                        break
                    
                    if last_msg:
                        response = f"ℹ️ No new messages found (Last channel message: ID {last_msg.id})"
                    else:
                        response = "ℹ️ No messages found in source channel"
                except Exception as e:
                    response = f"ℹ️ No new messages found (Error checking channel: {str(e)})"
                
                logger.info(response)
                
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error in handle_forward: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def run(self):
        """Main bot loop with enhanced error recovery"""
        await self.initialize()
        
        # Additional startup check
        if not self.initialized:
            logger.critical("Bot failed to initialize properly")
            return
            
        logger.info("Starting main bot loop...")
        
        while True:
            try:
                # Periodic self-check
                if not await self.health_check():
                    logger.error("Health check failed, attempting to reconnect...")
                    try:
                        await self.user_client.stop()
                        await self.bot_client.stop()
                        await self.initialize()
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")
                
                await asyncio.sleep(3600)  # Keep alive
                
            except asyncio.CancelledError:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def health_check(self):
        """Check if the bot is still functioning properly"""
        try:
            # Check if clients are connected
            if not self.user_client.is_connected or not self.bot_client.is_connected:
                return False
                
            # Verify we can still access the source channel
            try:
                async for msg in self.user_client.get_chat_history(SOURCE_CHANNEL, limit=1):
                    break
                return True
            except RPCError:
                return False
                
        except Exception:
            return False

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
