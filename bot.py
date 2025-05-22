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
# Client handlers (CHANGE THIS)
@Bot.on_message(filters.private & filters.command("forward"))
async def handle_forward_command(client: Bot, message: Message):
    """Handle /forward command in DM"""
    try:
        # Debug logging
        logging.info(f"Received /forward from {message.from_user.id}")
        
        # Authorization
        YOUR_USER_ID = 2031106491  # Replace with your actual ID
        if message.from_user.id != YOUR_USER_ID:
            await message.reply("❌ Unauthorized access!")
            return

        total_forwarded = 0
        status_messages = []
        
        for subject, dest_channel in DESTINATION_CHANNELS.items():
            try:
                # Debug logging
                logging.info(f"Checking {subject} channel...")
                
                # Get channel info to verify access
                try:
                    chat = await client.get_chat(dest_channel)
                    logging.info(f"Access to {subject} channel verified")
                except Exception as e:
                    logging.error(f"No access to {subject} channel: {e}")
                    status_messages.append(f"❌ {subject}: Channel access failed")
                    continue

                new_messages = await client.get_new_messages(subject)
                if not new_messages:
                    logging.info(f"No new messages for {subject}")
                    continue
                
                status_msg = await message.reply(f"⏳ Forwarding {len(new_messages)} messages for {subject}...")
                
                # Forward messages with progress updates
                success_count = 0
                for msg in new_messages:
                    try:
                        if msg.text:
                            await msg.copy(dest_channel)
                        else:
                            await msg.copy(
                                dest_channel,
                                caption=msg.caption,
                                caption_entities=msg.caption_entities
                            )
                        client.last_forwarded[subject] = msg.id
                        success_count += 1
                    except Exception as e:
                        logging.error(f"Failed to forward message {msg.id}: {e}")
                
                total_forwarded += success_count
                status_messages.append(
                    f"✅ {subject}: {success_count}/{len(new_messages)} messages\n"
                    f"Last: t.me/c/{str(SOURCE_CHANNEL).replace('-100', '')}/{new_messages[-1].id}"
                )
                await status_msg.delete()
                
            except Exception as e:
                logging.error(f"Error processing {subject}: {e}")
                status_messages.append(f"❌ {subject}: Processing failed - {str(e)}")
        
        # Send final report
        if total_forwarded == 0:
            await message.reply("⚠️ No new messages forwarded.")
        else:
            report = "\n".join(status_messages)
            await message.reply(
                f"📊 Forwarding complete!\n"
                f"Total: {total_forwarded} messages\n\n"
                f"{report}",
                disable_web_page_preview=True
            )
            
    except Exception as e:
        logging.error(f"Critical error in forward handler: {e}")
        await message.reply(f"❌ Critical error occurred: {str(e)}")

if __name__ == "__main__":
    bot = Bot()
    bot.run()
