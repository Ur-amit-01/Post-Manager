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
