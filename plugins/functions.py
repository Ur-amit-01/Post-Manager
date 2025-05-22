import os
import asyncio
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

# Track forwarded messages for confirmation
forwarded_messages = {channel: set() for channel in DESTINATION_CHANNELS.values()}

async def send_confirmation(client: Client, channel_id: int, count: int):
    """Send confirmation message to destination channel"""
    await client.send_message(
        channel_id,
        f"✅ {count} messages have been automatically sorted to this channel.",
        parse_mode=enums.ParseMode.MARKDOWN
    )
    forwarded_messages[channel_id].clear()

@Client.on_message(filters.chat(SOURCE_CHANNEL))
async def sort_content(client: Client, message: Message):
    text = message.text or message.caption or ""
    subject = matcher.find_subject(text)
    
    if subject and subject in DESTINATION_CHANNELS:
        dest_channel = DESTINATION_CHANNELS[subject]
        try:
            # Copy the message while preserving formatting
            if message.text:
                await client.send_message(
                    dest_channel,
                    text=message.text,
                    entities=message.entities
                )
            elif message.photo:
                await client.send_photo(
                    dest_channel,
                    photo=message.photo.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.document:
                await client.send_document(
                    dest_channel,
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.video:
                await client.send_video(
                    dest_channel,
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            
            forwarded_messages[dest_channel].add(message.id)
            print(f"Copied message {message.id} to {subject} channel")
            
            # Send confirmation if first message of batch
            if len(forwarded_messages[dest_channel]) == 1:
                await send_confirmation(client, dest_channel, 1)
                
        except Exception as e:
            print(f"Error copying message {message.id}: {str(e)}")

async def daily_summary(client: Client):
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 hours
        for channel_id, msg_ids in forwarded_messages.items():
            if msg_ids:
                await send_confirmation(client, channel_id, len(msg_ids))

