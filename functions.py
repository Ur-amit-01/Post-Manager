import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from config import *

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

USER_SESSION_STRING = "BQFP49AAn6jgY8Wwp8nhPAiF1PoD6hVxl0HWUtx8AldMjcpUOpkB0jI63t8aRNmAHQ_CWyU7CPZCiQVSOFMeL-5pLl2Z2D18R7uJx52rivl46MEe1i9aFC9gUxXRHChvUgAJWTAyytSg_BVKb8LhAKnPvNQoeV8znsy6U0wtEHY9a_lu04-fxzB5mAWZDrS12HGbkZvsocaEHgMLiGUl3q83bThYzHAciMjgzKxNiKB7VeLsyy5Ua01Ndh2uRP1KL43sp-KtF9wSw4wNV-LGtAGnMhDBG8_0Yt3zKIBk21KtM7BGsZZinxdgfs3sU53EmoAk61B8YEJ5MfAikBSRI00B8Ng4AAAAAAGVhUI_AA"   
YOUR_USER_ID = 2031106491  # Your Telegram User ID

SOURCE_CHANNEL = -1002027394591  # Channel to monitor

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
        self.user_client = None  # User account (for history)
        self.bot_client = None   # Bot (for forwarding)
        self.last_forwarded_id = 0

    async def initialize(self):
        """Initialize both user and bot clients"""
        # User client (uses session string)
        self.user_client = Client(
            "user_account",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=USER_SESSION_STRING  # From config.py
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
        logger.info("Hybrid bot started (User + Bot)")

        # Fetch last message ID using the user account
        async for msg in self.user_client.get_chat_history(SOURCE_CHANNEL, limit=1):
            self.last_forwarded_id = msg.id
            logger.info(f"Last message ID: {self.last_forwarded_id}")

        # Register bot command
        @self.bot_client.on_message(filters.command("forward") & filters.private)
        async def forward_command(_, message: Message):
            await self.handle_forward(message)

    async def scan_and_forward(self):
        """Use user account to fetch history, bot to forward"""
        new_messages = []
        async for msg in self.user_client.get_chat_history(
            SOURCE_CHANNEL,
            offset_id=self.last_forwarded_id
        ):
            if msg.id <= self.last_forwarded_id:
                break
            new_messages.append(msg)

        # Forward new messages using the bot
        for msg in reversed(new_messages):
            text = msg.text or msg.caption or ""
            subject = matcher.find_subject(text)
            if subject in DESTINATION_CHANNELS:
                try:
                    await self.bot_client.copy_message(
                        chat_id=DESTINATION_CHANNELS[subject],
                        from_chat_id=SOURCE_CHANNEL,
                        message_id=msg.id
                    )
                    self.last_forwarded_id = msg.id
                    logger.info(f"Forwarded to {subject}")
                except RPCError as e:
                    logger.error(f"Forward error: {e}")

    async def handle_forward(self, message: Message):
        """Handle /forward command"""
        if message.from_user.id != YOUR_USER_ID:
            return await message.reply("❌ Unauthorized")
        
        await message.reply("⏳ Scanning...")
        await self.scan_and_forward()
        await message.reply("✅ Forwarding complete")

    async def run(self):
        await self.initialize()
        while True:
            await asyncio.sleep(3600)  # Keep alive

# Import matcher
from plugins.Sorting import matcher

if __name__ == "__main__":
    hybrid = HybridForwarder()
    try:
        asyncio.run(hybrid.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
