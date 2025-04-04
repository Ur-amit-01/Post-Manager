from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database 
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add") & filters.channel & filters.user(ADMIN))
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
@Client.on_message(filters.command("rem") & filters.channel & filters.user(ADMIN))
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

    valid_channels = []
    removed_channels = []
    errors = []

    for channel in channels:
        channel_id = channel['_id']
        channel_name = channel.get('name', 'Unknown')
        
        try:
            # Try to get chat information
            chat = await client.get_chat(channel_id)
            
            # Verify it's still a channel
            if chat.type != "channel":
                await db.delete_channel(channel_id)
                removed_channels.append(f"{channel_name} (Not a channel)")
                continue
                
            # Check bot's admin status
            try:
                member = await client.get_chat_member(channel_id, "me")
                if not member.can_post_messages:
                    await db.delete_channel(channel_id)
                    removed_channels.append(f"{channel_name} (No posting rights)")
                    continue
                    
                valid_channels.append(channel)
                
            except Exception as admin_error:
                await db.delete_channel(channel_id)
                removed_channels.append(f"{channel_name} (Admin check failed)")
                errors.append(f"Admin check failed for {channel_id}: {admin_error}")

        except Exception as e:
            # Handle different types of errors more specifically
            error_msg = str(e)
            if "CHANNEL_INVALID" in error_msg or "CHANNEL_PRIVATE" in error_msg:
                await db.delete_channel(channel_id)
                removed_channels.append(f"{channel_name} (Invalid/Private)")
            elif "USER_NOT_PARTICIPANT" in error_msg:
                await db.delete_channel(channel_id)
                removed_channels.append(f"{channel_name} (Bot removed)")
            else:
                errors.append(f"Unknown error for {channel_id}: {error_msg}")

    # Prepare the response message
    response_parts = []
    
    if removed_channels:
        response_parts.append("**🚫 Removed Channels:**\n" + "\n".join(f"• {name}" for name in removed_channels))
    
    if errors:
        response_parts.append("\n**⚠️ Errors:**\n" + "\n".join(f"• {e}" for e in errors[:5]))  # Show first 5 errors
    
    if valid_channels:
        total = len(valid_channels)
        channel_list = [f"📢 **{ch['name']}** (`{ch['_id']}`)" for ch in valid_channels]
        response_parts.append(f"\n**✅ Valid Channels ({total}):**\n" + "\n".join(channel_list))
    else:
        response_parts.append("\n**No valid channels remaining.**")

    # Send the response (split if too long)
    full_response = "\n".join(response_parts)
    await message.reply(full_response[:4000])  # Telegram message limit
