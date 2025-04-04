from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database 
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add"))
async def add_current_channel(client, message: Message):
    # Debug info
    print(f"Add command received from {message.from_user.id} in chat {message.chat.id}")
    print(f"ADMIN list: {ADMIN}")
    
    # Check if in channel and sender is admin
    if message.chat.type != "channel":
        return await message.reply("❌ This command only works in channels!")
    
    if message.from_user.id not in ADMIN:
        return await message.reply("❌ You need to be bot admin to use this command!")
    
    # Check if bot is admin in channel
    try:
        bot_member = await client.get_chat_member(message.chat.id, "me")
        if not bot_member.can_post_messages:
            return await message.reply("❌ I need admin rights with post permissions in this channel!")
    except Exception as e:
        print(f"Admin check error: {e}")
        return await message.reply("❌ Failed to check my admin status in this channel!")

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
        await message.reply("❌ Database error. Contact developer.")

@Client.on_message(filters.command("rem"))
async def remove_current_channel(client, message: Message):
    # Debug info
    print(f"Remove command received from {message.from_user.id} in chat {message.chat.id}")
    
    # Check if in channel and sender is admin
    if message.chat.type != "channel":
        return await message.reply("❌ This command only works in channels!")
    
    if message.from_user.id not in ADMIN:
        return await message.reply("❌ You need to be bot admin to use this command!")

    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        if await db.is_channel_exist(channel_id):
            await db.delete_channel(channel_id)
            await message.reply(f"**Channel '{channel_name}' removed!**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' not found in database.")
    except Exception as e:
        print(f"Error removing channel: {e}")
        await message.reply("❌ Database error. Try again later.")


# Command to list all connected channels
@Client.on_message(filters.command("channels") & filters.private & filters.user(ADMIN))
async def list_channels(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)  # React with a random emoji
    except:
        pass
    # Retrieve all channels from the database
    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return
    total_channels = len(channels)
    # Format the list of channels
    channel_list = [f"📢 **{channel['name']}** :- `{channel['_id']}`" for channel in channels]
    response = (
        f"> **Total Channels :- ({total_channels})**\n\n"  # Add total count here
        + "\n".join(channel_list)
    )
    await message.reply(response)
    

@Client.on_message(filters.command("addchannels") & filters.private & filters.user(ADMIN))
async def add_multiple_channels(client, message: Message):
    # Check if message is a reply
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("⚠️ Please reply to a message containing channel IDs (one per line) with this command!")
    
    # Get the text from replied message
    text = message.reply_to_message.text
    added = 0
    skipped = 0
    
    # Process each line
    for line in text.split('\n'):
        line = line.strip()
        if not line:  # Skip empty lines
            continue
        
        # Extract channel ID (handle both -100 and 100 formats)
        channel_id = line.replace('-', '').strip()
        if not channel_id.isdigit():
            continue
            
        channel_id = int(channel_id)
        if channel_id > 0:  # Make sure it's negative for channels
            channel_id = -channel_id
        
        # Add to database
        if not await db.is_channel_exist(channel_id):
            await db.add_channel(channel_id, f"Channel {abs(channel_id)}")
            added += 1
        else:
            skipped += 1
    
    # Send result
    await message.reply(
        f"**Channels added successfully!**\n\n"
        f"✅ Added: {added}\n"
        f"⏩ Skipped (already exists): {skipped}"
    )
