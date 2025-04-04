from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database 
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add") & filters.private)
async def add_channels_via_dm(client, message: Message):
    if not message.from_user or message.from_user.id not in ADMIN:
        return await message.reply("❌ You are not authorized to use this command!")

    args = message.text.split()[1:]  # Extract arguments after /add
    if not args:
        return await message.reply("❌ Please provide at least one channel username or ID. Example:\n`/add @channel1 @channel2`", quote=True)

    added_channels = []
    already_exists = []
    failed = []

    for ch in args:
        try:
            chat = await client.get_chat(ch)
            channel_id = chat.id
            channel_name = chat.title

            if await db.add_channel(channel_id, channel_name):
                added_channels.append(channel_name)
            else:
                already_exists.append(channel_name)
        except Exception as e:
            print(f"Failed to add {ch}: {e}")
            failed.append(ch)

    # Create response
    response = ""
    if added_channels:
        response += "**✅ Added Channels:**\n" + "\n".join(added_channels) + "\n\n"
    if already_exists:
        response += "**ℹ️ Already Exists:**\n" + "\n".join(already_exists) + "\n\n"
    if failed:
        response += "**❌ Failed to Add:**\n" + "\n".join(failed)

    await message.reply(response or "No channels processed.")
    

@Client.on_message(filters.command("rem") & filters.private & filters.user(ADMIN))
async def remove_channels(client, message: Message):
    # Check if any channel IDs were provided
    if len(message.command) < 2:
        return await message.reply("❌ Please provide channel IDs separated by spaces\nExample: `/rem -100123 -100456 100789`")
    
    removed_channels = []
    not_found_channels = []
    invalid_channels = []
    
    for channel_input in message.command[1:]:  # Skip the "/rem" part
        try:
            # Convert to negative channel ID format if needed
            channel_id = int(channel_input)
            if channel_id > 0:  # If positive ID provided
                channel_id = -channel_id
            
            # Check if it's a valid channel ID format
            if not (-100 <= channel_id <= -1):
                invalid_channels.append(channel_input)
                continue
                
            # Remove from database
            if await db.delete_channel(channel_id):
                removed_channels.append(f"`{channel_id}`")
            else:
                not_found_channels.append(f"`{channel_id}`")
                
        except ValueError:
            invalid_channels.append(channel_input)
    
    # Prepare response message
    response = []
    
    if removed_channels:
        response.append("🗑️ **Removed Channels:** " + ", ".join(removed_channels))
    
    if not_found_channels:
        response.append("\n🔍 **Not Found in DB:** " + ", ".join(not_found_channels))
    
    if invalid_channels:
        response.append(f"\n❌ **Invalid IDs:** {', '.join(invalid_channels)}")
    
    if not response:  # Shouldn't happen but just in case
        response.append("No valid channel IDs were processed")
    
    await message.reply("\n".join(response)[:4000])  # Truncate if too long

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
    
