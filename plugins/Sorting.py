import os
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
from plugins.Chapters import CHAPTER_DATA

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

def find_matching_subject(text):
    """Identify which subject the message belongs to based on chapter keywords"""
    text_lower = text.lower()
    for subject, chapters in CHAPTER_DATA.items():
        for chapter in chapters:
            # Split chapter into words and check if any word matches
            words = re.split(r'\W+', chapter.lower())
            if any(word in text_lower for word in words if len(word) > 3):  # Only consider words longer than 3 chars
                return subject
    return None

@Client.on_message(filters.chat(SOURCE_CHANNEL))
async def sort_content(client: Client, message: Message):
    # Get message text (including captions for media)
    text = message.text or message.caption or ""
    
    # Find matching subject
    subject = find_matching_subject(text)
    
    if subject:
        dest_channel = DESTINATION_CHANNELS.get(subject)
        if dest_channel:
            try:
                # Copy the message (instead of forwarding) to preserve formatting
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
                # Add more media types as needed
                
                print(f"Copied message to {subject} channel")
            except Exception as e:
                print(f"Error copying message: {e}")
        else:
            print(f"No destination channel for subject: {subject}")
    else:
        print("No matching subject found for message")
