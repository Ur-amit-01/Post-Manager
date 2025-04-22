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

    channels = await db.get_all_channels()
    
    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return

    processing_msg = await message.reply("**⏳ Generating invite links for all channels...**")
    
    success_count = 0
    failed_count = 0
    links = []
    expiration_time = int(time.time()) + 3660  # 48 hours from now
    
    for channel in channels:
        try:
            # First check if bot is in channel and has admin rights
            chat = await client.get_chat(channel['_id'])
            
            if not chat:
                links.append(f"**❌ {channel['name']} - Bot not in channel**")
                failed_count += 1
                continue
                
            # Check if bot has admin privileges
            member = await client.get_chat_member(channel['_id'], "me")
            if not member.privileges or not member.privileges.can_invite_users:
                links.append(f"**❌ {channel['name']} - No invite permission**")
                failed_count += 1
                continue
                
            # Create invite link
            invite_link = await client.create_chat_invite_link(
                chat_id=channel['_id'],
                expire_date=expiration_time,
                creates_join_request=True
            )
            
            links.append(f"**🔗 [{channel['name']}]({invite_link.invite_link})**")
            success_count += 1
            
            await asyncio.sleep(0.25)  # Rate limiting
            
        except Exception as e:
            error_msg = str(e).lower()
            if "forbidden" in error_msg:
                reason = "Bot not admin or kicked"
            elif "chat not found" in error_msg:
                reason = "Bot not in channel"
            elif "not enough rights" in error_msg:
                reason = "Missing invite permission"
            else:
                reason = "Unknown error"
                
            links.append(f"❌ {channel['name']} - {reason}")
            failed_count += 1
            print(f"Error in {channel['name']}: {e}")

    # Format results
    header = (
        f"**🔗 Temporary Invite Links (Expires in 1 hour 1minute)**\n"
        f"**✅ Success: {success_count} | ❌ Failed: {failed_count}**\n\n"
    )
    
    # Split long messages if needed
    message_text = header + "\n".join(links)
    if len(message_text) > 4096:
        parts = [message_text[i:i+4096] for i in range(0, len(message_text), 4096)]
        await processing_msg.delete()
        for part in parts:
            await message.reply(part, disable_web_page_preview=True)
    else:
        await processing_msg.edit_text(
            text=message_text,
            disable_web_page_preview=True
        )
        
