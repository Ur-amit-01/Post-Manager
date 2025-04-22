from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database 
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add") & filters.channel)
async def add_current_channel(client, message: Message):

    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        added = await db.add_channel(channel_id, channel_name)
        if added:
            await message.reply(f"**Channel '{channel_name}' added! ✅**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' already exists.")
    except Exception as e:
        print(f"Error adding channel: {e}")
        await message.reply("❌ Failed to add channel. Contact developer.")

# Command to remove the current channel from the database
@Client.on_message(filters.command("rem") & filters.channel)
async def remove_current_channel(client, message: Message):

    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        if await db.is_channel_exist(channel_id):
            await db.delete_channel(channel_id)
            await message.reply(f"**Channel '{channel_name}' removed from my database!**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' not found.")
    except Exception as e:
        print(f"Error removing channel: {e}")
        await message.reply("❌ Failed to remove channel. Try again.")

# Command to list all connected channels
@Client.on_message(filters.command("channels") & filters.private & filters.user(ADMIN))
async def list_channels(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return

    total_channels = len(channels)
    channel_list = [f"• **{channel['name']}** :- `{channel['_id']}`" for channel in channels]

    header = f"> **Total Channels :- ({total_channels})**\n\n"
    messages = []
    current_message = header

    for line in channel_list:
        if len(current_message) + len(line) + 1 > 4096:
            messages.append(current_message)
            current_message = ""
        current_message += line + "\n"

    if current_message:
        messages.append(current_message)

    for part in messages:
        await message.reply(part)




@Client.on_message(filters.command("link") & filters.private & filters.user(ADMIN))
async def generate_invite_links(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    # Get all channels from database
    channels = await db.get_all_channels()
    
    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return

    processing_msg = await message.reply("⏳ Generating invite links for all channels...")
    
    links = []
    expiration_time = int(time.time()) + 60 #172800  # 48 hours from now (48*60*60)
    
    for channel in channels:
        try:
            # Create invite link that expires in 48 hours
            invite_link = await client.create_chat_invite_link(
                chat_id=channel['_id'],
                expire_date=expiration_time,
                creates_join_request=False
            )
            
            links.append(
                f"🔗 [{channel['name']}]({invite_link.invite_link})"
            )
            
            # Small delay to avoid flood limits
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error generating link for {channel['name']}: {e}")
            links.append(
                f"❌ {channel['name']} - Failed to generate link"
            )
    
    # Format the message with all links
    header = "**🔗 Temporary Invite Links (Expires in 1 minute):**\n\n"
    message_text = header + "\n".join(links)
    
    # Edit the processing message with the results
    await processing_msg.edit_text(
        text=message_text,
        disable_web_page_preview=True
    )
