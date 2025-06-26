from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db
import time
import random
import asyncio
from config import *
from plugins.Post.admin_panel import admin_filter

async def get_channel_info(client, channel_id):
    """Get channel info from Telegram"""
    try:
        chat = await client.get_chat(channel_id)
        return {
            "id": chat.id,
            "name": chat.title,
            "username": chat.username
        }
    except Exception as e:
        print(f"Error getting channel info: {e}")
        return None

# Command to add channel (works in both channels and DMs)
@Client.on_message(filters.command("add") & (filters.channel | (filters.private & admin_filter)))
async def add_channel(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    if not await db.is_admin(message.from_user.id):
        await message.reply("**❌ You are not authorized to use this command!**")
        return

    # If command is used in a channel
    if message.chat.type == "channel":
        channel_id = message.chat.id
        channel_name = message.chat.title
    # If command is used in DM with channel ID
    elif len(message.command) > 1:
        try:
            channel_id = int(message.command[1])
            channel_info = await get_channel_info(client, channel_id)
            if not channel_info:
                await message.reply("❌ Invalid channel ID or I don't have access to that channel")
                return
            channel_name = channel_info["name"]
        except ValueError:
            await message.reply("❌ Please provide a valid channel ID (numeric)")
            return
    else:
        await message.reply("ℹ️ Usage in DM: `/add <channel_id>`\nIn channels: just send `/add`")
        return

    try:
        added = await db.add_channel(channel_id, channel_name)
        if added:
            await message.reply(f"**✅ Channel added successfully!**\n\n"
                              f"• **Name:** {channel_name}\n"
                              f"• **ID:** `{channel_id}`")
            
            # Send to log channel
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"#New_Channel\n\n"
                    f"📢 **Channel Added**\n"
                    f"👤 **By:** {message.from_user.mention}\n"
                    f"📌 **Name:** {channel_name}\n"
                    f"🆔 **ID:** `{channel_id}`"
                )
            except:
                pass
        else:
            await message.reply(f"ℹ️ Channel `{channel_id}` already exists in database.")
    except Exception as e:
        print(f"Error adding channel: {e}")
        await message.reply("❌ Failed to add channel. Contact developer.")

# Command to remove channel (works in both channels and DMs)
@Client.on_message(filters.command("rem") & (filters.channel | (filters.private & admin_filter)))
async def remove_channel(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    if not await db.is_admin(message.from_user.id):
        await message.reply("**❌ You are not authorized to use this command!**")
        return

    # If command is used in a channel
    if message.chat.type == "channel":
        channel_id = message.chat.id
        channel_name = message.chat.title
    # If command is used in DM with channel ID
    elif len(message.command) > 1:
        try:
            channel_id = int(message.command[1])
            if not await db.is_channel_exist(channel_id):
                await message.reply("❌ This channel is not in my database")
                return
            channel_info = await db.get_channel(channel_id)
            channel_name = channel_info.get("name", str(channel_id))
        except ValueError:
            await message.reply("❌ Please provide a valid channel ID (numeric)")
            return
    else:
        await message.reply("ℹ️ Usage in DM: `/rem <channel_id>`\nIn channels: just send `/rem`")
        return

    try:
        if await db.is_channel_exist(channel_id):
            await db.delete_channel(channel_id)
            await message.reply(f"**🗑 Channel removed successfully!**\n\n"
                              f"• **Name:** {channel_name}\n"
                              f"• **ID:** `{channel_id}`")
            
            # Send to log channel
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"#Removed_Channel\n\n"
                    f"📢 **Channel Removed**\n"
                    f"👤 **By:** {message.from_user.mention}\n"
                    f"📌 **Name:** {channel_name}\n"
                    f"🆔 **ID:** `{channel_id}`"
                )
            except:
                pass
        else:
            await message.reply(f"ℹ️ Channel `{channel_id}` not found in database.")
    except Exception as e:
        print(f"Error removing channel: {e}")
        await message.reply("❌ Failed to remove channel. Try again.")

# Command to list all connected channels
@Client.on_message(filters.command("channels") & filters.private & admin_filter)
async def list_channels(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass
        
    if not await db.is_admin(message.from_user.id):
        await message.reply("**❌ You are not authorized to use this command!**")
        return
        
    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return

    total_channels = len(channels)
    channel_list = []
    
    for channel in channels:
        line = f"• **{channel['name']}** - `{channel['_id']}`"
        if channel.get("username"):
            line += f" @{channel['username']}"
        channel_list.append(line)

    header = f"> **📢 Total Connected Channels: {total_channels}**\n\n"
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
