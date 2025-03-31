from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from config import AUTH_CHANNEL

#=====================================================================================

async def is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'🛸 Join {chat.title} 🛸', url=chat.invite_link)])
        except Exception as e:
            print(e)
    return btn

def auth_check(func):
    async def wrapper(client, message):
        if AUTH_CHANNEL:
            btn = await is_subscribed(client, message, AUTH_CHANNEL)
            if btn:
                username = (await client.get_me()).username
                start_param = message.command[1] if len(message.command) > 1 else "true"
                btn.append([InlineKeyboardButton("🔄 Rᴇғʀᴇsʜ 🔄", url=f"https://t.me/{username}?start={start_param}")])

                await message.reply_photo(
                    photo=FORCE_PIC,  # Using the variable FORCE_PIC
                    caption=f"<b>👋🏻 Hello {message.from_user.mention}\nᴛᴏ ᴘʀᴇᴠᴇɴᴛ ᴏᴠᴇʀʟᴏᴀᴅ, ᴏɴʟʏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴜsᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.\n\nᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴄʟɪᴄᴋ Rᴇғʀᴇsʜ 👇🏻</b>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
        return await func(client, message)
    return wrapper
