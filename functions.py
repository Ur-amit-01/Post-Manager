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

    async def initialize(self):
        """Initialize both user and bot clients with error handling"""
        try:
            # User client (uses session string)
            self.user_client = Client(
                "user_account",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=USER_SESSION_STRING,
                in_memory=True  # Reduces session file issues
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

            # Verify channel access
            try:
                user_chat = await self.user_client.get_chat(SOURCE_CHANNEL)
                logger.info(f"User has access to source channel: {user_chat.title}")
            except RPCError as e:
                logger.error(f"User cannot access source channel: {e}")
                raise

            # Get last message ID
            try:
                last_msg = None
                async for msg in self.user_client.get_chat_history(SOURCE_CHANNEL, limit=1):
                    last_msg = msg
                    break
                
                if last_msg:
                    self.last_forwarded_id = last_msg.id
                    logger.info(f"Last message ID initialized to: {self.last_forwarded_id}")
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

            logger.info("Hybrid bot initialized successfully")

        except Exception as e:
            logger.critical(f"Initialization failed: {e}")
            raise

    async def scan_and_forward(self):
        """Scan for new messages and forward them with detailed logging"""
        if self.forwarding_active:
            logger.warning("Forwarding already in progress")
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            logger.info(f"Scanning for new messages after ID: {self.last_forwarded_id}")
            
            # Collect new messages
            new_messages = []
            try:
                async for msg in self.user_client.get_chat_history(
                    SOURCE_CHANNEL,
                    offset_id=self.last_forwarded_id
                ):
                    if msg.id <= self.last_forwarded_id:
                        break
                    new_messages.append(msg)
                    logger.debug(f"Found new message ID: {msg.id}")
            except RPCError as e:
                logger.error(f"Failed to fetch chat history: {e}")
                return 0

            if not new_messages:
                logger.info("No new messages found")
                return 0

            logger.info(f"Found {len(new_messages)} new messages to process")

            # Process messages in chronological order
            for msg in reversed(new_messages):
                try:
                    text = msg.text or msg.caption or ""
                    logger.debug(f"Processing message {msg.id} with text: {text[:50]}...")
                    
                    subject = matcher.find_subject(text)
                    if not subject:
                        logger.debug(f"No subject found in message {msg.id}")
                        continue
                        
                    if subject not in DESTINATION_CHANNELS:
                        logger.debug(f"Subject '{subject}' not in destination channels")
                        continue
                        
                    dest_channel = DESTINATION_CHANNELS[subject]
                    logger.info(f"Forwarding message {msg.id} to {subject} (Channel: {dest_channel})")
                    
                    try:
                        await self.bot_client.copy_message(
                            chat_id=dest_channel,
                            from_chat_id=SOURCE_CHANNEL,
                            message_id=msg.id
                        )
                        self.last_forwarded_id = msg.id
                        forwarded_count += 1
                        logger.info(f"Successfully forwarded message {msg.id}")
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
        """Handle /forward command with detailed feedback"""
        try:
            if message.from_user.id != YOUR_USER_ID:
                logger.warning(f"Unauthorized access attempt from {message.from_user.id}")
                return await message.reply("❌ Unauthorized")
            
            logger.info(f"Forward command received from {message.from_user.id}")
            
            await message.reply("⏳ Scanning for new messages...")
            forwarded_count = await self.scan_and_forward()
            
            if forwarded_count > 0:
                response = f"✅ Successfully forwarded {forwarded_count} message(s)"
                logger.info(response)
            else:
                response = "ℹ️ No new messages found to forward"
                logger.info(response)
                
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error in handle_forward: {e}")
            await message.reply(f"⚠️ Error: {str(e)}")

    async def run(self):
        """Main bot loop with error recovery"""
        await self.initialize()
        
        while True:
            try:
                await asyncio.sleep(3600)  # Keep alive
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
