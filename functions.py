import os
import asyncio
from typing import Dict, List
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

# Store messages in order for each subject
message_queue: Dict[str, List[Message]] = {subject: [] for subject in DESTINATION_CHANNELS.keys()}
forwarding_active = False
last_forwarded_id = 0  # Track last forwarded message ID

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

async def forward_queued_messages(client: Client):
    """Forward all queued messages in correct order"""
    global forwarding_active, last_forwarded_id
    
    forwarding_active = True
    total_forwarded = 0
    
    for subject, messages in message_queue.items():
        if messages and subject in DESTINATION_CHANNELS:
            dest_channel = DESTINATION_CHANNELS[subject]
            try:
                # Forward messages in chronological order
                for message in messages:
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
                
                total_forwarded += len(messages)
                print(f"Forwarded {len(messages)} messages to {subject} channel")
                
                # Send confirmation
                await client.send_message(
                    dest_channel,
                    f"✅ {len(messages)} messages have been forwarded in sequence.",
                    parse_mode=enums.ParseMode.MARKDOWN
                )
                
            except Exception as e:
                print(f"Error forwarding to {subject}: {str(e)}")
    
    # Clear all queues after forwarding
    for subject in message_queue:
        message_queue[subject].clear()
    
    forwarding_active = False
    return total_forwarded

@Client.on_message(filters.chat(SOURCE_CHANNEL) & ~filters.command("forward"))
async def queue_content(client: Client, message: Message):
    """Queue messages when they arrive in source channel"""
    if forwarding_active:
        return
        
    text = message.text or message.caption or ""
    subject = matcher.find_subject(text)
    
    if subject and subject in message_queue:
        message_queue[subject].append(message)
        print(f"Queued message for {subject} (Total: {len(message_queue[subject])})")

@Client.on_message(filters.private & filters.command("forward"))
async def start_forwarding(client: Client, message: Message):
    """Handle /forward command in DM"""
    if message.from_user.id != YOUR_USER_ID:  # Replace with your user ID
        return await message.reply("❌ You're not authorized to use this command.")
    
    # First check if there are queued messages
    total_queued = sum(len(q) for q in message_queue.values())
    
    if total_queued == 0:
        # No queued messages, fetch new ones since last forwarded ID
        await message.reply("⏳ Fetching new messages since last forward...")
        new_messages = await get_new_messages(client)
        
        if not new_messages:
            return await message.reply("⚠️ No new messages to forward.")
            
        # Queue the new messages
        for msg in new_messages:
            text = msg.text or msg.caption or ""
            subject = matcher.find_subject(text)
            if subject and subject in message_queue:
                message_queue[subject].append(msg)
        
        total_queued = sum(len(q) for q in message_queue.values())
    
    await message.reply(f"⏳ Starting to forward {total_queued} messages...")
    total_forwarded = await forward_queued_messages(client)
    await message.reply(f"✅ {total_forwarded} messages forwarded successfully!")

async def check_queue_status():
    """Periodically check queue status"""
    while True:
        await asyncio.sleep(3600)  # Check every hour
        total = sum(len(q) for q in message_queue.values())
        if total > 0:
            print(f"Queue status: {total} messages waiting to be forwarded")
            print(f"Last forwarded message ID: {last_forwarded_id}")

