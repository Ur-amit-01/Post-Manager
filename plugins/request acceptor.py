import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, NEW_REQ_MODE, SESSION_STRING

@Client.on_message(filters.command('accept'))
async def accept(client, message):
    # Log the chat type for debugging
    print(f"Received message from chat: {message.chat.type}")

    # Check if the command is issued in a private chat (DM)
    if message.chat.type == enums.ChatType.PRIVATE:
        print("Command issued in DM, sending reply...")
        return await message.reply("🚫 **This command works in channels only.**")
    
    # Proceed if the command is issued in a channel
    channel_id = message.chat.id
    show = await client.send_message(channel_id, "⏳ **Please wait...**")
    
    try:
        acc = Client("joinrequest", session_string=SESSION_STRING, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()
    except:
        return await show.edit("❌ **Login session has expired. Please update the session string and try again.**")
    
    # Directly accept join requests without needing a forwarded message
    msg = await show.edit("✅ **Accepting all join requests... Please wait until it's completed.**")
    
    try:
        while True:
            await acc.approve_all_chat_join_requests(channel_id)
            await asyncio.sleep(1)
            join_requests = [request async for request in acc.get_chat_join_requests(channel_id)]
            if not join_requests:
                break
        await msg.edit("🎉 **Successfully accepted all join requests!**")
    except Exception as e:
        await msg.edit(f"⚠️ **An error occurred:** {str(e)}")


@Client.on_chat_join_request(filters.group | filters.channel)
async def approve_new(client, m):
    if not NEW_REQ_MODE:
        return  # If NEW_REQ_MODE is False, the function exits without processing the join request.

    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
        try:
            await client.send_message(
                m.from_user.id,
                f"**• Hello {m.from_user.mention}! 👋🏻\n• Your request for {m.chat.title} is accepted.**\n\n> **• Powered by: @Stellar_Bots x @Team_SAT_25**"
            )
        except:
            pass
    except Exception as e:
        print(f"⚠️ {str(e)}")
        pass
