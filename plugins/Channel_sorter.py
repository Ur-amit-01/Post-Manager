import os
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *

# Load chapter data (from previous extraction)
CHAPTER_DATA = {
    'Physics': ['Basic Maths & Calculus', 'Units and Measurements', 'Vectors', 'Motion in a straight line', ...],
    'Inorganic Chemistry': ['Classification of Elements and Periodicity in Properties', 'Chemical Bonding and Molecular Structure', ...],
    'Organic Chemistry': ['Organic Chemistry: Some Basic principles and Techniques', 'Hydrocarbon', ...],
    'Physical Chemistry': ['Some Basic Concept of Chemistry', 'Redox Reaction', ...],
    'Botany': ['Cell - The Unit of Life', 'Cell Cycle and Cell Division', ...],
    'Zoology': ['Structural Organization in Animals', 'Breathing and Exchange of Gases', ...]
}

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
    """Identify which subject the message belongs to based on chapter names"""
    text_lower = text.lower()
    for subject, chapters in CHAPTER_DATA.items():
        for chapter in chapters:
            if chapter.lower() in text_lower:
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
                # Forward the message to the appropriate channel
                await message.forward(dest_channel)
                print(f"Forwarded message to {subject} channel")
            except Exception as e:
                print(f"Error forwarding message: {e}")
        else:
            print(f"No destination channel for subject: {subject}")
    else:
        print("No matching subject found for message")
