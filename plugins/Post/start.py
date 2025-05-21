from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from plugins.helper.db import db
import random
from plugins.Extra.wallpaper import get_random_wallpaper
# =====================================================================================
START_PIC = get_random_wallpaper()

LOG_TEXT = """<blockquote><b>#NewUser</b></blockquote>
<blockquote><b>☃️ Nᴀᴍᴇ :~ {}
🪪 ID :~ <code>{}</code>
👨‍👨‍👦‍👦 ᴛᴏᴛᴀʟ :~ {}</b></blockquote>"""


@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    logger.info(f"Start command from {message.from_user.id}")
    await message.reply(
        "🤖 **Welcome to Channel Sorter Bot!**\n\n"
        "I can automatically organize content from your channels into subject-specific channels.\n\n"
        "**Available Commands:**\n"
        "/newbatch - Create a new sorting setup\n"
        "/mybatches - List your existing batches\n"
        "/help - Get assistance\n\n"
        "To begin, use /newbatch to create your first automatic sorting setup!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Create New Batch", callback_data="newbatch")],
            [InlineKeyboardButton("🆘 Help", callback_data="help")]
        ])
    )

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    logger.info(f"Help command from {message.from_user.id}")
    await message.reply(
        "🆘 **Channel Sorter Bot Help**\n\n"
        "**How It Works:**\n"
        "1. Create a batch with /newbatch\n"
        "2. Set up your main content channel\n"
        "3. Configure subject channels\n"
        "4. The bot will automatically sort content\n\n"
        "**Commands:**\n"
        "/start - Show welcome message\n"
        "/newbatch - Create new sorting setup\n"
        "/mybatches - List your batches\n"
        "/help - Show this message\n\n"
        "Need more help? Contact support!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Create New Batch", callback_data="newbatch")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start")]
        ])
    )
    


@Client.on_message(filters.command("id"))
async def id_command(client: Client, message: Message):
    if message.chat.title:
        chat_title = message.chat.title
    else:
        chat_title = message.from_user.full_name

    id_text = f"**Chat ID of** {chat_title} **is**\n`{message.chat.id}`"

    await client.send_message(
        chat_id=message.chat.id,
        text=id_text,
        reply_to_message_id=message.id,
    )
