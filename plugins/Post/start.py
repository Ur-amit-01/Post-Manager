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
        f"> **✨👋🏻 Hey {message.from_user.mention} !!**\n"
        f"**Welcome to the PW Link Changer Bot! ,I can transform PW lecture links into direct downloadable URLs.**\n\n"
        f"**🚀 How to Use:**\n"
        f"> **Send links in this format 👇🏻\n**"
        f"> **/amit https://pw.live/watch?v=abc123&bat\n\n**"
        f"> **ᴅᴇᴠᴇʟᴏᴘᴇʀ 🧑🏻‍💻 :- @xDzoddd**"
    )   
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton('Powered by Team SAT ✨', url='https://t.me/Team_Sat_25')]
    ])

    # Send the start message with or without a picture
    if START_PIC:
        await message.reply_photo(START_PIC, caption=txt, reply_markup=button)
    else:
        await message.reply_text(text=txt, reply_markup=button, disable_web_page_preview=True)



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
