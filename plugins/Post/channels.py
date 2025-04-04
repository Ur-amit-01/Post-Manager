from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database 
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add") & filters.private & filters.user(ADMIN))
async def add_channels(client, message: Message):
    """
    Add one or more channels to the database
    Usage: /add [-100...] [100...] [...]
    Examples:
    /add -10012345678
    /add 10012345678 10023456789
    """
    # Check if channel IDs were provided
    if len(message.command) < 2:
        return await message.reply(
            "❌ Please provide channel IDs separated by spaces\n"
            "Examples:\n"
            "• `/add -10012345678`\n"
            "• `/add 10012345678 10023456789`"
        )

    processing_msg = await message.reply("⏳ Processing channel IDs...")
    added_channels = []
    existing_channels = []
    invalid_channels = []
    failed_channels = []

    for channel_input in message.command[1:]:  # Skip the "/add" part
        try:
            # Convert to proper channel ID format
            channel_id = int(channel_input)
            if channel_id > 0:  # Convert positive to negative
                channel_id = -abs(channel_id)
            
            # Validate channel ID range
            if not (-1000000000000 < channel_id < -1):
                invalid_channels.append(channel_input)
                continue

            # Try to get channel info (verifies existence and access)
            try:
                chat = await client.get_chat(channel_id)
                channel_name = chat.title
                
                # Check if bot has admin rights
                try:
                    bot_member = await client.get_chat_member(channel_id, "me")
                    if not (bot_member.can_post_messages or bot_member.status == "administrator"):
                        failed_channels.append(f"{channel_id} (No admin rights)")
                        continue
                except Exception:
                    failed_channels.append(f"{channel_id} (Access denied)")
                    continue

                # Add to database
                if await db.add_channel(channel_id, channel_name):
                    added_channels.append(f"{channel_name} (`{channel_id}`)")
                else:
                    existing_channels.append(f"{channel_name} (`{channel_id}`)")
                    
            except Exception as e:
                failed_channels.append(f"{channel_id} (Error: {str(e)})")
                continue
                
        except ValueError:
            invalid_channels.append(channel_input)

    # Prepare response message
    response = ["**Channel Addition Results**"]
    
    if added_channels:
        response.append("\n✅ **Successfully Added:**")
        response.extend(f"• {ch}" for ch in added_channels[:10])  # Show first 10
        if len(added_channels) > 10:
            response.append(f"• ...and {len(added_channels)-10} more")

    if existing_channels:
        response.append("\nℹ️ **Already Existed:**")
        response.extend(f"• {ch}" for ch in existing_channels[:5])
        if len(existing_channels) > 5:
            response.append(f"• ...and {len(existing_channels)-5} more")

    if invalid_channels:
        response.append("\n❌ **Invalid IDs:**")
        response.append(", ".join(invalid_channels[:10]))
        if len(invalid_channels) > 10:
            response.append(f"(+ {len(invalid_channels)-10} more)")

    if failed_channels:
        response.append("\n⚠️ **Failed to Add:**")
        response.extend(f"• {ch}" for ch in failed_channels[:5])
        if len(failed_channels) > 5:
            response.append(f"• ...and {len(failed_channels)-5} more")

    if not (added_channels or existing_channels or invalid_channels or failed_channels):
        response.append("\nNo valid channel IDs were processed")

    # Edit original processing message
    full_response = "\n".join(response)
    await processing_msg.edit_text(
        text=full_response[:4000],  # Telegram message limit
        disable_web_page_preview=True
    )

    # Log summary to console
    print(
        f"Channel add results:\n"
        f"Added: {len(added_channels)}\n"
        f"Existing: {len(existing_channels)}\n"
        f"Invalid: {len(invalid_channels)}\n"
        f"Failed: {len(failed_channels)}"
    )

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
    
