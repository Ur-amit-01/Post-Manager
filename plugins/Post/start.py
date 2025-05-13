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


@Client.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)  # React with a random emoji
    except:
        pass

    # Add user to the database if they don't exist
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)
        total_users = await db.total_users_count()
        await client.send_message(LOG_CHANNEL, LOG_TEXT.format(message.from_user.mention, message.from_user.id, total_users))

    # Welcome message
    txt = (
        f"> **✨👋🏻 Hey {message.from_user.mention} !!**\n\n"
        f"**Welcome to the PW Link Changer Bot! ,💡 Click on help to learn how to use me.**\n\n"
        f"> **ᴅᴇᴠᴇʟᴏᴘᴇʀ 🧑🏻‍💻 :- @xDzoddd**"
    )
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton('🕵🏻‍♀️ ʜᴇʟᴘ', callback_data='help'),
         InlineKeyboardButton('🔗 Try Now', switch_inline_query="amit ")]
    ])

    # Send the start message with or without a picture
    if START_PIC:
        await message.reply_photo(START_PIC, caption=txt, reply_markup=button)
    else:
        await message.reply_text(text=txt, reply_markup=button, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback_query):
    user = callback_query.from_user
    
    help_text = f"""
> **🛠️ Help Section:**

**1️⃣ Change PW Lecture Links:**
• Send /amit followed by PW URL  
• Example:  
  ```/amit https://pw.live/watch?v=abc123```  
• Then select your preferred quality  

**2️⃣ Supported Qualities:**
• 240p | 360p | 480p | 720p  

**Need more help? Contact @xDzoddd**
    """
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start"),
         InlineKeyboardButton("🚀 Try Now", switch_inline_query_current_chat="amit ")]
    ])
    
    try:
        await callback_query.message.edit_text(
            text=help_text,
            reply_markup=buttons,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Error editing message: {e}")
    
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(client, callback_query):
    # Reuse your existing start message logic
    txt = f"""
> **✨👋🏻 Hey {callback_query.from_user.mention} !!**  

**Welcome to the PW Link Changer Bot! ,💡 Click on help to learn how to use me.**  

> **ᴅᴇᴠᴇʟᴏᴘᴇʀ 🧑🏻‍💻 :- @xDzoddd**
    """

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton('🕵🏻‍♀️ ʜᴇʟᴘ', callback_data='help'),
         InlineKeyboardButton('🔗 Try Now', switch_inline_query_current_chat="amit ")]
    ])
    
    await callback_query.message.edit_text(
        text=txt,
        reply_markup=buttons,
        disable_web_page_preview=True
    )
    await callback_query.answer()


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
