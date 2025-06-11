from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from constants import MAIN_HELP_TXT

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    try:
        await message.reply_text(
            MAIN_HELP_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʀᴇǫᴜᴇsᴛ ᴀᴄᴄᴇᴘᴛᴏʀ ✅", callback_data="request")],
                [InlineKeyboardButton("ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ sᴀᴠᴇʀ 📥", callback_data="restricted")],
                [InlineKeyboardButton("📢 Post Help", callback_data="post_help"),
                 InlineKeyboardButton("📋 Channel Help", callback_data="channel_help")],
                [InlineKeyboardButton("🗑 Delete Help", callback_data="delete_help"),
                 InlineKeyboardButton("🏠 Home", callback_data="start")]
            ]),
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error showing help: {str(e)}")
