
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
    text_words = set(re.findall(r'\w{4,}', text_lower))  # Get all words with 4+ chars
    
    best_match = None
    best_score = 0
    
    for subject, chapters in CHAPTER_DATA.items():
        for chapter in chapters:
            # Get all meaningful words from chapter name (4+ chars)
            chapter_words = set(re.findall(r'\w{4,}', chapter.lower()))
            
            # Count how many chapter words appear in message
            matches = len(chapter_words & text_words)
            
            # Require at least 2 matching words (or 1 if chapter has only 1 word)
            min_required = min(2, len(chapter_words))
            
            if matches >= min_required and matches > best_score:
                best_score = matches
                best_match = subject
    
    return best_match

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
                
                print(f"Copied message to {subject} channel (matched {best_score} words)")
            except Exception as e:
                print(f"Error copying message: {e}")
        else:
            print(f"No destination channel for subject: {subject}")
    else:
        print("No matching subject found for message")
