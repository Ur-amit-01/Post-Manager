from asyncio import sleep
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message, BotCommand
from config import *

# =====================================================================================

# Set bot commands
@Client.on_message(filters.command("set") & filters.user(ADMIN))
async def set_commands(client: Client, message: Message):
    await client.set_bot_commands([
        BotCommand("start", "🤖 Start me "),
        BotCommand("channels", "🛠 Start PDF merge"),
        BotCommand("post", "📂 Merge PDFs"),
        BotCommand("del_post", "🌐 Get Telegraph link"),
        BotCommand("add", "🎭 Get sticker ID"),
        BotCommand("rem", "✅ Accept pending join requests"),
    ])
    await message.reply_text("✅ Bot commands have been set.")
