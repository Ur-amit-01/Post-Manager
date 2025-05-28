from pyrogram import filters
from pyrogram.types import Message
from config import YOUR_USER_ID
from database import Database

class CommandHandlers:
    def __init__(self, bot_client, forwarder, db: Database):
        self.bot = bot_client
        self.forwarder = forwarder
        self.db = db

    async def handle_forward(self, _, message: Message):
        """Handle /forward command"""
        if message.from_user.id != YOUR_USER_ID:
            return await message.reply("🚨 Access denied")
        
        # Forwarding logic here
        await message.reply("Forwarding started...")

    async def handle_channels(self, _, message: Message):
        """Handle /channels command"""
        if message.from_user.id != YOUR_USER_ID:
            return await message.reply("🚨 Access denied")
        
        # Channel listing logic here
        await message.reply("Channel list...")

    def register_handlers(self):
        self.bot.on_message(filters.command("forward") & filters.private)(self.handle_forward)
        self.bot.on_message(filters.command("channels") & filters.private)(self.handle_channels)
