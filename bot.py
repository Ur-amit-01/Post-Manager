import logging
import logging.config
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from config import *
from aiohttp import web
from plugins.Sorting import matcher  # Import your subject matcher

# Configure logging
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Channel IDs (move these to config.py if preferred)
SOURCE_CHANNEL = -1002027394591  # Main channel to monitor
DESTINATION_CHANNELS = {
    'Physics': -1002611033664,
    'Inorganic Chemistry': -1002530766847,
    'Organic Chemistry': -1002623306070,
    'Physical Chemistry': -1002533864126,
    'Botany': -1002537691102,
    'Zoology': -1002549422245
}

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="renamer",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )
        self.last_forwarded = {subject: None for subject in DESTINATION_CHANNELS.keys()}

    async def get_new_messages(self, subject: str) -> list[Message]:
        """Get new messages since last forwarded for a subject"""
        messages = []
        last_id = self.last_forwarded[subject]
        
        async for message in self.get_chat_history(SOURCE_CHANNEL):
            if message.id == last_id:
                break
                
            text = message.text or message.caption or ""
            if matcher.find_subject(text) == subject:
                messages.append(message)
        
        return messages[::-1]  # Return in chronological order

    async def forward_messages(self, subject: str, messages: list[Message]):
        """Forward messages to destination channel"""
        dest_channel = DESTINATION_CHANNELS[subject]
        
        for message in messages:
            try:
                if message.text:
                    await message.copy(dest_channel)
                elif message.media:
                    await message.copy(
                        dest_channel,
                        caption=message.caption,
                        caption_entities=message.caption_entities
                    )
                self.last_forwarded[subject] = message.id
            except Exception as e:
                logging.error(f"Error forwarding to {subject}: {str(e)}")
                continue

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start web server
        # await web_server()  # Uncomment if you need web server
        
        logging.info(f"{me.first_name} ✅✅ BOT started successfully ✅✅")
        logging.info(f"{me.first_name} Pending deletions restored successfully.")

    async def stop(self, *args):
        await super().stop()      
        logging.info(f"{self.username} Bot Stopped 🙄")

# Client handlers
@Bot.on_message(filters.private & filters.command("forward"))
async def handle_forward_command(client: Bot, message: Message):
    """Handle /forward command in DM"""
    if message.from_user.id != 2031106491:  # Replace with your user ID
        return await message.reply("❌ You're not authorized to use this command.")
    
    total_forwarded = 0
    status_messages = []
    
    for subject in DESTINATION_CHANNELS:
        new_messages = await client.get_new_messages(subject)
        if not new_messages:
            continue
            
        status_msg = await message.reply(f"⏳ Forwarding {len(new_messages)} new messages for {subject}...")
        await client.forward_messages(subject, new_messages)
        total_forwarded += len(new_messages)
        
        status_messages.append(
            f"✅ {subject}: {len(new_messages)} messages\n"
            f"Last: t.me/c/{str(SOURCE_CHANNEL).replace('-100', '')}/{new_messages[-1].id}"
        )
        await status_msg.delete()
    
    if total_forwarded == 0:
        await message.reply("⚠️ No new messages to forward in any subject.")
    else:
        report = "\n".join(status_messages)
        await message.reply(
            f"📊 Forwarding complete!\n"
            f"Total: {total_forwarded} messages\n\n"
            f"{report}",
            disable_web_page_preview=True
        )

if __name__ == "__main__":
    bot = Bot()
    bot.run()
