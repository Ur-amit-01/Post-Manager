import os
import asyncio
from typing import Dict
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from config import *
from plugins.Chapters import CHAPTER_DATA
from plugins.Sorting import matcher

# Channel IDs
SOURCE_CHANNEL = -1002027394591  # Main channel to monitor
DESTINATION_CHANNELS = {
    'Physics': -1002611033664,
    'Inorganic Chemistry': -1002530766847,
    'Organic Chemistry': -1002623306070,
    'Physical Chemistry': -1002533864126,
    'Botany': -1002537691102,
    'Zoology': -1002549422245
}

# Track last forwarded message ID
last_forwarded_id = 0
forwarding_active = False

async def get_new_messages(client: Client):
    """Fetch new messages since last forwarded ID"""
    global last_forwarded_id
    
    messages = []
    async for message in client.get_chat_history(SOURCE_CHANNEL):
        if message.id <= last_forwarded_id:
            break
        messages.append(message)
    
    # Reverse to process in chronological order (oldest first)
    return messages[::-1]

async def forward_messages(client: Client, messages: list):
    """Forward messages to their respective channels"""
    global last_forwarded_id, forwarding_active
    
    forwarding_active = True
    forwarded_count = 0
    
    for message in messages:
        text = message.text or message.caption or ""
        subject = matcher.find_subject(text)
        
        if subject and subject in DESTINATION_CHANNELS:
            dest_channel = DESTINATION_CHANNELS[subject]
            try:
                if message.text:
                    await message.copy(dest_channel)
                elif message.media:
                    await message.copy(
                        dest_channel,
                        caption=message.caption,
                        caption_entities=message.caption_entities
                    )
                
                # Update last forwarded ID
                if message.id > last_forwarded_id:
                    last_forwarded_id = message.id
                
                forwarded_count += 1
                print(f"Forwarded message {message.id} to {subject}")
                
            except Exception as e:
                print(f"Error forwarding message {message.id}: {str(e)}")
    
    forwarding_active = False
    return forwarded_count

@Client.on_message(filters.private & filters.command("forward"))
async def handle_forward_command(client: Client, message: Message):
    """Handle /forward command in DM"""
    if message.from_user.id != YOUR_USER_ID:  # Replace with your user ID
        return await message.reply("❌ You're not authorized to use this command.")
    
    if forwarding_active:
        return await message.reply("⏳ Forwarding is already in progress. Please wait.")
    
    await message.reply("⏳ Fetching new messages...")
    new_messages = await get_new_messages(client)
    
    if not new_messages:
        return await message.reply("⚠️ No new messages to forward since last time.")
    
    await message.reply(f"⏳ Forwarding {len(new_messages)} new messages...")
    total_forwarded = await forward_messages(client, new_messages)
    
    await message.reply(f"✅ Successfully forwarded {total_forwarded} messages!")
    print(f"Last forwarded message ID is now: {last_forwarded_id}")

# Optional: Save/load last_forwarded_id to persist across restarts
"""async def save_last_id():
    """Save last forwarded ID to file"""
    with open("last_id.txt", "w") as f:
        f.write(str(last_forwarded_id))

async def load_last_id():
    """Load last forwarded ID from file"""
    global last_forwarded_id
    try:
        with open("last_id.txt", "r") as f:
            last_forwarded_id = int(f.read())
    except (FileNotFoundError, ValueError):
        last_forwarded_id = 0

# Load last ID when starting
async def startup():
    await load_last_id()
    print(f"Loaded last forwarded ID: {last_forwarded_id}")

# Run startup when bot initializes
if __name__ == "__main__":
    app = Client("my_bot")
    app.run(startup())"""
